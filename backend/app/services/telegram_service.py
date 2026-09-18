"""
Telegram Notification Service Module for KhetRakshak Backend.

Provides a clean interface for dispatching text alerts and photo snapshots
to farmers and administrators via the Telegram Bot API with automatic retries.
"""

import os
import time
import requests
from datetime import datetime
from typing import Optional, Dict, Any, Union
from app.utils.logger import get_logger

# Import Configuration Settings
try:
    from config import Config
    _cfg = Config()
    TELEGRAM_BOT_TOKEN = getattr(_cfg, "TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = getattr(_cfg, "TELEGRAM_CHAT_ID", "")
except Exception:
    try:
        from app.config.config import Config
        _cfg = Config()
        TELEGRAM_BOT_TOKEN = getattr(_cfg, "TELEGRAM_BOT_TOKEN", "")
        TELEGRAM_CHAT_ID = getattr(_cfg, "TELEGRAM_CHAT_ID", "")
    except Exception:
        from app.config.settings import settings
        TELEGRAM_BOT_TOKEN = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        TELEGRAM_CHAT_ID = getattr(settings, "TELEGRAM_CHAT_ID", "")

logger = get_logger(__name__)


class TelegramService:
    """
    Service class managing Telegram Bot HTTP API notifications.
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> None:
        """
        Initializes the TelegramService.

        Args:
            bot_token (Optional[str]): Telegram Bot Token (from BotFather).
            chat_id (Optional[str]): Target Telegram Chat or Group ID.
            max_retries (int): Maximum retry attempts for failed requests.
            retry_delay (float): Delay in seconds between retries.
        """
        self.bot_token: str = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id: str = chat_id or TELEGRAM_CHAT_ID
        self.max_retries: int = max_retries
        self.retry_delay: float = retry_delay

        if not self.bot_token:
            logger.warning("Telegram Bot Token is not configured.")

    def _get_api_url(self, method: str) -> str:
        """Helper to construct Telegram Bot API method URL."""
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    def send_text_message(
        self,
        message: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML"
    ) -> Dict[str, Any]:
        """
        Sends a text message to a Telegram chat with automatic retry logic.

        Args:
            message (str): Text content.
            chat_id (Optional[str]): Target chat ID (defaults to config chat ID).
            parse_mode (str): Formatting mode ('HTML' or 'MarkdownV2').

        Returns:
            Dict[str, Any]: Structured execution outcome.
        """
        target_chat = chat_id or self.chat_id
        if not self.bot_token or not target_chat:
            logger.error("Cannot send Telegram message: Bot Token or Chat ID is missing.")
            return {"success": False, "error": "Missing credentials", "message_id": None}

        url = self._get_api_url("sendMessage")
        payload = {
            "chat_id": target_chat,
            "text": message,
            "parse_mode": parse_mode
        }

        logger.info(f"Sending Telegram text message to {target_chat}...")

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(url, json=payload, timeout=10)
                res_data = resp.json()

                if resp.status_code == 200 and res_data.get("ok"):
                    msg_id = res_data.get("result", {}).get("message_id")
                    logger.info(f"Telegram text message delivered successfully (Msg ID: {msg_id}).")
                    return {"success": True, "message_id": msg_id, "response": res_data}
                else:
                    err_msg = res_data.get("description", resp.text)
                    logger.warning(f"Telegram API error (Attempt {attempt}/{self.max_retries}): {err_msg}")

            except Exception as e:
                logger.error(f"Network exception sending Telegram message (Attempt {attempt}/{self.max_retries}): {e}")

            if attempt < self.max_retries:
                time.sleep(self.retry_delay)

        return {"success": False, "error": "Max retries exceeded", "message_id": None}

    def send_photo(
        self,
        photo: str,
        caption: Optional[str] = None,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML"
    ) -> Dict[str, Any]:
        """
        Sends a photo snapshot with optional text caption to Telegram.

        Args:
            photo (str): Local image file path or public HTTP image URL.
            caption (Optional[str]): Photo caption text.
            chat_id (Optional[str]): Target chat ID.
            parse_mode (str): Formatting mode ('HTML' or 'MarkdownV2').

        Returns:
            Dict[str, Any]: Structured execution outcome.
        """
        target_chat = chat_id or self.chat_id
        if not self.bot_token or not target_chat:
            logger.error("Cannot send Telegram photo: Bot Token or Chat ID is missing.")
            return {"success": False, "error": "Missing credentials", "message_id": None}

        url = self._get_api_url("sendPhoto")
        logger.info(f"Sending Telegram photo to {target_chat}...")

        if photo.startswith("http://") or photo.startswith("https://"):
            payload = {
                "chat_id": target_chat,
                "photo": photo,
                "caption": caption or "",
                "parse_mode": parse_mode
            }
            for attempt in range(1, self.max_retries + 1):
                try:
                    resp = requests.post(url, json=payload, timeout=15)
                    res_data = resp.json()
                    if resp.status_code == 200 and res_data.get("ok"):
                        msg_id = res_data.get("result", {}).get("message_id")
                        logger.info(f"Telegram photo (URL) delivered successfully (Msg ID: {msg_id}).")
                        return {"success": True, "message_id": msg_id, "response": res_data}
                except Exception as e:
                    logger.error(f"Error sending photo URL (Attempt {attempt}): {e}")
                time.sleep(self.retry_delay)

        elif os.path.exists(photo):
            for attempt in range(1, self.max_retries + 1):
                try:
                    with open(photo, "rb") as file_obj:
                        files = {"photo": file_obj}
                        data = {
                            "chat_id": target_chat,
                            "caption": caption or "",
                            "parse_mode": parse_mode
                        }
                        resp = requests.post(url, data=data, files=files, timeout=20)
                        res_data = resp.json()
                        if resp.status_code == 200 and res_data.get("ok"):
                            msg_id = res_data.get("result", {}).get("message_id")
                            logger.info(f"Telegram photo (File) delivered successfully (Msg ID: {msg_id}).")
                            return {"success": True, "message_id": msg_id, "response": res_data}
                except Exception as e:
                    logger.error(f"Error uploading local photo file (Attempt {attempt}): {e}")
                time.sleep(self.retry_delay)
        else:
            logger.error(f"Local photo file not found: {photo}")
            return {"success": False, "error": "Photo file not found", "message_id": None}

        return {"success": False, "error": "Max retries exceeded", "message_id": None}

    def format_detection_message(
        self,
        camera_name: str,
        zone: str,
        confidence: float,
        detection_time: Optional[str] = None,
        device_status: str = "ALERT",
        speaker_activated: bool = True,
        flash_activated: bool = True
    ) -> str:
        """
        Formats a structured HTML notification message for Telegram.

        Returns:
            str: Formatted HTML message.
        """
        time_str = detection_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        speaker_str = "🔊 Yes" if speaker_activated else "🔇 No"
        flash_str = "⚡ Yes" if flash_activated else "⚪ No"

        formatted_msg = (
            f"🚨 <b>Monkey Detection Alert</b> 🚨\n\n"
            f"🎥 <b>Camera:</b> {camera_name}\n"
            f"📍 <b>Zone:</b> {zone}\n"
            f"🎯 <b>Confidence:</b> {confidence:.1f}%\n"
            f"🕒 <b>Time:</b> {time_str}\n"
            f"🔴 <b>Device Status:</b> {device_status}\n\n"
            f"<b>Deterrence Actions:</b>\n"
            f"• Speaker: {speaker_str}\n"
            f"• Flash Light: {flash_str}\n\n"
            f"<i>KhetRakshak Automated Crop Defense System</i>"
        )
        return formatted_msg

    def send_detection_alert(
        self,
        camera_name: str,
        zone: str,
        confidence: float,
        image_path_or_url: Optional[str] = None,
        detection_time: Optional[str] = None,
        device_status: str = "ALERT",
        speaker_activated: bool = True,
        flash_activated: bool = True,
        chat_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches a formatted detection alert (with image if available) to Telegram.

        Returns:
            Dict[str, Any]: Execution outcome metadata.
        """
        caption_text = self.format_detection_message(
            camera_name=camera_name,
            zone=zone,
            confidence=confidence,
            detection_time=detection_time,
            device_status=device_status,
            speaker_activated=speaker_activated,
            flash_activated=flash_activated
        )

        if image_path_or_url:
            return self.send_photo(
                photo=image_path_or_url,
                caption=caption_text,
                chat_id=chat_id,
                parse_mode="HTML"
            )
        else:
            return self.send_text_message(
                message=caption_text,
                chat_id=chat_id,
                parse_mode="HTML"
            )


# Global singleton instance
telegram_service = TelegramService()
