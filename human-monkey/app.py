"""
app.py - Refactored Monkey Detector (Ultralytics YOLO Backend) with Dual Camera Support

Architecture:
=============
- Model loaded via Ultralytics YOLO using `my_model/best.pt` and `my_model/data.yaml`
- CameraThread       : Grabs video frames at ~30 FPS, one for each camera (cam_id=1, cam_id=2)
- DetectionThread    : Runs inference every N frames. Uses an inference lock to prevent GPU/CPU OOM.
- Sound Player       : Pygame mixer playing warning audio (`sounds/tiger.mp3`) on valid alert
- Serial Controller  : Thread-safe Arduino communication (b"1" = monkey alert, b"0" = clear)
- generate_frames()  : Reads `latest_frame`, draws `last_result` overlay, yields MJPEG stream per cam
- /start /stop       : Flask HTTP lifecycle endpoints supporting `/<int:cam_id>`
"""

import os
import sys
import cv2
import time
import yaml
import signal
import atexit
import datetime
import threading
from typing import List, Dict, Tuple, Optional

# Fix duplicate OpenMP runtime issue on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from dotenv import load_dotenv
load_dotenv()

import torch
import serial
import pygame
from flask import Flask, Response, render_template, jsonify
from flask_cors import CORS
from ultralytics import YOLO

# ---------------------------------------------------------------------------
# Flask Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)

# CORS — allow the Vite dev server (port 3000 / 5173) and any localhost origin
CORS(app, origins=[
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://localhost:*",
], supports_credentials=False)

# ---------------------------------------------------------------------------
# Logging System (ASCII-safe for Windows console)
# ---------------------------------------------------------------------------
LOG_FILE_PATH = "prediction_log.txt"
log_file = open(LOG_FILE_PATH, "a", buffering=1, encoding="utf-8")

