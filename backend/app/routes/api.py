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

    def get_jpeg_frame(self, camera_id: int) -> bytes:
        self.ensure_camera(camera_id)
        with self._jpeg_locks.get(camera_id, self._init_lock):
            return self._latest_jpeg.get(camera_id, self._create_standby_frame(camera_id))

    def get_status(self) -> Dict[str, Any]:
        cams = []
        for cid, (cname, ctype) in enumerate([("CAM-01 (Laptop Camera)", "Integrated"),
                                              ("CAM-02 (USB Webcam)", "External")]):
            disaster_info = self._latest_disaster.get(cid, {})
            cam_data: Dict[str, Any] = {
                "id": cid,
                "name": cname,
                "type": ctype,
                "online": self._online_status.get(cid, False),
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

