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


def generate_mjpeg_stream():
    """Generator function that captures camera frames and yields MJPEG HTTP stream."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.warning("Camera index 0 not available for stream. Serving synthetic frame stream.")
        # Synthetic frame fallback generator
        while True:
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(img, "KhetRakshak Live Feed", (140, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            cv2.putText(img, f"Time: {time.strftime('%H:%M:%S')}", (210, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (183, 227, 111), 2)
            _, encoded = cv2.imencode('.jpg', img)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + encoded.tobytes() + b'\r\n')
            time.sleep(0.1)

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue
            
            # Timestamp overlay
            cv2.putText(frame, f"KhetRakshak LIVE - {time.strftime('%Y-%m-%d %H:%M:%S')}", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            _, encoded = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + encoded.tobytes() + b'\r\n')
            time.sleep(0.04) # ~25 fps
    finally:
        cap.release()


@router.get(
    "/video_feed",
    summary="Live Camera MJPEG Stream",
    tags=["Live Feed"]
)
async def video_feed():
    """Returns a continuous MJPEG video stream from the USB camera for live-monitoring.html."""
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
