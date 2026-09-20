"""
API Router module.
Defines HTTP endpoints for system health checks, detection processing, hardware control, and dashboard metrics.
Follows Clean Architecture by delegating processing to controller layer.
"""
import cv2
import time
import numpy as np
from typing import Optional
from fastapi import APIRouter, status, Query, Body
from fastapi.responses import StreamingResponse
from app.models.schemas import DetectionPayload, DetectionResponse
from app.controllers.detection_controller import detection_controller
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="System Health Check",
    tags=["System"]
)
async def health_check():
    """Returns the operational status of the KhetRakshak backend API."""
    return {
        "status": "online",
        "service": "KhetRakshak Backend API",
        "version": "1.0.0"
    }


@router.post(
    "/detect",
    response_model=DetectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Process Object Detection Event",
    tags=["Detection"]
)
async def handle_detection(payload: DetectionPayload):
    """Receives detection data payloads and hands them off to the DetectionController."""
    return await detection_controller.process_detection(payload)


@router.get(
    "/dashboard/summary",
    status_code=status.HTTP_200_OK,
    summary="Get Dashboard Summary Metrics",
    tags=["Dashboard"]
)
async def get_dashboard_summary():
    """Returns real-time aggregated metrics for the frontend dashboard overview cards."""
    return detection_controller.get_dashboard_summary()


@router.get(
    "/detections",
    status_code=status.HTTP_200_OK,
    summary="Get Detection History Records",
    tags=["Detection"]
)
async def get_detections(limit: int = Query(default=50, ge=1, le=200)):
    """Returns historical detection event logs."""
    return detection_controller.get_detections_history(limit=limit)


@router.get(
    "/speakers",
    status_code=status.HTTP_200_OK,
    summary="Get Speaker Hardware Status",
    tags=["Hardware"]
)
async def get_speakers():
    """Returns the operational status and list of deterrence speakers."""
    return detection_controller.get_speaker_status()


@router.post(
    "/speakers/control",
    status_code=status.HTTP_200_OK,
    summary="Manual Speaker Override Control",
    tags=["Hardware"]
)
async def control_speaker(action: str = Query(..., description="'ON' or 'OFF'")):
    """Manually activates or deactivates the Arduino deterrence speaker."""
    return detection_controller.trigger_speaker(action=action)


@router.post(
    "/lights/control",
    status_code=status.HTTP_200_OK,
    summary="Manual Flash Light Override Control",
    tags=["Hardware"]
)
async def control_light(action: str = Query(..., description="'ON' or 'OFF'")):
    """Manually activates or deactivates the Arduino flash light."""
    return detection_controller.trigger_light(action=action)


@router.get(
    "/notifications",
    status_code=status.HTTP_200_OK,
    summary="Get Notification History Logs",
    tags=["Notifications"]
)
async def get_notifications(limit: int = Query(default=50, ge=1, le=200)):
    """Returns logs of sent Telegram and system alerts."""
    return detection_controller.get_notifications(limit=limit)


@router.get(
    "/analytics",
    status_code=status.HTTP_200_OK,
    summary="Get Analytics Metrics",
    tags=["Analytics"]
)
async def get_analytics():
    """Returns historical metrics for Chart.js graphics."""
    return detection_controller.get_analytics()


import threading
from typing import Optional, Dict, Any


