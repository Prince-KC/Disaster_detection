"""
LoRa Offline Emergency Alert Service for विपद्Sathi (BipatSathi).

Manages USB serial communications with a LoRa radio transmitter module (Sender.ino)
at 433 MHz, providing long-range offline disaster early warning broadcasts to
remote villages, ranger outposts, and siren stations without requiring internet,
cellular data, or electrical grid access.
"""

import os
import time
import threading
import datetime
from typing import Optional, Dict, Any, List
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Defaults
DEFAULT_LORA_PORT = "COM8"
DEFAULT_LORA_BAUD_RATE = 9600


class LoRaService:
    """
    Service responsible for dispatching offline disaster alerts over LoRa RF.
    Maintains thread-safe serial communication with the LoRa transmitter node
    and provides a simulation fallback when hardware is disconnected.
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baud_rate: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        self.port: str = port or os.getenv("LORA_PORT", DEFAULT_LORA_PORT).strip()
        self.baud_rate: int = baud_rate or int(os.getenv("LORA_BAUD_RATE", str(DEFAULT_LORA_BAUD_RATE)))
        self.enabled: bool = (
            enabled
            if enabled is not None
            else os.getenv("LORA_ENABLED", "true").lower() in ("true", "1", "t", "yes")
        )

        self._serial_conn = None
        self._lock = threading.Lock()
        self.connected: bool = False
        self.total_alerts_sent: int = 0
        self.last_alert_payload: Optional[str] = None
        self.last_alert_time: Optional[str] = None
        self.recent_logs: List[Dict[str, Any]] = []

        if self.enabled:
            self._init_connection()

    def _init_connection(self) -> bool:
        """Attempts to open serial connection to the LoRa transmitter board."""
        try:
            import serial
            from serial import SerialException
        except ImportError:
            logger.warning("[LoRaService] pyserial library not found. Running in simulation mode.")
            self.connected = False
            return False

        with self._lock:
            try:
                logger.info(f"[LoRaService] Connecting to LoRa transmitter on {self.port} @ {self.baud_rate} baud...")
                self._serial_conn = serial.Serial(
                    port=self.port,
                    baudrate=self.baud_rate,
                    timeout=2.0,
                    write_timeout=2.0
                )
                time.sleep(1.5)  # Allow Arduino/ESP to settle after DTR reset
                self.connected = True
                logger.info(f"[LoRaService] Successfully connected to LoRa transmitter on {self.port}.")
                self._log_event("CONNECTION", f"Connected to transmitter on {self.port} ({self.baud_rate} baud)")
                return True
            except (SerialException, OSError) as e:
                self.connected = False
                self._serial_conn = None
                logger.warning(
                    f"[LoRaService] Hardware not detected on {self.port} ({e}). "
                    "Offline LoRa service will run in simulated broadcast mode."
                )
                self._log_event("STANDBY", f"Hardware standby on {self.port} (Simulation mode active)")
                return False

    def _log_event(self, event_type: str, message: str, payload: Optional[str] = None) -> None:
        """Appends a timestamped log to the in-memory recent event history."""
        entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "type": event_type,
            "message": message,
            "payload": payload,
            "mode": "HARDWARE" if self.connected else "SIMULATED",
        }
        self.recent_logs.insert(0, entry)
        if len(self.recent_logs) > 50:
            self.recent_logs.pop()

    def disconnect(self) -> None:
        """Closes the active serial connection safely."""
        with self._lock:
            if self._serial_conn and self._serial_conn.is_open:
                try:
                    self._serial_conn.close()
                    logger.info(f"[LoRaService] Closed serial connection on {self.port}.")
                except Exception as e:
                    logger.error(f"[LoRaService] Error closing serial connection: {e}")
                finally:
                    self._serial_conn = None
                    self.connected = False

    def reconnect(self, port: Optional[str] = None, baud_rate: Optional[int] = None) -> Dict[str, Any]:
        """Dynamically reconfigures port or retries connection."""
        if port:
            self.port = port.strip()
        if baud_rate:
            self.baud_rate = baud_rate

        self.disconnect()
        success = self._init_connection()
        return {
            "success": success,
            "connected": self.connected,
            "port": self.port,
            "baud_rate": self.baud_rate,
            "mode": "HARDWARE" if self.connected else "SIMULATED",
        }

    def broadcast(self, alert_payload: str) -> Dict[str, Any]:
        """
        Sends an alert payload across LoRa RF via serial transmission to Sender.ino,
        or simulates delivery if no hardware transmitter is connected.
        """
        alert_payload = alert_payload.strip()
        if not alert_payload:
            return {"success": False, "error": "Empty payload"}

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.last_alert_payload = alert_payload
        self.last_alert_time = now_str
        self.total_alerts_sent += 1

        # Attempt hardware dispatch if connected
        if self.connected and self._serial_conn:
            with self._lock:
                try:
                    tx_line = f"{alert_payload}\n".encode("utf-8")
                    self._serial_conn.write(tx_line)
                    self._serial_conn.flush()
                    logger.info(f"[LoRa RF TX] Dispatched packet to {self.port}: {alert_payload}")
                    self._log_event("BROADCAST", "Dispatched to LoRa transmitter hardware", alert_payload)
                    return {
                        "success": True,
                        "mode": "HARDWARE",
                        "port": self.port,
                        "payload": alert_payload,
                        "timestamp": now_str,
                    }
                except Exception as e:
                    logger.error(f"[LoRaService] Serial write error on {self.port}: {e}")
                    self.connected = False
                    self._serial_conn = None

        # Fallback to simulated broadcast
        logger.info(f"[LoRa RF TX - SIMULATED] Broadcast to offline communities: {alert_payload}")
        self._log_event("BROADCAST", "Dispatched via simulated radio channel", alert_payload)
        return {
            "success": True,
            "mode": "SIMULATED",
            "port": self.port,
            "payload": alert_payload,
            "timestamp": now_str,
            "note": "Hardware transmitter not connected; packet logged to system simulation channel.",
        }

    # -------------------------------------------------------------------------
    # High-level Alert Methods
    # -------------------------------------------------------------------------
    def send_detection_alert(
        self,
        cam_id: int,
        class_name: str,
        confidence: float,
        vehicle_info: Optional[Dict[str, Any]] = None,
        location: str = "Bagmati Monitoring Zone",
    ) -> Dict[str, Any]:
        """
        Formats and broadcasts a verified camera AI detection emergency alert.
        Packets are kept concise (under 240 bytes) for optimal LoRa airtime and reach.
        """
        event_name = class_name.replace("_", " ").upper()
        conf_pct = round(confidence * 100, 1) if confidence <= 1.0 else round(confidence, 1)
        time_str = datetime.datetime.now().strftime("%I:%M %p")

        # Format compact radio packet
        payload = f"[विपद्Sathi-LORA] 🚨 ALERT: {event_name} | CAM: CAM-0{cam_id} | CONF: {conf_pct}% | LOC: {location} | TIME: {time_str}"
        
        # Add vehicle/casualty summary if accident
        if vehicle_info and vehicle_info.get("vehicles_line"):
            v_line = vehicle_info.get("vehicles_line")
            payload += f" | VEHICLES: {v_line}"

        return self.broadcast(payload)

    def send_citizen_alert(
        self,
        report_id: str,
        incident_type: str,
        location: str,
        incident_time: str,
    ) -> Dict[str, Any]:
        """
        Formats and broadcasts an emergency alert for a verified citizen incident report.
        """
        now_str = datetime.datetime.now().strftime("%I:%M %p")
        payload = f"[विपद्Sathi-LORA] 🚨 CITIZEN REPORT: {incident_type.upper()} | ID: {report_id} | LOC: {location} | REPORTED: {incident_time or now_str}"
        return self.broadcast(payload)

    def send_custom_alert(self, message: str) -> Dict[str, Any]:
        """Sends a custom emergency broadcast message."""
        payload = f"[विपद्Sathi-LORA] ⚠️ BROADCAST: {message.strip()}"
        return self.broadcast(payload)

    def test_alert(self) -> Dict[str, Any]:
        """Sends a verification radio test packet."""
        test_payload = f"[विपद्Sathi-LORA] 📡 TEST: Radio Grid Online @ {datetime.datetime.now().strftime('%I:%M:%S %p')}"
        return self.broadcast(test_payload)

    def get_status(self) -> Dict[str, Any]:
        """Returns current operational status and telemetry for dashboard display."""
        available_ports = []
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            available_ports = [p.device for p in ports]
        except Exception:
            pass

        return {
            "enabled": self.enabled,
            "connected": self.connected,
            "mode": "HARDWARE" if self.connected else "SIMULATED",
            "port": self.port,
            "baud_rate": self.baud_rate,
            "frequency": "433 MHz (ISM Band)",
            "available_ports": available_ports,
            "total_alerts_sent": self.total_alerts_sent,
            "last_alert_payload": self.last_alert_payload,
            "last_alert_time": self.last_alert_time,
            "recent_logs": self.recent_logs[:15],
        }


# Global Singleton Instance
lora_service = LoRaService()
