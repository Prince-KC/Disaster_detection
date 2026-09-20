"""
API Router module.
Defines HTTP endpoints for system health checks, detection processing, hardware control, and dashboard metrics.
Integrates disaster detection model (YOLO) with Telegram alerts, debouncing, and live annotated MJPEG streams.
"""
import cv2
import os
import time
import threading
import datetime
import numpy as np
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, status, Query, Body
from fastapi.responses import StreamingResponse
from app.utils.logger import get_logger

# Load env vars (.env file at project root)
from dotenv import load_dotenv
load_dotenv()

logger = get_logger(__name__)
router = APIRouter()

# ============================================================================
# Disaster Detection Model — loaded ONCE at module startup
# ============================================================================
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

_disaster_model = None
_disaster_class_names: Dict[int, str] = {}
CONF_THRES           = float(os.getenv("CONFIDENCE_THRESHOLD", "0.40"))
DETECT_EVERY         = 3     # run YOLO every Nth frame
DEBOUNCE_FRAMES      = 3     # consecutive positives needed before alert fires
SMS_COOLDOWN_SECONDS = 15    # minimum seconds between Telegram alerts per camera

# Resolve model path: try detection_model/my_model/best.pt relative to project root
_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", ".."))

_MODEL_CANDIDATES = [
    os.path.join(_PROJECT_ROOT, "detection_model", "my_model", "best.pt"),
    os.path.join(_PROJECT_ROOT, "detection_model", "my_model", "my_model.pt"),
    os.path.join(_PROJECT_ROOT, "backend", "models", "best.pt"),
    os.getenv("MODEL_PATH", ""),
]


def _load_disaster_model() -> None:
    global _disaster_model, _disaster_class_names
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("ultralytics not installed — disaster detection disabled.")
        return

    model_path = None
    for candidate in _MODEL_CANDIDATES:
        if candidate and os.path.exists(candidate):
            model_path = candidate
            break

    if not model_path:
        logger.warning(
            f"Disaster model not found. Searched: {_MODEL_CANDIDATES}. "
            "Video feed will stream without AI inference."
        )
        return

    try:
        logger.info(f"Loading disaster detection model from: {model_path}")
        _disaster_model = YOLO(model_path)
        names = getattr(_disaster_model, "names", {})
        if isinstance(names, list):
            _disaster_class_names = {i: n for i, n in enumerate(names)}
        elif isinstance(names, dict):
            _disaster_class_names = {int(k): str(v) for k, v in names.items()}
        logger.info(f"Disaster model loaded. Classes: {_disaster_class_names}")
    except Exception as exc:
        logger.error(f"Failed to load disaster model: {exc}")
        _disaster_model = None


_load_disaster_model()

# Global inference lock — prevents two camera threads from running YOLO simultaneously
_inference_lock = threading.Lock()

# ============================================================================
# Telegram Alert Helper
# ============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "").strip()

DISASTER_DISPLAY: Dict[str, tuple] = {
    "flood":         ("🌊", "FLOOD"),
    "road_accident": ("🚗", "ROAD ACCIDENT"),
    "forest_fire":   ("🔥", "FOREST FIRE"),
    "landslide":     ("⛰️",  "LANDSLIDE"),
}


def _send_telegram_alert(cam_id: int, class_name: str, confidence: float,
                          image_bytes: Optional[bytes] = None) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.info(
            f"[Telegram] No token/chat_id — simulated alert cam {cam_id}: "
            f"{class_name} {confidence:.1%}"
        )
        return

    emoji, label = DISASTER_DISPLAY.get(
        class_name.lower().replace(" ", "_"), ("🚨", class_name.upper())
    )
    caption = (
        f"{emoji} *विपद्Sathi DISASTER ALERT!*\n\n"
        f"📷 *Camera:* CAM-0{cam_id}\n"
        f"⚠️ *Event:* {label}\n"
        f"🎯 *Confidence:* {round(confidence * 100, 1)}%\n"
        f"⏰ *Time:* {datetime.datetime.now().strftime('%I:%M %p')}\n"
        f"📍 *Location:* Bagmati Monitoring Zone"
    )
    try:
        import requests as _req
        if image_bytes:
            url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            files = {"photo": (f"{class_name}.jpg", image_bytes, "image/jpeg")}
            data  = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
            resp  = _req.post(url, data=data, files=files, timeout=10)
        else:
            url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "Markdown"}
            resp = _req.post(url, json=data, timeout=10)
        if resp.status_code == 200:
            logger.info(f"[Telegram] Alert sent — cam {cam_id}: {class_name}")
        else:
            logger.warning(f"[Telegram] API {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        logger.error(f"[Telegram] Send error: {exc}")


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="System Health Check",
    tags=["System"]
)
async def health_check():
    """Returns the operational status of the विपद्Sathi backend API."""
    return {
        "status":        "online",
        "service":       "विपद्Sathi Disaster Detection Backend API",
        "version":       "2.0.0",
        "model_loaded":  _disaster_model is not None,
        "model_classes": _disaster_class_names,
    }