class CameraStreamManager:
    """
    Thread-safe camera stream manager for multi-camera streaming (e.g. Index 0: Laptop, Index 1: Webcam).
    Maintains one capture thread per physical camera to eliminate resource contention and device locking.
    Provides high-definition frames (1280x720) with optimal JPEG encoding quality for clear, non-blurry output.
    """
    def __init__(self):
        self._threads: Dict[int, threading.Thread] = {}
        self._locks: Dict[int, threading.Lock] = {}
        self._latest_jpeg: Dict[int, bytes] = {}
        self._online_status: Dict[int, bool] = {}
        self._stop_events: Dict[int, threading.Event] = {}
        self._init_lock = threading.Lock()

    def _create_standby_frame(self, camera_id: int) -> bytes:
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        img[:] = (24, 28, 26)  # Dark slate background matching UI

        cam_label = "Laptop Integrated Camera (Index 0)" if camera_id == 0 else "External USB Webcam (Index 1)"
        cv2.putText(img, f"CAM-0{camera_id + 1} - {cam_label}", (60, 320), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, "Status: Standby / Waiting for connection...", (60, 375), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (120, 180, 150), 2, cv2.LINE_AA)
        cv2.putText(img, f"Bagmati Monitoring Grid - {time.strftime('%Y-%m-%d %H:%M:%S')}", (60, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (160, 165, 160), 1, cv2.LINE_AA)

        _, encoded = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return encoded.tobytes()

    def _worker(self, camera_id: int):
        logger.info(f"Starting dedicated camera worker for camera index {camera_id}")
        cap = None
        consecutive_errors = 0

        while not self._stop_events[camera_id].is_set():
            if cap is None or not cap.isOpened():
                try:
                    # Prefer DirectShow on Windows with fast initialization
                    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                    if not cap.isOpened():
                        cap = cv2.VideoCapture(camera_id)
                except Exception as e:
                    logger.debug(f"Camera {camera_id} capture init exception: {e}")
                    cap = None

                if cap and cap.isOpened():
                    try:
                        # Set MJPG FOURCC for Windows DirectShow HD compatibility
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                    except Exception:
                        pass
                    try:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    except Exception:
                        pass
                    try:
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    except Exception:
                        pass

                    self._online_status[camera_id] = True
                    consecutive_errors = 0
                    logger.info(f"Camera index {camera_id} connected successfully.")
                else:
                    self._online_status[camera_id] = False
                    standby = self._create_standby_frame(camera_id)
                    with self._locks[camera_id]:
                        self._latest_jpeg[camera_id] = standby
                    time.sleep(1.2)
                    continue

            try:
                ret, frame = cap.read()
            except Exception as read_err:
                ret, frame = False, None
                logger.debug(f"Frame read exception on camera {camera_id}: {read_err}")

            if not ret or frame is None:
                consecutive_errors += 1
                if consecutive_errors > 8:
                    logger.warning(f"Camera {camera_id} consecutive read failures ({consecutive_errors}). Re-initializing...")
                    if cap:
                        try:
                            cap.release()
                        except Exception:
                            pass
                    cap = None
                    self._online_status[camera_id] = False
                    consecutive_errors = 0
                time.sleep(0.08)
                continue

            consecutive_errors = 0
            self._online_status[camera_id] = True

            cam_name = "CAM-01 (Laptop)" if camera_id == 0 else "CAM-02 (Webcam)"
            cv2.putText(
                frame,
                f"{cam_name} LIVE  |  {time.strftime('%Y-%m-%d %H:%M:%S')}",
                (18, 38),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 128),
                2,
                cv2.LINE_AA
            )

            _, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            with self._locks[camera_id]:
                self._latest_jpeg[camera_id] = encoded.tobytes()

            time.sleep(0.033)  # ~30 fps

        if cap and cap.isOpened():
            try:
                cap.release()
            except Exception:
                pass

    def ensure_camera(self, camera_id: int):
        with self._init_lock:
            if camera_id not in self._threads or not self._threads[camera_id].is_alive():
                self._locks[camera_id] = threading.Lock()
                self._stop_events[camera_id] = threading.Event()
                self._online_status[camera_id] = False
                self._latest_jpeg[camera_id] = self._create_standby_frame(camera_id)

                t = threading.Thread(
                    target=self._worker,
                    args=(camera_id,),
                    daemon=True,
                    name=f"CameraWorker_{camera_id}"
                )
                self._threads[camera_id] = t
                t.start()

    def get_jpeg_frame(self, camera_id: int) -> bytes:
        self.ensure_camera(camera_id)
        with self._locks.get(camera_id, self._init_lock):
            return self._latest_jpeg.get(camera_id, self._create_standby_frame(camera_id))

    def get_status(self) -> Dict[str, Any]:
        return {
            "cameras": [
                {
                    "id": 0,
                    "name": "CAM-01 (Laptop Camera)",
                    "type": "Integrated",
                    "online": self._online_status.get(0, False)
                },
                {
                    "id": 1,
                    "name": "CAM-02 (USB Webcam)",
                    "type": "External",
                    "online": self._online_status.get(1, False)
                }
            ],
            "total": 2,
            "online_count": sum(1 for v in [self._online_status.get(0, False), self._online_status.get(1, False)] if v)
        }


camera_stream_manager = CameraStreamManager()


def generate_camera_stream(camera_id: int = 0):
    """Generator function that yields MJPEG HTTP stream from the requested camera."""
    camera_stream_manager.ensure_camera(camera_id)
    while True:
        frame_bytes = camera_stream_manager.get_jpeg_frame(camera_id)
        if frame_bytes:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)


@router.get(
    "/video_feed",
    summary="Live Camera MJPEG Stream",
    tags=["Live Feed"]
)
async def video_feed(camera_id: int = Query(default=0, ge=0, le=5)):
    """Returns a continuous MJPEG video stream from the specified camera index (0=Laptop, 1=Webcam)."""
    return StreamingResponse(
        generate_camera_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get(
    "/video_feed/{camera_id}",
    summary="Live Camera MJPEG Stream by ID",
    tags=["Live Feed"]
)
async def video_feed_by_id(camera_id: int):
    """Returns a continuous MJPEG video stream from the specified camera ID."""
    return StreamingResponse(
        generate_camera_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get(
    "/cameras/status",
    summary="Get Camera Operational Status",
    tags=["Live Feed"]
)
async def get_cameras_status():
    """Returns operational online/offline status of configured cameras."""
    return camera_stream_manager.get_status()