def log_msg(msg: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        print(line.encode("ascii", "replace").decode(), flush=True)
    log_file.write(line + "\n")
    log_file.flush()

# ---------------------------------------------------------------------------
# Model & Class Configuration
# ---------------------------------------------------------------------------
MODEL_PATH      = os.path.join("my_model", "best.pt")
DATA_YAML_PATH  = os.path.join("my_model", "data.yaml")
CONF_THRES      = 0.40   # Minimum confidence threshold for detection
DETECT_EVERY    = 3      # Run inference every Nth grabbed frame
DEBOUNCE_FRAMES = 3      # Consecutive detection frames required for alert (Time-in-Sight)

log_msg(f"Loading YOLO model from: {MODEL_PATH}")

if not os.path.exists(MODEL_PATH):
    # Fallback check
    alt_path = os.path.join("my_model", "my_model.pt")
    if os.path.exists(alt_path):
        MODEL_PATH = alt_path
        log_msg(f"Primary weights missing, using fallback: {MODEL_PATH}")
    else:
        log_msg(f"ERROR: Model file not found at {MODEL_PATH}")
        sys.exit(1)

model = YOLO(MODEL_PATH)
log_msg("YOLO model loaded successfully.")

# Parse class names dynamically from data.yaml or model.names
class_names: Dict[int, str] = {}
if os.path.exists(DATA_YAML_PATH):
    try:
        with open(DATA_YAML_PATH, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
            if yaml_data and "names" in yaml_data:
                yaml_names = yaml_data["names"]
                if isinstance(yaml_names, list):
                    class_names = {idx: name for idx, name in enumerate(yaml_names)}
                elif isinstance(yaml_names, dict):
                    class_names = {int(k): str(v) for k, v in yaml_names.items()}
                log_msg(f"Parsed class names from {DATA_YAML_PATH}: {class_names}")
    except Exception as exc:
        log_msg(f"Warning: Failed to parse {DATA_YAML_PATH}: {exc}")

if not class_names:
    class_names = model.names if hasattr(model, "names") else {0: "Monkey", 1: "Not monkey"}
    log_msg(f"Using model default class names: {class_names}")

# Identify Monkey class IDs strictly (matching 'monkey', excluding 'not monkey')
MONKEY_CLASS_IDS: List[int] = []
for cid, cname in class_names.items():
    cname_lower = str(cname).lower().strip()
    if "monkey" in cname_lower and "not monkey" not in cname_lower:
        MONKEY_CLASS_IDS.append(cid)

if not MONKEY_CLASS_IDS:
    # Default to class ID 0 if name parsing didn't find explicit 'Monkey'
    MONKEY_CLASS_IDS = [0]

log_msg(f"Strict Monkey Class IDs: {MONKEY_CLASS_IDS} -> {[class_names.get(i) for i in MONKEY_CLASS_IDS]}")

# ---------------------------------------------------------------------------
# Audio System (Multi-Engine Alert Sound Player)
# ---------------------------------------------------------------------------
SOUND_FILE = os.path.abspath(os.path.join("sounds", "tiger.mp3"))
_audio_lock = threading.Lock()
_sound_playing = False
_audio_engine = "none"   # "pygame" / "mci" / "beep"
_sound_object: Optional[pygame.mixer.Sound] = None
_sound_channel: Optional[pygame.mixer.Channel] = None

# Attempt Pygame mixer init
try:
    pygame.mixer.init()
    if os.path.exists(SOUND_FILE):
        _sound_object = pygame.mixer.Sound(SOUND_FILE)
        _audio_engine = "pygame"
        log_msg(f"Loaded alert audio via Pygame: {SOUND_FILE}")
except Exception as exc:
    log_msg(f"Pygame mixer sound load skipped: {exc}")

# Fallback to Windows MCI if pygame cannot load this specific file format
if _audio_engine == "none" and sys.platform == "win32" and os.path.exists(SOUND_FILE):
    try:
        import ctypes
        winmm = ctypes.windll.winmm
        ret = winmm.mciSendStringW(f'open "{SOUND_FILE}" alias monkey_alert', None, 0, 0)
        if ret == 0:
            _audio_engine = "mci"
            log_msg(f"Loaded alert audio via Windows MCI: {SOUND_FILE}")
        else:
            log_msg(f"Windows MCI open code: {ret}")
    except Exception as exc:
        log_msg(f"Windows MCI init error: {exc}")

if _audio_engine == "none":
    _audio_engine = "beep"
    log_msg("Audio engine initialized in Beep mode.")

def play_alert_sound() -> None:
    global _sound_playing, _sound_channel
    with _audio_lock:
        if _sound_playing:
            return
        _sound_playing = True
        try:
            if _audio_engine == "pygame" and _sound_object:
                _sound_channel = _sound_object.play(loops=-1)
                log_msg("Audio alert started (Pygame)")
            elif _audio_engine == "mci":
                import ctypes
                ctypes.windll.winmm.mciSendStringW('play monkey_alert repeat', None, 0, 0)
                log_msg("Audio alert started (MCI)")
            elif _audio_engine == "beep" and sys.platform == "win32":
                import winsound
                winsound.Beep(1000, 400)
        except Exception as exc:
            log_msg(f"Error playing sound: {exc}")

def stop_alert_sound() -> None:
    global _sound_playing, _sound_channel
    with _audio_lock:
        if not _sound_playing:
            return
        try:
            if _audio_engine == "pygame":
                if _sound_channel:
                    _sound_channel.stop()
                elif _sound_object:
                    _sound_object.stop()
            elif _audio_engine == "mci":
                import ctypes
                ctypes.windll.winmm.mciSendStringW('stop monkey_alert', None, 0, 0)
            log_msg("Audio alert stopped")
        except Exception as exc:
            log_msg(f"Error stopping sound: {exc}")
        finally:
            _sound_playing = False
            _sound_channel = None

# ---------------------------------------------------------------------------
# Telegram Bot Alert System (Text & Photo Snapshot Notifications)
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
DEFAULT_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def send_telegram_alert(chat_id: str, cam_id: int, confidence: float, image_bytes: Optional[bytes] = None) -> None:
    """Send a Telegram alert (text + optional photo) to a specific chat ID.
    Args:
        chat_id: Telegram chat identifier (e.g., user or group ID).
        cam_id: Camera identifier.
        confidence: Detection confidence (0‑1).
        image_bytes: JPEG bytes of the snapshot (optional).
    """
    if not TELEGRAM_BOT_TOKEN:
        log_msg(f"[Telegram] No BOT_TOKEN – simulated alert to {chat_id} (Camera {cam_id})")
        return

    caption = (
        f"🚨 *khetRakshak MONKEY ALERT!* 🐒\n"
        f"\n📷 *Camera:* Camera 0{cam_id}\n"
        f"🎯 *Confidence:* {round(confidence * 100, 1)}%\n"
        f"⏰ *Time:* {datetime.datetime.now().strftime('%I:%M %p')}\n"
        f"📍 *Location:* Protected Farm Area"
    )
    try:
        import requests
        if image_bytes:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            files = {"photo": ("monkey.jpg", image_bytes, "image/jpeg")}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
            resp = requests.post(url, data=data, files=files, timeout=10)
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": chat_id, "text": caption, "parse_mode": "Markdown"}
            resp = requests.post(url, json=data, timeout=10)
        if resp.status_code == 200:
            log_msg(f"[Telegram] Sent alert to {chat_id} (Camera {cam_id})")
        else:
            log_msg(f"[Telegram] API error {resp.status_code}: {resp.text}")
    except Exception as exc:
        log_msg(f"[Telegram] Connection error: {exc}")


# ---------------------------------------------------------------------------
# Supabase Detection Logger
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "").strip()
last_detection_times: Dict[int, Optional[str]] = {1: None, 2: None}

def record_detection_supabase(cam_id: int, confidence: float, image_bytes: Optional[bytes] = None) -> None:
    """Save monkey detection event to Supabase DB asynchronously."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        import requests
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        device_name = f"Camera 0{cam_id}"
        payload = {
            "device_id": device_name,
            "object_class": "monkey",
            "confidence": round(float(confidence) * 100, 1),
            "metadata": {
                "cam_id": cam_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "location": "East Boundary" if cam_id == 1 else "North Field"
            }
        }
        url = f"{SUPABASE_URL}/rest/v1/detections"
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        if resp.status_code in (200, 201):
            log_msg(f"[Supabase] Logged monkey detection for {device_name} (Conf: {payload['confidence']}%)")
        else:
            log_msg(f"[Supabase] Detection insert returned {resp.status_code}: {resp.text}")
    except Exception as exc:
        log_msg(f"[Supabase] Logging error: {exc}")

def load_last_detections_from_supabase() -> None:
    """Fetch the latest detection timestamp from Supabase on startup."""
    global last_detection_times
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        import requests
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        url = f"{SUPABASE_URL}/rest/v1/detections?order=created_at.desc&limit=10"
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            records = resp.json()
            for rec in records:
                dev = str(rec.get("device_id", ""))
                created = rec.get("created_at")
                cid = 1 if "1" in dev else (2 if "2" in dev else 1)
                if last_detection_times[cid] is None and created:
                    try:
                        dt = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
                        last_detection_times[cid] = dt.strftime("Today, %I:%M %p")
                    except Exception:
                        last_detection_times[cid] = created
            log_msg(f"[Supabase] Synced previous detection history: {last_detection_times}")
    except Exception as exc:
        log_msg(f"[Supabase] Initial sync skipped: {exc}")


# ---------------------------------------------------------------------------
# Arduino Hardware Communication
# ---------------------------------------------------------------------------
ARDUINO_PORT = "COM9"
ARDUINO_BAUD = 9600
arduino: Optional[serial.Serial] = None

try:
    arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
    time.sleep(2)
    log_msg(f"Arduino connected on {ARDUINO_PORT}")
except Exception as exc:
    log_msg(f"Arduino connection failed on {ARDUINO_PORT}: {exc}")
    arduino = None

_state_lock = threading.Lock()
_detection_state: Optional[bool] = None   # None / True / False

def send_arduino(value: bytes, label: str) -> None:
    global _detection_state
    new_state = (value == b"1")
    with _state_lock:
        if _detection_state == new_state:
            return
        _detection_state = new_state

    if arduino:
        try:
            arduino.write(value)
            arduino.flush()
            log_msg(f"Arduino << {value.decode()} ({label})")
        except Exception as exc:
            log_msg(f"Arduino write error: {exc}")

# ---------------------------------------------------------------------------
# Shared State & Locks
# ---------------------------------------------------------------------------
_inference_lock = threading.Lock() # Prevent two cameras from running YOLO at the exact same moment

# Dictionary states for multiple cameras: cam_id -> state
latest_frames = {1: None, 2: None}
last_results = {1: None, 2: None}
running_cams = {1: False, 2: False}

_frame_locks = {1: threading.Lock(), 2: threading.Lock()}
_result_locks = {1: threading.Lock(), 2: threading.Lock()}

# Telegram alert chat IDs / phone numbers per camera
camera_phones: Dict[int, List[str]] = {
    1: [DEFAULT_CHAT_ID] if DEFAULT_CHAT_ID else [],
    2: [DEFAULT_CHAT_ID] if DEFAULT_CHAT_ID else []
}
_phone_lock = threading.Lock()

# Rate-limiting: stores the last time an alert was sent per camera (unix timestamp)
SMS_COOLDOWN_SECONDS = 15  # 15 seconds cooldown for responsive testing
last_sms_time: Dict[int, float] = {1: 0.0, 2: 0.0}

# ---------------------------------------------------------------------------
# Camera Thread
# ---------------------------------------------------------------------------
class CameraThread(threading.Thread):
    def __init__(self, cam_id: int, src_index: int):
        super().__init__(daemon=True, name=f"CameraThread_{cam_id}")
        self.cam_id = cam_id
        self.src_index = src_index
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self.src_index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            # Fallback for systems without CAP_DSHOW
            self._cap = cv2.VideoCapture(self.src_index)

        if not self._cap.isOpened():
            log_msg(f"[Cam {self.cam_id}] Failed to open webcam at index {self.src_index}")
            self._cap = None
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        log_msg(f"[Cam {self.cam_id}] Webcam opened successfully on index {self.src_index}")
        return True

    def release(self) -> None:
        if self._cap:
            self._cap.release()
            self._cap = None
            log_msg(f"[Cam {self.cam_id}] Webcam released")
            
        with _frame_locks[self.cam_id]:
            latest_frames[self.cam_id] = None

    def run(self) -> None:
        log_msg(f"[Cam {self.cam_id}] CameraThread running")
        while True:
            if not running_cams[self.cam_id] or self._cap is None:
                time.sleep(0.02)
                continue

            ret, frame = self._cap.read()
            if not ret or frame is None:
                time.sleep(0.02)
                continue

            with _frame_locks[self.cam_id]:
                latest_frames[self.cam_id] = frame

# Create thread instances
camera_threads = {
    1: CameraThread(cam_id=1, src_index=0),
    2: CameraThread(cam_id=2, src_index=1)
}

# ---------------------------------------------------------------------------
# Detection Thread with Strict Class Filtering & Temporal Debouncing
# ---------------------------------------------------------------------------
class DetectionThread(threading.Thread):
    def __init__(self, cam_id: int):
        super().__init__(daemon=True, name=f"DetectionThread_{cam_id}")
        self.cam_id = cam_id

    def run(self) -> None:
        frame_counter = 0
        consecutive_monkey_count = 0
        log_msg(f"[Cam {self.cam_id}] DetectionThread running")

        while True:
            if not running_cams[self.cam_id]:
                consecutive_monkey_count = 0
                time.sleep(0.05)
                continue

            with _frame_locks[self.cam_id]:
                frame = latest_frames[self.cam_id]

            if frame is None:
                time.sleep(0.05)
                continue

            frame_counter += 1
            if frame_counter % DETECT_EVERY != 0:
                time.sleep(0.01)
                continue

            try:
                # Run inference via Ultralytics inside a global lock to prevent OOM
                with _inference_lock:
                    results = model(frame, verbose=False, conf=CONF_THRES)
                
                boxes_summary = []
                monkey_detected_in_frame = False
                best_monkey_conf = 0.0

                if len(results) > 0 and len(results[0].boxes) > 0:
                    det_boxes = results[0].boxes
                    for box in det_boxes:
                        xyxy = box.xyxy[0].cpu().numpy().astype(int)
                        x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
                        conf = float(box.conf[0].item())
                        cls_id = int(box.cls[0].item())
                        cls_name = class_names.get(cls_id, f"class_{cls_id}")

                        is_monkey = (cls_id in MONKEY_CLASS_IDS)
                        boxes_summary.append({
                            "bbox": (x1, y1, x2, y2),
                            "conf": conf,
                            "cls_id": cls_id,
                            "cls_name": cls_name,
                            "is_monkey": is_monkey
                        })

                        if is_monkey:
                            monkey_detected_in_frame = True
                            if conf > best_monkey_conf:
                                best_monkey_conf = conf

                # Temporal Debouncing Logic (Time-in-Sight filter)
                if monkey_detected_in_frame:
                    consecutive_monkey_count += 1
                else:
                    consecutive_monkey_count = 0

                debounced_alert = (consecutive_monkey_count >= DEBOUNCE_FRAMES)

                with _result_locks[self.cam_id]:
                    last_results[self.cam_id] = {
                        "monkey_detected_raw": monkey_detected_in_frame,
                        "debounced": debounced_alert,
                        "consecutive_count": consecutive_monkey_count,
                        "best_conf": best_monkey_conf,
                        "boxes": boxes_summary
                    }

                # Trigger Hardware Payload & Audio Warning (if either camera detects a monkey, trigger alarm)
                # We check global state from both results
                any_monkey_detected = False
                for cid in [1, 2]:
                    with _result_locks[cid]:
                        res = last_results[cid]
                        if res and res.get("debounced", False):
                            any_monkey_detected = True

                if any_monkey_detected:
                    log_msg(f"[Cam {self.cam_id}] MONKEY ALERT CONFIRMED (Conf={best_monkey_conf:.2f})")
                    send_arduino(b"1", "MONKEY DETECTED")
                    play_alert_sound()
                    # Immediate Telegram alert (subject to cooldown)
                    now = time.time()
                    # Capture current frame as JPEG for Telegram photo
                    image_bytes = None
                    with _frame_locks[self.cam_id]:
                        current_frame = latest_frames[self.cam_id]
                        if current_frame is not None:
                            success, encoded_img = cv2.imencode('.jpg', current_frame)
                            if success:
                                image_bytes = encoded_img.tobytes()
                    # Prepare chat list
                    with _phone_lock:
                        chats = list(camera_phones.get(self.cam_id, []))
                        if not chats and DEFAULT_CHAT_ID:
                            chats = [DEFAULT_CHAT_ID]
                    if chats and (now - last_sms_time[self.cam_id] >= SMS_COOLDOWN_SECONDS):
                        last_sms_time[self.cam_id] = now
                        for chat_id in chats:
                            threading.Thread(
                                target=send_telegram_alert,
                                args=(chat_id, self.cam_id, best_monkey_conf, image_bytes),
                                daemon=True
                            ).start()
                    # Supabase logging (only on debounced alert)
                    if debounced_alert:
                        det_time_str = datetime.datetime.now().strftime("Today, %I:%M %p")
                        last_detection_times[self.cam_id] = det_time_str
                        # Log detection to Supabase DB asynchronously
                        threading.Thread(
                            target=record_detection_supabase,
                            args=(self.cam_id, best_monkey_conf, image_bytes),
                            daemon=True
                        ).start()
                else:
                    if monkey_detected_in_frame:
                        log_msg(f"[Cam {self.cam_id}] Monkey seen (Debouncing count={consecutive_monkey_count}/{DEBOUNCE_FRAMES})")
                    send_arduino(b"0", "clear/no monkey")
                    stop_alert_sound()

            except Exception as exc:
                log_msg(f"[Cam {self.cam_id}] Inference processing error: {exc}")

detection_threads = {
    1: DetectionThread(cam_id=1),
    2: DetectionThread(cam_id=2)
}

# ---------------------------------------------------------------------------
# MJPEG Frame Generator
# ---------------------------------------------------------------------------
def generate_frames(cam_id: int):
    while running_cams[cam_id]:
        with _frame_locks[cam_id]:
            frame = latest_frames[cam_id]

        if frame is None:
            time.sleep(0.03)
            continue

        display = frame.copy()

        with _result_locks[cam_id]:
            result = last_results[cam_id]

        if result:
            debounced = result.get("debounced", False)
            raw_monkey = result.get("monkey_detected_raw", False)
            count = result.get("consecutive_count", 0)

            for item in result.get("boxes", []):
                x1, y1, x2, y2 = item["bbox"]
                conf = item["conf"]
                cname = item["cls_name"]
                is_m = item["is_monkey"]

                if is_m:
                    color = (0, 255, 0) if debounced else (0, 255, 255)
                    label = f"🐒 {cname}: {conf * 100:.1f}%"
                else:
                    color = (180, 180, 180)
                    label = f"{cname}: {conf * 100:.1f}%"

                # Draw bounding box
                cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

                # Draw label box
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                lbl_y = max(y1 - 8, th + 8)
                cv2.rectangle(display, (x1, lbl_y - th - 6), (x1 + tw + 6, lbl_y + 2), color, -1)
                cv2.putText(display, label, (x1 + 3, lbl_y - 3),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            # Header Overlay
            if debounced:
                cv2.putText(display, f"ALERT: MONKEY DETECTED [{count}/{DEBOUNCE_FRAMES}]", (10, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 255), 2)
            elif raw_monkey:
                cv2.putText(display, f"VERIFYING MONKEY... [{count}/{DEBOUNCE_FRAMES}]", (10, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
            else:
                cv2.putText(display, "STATUS: CLEAR (No Monkey)", (10, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 200, 200), 2)
        else:
            cv2.putText(display, "STATUS: INITIALIZING...", (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 200, 200), 2)

        ok, buf = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            buf.tobytes() +
            b"\r\n"
        )
        time.sleep(0.033)   # ~30 FPS

# ---------------------------------------------------------------------------
# Flask HTTP Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start/<int:cam_id>", methods=["POST"])
def start(cam_id):
    if cam_id not in [1, 2]:
        return "Invalid camera ID", 400
        
    if running_cams[cam_id]:
        return f"Camera {cam_id} already running", 200

    if not camera_threads[cam_id].open():
        return f"Failed to open webcam {cam_id}", 500

    with _result_locks[cam_id]:
        last_results[cam_id] = None
        
    global _detection_state
    _detection_state = None
    running_cams[cam_id] = True
    log_msg(f"[Cam {cam_id}] Detection system started via /start endpoint")
    return f"Camera {cam_id} Started", 200

@app.route("/stop/<int:cam_id>", methods=["POST"])
def stop(cam_id):
    if cam_id not in [1, 2]:
        return "Invalid camera ID", 400
        
    if not running_cams[cam_id]:
        return f"Camera {cam_id} not running", 200

    running_cams[cam_id] = False
    time.sleep(0.15)
    camera_threads[cam_id].release()
    
    # If all cameras are stopped, turn off the alarm
    if not any(running_cams.values()):
        stop_alert_sound()
        send_arduino(b"0", "relay OFF on stop")
        
    log_msg(f"[Cam {cam_id}] Detection system stopped via /stop endpoint")
    return f"Camera {cam_id} Stopped", 200

@app.route("/video_feed/<int:cam_id>")
def video_feed(cam_id):
    if cam_id not in [1, 2]:
        return "Invalid camera ID", 400
        
    return Response(
        generate_frames(cam_id),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma":        "no-cache",
            "Expires":       "0",
            "Access-Control-Allow-Origin": "*",
        },
    )

@app.route("/status")
def status():
    """Health-check endpoint for the frontend to poll."""
    response_data = {}
    
    for cid in [1, 2]:
        with _result_locks[cid]:
            result = last_results[cid]
        monkey_alert = False
        confidence = 0.0
        if result:
            monkey_alert = result.get("debounced", False)
            confidence = result.get("best_conf", 0.0)
        with _phone_lock:
            phones = list(camera_phones.get(cid, []))
            
        response_data[f"cam{cid}"] = {
            "running": running_cams[cid],
            "monkey_alert": monkey_alert,
            "confidence": round(confidence * 100, 1),
            "camera_online": running_cams[cid],
            "phones": phones,
            "last_detection": last_detection_times.get(cid)
        }
    
    return jsonify(response_data)

@app.route("/set_phone/<int:cam_id>", methods=["POST"])
def set_phone(cam_id):
    """Add a phone number to the alert list for a given camera."""
    from flask import request
    if cam_id not in [1, 2]:
        return jsonify({"error": "Invalid camera ID"}), 400
    data = request.get_json()
    if not data or "phone" not in data:
        return jsonify({"error": "Missing 'phone' field in JSON body"}), 400
    phone = str(data["phone"]).strip()
    if not phone:
        return jsonify({"error": "Phone number cannot be empty"}), 400
    with _phone_lock:
        if phone not in camera_phones[cam_id]:
            camera_phones[cam_id].append(phone)
        phones = list(camera_phones[cam_id])
    log_msg(f"[Cam {cam_id}] Alert phone added: {phone} (total: {len(phones)})")
    return jsonify({"success": True, "cam_id": cam_id, "phones": phones})

@app.route("/remove_phone/<int:cam_id>/<int:idx>", methods=["POST"])
def remove_phone(cam_id, idx):
    """Remove a phone number by index from the alert list for a given camera."""
    if cam_id not in [1, 2]:
        return jsonify({"error": "Invalid camera ID"}), 400
    with _phone_lock:
        phones = camera_phones[cam_id]
        if idx < 0 or idx >= len(phones):
            return jsonify({"error": "Index out of range"}), 400
        removed = phones.pop(idx)
        phones_copy = list(phones)
    log_msg(f"[Cam {cam_id}] Alert phone removed: {removed} (remaining: {len(phones_copy)})")
    return jsonify({"success": True, "cam_id": cam_id, "phones": phones_copy})

# ---------------------------------------------------------------------------
# Graceful Shutdown Handler
# ---------------------------------------------------------------------------
def _shutdown(signum=None, frame_arg=None):
    for cid in [1, 2]:
        running_cams[cid] = False
        camera_threads[cid].release()
    stop_alert_sound()
    if arduino:
        try:
            if arduino.is_open:
                arduino.write(b"0")
                arduino.flush()
                arduino.close()
        except Exception:
            pass
    log_msg("Application shutdown complete.")
    if signum is not None:
        sys.exit(0)

for _sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(_sig, _shutdown)
atexit.register(_shutdown)

# ---------------------------------------------------------------------------
# Program Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Sync previous detection history from Supabase if online
    load_last_detections_from_supabase()

    # Auto-start cameras and detection on boot so frontend gets a live stream immediately
    for cid in [1, 2]:
        if camera_threads[cid].open():
            with _result_locks[cid]:
                last_results[cid] = None
            _detection_state = None
            running_cams[cid] = True
            log_msg(f"Camera {cid} auto-started on boot.")
        else:
            log_msg(f"WARNING: Camera {cid} auto-start failed. POST /start/{cid} when camera is ready.")

        camera_threads[cid].start()
        detection_threads[cid].start()
        
    log_msg("Starting Flask application server on http://127.0.0.1:5000")
    app.run(debug=False, use_reloader=False, host="0.0.0.0", port=5000, threaded=True)
