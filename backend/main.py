"""
Main Application Controller for KhetRakshak AI-Powered Crop & Monkey Deterrence System.

Orchestrates complete monitoring loop:
1. Loads configuration and logging.
2. Connects to Supabase, Arduino, and YOLOv8 Detector.
3. Opens USB Camera feed.
4. Performs real-time frame inference.
5. Handles threat responses (hardware alarms, cloud logging, Telegram alerts) resiliently.
6. Supports graceful shutdown via Ctrl+C / SIGINT signals.
"""

import os
import sys
import time
import signal
import cv2
from datetime import datetime
from typing import Optional, Dict, Any

# Adjust sys.path to resolve root and package level imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------------------
# 1. Imports from Core Modules
# ------------------------------------------------------------------------------
from app.utils.logger import get_logger
from app.utils.exceptions import AppError

# Config Module
try:
    from config import Config, config as app_config
except ImportError:
    from app.config.config import Config
    app_config = Config()

# Supabase Service
try:
    from supabase_service import SupabaseService, supabase_service
except ImportError:
    from app.services.supabase_service import SupabaseService, supabase_service

# Arduino Service
try:
    from arduino import ArduinoController, arduino_controller
except ImportError:
    from app.services.arduino_service import ArduinoController, arduino_controller

# Telegram Service
try:
    from telegram import TelegramService, telegram_service
except ImportError:
    from app.services.telegram_service import TelegramService, telegram_service

# Detector Service
try:
    from detector import MonkeyDetector, detector
except ImportError:
    from app.services.detector_service import MonkeyDetector, detector

logger = get_logger("KhetRakshakMain")


