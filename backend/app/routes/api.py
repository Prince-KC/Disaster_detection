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
from fastapi import APIRouter, status, Query, Body, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from app.utils.logger import get_logger
from app.services.email_service import email_service

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
# Telegram Alert Helper & Direct Endpoint Resolution
# ============================================================================
try:
    import urllib3.util.connection
    _orig_create_connection = urllib3.util.connection.create_connection

    def _patched_create_connection(address, *args, **kwargs):
        host, port = address
        if host == "api.telegram.org":
            host = "149.154.166.110"
        return _orig_create_connection((host, port), *args, **kwargs)

    urllib3.util.connection.create_connection = _patched_create_connection
except Exception as _patch_exc:
    logger.debug(f"Telegram DNS patch skipped: {_patch_exc}")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "").strip()

DISASTER_DISPLAY: Dict[str, tuple] = {
    "flood":         ("🌊", "FLOOD"),
    "road_accident": ("🚗", "ROAD ACCIDENT"),
    "car_accident":  ("🚗", "CAR ACCIDENT"),
    "bike_accident": ("🏍️", "BIKE ACCIDENT"),
    "bus_accident":  ("🚌", "BUS ACCIDENT"),
    "forest_fire":   ("🔥", "FOREST FIRE"),
    "landslide":     ("⛰️",  "LANDSLIDE"),
}


# Ambulance tier mapping for accident classes (per detected box)
ACCIDENT_TIERS: Dict[str, tuple] = {
    "bike_accident": (1, 2, "bike"),
    "car_accident":  (3, 5, "car"),
    "bus_accident":  (15, 20, "bus"),
}


