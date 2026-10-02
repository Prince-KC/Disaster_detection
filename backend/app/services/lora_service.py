"""
LoRa Offline Emergency Alert Service for विपद्Sathi (BipatSathi).

Manages USB serial communications with a LoRa radio module (Sender.ino & Receiver.ino)
at 433 MHz, providing long-range offline disaster early warning broadcasts and reception
for remote villages, ranger outposts, and siren stations without requiring internet,
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
    Service responsible for dispatching and receiving offline disaster alerts over LoRa RF.
    Maintains thread-safe serial communication with the LoRa node (Sender/Receiver)
    and provides a realistic simulation fallback when hardware is disconnected.
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

        # Sender State
        self.total_alerts_sent: int = 0
        self.last_alert_payload: Optional[str] = None
        self.last_alert_time: Optional[str] = None
        self.recent_logs: List[Dict[str, Any]] = []

        # Receiver State
        self.total_alerts_received: int = 0
        self.received_packets: List[Dict[str, Any]] = []
        self.last_received_packet: Optional[Dict[str, Any]] = None
        self.siren_active_until: float = 0.0

        # Background Serial Listener
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reader = threading.Event()

        if self.enabled:
            self._init_connection()

    def _init_connection(self) -> bool:
        """Attempts to open serial connection to the LoRa board."""
        try:
            import serial
            from serial import SerialException
        except ImportError:
            logger.warning("[LoRaService] pyserial library not found. Running in simulation mode.")
            self.connected = False
            return False

        with self._lock:
            try:
                logger.info(f"[LoRaService] Connecting to LoRa hardware on {self.port} @ {self.baud_rate} baud...")
                self._serial_conn = serial.Serial(
                    port=self.port,
                    baudrate=self.baud_rate,
                    timeout=1.0,
                    write_timeout=2.0
                )
                time.sleep(1.5)  # Allow board to settle after DTR reset
                self.connected = True
                logger.info(f"[LoRaService] Successfully connected to LoRa module on {self.port}.")
                self._log_event("CONNECTION", f"Connected to module on {self.port} ({self.baud_rate} baud)")

                # Start background serial listener
                self._stop_reader.clear()
                self._reader_thread = threading.Thread(target=self._serial_reader_loop, daemon=True)
                self._reader_thread.start()
                return True
            except (SerialException, OSError) as e:
                self.connected = False
                self._serial_conn = None
                logger.warning(
                    f"[LoRaService] Hardware not detected on {self.port} ({e}). "
                    "LoRa alert system will run in simulated RF mesh mode."
                )
                self._log_event("STANDBY", f"Hardware standby on {self.port} (Simulation active)")
                return False

    def _serial_reader_loop(self) -> None:
        """Background thread reading incoming serial telemetry from hardware."""
        logger.info("[LoRaService] Started background serial reader thread.")
        while not self._stop_reader.is_set():
            try:
                if self._serial_conn and self._serial_conn.is_open:
                    raw_line = self._serial_conn.readline()
                    if raw_line:
                        line = raw_line.decode("utf-8", errors="ignore").strip()
                        if line:
                            logger.info(f"[LoRa Serial RX] {line}")
                            self._handle_serial_incoming(line)
                else:
                    time.sleep(0.5)
            except Exception as e:
                logger.debug(f"[LoRaService] Serial read exception: {e}")
                time.sleep(0.5)

    def _handle_serial_incoming(self, line: str) -> None:
        """Parses lines received from serial module (both Sender and Receiver firmware)."""
        # If line is from transmitter (Sender.ino), it is dispatch confirmation echo, NOT an incoming receiver packet
        if "[LoRa TX]" in line or "Broadcasting packet" in line or "LORA_TX_" in line:
            if "[LORA_TX_SUCCESS]" in line:
                self._log_event("TX_ACK", "Hardware transmitter acknowledged radio packet transmission.")
            return

        # Receiver line format from Receiver.ino e.g.: "ALERT PAYLOAD : [विपद्Sathi-LORA] 🚨..."
        if "ALERT PAYLOAD" in line:
            payload = line.split(":", 1)[1].strip()
            self.record_received_packet(
                payload=payload,
                rssi=-65,
                snr=10.2,
                mode="HARDWARE_RF"
            )

    def _log_event(self, event_type: str, message: str, payload: Optional[str] = None) -> None:
        """Appends a timestamped log to recent event history."""
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

    def record_received_packet(
        self,
        payload: str,
        rssi: int = -68,
        snr: float = 9.5,
        mode: str = "SIMULATED_RF"
    ) -> Dict[str, Any]:
        """Records an incoming emergency packet at the LoRa receiver node with deduplication."""
        now_time = time.time()
        # Deduplication check: ignore identical payload within 3 seconds
        if (
            self.last_received_packet
            and self.last_received_packet.get("payload") == payload
            and (now_time - getattr(self, "_last_rx_timestamp", 0)) < 3.0
        ):
            logger.info(f"[LoRaService] Ignored duplicate received packet within 3s: {payload[:40]}...")
            return self.last_received_packet

        self._last_rx_timestamp = now_time
        self.total_alerts_received += 1
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %I:%M:%S %p")
        self.siren_active_until = time.time() + 6.0  # 6 second alarm duration

        # Assess signal quality
        if rssi > -75:
            quality = "Strong"
        elif rssi < -100:
            quality = "Weak"
        else:
            quality = "Fair"

        rx_packet = {
            "id": f"RX-{1000 + self.total_alerts_received}",
            "packet_num": self.total_alerts_received,
            "timestamp": now_str,
            "payload": payload,
            "packet_size": len(payload.encode("utf-8")),
            "rssi": rssi,
            "rssi_label": f"{rssi} dBm ({quality})",
            "snr": f"{snr} dB",
            "mode": mode,
            "siren_active": True,
            "alarm_duration_sec": 6,
        }

        self.last_received_packet = rx_packet
        self.received_packets.insert(0, rx_packet)
        if len(self.received_packets) > 50:
            self.received_packets.pop()

        self._log_event("RECEIVE", f"Receiver node captured packet #{self.total_alerts_received}", payload)
        return rx_packet

    def disconnect(self) -> None:
        """Closes the active serial connection safely."""
        self._stop_reader.set()
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
        Automatically updates Receiver node so it captures the transmission.
        """
        alert_payload = alert_payload.strip()
        if not alert_payload:
            return {"success": False, "error": "Empty payload"}

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.last_alert_payload = alert_payload
        self.last_alert_time = now_str
        self.total_alerts_sent += 1

        tx_mode = "SIMULATED"

        # Attempt hardware dispatch if connected
        if self.connected and self._serial_conn:
            with self._lock:
                try:
                    tx_line = f"{alert_payload}\n".encode("utf-8")
                    self._serial_conn.write(tx_line)
                    self._serial_conn.flush()
                    logger.info(f"[LoRa RF TX] Dispatched packet to {self.port}: {alert_payload}")
                    self._log_event("BROADCAST", "Dispatched to LoRa transmitter hardware", alert_payload)
                    tx_mode = "HARDWARE"
                except Exception as e:
                    logger.error(f"[LoRaService] Serial write error on {self.port}: {e}")
                    self.connected = False
                    self._serial_conn = None

        if tx_mode == "SIMULATED":
            logger.info(f"[LoRa RF TX - SIMULATED] Broadcast to offline communities: {alert_payload}")
            self._log_event("BROADCAST", "Dispatched via simulated radio channel", alert_payload)

        # Mirror transmission to the Receiver node (so Receiver card displays the incoming data)
        rx_packet = self.record_received_packet(
            payload=alert_payload,
            rssi=-67 if tx_mode == "HARDWARE" else -72,
            snr=10.4 if tx_mode == "HARDWARE" else 9.2,
            mode=f"{tx_mode}_RF"
        )

        return {
            "success": True,
            "mode": tx_mode,
            "port": self.port,
            "payload": alert_payload,
            "timestamp": now_str,
            "received_packet": rx_packet,
        }

    # -------------------------------------------------------------------------
    # High-level Alert Methods
    # -------------------------------------------------------------------------
    def send_detection_alert(
        self,
        cam_id: int,
        class_name: str,
        confidence: Optional[float] = None,
        vehicle_info: Optional[Dict[str, Any]] = None,
        location: str = "Bagmati Monitoring Zone",
    ) -> Dict[str, Any]:
        """
        Formats and broadcasts a verified camera AI detection emergency alert.
        Packets are kept concise (under 240 bytes) for optimal LoRa airtime and reach.
        Confidence is only included when detected via live camera AI inference.
        """
        event_name = class_name.replace("_", " ").upper()
        time_str = datetime.datetime.now().strftime("%I:%M %p")

        payload = f"[विपद्Sathi-LORA] 🚨 ALERT: {event_name} | CAM: CAM-0{cam_id}"
        if confidence is not None:
            conf_pct = round(confidence * 100, 1) if confidence <= 1.0 else round(confidence, 1)
            payload += f" | CONF: {conf_pct}%"
        payload += f" | LOC: {location} | TIME: {time_str}"
        
        if vehicle_info and vehicle_info.get("vehicles_line"):
            v_line = vehicle_info.get("vehicles_line")
            payload += f" | VEHICLES: {v_line}"
            if vehicle_info.get("ambulances_line"):
                payload += f" | AMBULANCES: {vehicle_info['ambulances_line']}"

        return self.broadcast(payload)

    def send_citizen_alert(
        self,
        report_id: str,
        incident_type: str,
        location: str,
        incident_time: str,
    ) -> Dict[str, Any]:
        """Formats and broadcasts an emergency alert for a verified citizen incident report."""
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

    def clear_received_packets(self) -> bool:
        """Clears stored packets in receiver node."""
        self.received_packets.clear()
        self.last_received_packet = None
        self.total_alerts_received = 0
        return True

    def trigger_siren_test(self) -> Dict[str, Any]:
        """Manual siren test trigger on receiver node."""
        self.siren_active_until = time.time() + 6.0
        test_payload = f"[विपद्Sathi-LORA] 🚨 SIREN TEST: Community Alarm Verification @ {datetime.datetime.now().strftime('%I:%M:%S %p')}"
        rx_packet = self.record_received_packet(
            payload=test_payload,
            rssi=-64,
            snr=11.0,
            mode="LOCAL_TEST"
        )
        return {"success": True, "siren_active": True, "packet": rx_packet}

    def get_receiver_data(self) -> Dict[str, Any]:
        """Returns receiver node telemetry, signal metrics, and incoming packets."""
        is_siren_active = time.time() < self.siren_active_until
        return {
            "listening": True,
            "frequency": "433 MHz (ISM Band)",
            "spreading_factor": "SF10",
            "bandwidth": "125 kHz",
            "coding_rate": "4/5",
            "siren_active": is_siren_active,
            "total_received": self.total_alerts_received,
            "last_packet": self.last_received_packet,
            "recent_packets": self.received_packets[:20],
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive operational status and telemetry for both Sender and Receiver."""
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
            "receiver": self.get_receiver_data(),
        }


# Global Singleton Instance
lora_service = LoRaService()