class KhetRakshakApp:
    """
    Main Orchestrator Application Class.
    Follows Clean Architecture and Dependency Injection design principles.
    """

    def __init__(
        self,
        config_obj: Optional[Config] = None,
        db_service: Optional[SupabaseService] = None,
        serial_service: Optional[ArduinoController] = None,
        alert_service: Optional[TelegramService] = None,
        ai_detector: Optional[MonkeyDetector] = None
    ) -> None:
        """
        Injects dependencies or uses default global singletons.
        """
        self.config = config_obj or app_config
        self.db = db_service or supabase_service
        self.arduino = serial_service or arduino_controller
        self.telegram = alert_service or telegram_service
        self.detector = ai_detector or detector

        self.device_id: str = "DEV_KHET_01"
        self.farmer_id: str = "FARMER_01"
        self.running: bool = True
        self.camera_cap: Optional[cv2.VideoCapture] = None

    def initialize_system(self) -> None:
        """
        Initializes logging, hardware connections, cloud databases, and AI models.
        """
        logger.info("==================================================")
        logger.info("Initializing KhetRakshak AI System...")
        logger.info("==================================================")

        # 1. Register signal handlers for graceful exit
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)

        # 2. Check Supabase database connectivity
        try:
            logger.info("Checking Supabase connection...")
            # Fire initial system log
            self.db.insert_system_log(
                log_level="INFO",
                module="MainApp",
                message="KhetRakshak system starting up."
            )
        except Exception as e:
            logger.error(f"Supabase connection warning (non-fatal): {e}")

        # 3. Connect Arduino Hardware
        try:
            logger.info("Connecting to Arduino serial board...")
            if not self.arduino.connect():
                logger.warning("Arduino serial connection pending/failed. Retrying in loop.")
        except Exception as e:
            logger.error(f"Arduino connection warning (non-fatal): {e}")

        # 4. Load YOLO AI Model
        try:
            logger.info("Verifying YOLOv8 model loading...")
            if not self.detector.model:
                self.detector.load_model()
        except Exception as e:
            logger.error(f"YOLO detector loading warning (non-fatal): {e}")

        # 5. Initialize Camera Hardware
        cam_idx = getattr(self.config, "CAMERA_INDEX", 1)
        logger.info(f"Opening camera feed on index {cam_idx}...")
        self.camera_cap = cv2.VideoCapture(cam_idx)
        if not self.camera_cap.isOpened():
            logger.error(f"Failed to open video capture on camera index {cam_idx}.")
        else:
            logger.info("Camera initialized successfully.")

    def _handle_shutdown_signal(self, signum: int, frame: Any) -> None:
        """Handles SIGINT / SIGTERM for clean shutdown."""
        logger.info("Shutdown signal received. Exiting loop safely...")
        self.running = False

    def handle_safe_state(self) -> None:
        """
        Executes logic when NO threat/monkey is detected.
        """
        try:
            # Update device status in Supabase
            self.db.update_device_status(
                device_id=self.device_id,
                status="SAFE",
                speaker_status="off",
                light_status="off"
            )
        except Exception as e:
            logger.error(f"Error updating SAFE status to database: {e}")

    def handle_threat_detected(self, frame: cv2.Mat, detection_info: Dict[str, Any]) -> None:
        """
        Executes complete multi-step deterrence and notification pipeline upon monkey detection.
        """
        animal_label = detection_info.get("animal", "Monkey")
        conf = detection_info.get("confidence", 0.0)
        logger.warning(f"🚨 THREAT DETECTED: {animal_label} (Confidence: {conf}%)")

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_filename = f"snapshots/detection_{timestamp_str}.jpg"
        public_image_url: Optional[str] = None

        # 1. Save Detection Snapshot Locally
        try:
            snapshot_filename = self.detector.save_detection_image(
                frame=frame,
                output_path=snapshot_filename,
                detection_result=detection_info
            )
        except Exception as e:
            logger.error(f"Failed to save local detection snapshot: {e}")

        # 2. Upload Image to Supabase Storage
        try:
            if os.path.exists(snapshot_filename):
                public_image_url = self.db.upload_detection_image(snapshot_filename)
        except Exception as e:
            logger.error(f"Failed to upload detection snapshot to Supabase: {e}")

        # 3. Insert Record into Detections Table
        try:
            self.db.insert_detection(
                device_id=self.device_id,
                object_class=animal_label,
                confidence=conf,
                image_url=public_image_url,
                metadata={"detection_info": detection_info}
            )
        except Exception as e:
            logger.error(f"Failed to insert detection into Supabase: {e}")

        # 4. Update Device Status to ALERT
        try:
            self.db.update_device_status(
                device_id=self.device_id,
                status="ALERT",
                speaker_status="on",
                light_status="on"
            )
        except Exception as e:
            logger.error(f"Failed to update device status to ALERT: {e}")

        # 5. Activate Arduino Speaker
        try:
            self.arduino.speaker_on()
        except Exception as e:
            logger.error(f"Failed to activate Arduino speaker: {e}")

        # 6. Activate Arduino Flash Light
        try:
            self.arduino.flash_on()
        except Exception as e:
            logger.error(f"Failed to activate Arduino flash light: {e}")

        # 7. Insert Speaker Playback Log
        try:
            self.db.insert_speaker_log(
                device_id=self.device_id,
                sound_played="ultrasonic_deterrent_freq1.mp3",
                duration_seconds=5,
                triggered_by="automatic_yolo_detection"
            )
        except Exception as e:
            logger.error(f"Failed to insert speaker log: {e}")

        # 8. Insert System Event Log
        try:
            self.db.insert_system_log(
                log_level="WARNING",
                module="DeterrencePipeline",
                message=f"Triggered deterrence for detected {animal_label} ({conf}%)"
            )
        except Exception as e:
            logger.error(f"Failed to insert system event log: {e}")

        # 9. Read Farmer Contact Information
        try:
            farmer_data = self.db.get_farmer(self.farmer_id)
        except Exception as e:
            logger.error(f"Failed to retrieve farmer information: {e}")
            farmer_data = None

        # 10. Send Telegram Detection Alert
        telegram_sent = False
        try:
            result = self.telegram.send_detection_alert(
                camera_name=f"Camera-{getattr(self.config, 'CAMERA_INDEX', 1)}",
                zone=self.device_id,
                confidence=conf,
                image_path_or_url=public_image_url or snapshot_filename,
                device_status="ALERT",
                speaker_activated=True,
                flash_activated=True
            )
            telegram_sent = result.get("success", False)
            if telegram_sent:
                logger.info("Telegram detection alert delivered successfully.")
            else:
                logger.warning(f"Telegram alert delivery failed: {result.get('error')}")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")

        # 11. Insert Notification Log
        try:
            self.db.insert_notification(
                farmer_id=self.farmer_id,
                title=f"Monkey Alert - {animal_label}",
                message=f"Monkey detected: {animal_label} ({conf}%) at {self.device_id}",
                channel="telegram",
                status="sent" if telegram_sent else "failed"
            )
        except Exception as e:
            logger.error(f"Failed to insert notification log: {e}")

        # 12. Update Analytics
        try:
            self.db.insert_system_log(
                log_level="INFO",
                module="Analytics",
                message=f"Analytics increment: {animal_label} threat logged."
            )
        except Exception as e:
            logger.error(f"Failed to record analytics update: {e}")

    def run(self) -> None:
        """
        Main execution loop for continuous video frame detection.
        """
        self.initialize_system()

        logger.info("==================================================")
        logger.info("Starting continuous KhetRakshak monitoring loop...")
        logger.info("Press Ctrl+C to stop.")
        logger.info("==================================================")

        while self.running:
            try:
                if not self.camera_cap or not self.camera_cap.isOpened():
                    logger.warning("Camera connection unavailable. Re-attempting connection...")
                    cam_idx = getattr(self.config, "CAMERA_INDEX", 1)
                    self.camera_cap = cv2.VideoCapture(cam_idx)
                    time.sleep(2.0)
                    continue

                ret, frame = self.camera_cap.read()
                if not ret or frame is None:
                    logger.warning("Failed to grab camera frame. Retrying...")
                    time.sleep(0.5)
                    continue

                # Run Object Detection on captured frame
                detection_result = self.detector.predict_frame(frame)

                if detection_result.get("detected", False):
                    # Threat Detected -> Run Full Deterrence Pipeline
                    self.handle_threat_detected(frame, detection_result)
                else:
                    # No Threat -> Maintain Safe State
                    self.handle_safe_state()

                # Short delay to limit CPU overuse in loop
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in main processing loop: {e}", exc_info=True)
                time.sleep(1.0) # Prevent rapid exception spinning

        self.cleanup()

    def cleanup(self) -> None:
        """
        Performs safe shutdown cleanup.
        """
        logger.info("Cleaning up resources...")
        if self.camera_cap and self.camera_cap.isOpened():
            self.camera_cap.release()
            logger.info("Camera video capture released.")

        try:
            self.arduino.speaker_off()
            self.arduino.flash_off()
            self.arduino.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting Arduino: {e}")

        logger.info("KhetRakshak system shut down cleanly.")


# ------------------------------------------------------------------------------
# 2. FastAPI Application Instance Export
# ------------------------------------------------------------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.api import router as api_router

app = FastAPI(
    title="KhetRakshak Backend API",
    description="AI-Powered Crop & Monkey Defense Control System Backend",
    version="1.0.0"
)

# Enable CORS for Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    print("Starting KhetRakshak FastAPI Server on http://localhost:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