def _compute_accident_vehicle_info(detections: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Computes vehicle counts and required ambulance range based on detected accident boxes.
    Tiers per box:
      bike_accident -> 1-2 ambulances
      car_accident  -> 3-5 ambulances
      bus_accident  -> 15-20 ambulances
    """
    counts: Dict[str, int] = {}
    if detections:
        for det in detections:
            cname = det.get("cls_name", "").lower().strip().replace(" ", "_")
            if cname in ACCIDENT_TIERS:
                counts[cname] = counts.get(cname, 0) + 1

    if not counts:
        return {
            "vehicle_counts": {},
            "ambulance_low": None,
            "ambulance_high": None,
            "vehicles_line": "none identified",
            "ambulances_line": "unable to estimate - manual assessment required"
        }

    total_low = 0
    total_high = 0
    vehicle_parts = []
    # Consistent ordering
    for cname in ["car_accident", "bus_accident", "bike_accident"]:
        if cname in counts:
            cnt = counts[cname]
            low_per, high_per, label = ACCIDENT_TIERS[cname]
            total_low += cnt * low_per
            total_high += cnt * high_per
            vehicle_parts.append(f"{cnt} x {label}")

    return {
        "vehicle_counts": counts,
        "ambulance_low": total_low,
        "ambulance_high": total_high,
        "vehicles_line": ", ".join(vehicle_parts) if vehicle_parts else "none identified",
        "ambulances_line": f"{total_low}-{total_high}"
    }


def _record_detection_supabase(cam_id: int, object_class: str, confidence: float,
                               vehicle_info: Optional[Dict[str, Any]] = None) -> None:
    """Save disaster detection event to Supabase DB asynchronously."""
    sup_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    sup_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "").strip()
    if not sup_url or not sup_key:
        return
    try:
        import requests as _req
        headers = {
            "apikey": sup_key,
            "Authorization": f"Bearer {sup_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        device_name = f"CAM-0{cam_id}"
        meta: Dict[str, Any] = {
            "cam_id": cam_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "location": "Bagmati Monitoring Zone"
        }
        if vehicle_info:
            meta["vehicle_counts"] = vehicle_info.get("vehicle_counts", {})
            meta["ambulance_low"] = vehicle_info.get("ambulance_low")
            meta["ambulance_high"] = vehicle_info.get("ambulance_high")

        payload = {
            "device_id": device_name,
            "object_class": object_class,
            "confidence": round(float(confidence) * 100, 1),
            "metadata": meta
        }
        url = f"{sup_url}/rest/v1/detections"
        resp = _req.post(url, json=payload, headers=headers, timeout=5)
        if resp.status_code in (200, 201):
            logger.info(f"[Supabase] Logged detection for {device_name}: {object_class}")
        else:
            logger.warning(f"[Supabase] Detection insert returned {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        logger.error(f"[Supabase] Logging error: {exc}")


def _send_telegram_alert(cam_id: int, class_name: str, confidence: float,
                          image_bytes: Optional[bytes] = None,
                          frame_detections: Optional[List[Dict[str, Any]]] = None) -> None:
    clean_key = class_name.lower().strip().replace(" ", "_")
    is_accident = clean_key in ("bike_accident", "car_accident", "bus_accident", "road_accident")

    vehicle_info = None
    if is_accident:
        vehicle_info = _compute_accident_vehicle_info(frame_detections)

    # Also log to Supabase in background
    threading.Thread(
        target=_record_detection_supabase,
        args=(cam_id, class_name, confidence, vehicle_info),
        daemon=True
    ).start()

    # Also dispatch Email alert to authorities in background
    threading.Thread(
        target=email_service.send_detection_email,
        args=(cam_id, class_name, confidence, image_bytes, vehicle_info),
        daemon=True
    ).start()

    chat_ids = [c.strip() for c in TELEGRAM_CHAT_ID.split(",") if c.strip()]
    if not TELEGRAM_BOT_TOKEN or not chat_ids:
        logger.info(
            f"[Telegram] No token/chat_id — simulated alert cam {cam_id}: "
            f"{class_name} {confidence:.1%}"
        )
        return

    emoji, label = DISASTER_DISPLAY.get(
        clean_key, ("🚨", class_name.replace("_", " ").upper())
    )

    caption = (
        f"{emoji} <b>विपद्Sathi DISASTER ALERT!</b>\n\n"
        f"📷 <b>Camera:</b> CAM-0{cam_id}\n"
        f"⚠️ <b>Event:</b> {label}\n"
        f"🎯 <b>Confidence:</b> {round(confidence * 100, 1)}%\n"
        f"⏰ <b>Time:</b> {datetime.datetime.now().strftime('%I:%M %p')}\n"
        f"📍 <b>Location:</b> Bagmati Monitoring Zone"
    )

    # For road_accident events, append vehicle and ambulance lines directly after Location
    if is_accident and vehicle_info is not None:
        caption += (
            f"\n🚗 <b>Vehicles Involved:</b> {vehicle_info['vehicles_line']}\n"
            f"🚑 <b>Ambulances Needed:</b> {vehicle_info['ambulances_line']}"
        )

    try:
        import requests as _req
        for target_chat_id in chat_ids:
            try:
                if image_bytes:
                    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                    files = {"photo": (f"{clean_key}.jpg", image_bytes, "image/jpeg")}
                    data  = {"chat_id": target_chat_id, "caption": caption, "parse_mode": "HTML"}
                    resp  = _req.post(url, data=data, files=files, timeout=10)
                else:
                    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                    data = {"chat_id": target_chat_id, "text": caption, "parse_mode": "HTML"}
                    resp = _req.post(url, json=data, timeout=10)
                if resp.status_code == 200:
                    logger.info(f"[Telegram] Alert sent to {target_chat_id} — cam {cam_id}: {label}")
                else:
                    logger.warning(f"[Telegram] API {resp.status_code} for {target_chat_id}: {resp.text[:200]}")
            except Exception as e:
                logger.error(f"[Telegram] Error sending to {target_chat_id}: {e}")
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
    records = []
    if _ctrl_ok:
        records = detection_controller.get_detections_history(limit=limit)
    # Ensure vehicle_counts, ambulance_low, ambulance_high are flattened for consumers
    enriched = []
    for rec in (records or []):
        meta = rec.get("metadata") or {}
        rec_copy = dict(rec)
        if "vehicle_counts" in meta:
            rec_copy["vehicle_counts"] = meta.get("vehicle_counts")
        if "ambulance_low" in meta:
            rec_copy["ambulance_low"] = meta.get("ambulance_low")
        if "ambulance_high" in meta:
            rec_copy["ambulance_high"] = meta.get("ambulance_high")
        enriched.append(rec_copy)
    return {"detections": enriched}


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
# Camera Stream Manager — SPLIT THREAD ARCHITECTURE
#
# Camera thread  : captures frames at ~30fps, encodes JPEG → never blocked
# Inference thread: runs YOLO asynchronously → never blocks the camera thread
# Result is shared via locks; annotations overlay the latest result on every frame
# ============================================================================
class CameraStreamManager:
    """
    Thread-safe, dual-thread camera manager.
    - _camera_worker: grabs frames from hardware at ~30fps and encodes annotated JPEG
    - _inference_worker: reads the latest raw frame and runs YOLO asynchronously

    Video display is NEVER blocked by inference; inference updates the overlay
    in the background and the camera thread uses whatever result is current.
    """

    def __init__(self):
        self._cam_threads:   Dict[int, threading.Thread] = {}
        self._inf_threads:   Dict[int, threading.Thread] = {}
        self._frame_locks:   Dict[int, threading.Lock]   = {}   # guards latest raw frame
        self._result_locks:  Dict[int, threading.Lock]   = {}   # guards last inference result
        self._jpeg_locks:    Dict[int, threading.Lock]   = {}   # guards encoded JPEG
        self._stop_events:   Dict[int, threading.Event]  = {}
        self._latest_frame:  Dict[int, Optional[np.ndarray]] = {}
        self._latest_jpeg:   Dict[int, bytes]            = {}
        self._last_result:   Dict[int, Optional[Dict]]   = {}
        self._online_status: Dict[int, bool]             = {}
        self._latest_disaster: Dict[int, Dict[str, Any]] = {}
        self._disabled:        Dict[int, bool]             = {}   # True = user turned camera off
        self._init_lock = threading.Lock()

    # ------------------------------------------------------------------
    def _create_standby_frame(self, camera_id: int) -> bytes:
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        img[:] = (24, 28, 26)
        cam_label = "Laptop Camera (Index 0)" if camera_id == 0 else "External USB Webcam (Index 1)"
        cv2.putText(img, f"CAM-0{camera_id + 1} — {cam_label}",
                    (60, 320), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, "Status: Standby / Waiting for connection...",
                    (60, 375), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (120, 180, 150), 2, cv2.LINE_AA)
        cv2.putText(img, f"Bagmati Monitoring Grid — {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    (60, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (160, 165, 160), 1, cv2.LINE_AA)
        _, enc = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return enc.tobytes()

    def _create_disabled_frame(self, camera_id: int) -> bytes:
        """Dark frame shown in the MJPEG stream when the camera is turned off."""
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        img[:] = (10, 10, 12)
        cam_label = "Laptop Camera (Index 0)" if camera_id == 0 else "External USB Webcam (Index 1)"
        cv2.putText(img, f"CAM-0{camera_id + 1} — {cam_label}",
                    (60, 310), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (200, 200, 200), 2, cv2.LINE_AA)
        cv2.putText(img, "Camera disabled — turn on to resume monitoring",
                    (60, 368), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (80, 80, 90), 2, cv2.LINE_AA)
        cv2.putText(img, f"Bagmati Monitoring Grid — {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    (60, 422), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (55, 60, 65), 1, cv2.LINE_AA)
        _, enc = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return enc.tobytes()

    # ------------------------------------------------------------------
    def _annotate(self, frame: np.ndarray, result: Optional[Dict],
                  camera_id: int) -> np.ndarray:
        """Draw bounding boxes and status text onto a copy of frame."""
        display  = frame.copy()
        cam_name = "CAM-01 (Laptop)" if camera_id == 0 else "CAM-02 (Webcam)"

        if result is None:
            cv2.putText(display,
                        f"{cam_name}  LIVE  |  {time.strftime('%H:%M:%S')}",
                        (18, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 128), 2, cv2.LINE_AA)
            return display

        debounced  = result.get("debounced", False)
        detections = result.get("detections", [])
        count      = result.get("consecutive_count", 0)

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            conf  = det["conf"]
            cname = det["cls_name"]
            _, lbl = DISASTER_DISPLAY.get(cname.lower().replace(" ", "_"), ("X", cname.upper()))
            color = (0, 0, 255) if debounced else (0, 255, 255)
            text  = f"{lbl}: {conf * 100:.1f}%"
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            ly = max(y1 - 8, th + 8)
            cv2.rectangle(display, (x1, ly - th - 6), (x1 + tw + 6, ly + 2), color, -1)
            cv2.putText(display, text, (x1 + 3, ly - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        if debounced and detections:
            top = detections[0]["cls_name"].upper()
            cv2.putText(display, f"🚨 ALERT: {top} [{count}/{DEBOUNCE_FRAMES}]",
                        (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 255), 2, cv2.LINE_AA)
        elif detections:
            cv2.putText(display, f"VERIFYING... [{count}/{DEBOUNCE_FRAMES}]",
                        (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2, cv2.LINE_AA)
        else:
            cv2.putText(display,
                        f"{cam_name}  LIVE  |  {time.strftime('%H:%M:%S')}",
                        (18, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 128), 2, cv2.LINE_AA)
        return display

    # ------------------------------------------------------------------
    def _camera_worker(self, camera_id: int):
        """
        CAMERA THREAD — pure capture + encode loop. ~30fps.
        No inference here. Just reads camera, overlays last result, encodes JPEG.
        """
        logger.info(f"[CamThread {camera_id}] Starting camera capture thread")
        cap = None
        consecutive_errors = 0

        while not self._stop_events[camera_id].is_set():
            # ---- open / reconnect ----
            if cap is None or not cap.isOpened():
                try:
                    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                    if not cap.isOpened():
                        cap = cv2.VideoCapture(camera_id)
                except Exception as e:
                    logger.debug(f"[CamThread {camera_id}] open error: {e}")
                    cap = None

                if cap and cap.isOpened():
                    try:
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        cap.set(cv2.CAP_PROP_FPS,          30)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)  # keep buffer tiny → minimal latency
                    except Exception:
                        pass
                    self._online_status[camera_id] = True
                    consecutive_errors = 0
                    logger.info(f"[CamThread {camera_id}] camera connected.")
                else:
                    self._online_status[camera_id] = False
                    with self._jpeg_locks[camera_id]:
                        self._latest_jpeg[camera_id] = self._create_standby_frame(camera_id)
                    time.sleep(1.0)
                    continue

            # ---- read ----
            try:
                ret, frame = cap.read()
            except Exception as e:
                ret, frame = False, None

            if not ret or frame is None:
                consecutive_errors += 1
                if consecutive_errors > 10:
                    logger.warning(f"[CamThread {camera_id}] too many read failures, re-opening")
                    try:
                        cap.release()
                    except Exception:
                        pass
                    cap = None
                    self._online_status[camera_id] = False
                    consecutive_errors = 0
                time.sleep(0.05)
                continue

            consecutive_errors = 0
            self._online_status[camera_id] = True

            # share raw frame with inference thread (non-blocking copy)
            with self._frame_locks[camera_id]:
                self._latest_frame[camera_id] = frame

            # fetch the last inference result (never waits for inference)
            with self._result_locks[camera_id]:
                result = self._last_result.get(camera_id)

            # annotate + encode (fast CPU ops, never blocks on YOLO)
            annotated = self._annotate(frame, result, camera_id)
            ok, enc = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 88])
            if ok:
                with self._jpeg_locks[camera_id]:
                    self._latest_jpeg[camera_id] = enc.tobytes()

            # no sleep here — let the camera read at full hardware speed;
            # the encode time (~2-4ms) provides natural pacing

        if cap and cap.isOpened():
            try:
                cap.release()
            except Exception:
                pass
        logger.info(f"[CamThread {camera_id}] stopped.")

    # ------------------------------------------------------------------
    def _inference_worker(self, camera_id: int):
        """
        INFERENCE THREAD — runs YOLO on the latest frame, completely independent
        of the camera thread. Speed limited only by the model, not the stream.
        """
        logger.info(f"[InfThread {camera_id}] Starting inference thread")
        debounce_count = 0
        last_sms_time  = 0.0

        while not self._stop_events[camera_id].is_set():
            if _disaster_model is None:
                time.sleep(0.5)
                continue

            # grab latest frame (non-blocking)
            with self._frame_locks[camera_id]:
                frame = self._latest_frame.get(camera_id)

            if frame is None:
                time.sleep(0.05)
                continue

            # run YOLO (this is the slow step — happens on its own thread)
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
                        detections.append({"bbox": xyxy, "conf": conf,
                                           "cls_id": cls_id, "cls_name": cls_name})
            except Exception as exc:
                logger.debug(f"[InfThread {camera_id}] inference error: {exc}")
                time.sleep(0.1)
                continue

            # debounce
            if detections:
                debounce_count += 1
            else:
                debounce_count = 0

            debounced = debounce_count >= DEBOUNCE_FRAMES
            best_conf = max((d["conf"] for d in detections), default=0.0)

            # store result for camera thread to overlay
            with self._result_locks[camera_id]:
                self._last_result[camera_id] = {
                    "detections":        detections,
                    "debounced":         debounced,
                    "consecutive_count": debounce_count,
                    "best_conf":         best_conf,
                }

            # Telegram alert on confirmed detection
            if debounced and detections and (time.time() - last_sms_time >= SMS_COOLDOWN_SECONDS):
                last_sms_time = time.time()
                top = detections[0]
                with self._frame_locks[camera_id]:
                    snap = self._latest_frame.get(camera_id)
                img_bytes = None
                if snap is not None:
                    ok, buf = cv2.imencode('.jpg', snap, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ok:
                        img_bytes = buf.tobytes()

                # Update camera manager's latest confirmed disaster state
                cname_clean = top["cls_name"].lower().strip().replace(" ", "_")
                is_acc = cname_clean in ("bike_accident", "car_accident", "bus_accident", "road_accident")
                v_info = _compute_accident_vehicle_info(detections) if is_acc else None
                self._latest_disaster[camera_id] = {
                    "event": top["cls_name"],
                    "confidence": round(float(top["conf"]) * 100, 1),
                    "timestamp": datetime.datetime.now().isoformat(),
                    "vehicle_counts": v_info.get("vehicle_counts", {}) if v_info else {},
                    "ambulance_low": v_info.get("ambulance_low") if v_info else None,
                    "ambulance_high": v_info.get("ambulance_high") if v_info else None,
                }

                threading.Thread(
                    target=_send_telegram_alert,
                    args=(camera_id + 1, top["cls_name"], top["conf"], img_bytes, detections),
                    daemon=True
                ).start()
                logger.warning(
                    f"[InfThread {camera_id}] DISASTER CONFIRMED: "
                    f"{top['cls_name']} ({top['conf']:.1%}) — Telegram dispatched."
                )

            # no fixed sleep — run as fast as the model allows
            # (typically 5-20 FPS on CPU; stream stays at 30fps regardless)

        logger.info(f"[InfThread {camera_id}] stopped.")

    # ------------------------------------------------------------------
    def ensure_camera(self, camera_id: int):
        with self._init_lock:
            need_start = (
                camera_id not in self._cam_threads
                or not self._cam_threads[camera_id].is_alive()
            )
            if not need_start:
                return

            # initialise shared state
            self._frame_locks[camera_id]  = threading.Lock()
            self._result_locks[camera_id] = threading.Lock()
            self._jpeg_locks[camera_id]   = threading.Lock()
            self._stop_events[camera_id]  = threading.Event()
            self._online_status[camera_id] = False
            self._latest_frame[camera_id]  = None
            self._latest_jpeg[camera_id]   = self._create_standby_frame(camera_id)
            self._last_result[camera_id]   = None

            # camera thread
            ct = threading.Thread(target=self._camera_worker, args=(camera_id,),
                                  daemon=True, name=f"CamThread_{camera_id}")
            self._cam_threads[camera_id] = ct
            ct.start()

            # inference thread (only if model is loaded)
            if _disaster_model is not None:
                it = threading.Thread(target=self._inference_worker, args=(camera_id,),
                                      daemon=True, name=f"InfThread_{camera_id}")
                self._inf_threads[camera_id] = it
                it.start()

    def set_camera_enabled(self, camera_id: int, enabled: bool) -> None:
        """Enable or disable a camera (frontend toggle). Thread-safe."""
        with self._init_lock:
            self._disabled[camera_id] = not enabled

    def is_camera_enabled(self, camera_id: int) -> bool:
        return not self._disabled.get(camera_id, False)

    def get_jpeg_frame(self, camera_id: int) -> bytes:
        # Return a static disabled frame without touching camera threads
        if self._disabled.get(camera_id, False):
            return self._create_disabled_frame(camera_id)
        self.ensure_camera(camera_id)
        with self._jpeg_locks.get(camera_id, self._init_lock):
            return self._latest_jpeg.get(camera_id, self._create_standby_frame(camera_id))

    def get_status(self) -> Dict[str, Any]:
        cams = []
        for cid, (cname, ctype) in enumerate([("CAM-01 (Laptop Camera)", "Integrated"),
                                              ("CAM-02 (USB Webcam)", "External")]):
            disaster_info = self._latest_disaster.get(cid, {})
            cam_data: Dict[str, Any] = {
                "id":      cid,
                "name":    cname,
                "type":    ctype,
                "online":  self._online_status.get(cid, False),
                "enabled": self.is_camera_enabled(cid),
            }
            if disaster_info:
                cam_data["latest_event"]    = disaster_info.get("event")
                cam_data["confidence"]      = disaster_info.get("confidence")
                cam_data["timestamp"]       = disaster_info.get("timestamp")
                cam_data["vehicle_counts"]  = disaster_info.get("vehicle_counts", {})
                cam_data["ambulance_low"]   = disaster_info.get("ambulance_low")
                cam_data["ambulance_high"]  = disaster_info.get("ambulance_high")
            cams.append(cam_data)

        return {
            "cameras": cams,
            "total": 2,
            "online_count": sum(
                1 for v in [self._online_status.get(0, False),
                             self._online_status.get(1, False)] if v
            )
        }


camera_stream_manager = CameraStreamManager()


def generate_camera_stream(camera_id: int = 0):
    """Generator that yields an endless MJPEG stream for the given camera."""
    camera_stream_manager.ensure_camera(camera_id)
    while True:
        frame_bytes = camera_stream_manager.get_jpeg_frame(camera_id)
        if frame_bytes:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)   # ~30fps pacing for the HTTP generator


@router.get("/video_feed", summary="Live Camera MJPEG Stream", tags=["Live Feed"])
async def video_feed(camera_id: int = Query(default=0, ge=0, le=5)):
    """Returns a continuous MJPEG video stream (0=Laptop, 1=Webcam)."""
    return StreamingResponse(
        generate_camera_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/video_feed/{camera_id}", summary="Live Camera MJPEG Stream by ID", tags=["Live Feed"])
async def video_feed_by_id(camera_id: int):
    """Returns a continuous MJPEG video stream from the specified camera ID."""
    return StreamingResponse(
        generate_camera_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/cameras/status", summary="Get Camera Operational Status", tags=["Live Feed"])
async def get_cameras_status():
    """Returns online/offline status of configured cameras."""
    return camera_stream_manager.get_status()


@router.get("/live-alerts", summary="Latest Confirmed Disaster Alerts", tags=["Alerts"])
async def get_live_alerts():
    """
    Returns the latest confirmed disaster event detected per camera.
    The frontend polls this endpoint every few seconds to update the Incident Alerts table.
    """
    alerts = []
    status = camera_stream_manager.get_status()
    for cam in status.get("cameras", []):
        event = cam.get("latest_event")
        if not event:
            continue
        ambulance_low  = cam.get("ambulance_low")
        ambulance_high = cam.get("ambulance_high")
        vehicle_counts = cam.get("vehicle_counts", {})
        total_vehicles = sum(vehicle_counts.values()) if vehicle_counts else None
        alerts.append({
            "camera_id":      cam["id"],
            "camera_name":    cam["name"],
            "event":          event,
            "confidence":     cam.get("confidence"),
            "timestamp":      cam.get("timestamp"),
            "vehicle_counts": vehicle_counts,
            "total_vehicles": total_vehicles,
            "ambulance_low":  ambulance_low,
            "ambulance_high": ambulance_high,
        })
    # Sort newest first
    alerts.sort(key=lambda a: a["timestamp"] or "", reverse=True)
    return {"alerts": alerts, "count": len(alerts)}


@router.post("/cameras/{camera_id}/enable", summary="Enable a camera", tags=["Live Feed"])
async def enable_camera(camera_id: int):
    """Re-enable a camera that was previously disabled via the UI toggle."""
    if camera_id not in (0, 1):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Unknown camera ID")
    camera_stream_manager.set_camera_enabled(camera_id, True)
    logger.info(f"Camera {camera_id} enabled via API.")
    return {"camera_id": camera_id, "enabled": True}


@router.post("/cameras/{camera_id}/disable", summary="Disable a camera", tags=["Live Feed"])
async def disable_camera(camera_id: int):
    """Disable a camera so it stops sending a live stream (shows an off-screen)."""
    if camera_id not in (0, 1):
        raise HTTPException(status_code=404, detail="Unknown camera ID")
    camera_stream_manager.set_camera_enabled(camera_id, False)
    logger.info(f"Camera {camera_id} disabled via API.")
    return {"camera_id": camera_id, "enabled": False}


# ============================================================================
# Citizen Incident Report Submission
# ============================================================================
_UPLOAD_DIR = os.path.join(_PROJECT_ROOT, "uploads", "reports")
os.makedirs(_UPLOAD_DIR, exist_ok=True)


def _send_citizen_report_telegram(
    report_id: str,
    incident_type: str,
    incident_time: str,
    location: str,
    description: str,
    saved_files: List[str],
    report_dir: str
) -> None:
    """Dispatches a formatted Telegram alert to authorities when a citizen submits an incident."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or TELEGRAM_BOT_TOKEN
    chat_id_raw = os.getenv("TELEGRAM_CHAT_ID", "").strip() or TELEGRAM_CHAT_ID
    chat_ids = [c.strip() for c in chat_id_raw.split(",") if c.strip()]

    if not bot_token or not chat_ids:
        logger.warning(f"[Report {report_id}] Telegram not sent: token or chat_id not configured.")
        return

    # Choose incident emoji
    t_clean = incident_type.lower().replace("-", "_").replace(" ", "_")
    emoji = "🚨"
    if any(k in t_clean for k in ["accident", "crash", "car", "bike", "bus", "vehicle"]):
        emoji = "🚗"
    elif any(k in t_clean for k in ["flood", "water", "river"]):
        emoji = "🌊"
    elif any(k in t_clean for k in ["slide", "landslide"]):
        emoji = "⛰️"
    elif any(k in t_clean for k in ["fire", "smoke", "burn"]):
        emoji = "🔥"
    elif any(k in t_clean for k in ["block", "blocked", "traffic"]):
        emoji = "🚧"

    # Truncate description if too long so total caption doesn't exceed 1000 chars for sendPhoto
    clean_desc = (description or "").strip()
    if len(clean_desc) > 400:
        clean_desc = clean_desc[:397] + "..."

    files_text = f"{len(saved_files)} file(s)"
    if saved_files:
        files_text += f" ({', '.join(saved_files)})"

    caption = (
        f"📢 <b>विपद्Sathi CITIZEN INCIDENT REPORT</b>\n\n"
        f"🆔 <b>Report ID:</b> <code>{report_id}</code>\n"
        f"⚠️ <b>Incident Type:</b> {emoji} <b>{incident_type}</b>\n"
        f"📍 <b>Location:</b> {location}\n"
        f"⏰ <b>Incident Time:</b> {incident_time}\n"
        f"🕒 <b>Submitted:</b> {datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n"
        f"📝 <b>Description:</b>\n{clean_desc}\n\n"
        f"📎 <b>Evidence:</b> {files_text}"
    )

    # Check for image file in saved_files
    primary_image_path = None
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    for fname in saved_files:
        _, ext = os.path.splitext(fname.lower())
        if ext in image_exts:
            full_path = os.path.join(report_dir, fname)
            if os.path.isfile(full_path):
                primary_image_path = full_path
                break

    img_bytes = None
    if primary_image_path:
        try:
            with open(primary_image_path, "rb") as f:
                img_bytes = f.read()
        except Exception as e:
            logger.warning(f"[Report {report_id}] Could not read evidence image {primary_image_path}: {e}")

    try:
        import requests as _req
        for target_chat_id in chat_ids:
            try:
                if img_bytes:
                    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                    files = {"photo": (os.path.basename(primary_image_path), img_bytes, "image/jpeg")}
                    data = {"chat_id": target_chat_id, "caption": caption, "parse_mode": "HTML"}
                    resp = _req.post(url, data=data, files=files, timeout=10)
                else:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    data = {"chat_id": target_chat_id, "text": caption, "parse_mode": "HTML"}
                    resp = _req.post(url, json=data, timeout=10)

                if resp.status_code == 200:
                    logger.info(f"[Report {report_id}] Telegram alert delivered to {target_chat_id}")
                else:
                    logger.warning(f"[Report {report_id}] Telegram API {resp.status_code} for {target_chat_id}: {resp.text[:200]}")
            except Exception as e:
                logger.error(f"[Report {report_id}] Error sending Telegram alert to {target_chat_id}: {e}")
    except Exception as exc:
        logger.error(f"[Report {report_id}] Unexpected error in Telegram alert dispatch: {exc}")


@router.post("/reports/submit", summary="Submit a citizen incident report", tags=["Reports"])
async def submit_report(
    incident_type: str = Form(...),
    incident_time: str = Form(...),
    location:      str = Form(...),
    description:   str = Form(...),
    evidence: List[UploadFile] = File(default=[]),
):
    """
    Accepts a citizen incident report (multipart/form-data).
    Saves uploaded evidence files to disk under uploads/reports/<report_id>/
    and sends Telegram notification alerts to authorities.
    """
    import uuid, shutil

    report_id  = "RK-" + str(uuid.uuid4())[:6].upper()
    report_dir = os.path.join(_UPLOAD_DIR, report_id)
    os.makedirs(report_dir, exist_ok=True)

    saved_files: List[str] = []
    for upload in evidence:
        if not upload.filename:
            continue
        safe_name = upload.filename.replace("..", "").replace("/", "_").replace("\\", "_")
        dest = os.path.join(report_dir, safe_name)
        with open(dest, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        saved_files.append(safe_name)
        logger.info(f"[Report {report_id}] saved evidence file: {safe_name}")

    logger.info(
        f"[Report {report_id}] submitted — type={incident_type!r} "
        f"location={location!r} files={len(saved_files)}"
    )

    # Dispatch Telegram alert in background thread
    threading.Thread(
        target=_send_citizen_report_telegram,
        args=(report_id, incident_type, incident_time, location, description, saved_files, report_dir),
        daemon=True
    ).start()

    # Dispatch Email alert to authorities in background thread
    threading.Thread(
        target=email_service.send_citizen_report_email,
        args=(report_id, incident_type, incident_time, location, description, saved_files, report_dir),
        daemon=True
    ).start()

    return JSONResponse({
        "success":       True,
        "report_id":     report_id,
        "incident_type": incident_type,
        "incident_time": incident_time,
        "location":      location,
        "files_saved":   saved_files,
        "message":       "Report received. Authorities have been notified.",
    })


@router.get("/email/status", summary="Check Email Alert Service Status", tags=["Notifications"])
async def email_status():
    """Returns the configuration status of the Gmail alert system."""
    user = os.getenv("GMAIL_USER", "bipadsathi1@gmail.com").strip()
    configured = email_service.is_configured()
    recipients = email_service._get_recipients()
    return {
        "configured": configured,
        "sender": user,
        "recipients": recipients,
        "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", 587)),
        "note": "Configured and ready" if configured else "GMAIL_APP_PASSWORD not set in .env. Generate a 16-char App Password in Google Account -> Security -> App Passwords."
    }


