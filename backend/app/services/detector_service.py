"""
YOLOv8 Computer Vision Detection Module for KhetRakshak Backend.

Provides a clean wrapper interface around Ultralytics YOLOv8 for detecting monkeys
or animals in video frames, static image files, or live camera feeds.
"""

import os
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from app.utils.logger import get_logger
from app.utils.exceptions import AppError

# Try loading Ultralytics YOLO
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    YOLO = None

# Import configuration
try:
    from app.config.config import Config
    _cfg = Config()
    MODEL_PATH = getattr(_cfg, "YOLO_MODEL_PATH", "models/best.pt")
    CAMERA_INDEX = getattr(_cfg, "CAMERA_INDEX", 1)
    CONF_THRESHOLD = getattr(_cfg, "CONFIDENCE_THRESHOLD", 0.5)
except Exception:
    from app.config.settings import settings
    MODEL_PATH = getattr(settings, "YOLO_MODEL_PATH", "models/best.pt")
    CAMERA_INDEX = 1
    CONF_THRESHOLD = 0.5

logger = get_logger(__name__)


class MonkeyDetector:
    """
    Wrapper class for YOLOv8 model inference on frames, images, and live camera streams.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = CONF_THRESHOLD
    ) -> None:
        """
        Initializes the MonkeyDetector instance.

        Args:
            model_path (Optional[str]): Path to trained YOLO model weights (.pt).
            conf_threshold (float): Confidence threshold for detections (0.0 - 1.0).
        """
        self.model_path: str = model_path or MODEL_PATH
        self.conf_threshold: float = conf_threshold
        self.model: Optional[Any] = None

        # Load the model upon initialization
        self.load_model()

    def load_model(self) -> bool:
        """
        Loads the YOLOv8 model weights into memory.

        Returns:
            bool: True if model loaded successfully, False otherwise.
        """
        if not YOLO_AVAILABLE:
            logger.error("Ultralytics library is not installed. Run 'pip install ultralytics'.")
            return False

        if not os.path.exists(self.model_path):
            logger.warning(
                f"Model file not found at path '{self.model_path}'. "
                f"Attempting fallback to default 'yolov8n.pt'..."
            )
            self.model_path = "yolov8n.pt"

        try:
            logger.info(f"Loading YOLOv8 model from: '{self.model_path}'...")
            self.model = YOLO(self.model_path)
            logger.info("YOLOv8 model loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model from '{self.model_path}': {e}")
            self.model = None
            return False

    def predict_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Performs object detection on a single OpenCV BGR frame.

        Args:
            frame (np.ndarray): Image frame matrix.

        Returns:
            Dict[str, Any]: Structured detection metadata.
        """
        timestamp = datetime.now().isoformat()

        if frame is None or frame.size == 0:
            logger.error("Empty or invalid image frame passed to predict_frame.")
            return {
                "detected": False,
                "animal": None,
                "confidence": 0.0,
                "bounding_box": [],
                "image_path": None,
                "timestamp": timestamp,
                "detections_count": 0,
                "all_detections": []
            }

        if not self.model:
            logger.warning("YOLO model not loaded. Attempting re-load...")
            if not self.load_model():
                raise AppError("YOLO model unavailable for inference.", status_code=500)

        try:
            results = self.model(frame, conf=self.conf_threshold, verbose=False)
            all_detections = []
            highest_conf = 0.0
            primary_label = None
            primary_bbox = []

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    conf = float(box.conf[0]) * 100.0
                    cls_id = int(box.cls[0])
                    class_name = self.model.names.get(cls_id, f"class_{cls_id}")
                    bbox = [float(x) for x in box.xyxy[0].tolist()]

                    detection_item = {
                        "class_name": class_name,
                        "confidence": round(conf, 2),
                        "bounding_box": [round(b, 2) for b in bbox]
                    }
                    all_detections.append(detection_item)

                    if conf > highest_conf:
                        highest_conf = conf
                        primary_label = class_name
                        primary_bbox = [round(b, 2) for b in bbox]

            is_detected = len(all_detections) > 0

            return {
                "detected": is_detected,
                "animal": primary_label or ("Monkey" if is_detected else None),
                "confidence": round(highest_conf, 2),
                "bounding_box": primary_bbox,
                "image_path": None,
                "timestamp": timestamp,
                "detections_count": len(all_detections),
                "all_detections": all_detections
            }
        except Exception as e:
            logger.error(f"Inference error during predict_frame: {e}")
            raise AppError(f"Model prediction failed: {e}", status_code=500)

    def predict_image(self, image_path: str) -> Dict[str, Any]:
        """
        Performs object detection on a static image file.

        Args:
            image_path (str): File path to input image.

        Returns:
            Dict[str, Any]: Structured detection metadata.
        """
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: '{image_path}'")
            raise AppError(f"Image not found at path: {image_path}", status_code=404)

        frame = cv2.imread(image_path)
        if frame is None:
            logger.error(f"Failed to read image file: '{image_path}'")
            raise AppError(f"Unable to read image at path: {image_path}", status_code=400)

        result = self.predict_frame(frame)
        result["image_path"] = image_path
        return result

    def predict_camera(self, camera_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Captures a single frame from connected camera hardware and performs detection.

        Args:
            camera_index (Optional[int]): Camera index (defaults to CONFIG CAMERA_INDEX).

        Returns:
            Dict[str, Any]: Structured detection metadata.
        """
        idx = camera_index if camera_index is not None else CAMERA_INDEX
        logger.info(f"Opening camera index {idx}...")
        cap = cv2.VideoCapture(idx)

        if not cap.isOpened():
            logger.error(f"Failed to open video capture device at index {idx}.")
            raise AppError(f"Unable to open camera index {idx}.", status_code=500)

        try:
            ret, frame = cap.read()
            if not ret or frame is None:
                logger.error(f"Failed to capture frame from camera index {idx}.")
                raise AppError(f"Camera frame capture failed on index {idx}.", status_code=500)

            return self.predict_frame(frame)
        finally:
            cap.release()

    def draw_detections(self, frame: np.ndarray, detection_result: Dict[str, Any]) -> np.ndarray:
        """
        Draws bounding box annotations and confidence labels onto a frame copy.

        Args:
            frame (np.ndarray): Original image frame.
            detection_result (Dict[str, Any]): Structured output from predict_frame.

        Returns:
            np.ndarray: Annotated frame copy.
        """
        annotated = frame.copy()
        all_detections = detection_result.get("all_detections", [])

        for det in all_detections:
            bbox = det.get("bounding_box", [])
            label = det.get("class_name", "Detection")
            conf = det.get("confidence", 0.0)

            if len(bbox) == 4:
                xmin, ymin, xmax, ymax = [int(v) for v in bbox]
                cv2.rectangle(annotated, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                caption = f"{label} {conf}%"
                cv2.putText(
                    annotated, caption, (xmin, max(ymin - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
                )

        return annotated

    def save_detection_image(
        self,
        frame: np.ndarray,
        output_path: str,
        detection_result: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Saves the frame (with optional bounding box annotations) to disk.

        Args:
            frame (np.ndarray): Image frame.
            output_path (str): Target output file path.
            detection_result (Optional[Dict[str, Any]]): If provided, draws bounding boxes before saving.

        Returns:
            str: Absolute file path of saved image.
        """
        if detection_result:
            img_to_save = self.draw_detections(frame, detection_result)
        else:
            img_to_save = frame

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        cv2.imwrite(output_path, img_to_save)
        logger.info(f"Saved detection snapshot to: '{output_path}'")
        return os.path.abspath(output_path)


# Global singleton instance
detector = MonkeyDetector()