# ---- Keep original controller-based routes with safe import fallback ----
try:
    from app.models.schemas import DetectionPayload, DetectionResponse
    from app.controllers.detection_controller import detection_controller
    _ctrl_ok = True
except Exception:
    _ctrl_ok = False


@router.post(
    "/detect",
    status_code=status.HTTP_200_OK,
    summary="Process Object Detection Event",
    tags=["Detection"]
)
async def handle_detection(payload: dict = Body(...)):
    """Receives detection data payloads."""
    if _ctrl_ok:
        from app.models.schemas import DetectionPayload as DP
        return await detection_controller.process_detection(DP(**payload))
    return {"status": "received", "payload": payload}


@router.get(
    "/dashboard/summary",
    status_code=status.HTTP_200_OK,
    summary="Get Dashboard Summary Metrics",
    tags=["Dashboard"]
)
async def get_dashboard_summary():
    if _ctrl_ok:
        return detection_controller.get_dashboard_summary()
    return {"message": "unavailable"}


@router.get(
    "/detections",
    status_code=status.HTTP_200_OK,
    summary="Get Detection History Records",
    tags=["Detection"]
)
async def get_detections(limit: int = Query(default=50, ge=1, le=200)):
    if _ctrl_ok:
        return detection_controller.get_detections_history(limit=limit)
    return {"detections": []}


@router.get(
    "/speakers",
    status_code=status.HTTP_200_OK,
    summary="Get Speaker Hardware Status",
    tags=["Hardware"]
)
async def get_speakers():
    if _ctrl_ok:
        return detection_controller.get_speaker_status()
    return {"speakers": []}


@router.post(
    "/speakers/control",
    status_code=status.HTTP_200_OK,
    summary="Manual Speaker Override Control",
    tags=["Hardware"]
)
async def control_speaker(action: str = Query(..., description="'ON' or 'OFF'")):
    if _ctrl_ok:
        return detection_controller.trigger_speaker(action=action)
    return {"status": f"speaker {action}"}


@router.post(
    "/lights/control",
    status_code=status.HTTP_200_OK,
    summary="Manual Flash Light Override Control",
    tags=["Hardware"]
)
async def control_light(action: str = Query(..., description="'ON' or 'OFF'")):
    if _ctrl_ok:
        return detection_controller.trigger_light(action=action)
    return {"status": f"light {action}"}


@router.get(
    "/notifications",
    status_code=status.HTTP_200_OK,
    summary="Get Notification History Logs",
    tags=["Notifications"]
)
async def get_notifications(limit: int = Query(default=50, ge=1, le=200)):
    if _ctrl_ok:
        return detection_controller.get_notifications(limit=limit)
    return {"notifications": []}


@router.get(
    "/analytics",
    status_code=status.HTTP_200_OK,
    summary="Get Analytics Metrics",
    tags=["Analytics"]
)
async def get_analytics():
    if _ctrl_ok:
        return detection_controller.get_analytics()
    return {"analytics": {}}



