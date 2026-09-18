"""
Arduino Communication Module for KhetRakshak Backend.

Manages USB Serial communications with an Arduino Uno controlling hardware peripherals
(Flash Light & Speaker).
"""

import time
from typing import Optional
import serial
from serial import SerialException
from app.utils.logger import get_logger

# Import configuration settings
try:
    from app.config.config import Config
    _cfg = Config()
    SERIAL_PORT = getattr(_cfg, "SERIAL_PORT", "COM3")
    BAUD_RATE = getattr(_cfg, "BAUD_RATE", 9600)
except Exception:
    from app.config.settings import settings
    SERIAL_PORT = getattr(settings, "ARDUINO_PORT", "COM3")
    BAUD_RATE = getattr(settings, "ARDUINO_BAUD_RATE", 9600)

logger = get_logger(__name__)


class ArduinoController:
    """Serial controller interface for managing Arduino Uno hardware peripherals."""

    def __init__(
        self,
        port: Optional[str] = None,
        baud_rate: Optional[int] = None,
        timeout: float = 2.0
    ) -> None:
        self.port: str = port or SERIAL_PORT
        self.baud_rate: int = baud_rate or BAUD_RATE
        self.timeout: float = timeout
        self.serial_conn: Optional[serial.Serial] = None

        self.connect()

    def connect(self) -> bool:
        """Establishes a serial connection with the Arduino board."""
        if self.serial_conn and self.serial_conn.is_open:
            return True

        try:
            logger.info(f"Connecting to Arduino on port {self.port} at {self.baud_rate} baud...")
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout
            )
            time.sleep(2.0)
            initial_resp = self.read_response()
            if initial_resp:
                logger.info(f"Arduino startup response: {initial_resp}")
            logger.info(f"Connected to Arduino on {self.port}.")
            return True
        except SerialException as e:
            logger.error(f"Failed to connect to Arduino on port {self.port}: {e}")
            self.serial_conn = None
            return False
        except Exception as e:
            logger.error(f"Error during serial connection: {e}")
            self.serial_conn = None
            return False

    def disconnect(self) -> None:
        """Closes the active serial connection safely."""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
                logger.info(f"Closed serial connection on port {self.port}.")
            except SerialException as e:
                logger.error(f"Error while closing serial connection: {e}")
            finally:
                self.serial_conn = None

    def _ensure_connection(self) -> bool:
        """Internal check to verify connection state and auto-reconnect if link dropped."""
        if self.serial_conn and self.serial_conn.is_open:
            return True
        logger.warning("Arduino connection lost. Reconnecting...")
        return self.connect()

    def send_command(self, command: str) -> bool:
        """Sends a plain text command string to the Arduino."""
        if not self._ensure_connection():
            logger.error(f"Cannot send command '{command}': Arduino disconnected.")
            return False

        try:
            formatted_cmd = f"{command.strip().upper()}\n"
            self.serial_conn.write(formatted_cmd.encode("utf-8"))
            self.serial_conn.flush()
            logger.info(f"Sent command to Arduino: '{command.strip()}'")
            return True
        except SerialException as e:
            logger.error(f"SerialException sending command '{command}': {e}")
            self.disconnect()
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending command '{command}': {e}")
            return False

    def read_response(self) -> Optional[str]:
        """Reads and returns line response sent back from Arduino."""
        if not self.serial_conn or not self.serial_conn.is_open:
            return None

        try:
            if self.serial_conn.in_waiting > 0:
                line = self.serial_conn.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    logger.debug(f"Received response: '{line}'")
                    return line
            return None
        except SerialException as e:
            logger.error(f"SerialException reading response: {e}")
            self.disconnect()
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading response: {e}")
            return None

    def speaker_on(self) -> Optional[str]:
        """Turns ON the deterrence speaker."""
        if self.send_command("SPEAKER_ON"):
            time.sleep(0.1)
            return self.read_response() or "SPEAKER_ACTIVE"
        return None

    def speaker_off(self) -> Optional[str]:
        """Turns OFF the deterrence speaker."""
        if self.send_command("SPEAKER_OFF"):
            time.sleep(0.1)
            return self.read_response() or "OK"
        return None

    def flash_on(self) -> Optional[str]:
        """Turns ON the flash light."""
        if self.send_command("FLASH_ON"):
            time.sleep(0.1)
            return self.read_response() or "FLASH_ACTIVE"
        return None

    def flash_off(self) -> Optional[str]:
        """Turns OFF the flash light."""
        if self.send_command("FLASH_OFF"):
            time.sleep(0.1)
            return self.read_response() or "OK"
        return None

    def heartbeat(self) -> Optional[str]:
        """Sends a HEARTBEAT signal to check Arduino status."""
        if self.send_command("HEARTBEAT"):
            time.sleep(0.1)
            return self.read_response() or "READY"
        return None


# Global singleton instance
arduino_controller = ArduinoController()
