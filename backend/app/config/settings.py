"""
Settings configuration for the KhetRakshak backend.
Loads environment variables using python-dotenv.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings loaded from environment variables."""
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    SERIAL_PORT: str = os.getenv("SERIAL_PORT", "COM3")
    BAUD_RATE: int = int(os.getenv("BAUD_RATE", 9600))
    CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", 1))

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    MODEL_PATH: str = os.getenv("MODEL_PATH", "models/monkey_detector.pt")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

settings = Settings()