# ============================================================================
# Camera Stream Manager with integrated Disaster Detection
# ============================================================================
class CameraStreamManager:
    """
    Thread-safe camera stream manager for multi-camera streaming (Index 0: Laptop, Index 1: Webcam).
    Runs YOLO disaster detection every DETECT_EVERY frames with DEBOUNCE_FRAMES
    consecutive-positive gate before firing Telegram alerts.
    Provides HD frames (1280x720) with annotated overlays and JPEG quality 92.
    """

    def __init__(self):
        self._threads:       Dict[int, threading.Thread] = {}
        self._locks:         Dict[int, threading.Lock]   = {}
        self._result_locks:  Dict[int, threading.Lock]   = {}
        self._latest_jpeg:   Dict[int, bytes]            = {}
        self._online_status: Dict[int, bool]             = {}
        self._stop_events:   Dict[int, threading.Event]  = {}
        self._last_result:   Dict[int, Optional[Dict]]   = {}
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

    def _run_inference(self, frame: np.ndarray) -> List[Dict]:
        """Run YOLO inference on a frame. Returns list of detection dicts."""
        if _disaster_model is None:
            return []
        try:
            with _inference_lock:
                results = _disaster_model(frame, verbose=False, conf=CONF_THRES)
            detections = []
            if results and len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    xyxy     = box.xyxy[0].cpu().numpy().astype(int).tolist()
                    conf     = float(box.conf[0].item())
                    cls_id   = int(box.cls[0].item())
                    cls_name = _disaster_class_names.get(cls_id, f"class_{cls_id}")
                    detections.append({
                        "bbox":     xyxy,
                        "conf":     conf,
                        "cls_id":   cls_id,
                        "cls_name": cls_name,
                    })
            return detections
        except Exception as exc:
            logger.debug(f"Inference error: {exc}")
            return []

    def _annotate_frame(self, frame: np.ndarray, result: Optional[Dict],
                         camera_id: int) -> np.ndarray:
        """Draw bounding boxes + status overlay on a frame copy."""
        display  = frame.copy()
        cam_name = "CAM-01 (Laptop)" if camera_id == 0 else "CAM-02 (Webcam)"

        if result is None:
            cv2.putText(display, f"{cam_name} LIVE  |  {time.strftime('%Y-%m-%d %H:%M:%S')}",
                        (18, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 128), 2, cv2.LINE_AA)
            return display

        debounced  = result.get("debounced", False)
        detections = result.get("detections", [])
        count      = result.get("consecutive_count", 0)

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            conf   = det["conf"]
            cname  = det["cls_name"]
            _, display_label = DISASTER_DISPLAY.get(
                cname.lower().replace(" ", "_"), ("X", cname.upper()))
            color = (0, 0, 255) if debounced else (0, 255, 255)
            label = f"{display_label}: {conf * 100:.1f}%"
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            lbl_y = max(y1 - 8, th + 8)
            cv2.rectangle(display, (x1, lbl_y - th - 6), (x1 + tw + 6, lbl_y + 2), color, -1)
            cv2.putText(display, label, (x1 + 3, lbl_y - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        if debounced and detections:
            top_cls = detections[0]["cls_name"].upper()
            cv2.putText(display, f"ALERT: {top_cls} DETECTED [{count}/{DEBOUNCE_FRAMES}]",
                        (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 255), 2, cv2.LINE_AA)
        elif detections:
            cv2.putText(display, f"VERIFYING... [{count}/{DEBOUNCE_FRAMES}]",
                        (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2, cv2.LINE_AA)
        else:
            cv2.putText(display, f"{cam_name} LIVE  |  {time.strftime('%Y-%m-%d %H:%M:%S')}",
                        (18, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 128), 2, cv2.LINE_AA)
        return display

    def _worker(self, camera_id: int):
        logger.info(f"Starting dedicated camera worker for camera index {camera_id}")
        cap              = None
        consecutive_errors = 0
        frame_counter    = 0
        debounce_count   = 0
        last_sms_time    = 0.0

        while not self._stop_events[camera_id].is_set():
            # ---- Open / reconnect camera ----
            if cap is None or not cap.isOpened():
                try:
                    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                    if not cap.isOpened():
                        cap = cv2.VideoCapture(camera_id)
                except Exception as e:
                    logger.debug(f"Camera {camera_id} capture init exception: {e}")
                    cap = None

                if cap and cap.isOpened():
                    try:
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                    except Exception:
                        pass
                    try:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
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

            # ---- Read frame ----
            try:
                ret, frame = cap.read()
            except Exception as read_err:
                ret, frame = False, None
                logger.debug(f"Frame read exception on camera {camera_id}: {read_err}")

            if not ret or frame is None:
                consecutive_errors += 1
                if consecutive_errors > 8:
                    logger.warning(f"Camera {camera_id} consecutive read failures. Re-initializing...")
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
            frame_counter += 1

            # ---- Disaster detection every DETECT_EVERY frames ----
            current_result = None
            with self._result_locks[camera_id]:
                current_result = self._last_result.get(camera_id)

            if frame_counter % DETECT_EVERY == 0 and _disaster_model is not None:
                detections     = self._run_inference(frame)
                disaster_found = len(detections) > 0
                best_conf      = max((d["conf"] for d in detections), default=0.0)

                if disaster_found:
                    debounce_count += 1
                else:
                    debounce_count = 0

                debounced = debounce_count >= DEBOUNCE_FRAMES
                result = {
                    "detections":        detections,
                    "debounced":         debounced,
                    "consecutive_count": debounce_count,
                    "best_conf":         best_conf,
                }
                with self._result_locks[camera_id]:
                    self._last_result[camera_id] = result
                current_result = result

                # ---- Fire Telegram alert on confirmed debounced detection ----
                if debounced and (time.time() - last_sms_time >= SMS_COOLDOWN_SECONDS):
                    last_sms_time = time.time()
                    top = detections[0]
                    ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    img_bytes = buf.tobytes() if ok else None
                    threading.Thread(
                        target=_send_telegram_alert,
                        args=(camera_id + 1, top["cls_name"], top["conf"], img_bytes),
                        daemon=True
                    ).start()
                    logger.warning(
                        f"[Cam {camera_id}] DISASTER CONFIRMED: {top['cls_name']} "
                        f"({top['conf']:.1%}) — Telegram alert dispatched."
                    )

            # ---- Annotate + encode JPEG ----
            annotated = self._annotate_frame(frame, current_result, camera_id)
            ok, encoded = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])
            if ok:
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
                self._locks[camera_id]         = threading.Lock()
                self._result_locks[camera_id]  = threading.Lock()
                self._stop_events[camera_id]   = threading.Event()
                self._online_status[camera_id] = False
                self._latest_jpeg[camera_id]   = self._create_standby_frame(camera_id)
                self._last_result[camera_id]   = None

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
