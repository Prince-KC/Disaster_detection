"""
Configuration module for the KhetRakshak AI-powered monkey detection system.

This module loads environment variables from a `.env` file using `python-dotenv`,
validates required configuration keys, and exposes a strongly-typed `Config` class.
"""

import os
from typing import Optional
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Custom exception raised when configuration validation fails."""
    pass


class Config:
    """
    Application Configuration Class.
    
    Reads, parses, and validates all environment variables required by the system.
    """

    def __init__(self, env_path: Optional[str] = None) -> None:
        """
        Initializes configuration by loading `.env` file and validating variables.

        Args:
            env_path (Optional[str]): Custom path to `.env` file if applicable.
        """
        # Load environment variables from .env file
        if env_path:
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()

        # ----------------------------------------------------------------------
        # 1. Supabase Settings (Required)
        # ----------------------------------------------------------------------
        self.SUPABASE_URL: str = self._get_required_env("SUPABASE_URL")
        self.SUPABASE_SERVICE_KEY: str = self._get_required_env("SUPABASE_SERVICE_KEY")

        # ----------------------------------------------------------------------
        # 2. Telegram Bot API Settings (Required for farmer notifications)
        # ----------------------------------------------------------------------
        self.TELEGRAM_BOT_TOKEN: str = self._get_required_env("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_CHAT_ID: str = self._get_required_env("TELEGRAM_CHAT_ID")

        # ----------------------------------------------------------------------
        # 3. Hardware Serial & Camera Settings
        # ----------------------------------------------------------------------
        self.SERIAL_PORT: str = os.getenv("SERIAL_PORT", "COM3")
        self.BAUD_RATE: int = self._get_int_env("BAUD_RATE", default=9600)
        self.CAMERA_INDEX: int = self._get_int_env("CAMERA_INDEX", default=1)

        # ----------------------------------------------------------------------
        # 4. YOLO Model Settings
        # ----------------------------------------------------------------------
        self.MODEL_PATH: str = os.getenv("MODEL_PATH", "models/best.pt")
        self.YOLO_MODEL_PATH: str = os.getenv("MODEL_PATH", "models/best.pt")
        self.CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))

        # ----------------------------------------------------------------------
        # 5. Logging Settings
        # ----------------------------------------------------------------------
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    @staticmethod
    def _get_required_env(key: str) -> str:
        """
        Helper method to fetch a required environment variable.

        Raises:
            ConfigurationError: If the variable is missing or empty.
        """
        value = os.getenv(key)
        if not value or not value.strip():
            raise ConfigurationError(
                f"Missing required environment variable: '{key}'. "
                f"Please ensure it is defined in your .env file."
            )
        return value.strip()

    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """
        Helper method to parse integer environment variables safely.

        Raises:
            ConfigurationError: If the variable value cannot be converted to an integer.
        """
        raw_val = os.getenv(key)
        if raw_val is None or not raw_val.strip():
            return default
        try:
            return int(raw_val.strip())
        except ValueError:
            raise ConfigurationError(
                f"Invalid integer value for environment variable '{key}': '{raw_val}'"
            )


# Global instance for easy import across modules
# Note: Instantiate inside your entry point or import as needed