@router.post("/email/test", summary="Send Test Alert Email", tags=["Notifications"])
async def test_email(to_email: Optional[str] = Query(default=None, description="Optional recipient email override")):
    """Sends a test alert email via Gmail SMTP to verify configuration."""
    subject = "🧪 [विपद्Sathi] Test Emergency Alert Email"
    html = """
    <div style="font-family:sans-serif; max-width:500px; padding:20px; border:1px solid #ddd; border-radius:8px;">
      <h2 style="color:#b91c1c;">विपद्Sathi Email Alert System</h2>
      <p>This is a test notification confirming that Gmail SMTP alerts from <strong>bipadsathi1@gmail.com</strong> are working successfully.</p>
      <p style="font-size:12px; color:#666;">Bagmati Disaster & Incident Monitoring Operations</p>
    </div>
    """
    recipients = [to_email] if to_email else None
    result = email_service.send_email(
        subject=subject,
        html_content=html,
        text_content="विपद्Sathi Email Alert System test notification.",
        to_emails=recipients
    )
    return result


@router.get("/alerts/recipients", summary="Get Camera Alert Email Recipients", tags=["Notifications"])
async def get_alert_recipients():
    """Returns the list of recipient emails configured to receive live camera detection alerts."""
    return {
        "success": True,
        "sender": email_service.gmail_user,
        "configured": email_service.is_configured(),
        "recipients": email_service.get_recipients(),
        "smtp_host": email_service.smtp_host,
        "smtp_port": email_service.smtp_port,
    }


@router.post("/alerts/recipients", summary="Add or update alert recipients", tags=["Notifications"])
async def add_alert_recipient(payload: dict = Body(...)):
    """
    Adds an email address or replaces the full list of recipient emails.
    Accepts {"email": "user@gmail.com"} or {"emails": ["user1@gmail.com", "user2@gmail.com"]}
    """
    if "email" in payload:
        email = str(payload.get("email", "")).strip()
        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="A valid email address is required.")
        updated = email_service.add_recipient(email)
    elif "emails" in payload:
        emails = payload.get("emails", [])
        if not isinstance(emails, list):
            raise HTTPException(status_code=400, detail="'emails' must be an array of strings.")
        updated = email_service.set_recipients(emails)
    else:
        raise HTTPException(status_code=400, detail="Provide 'email' or 'emails' in JSON payload.")

    return {
        "success": True,
        "message": "Alert recipients updated successfully.",
        "recipients": updated,
        "count": len(updated),
    }


@router.delete("/alerts/recipients", summary="Remove an alert recipient", tags=["Notifications"])
async def remove_alert_recipient(email: str = Query(..., description="Email address to remove")):
    """Removes an email address from the alert recipients list."""
    clean_email = email.strip()
    if not clean_email:
        raise HTTPException(status_code=400, detail="Email parameter cannot be empty.")
    updated = email_service.remove_recipient(clean_email)
    return {
        "success": True,
        "message": f"Removed {clean_email} from alert recipients.",
        "recipients": updated,
        "count": len(updated),
    }


@router.post("/alerts/recipients/test", summary="Send Test Alert to Recipients", tags=["Notifications"])
async def test_alert_recipients(payload: dict = Body(default={})):
    """Sends a sample camera detection alert email to verify delivery to configured recipients."""
    to_email = payload.get("email")
    recipients = [to_email.strip()] if to_email else email_service.get_recipients()

    # Create a dummy test frame image
    dummy_img = np.zeros((360, 640, 3), dtype=np.uint8)
    dummy_img[:] = (30, 35, 40)
    cv2.putText(dummy_img, "BIPATSATHI LIVE CAMERA TEST", (40, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 128), 2)
    cv2.putText(dummy_img, f"Alert System Verification - {time.strftime('%Y-%m-%d %H:%M:%S')}", (40, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
    ok, buf = cv2.imencode('.jpg', dummy_img)
    img_bytes = buf.tobytes() if ok else None

    result = email_service.send_detection_email(
        cam_id=1,
        class_name="road_accident",
        confidence=0.942,
        image_bytes=img_bytes,
        vehicle_info={
            "vehicles_line": "1 x car, 1 x bike (simulated test)",
            "ambulances_line": "1-2"
        },
        to_emails=recipients
    )
    return result



