"""
Supabase Service Module for KhetRakshak Backend.

Provides a clean interface for database and storage operations against Supabase.
Handles query execution, data validation, exception logging, and structured return values.
"""

import os
from typing import Dict, Any, Optional, List
from supabase import create_client, Client
from app.utils.logger import get_logger
from app.utils.exceptions import AppError

# Try loading from app.config.config or app.config.settings
try:
    from app.config.config import Config
    _cfg = Config()
    SUPABASE_URL = getattr(_cfg, "SUPABASE_URL", "")
    SUPABASE_KEY = getattr(_cfg, "SUPABASE_SERVICE_KEY", "") or getattr(_cfg, "SUPABASE_KEY", "")
except Exception:
    from app.config.settings import settings
    SUPABASE_URL = getattr(settings, "SUPABASE_URL", "")
    SUPABASE_KEY = getattr(settings, "SUPABASE_KEY", "")

logger = get_logger(__name__)


class SupabaseService:
    """
    Service class managing all database tables and storage buckets in Supabase.
    
    Tables managed:
    - farmers
    - devices
    - detections
    - speakers
    - speaker_logs
    - notifications
    - system_logs
    - analytics_daily
    """

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None) -> None:
        """
        Initializes the Supabase client instance once.
        """
        self.url = url or SUPABASE_URL
        self.key = key or SUPABASE_KEY

        if not self.url or not self.key:
            logger.warning("Supabase URL or Key is not configured.")
            self.client: Optional[Client] = None
        else:
            try:
                self.client: Client = create_client(self.url, self.key)
                logger.info("Supabase client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.client = None

    def _ensure_client(self) -> Client:
        """Internal helper to ensure client is connected before executing requests."""
        if not self.client:
            raise AppError("Supabase client is not initialized or configured.", status_code=500)
        return self.client

    # --------------------------------------------------------------------------
    # 1. Farmers Table Operations
    # --------------------------------------------------------------------------
    def get_farmer(self, farmer_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves farmer details by farmer_id.

        Args:
            farmer_id (str): Unique identifier of the farmer.

        Returns:
            Optional[Dict[str, Any]]: Record dictionary if found, else None.
        """
        client = self._ensure_client()
        try:
            response = client.table("farmers").select("*").eq("id", farmer_id).execute()
            data = response.data
            return data[0] if data else None
        except Exception as e:
            logger.error(f"Error fetching farmer (ID: {farmer_id}): {e}")
            raise AppError(f"Failed to fetch farmer details: {e}", status_code=500)

    # --------------------------------------------------------------------------
    # 2. Devices Table Operations
    # --------------------------------------------------------------------------
    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves device details by device_id.

        Args:
            device_id (str): Unique identifier of the device.

        Returns:
            Optional[Dict[str, Any]]: Record dictionary if found, else None.
        """
        client = self._ensure_client()
        try:
            response = client.table("devices").select("*").eq("id", device_id).execute()
            data = response.data
            return data[0] if data else None
        except Exception as e:
            logger.error(f"Error fetching device (ID: {device_id}): {e}")
            raise AppError(f"Failed to fetch device details: {e}", status_code=500)

    def update_device_status(
        self,
        device_id: str,
        status: str,
        speaker_status: Optional[str] = None,
        light_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Updates the operational status of a device.

        Args:
            device_id (str): Unique identifier of the device.
            status (str): Device operational status (e.g., 'active', 'offline').
            speaker_status (Optional[str]): Speaker state ('on', 'off').
            light_status (Optional[str]): Light state ('on', 'off').

        Returns:
            Dict[str, Any]: Updated record data.
        """
        client = self._ensure_client()
        update_data: Dict[str, Any] = {"status": status}
        if speaker_status is not None:
            update_data["speaker_status"] = speaker_status
        if light_status is not None:
            update_data["light_status"] = light_status

        try:
            response = client.table("devices").update(update_data).eq("id", device_id).execute()
            logger.info(f"Updated status for device {device_id}: {update_data}")
            return response.data[0] if response.data else update_data
        except Exception as e:
            logger.error(f"Error updating device status (ID: {device_id}): {e}")
            raise AppError(f"Failed to update device status: {e}", status_code=500)

    # --------------------------------------------------------------------------
    # 3. Detections Table Operations
    # --------------------------------------------------------------------------
    def insert_detection(
        self,
        device_id: str,
        object_class: str,
        confidence: float,
        image_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Inserts a new animal/pest detection record.

        Args:
            device_id (str): Associated device ID.
            object_class (str): Class detected (e.g., 'monkey', 'wild_boar').
            confidence (float): Model detection confidence.
            image_url (Optional[str]): Public URL of captured snapshot.
            metadata (Optional[Dict[str, Any]]): Additional contextual JSON data.

        Returns:
            Dict[str, Any]: Inserted record data.
        """
        client = self._ensure_client()
        record = {
            "device_id": device_id,
            "object_class": object_class,
            "confidence": confidence,
            "image_url": image_url,
            "metadata": metadata or {}
        }
        try:
            response = client.table("detections").insert(record).execute()
            logger.info(f"Inserted detection record for device {device_id}: {object_class}")
            return response.data[0] if response.data else record
        except Exception as e:
            logger.error(f"Error inserting detection record: {e}")
            raise AppError(f"Failed to insert detection record: {e}", status_code=500)

    # --------------------------------------------------------------------------
    # 4. Notifications Table Operations
    # --------------------------------------------------------------------------
    def insert_notification(
        self,
        farmer_id: str,
        title: str,
        message: str,
        channel: str = "whatsapp",
        status: str = "sent"
    ) -> Dict[str, Any]:
        """
        Logs a sent alert notification.

        Args:
            farmer_id (str): Target farmer identifier.
            title (str): Brief title for notification.
            message (str): Full text message.
            channel (str): Notification channel ('whatsapp', 'sms', 'push').
            status (str): Delivery status ('sent', 'failed').

        Returns:
            Dict[str, Any]: Inserted notification record.
        """
        client = self._ensure_client()
        record = {
            "farmer_id": farmer_id,
            "title": title,
            "message": message,
            "channel": channel,
            "status": status
        }
        try:
            response = client.table("notifications").insert(record).execute()
            logger.info(f"Inserted notification for farmer {farmer_id}")
            return response.data[0] if response.data else record
        except Exception as e:
            logger.error(f"Error inserting notification: {e}")
            raise AppError(f"Failed to insert notification: {e}", status_code=500)

    # --------------------------------------------------------------------------
    # 5. Speaker Logs Table Operations
    # --------------------------------------------------------------------------
    def insert_speaker_log(
        self,
        device_id: str,
        sound_played: str,
        duration_seconds: int,
        triggered_by: str = "automatic"
    ) -> Dict[str, Any]:
        """
        Logs a speaker audio deterrent playback event.

        Args:
            device_id (str): Associated device ID.
            sound_played (str): Audio filename or deterrent frequency type.
            duration_seconds (int): Duration sound was played.
            triggered_by (str): Trigger source ('automatic', 'manual').

        Returns:
            Dict[str, Any]: Inserted speaker log record.
        """
        client = self._ensure_client()
        record = {
            "device_id": device_id,
            "sound_played": sound_played,
            "duration_seconds": duration_seconds,
            "triggered_by": triggered_by
        }
        try:
            response = client.table("speaker_logs").insert(record).execute()
            logger.info(f"Inserted speaker log for device {device_id}")
            return response.data[0] if response.data else record
        except Exception as e:
            logger.error(f"Error inserting speaker log: {e}")
            raise AppError(f"Failed to insert speaker log: {e}", status_code=500)

    # --------------------------------------------------------------------------
    # 6. System Logs Table Operations
    # --------------------------------------------------------------------------
    def insert_system_log(
        self,
        log_level: str,
        module: str,
        message: str,
        error_details: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Logs system events or backend errors to Supabase.

        Args:
            log_level (str): Severity level ('INFO', 'WARNING', 'ERROR').
            module (str): Module name generating log.
            message (str): Primary log message.
            error_details (Optional[str]): Stack trace or extra diagnostic text.

        Returns:
            Dict[str, Any]: Inserted system log record.
        """
        client = self._ensure_client()
        record = {
            "log_level": log_level,
            "module": module,
            "message": message,
            "error_details": error_details
        }
        try:
            response = client.table("system_logs").insert(record).execute()
            return response.data[0] if response.data else record
        except Exception as e:
            logger.error(f"Error inserting system log: {e}")
            # Avoid infinite exception recursion if database is unreachable
            return record

    # --------------------------------------------------------------------------
    # 7. Storage Operations (Detection Snapshots)
    # --------------------------------------------------------------------------
    def upload_detection_image(
        self,
        file_path: str,
        bucket_name: str = "detection_images"
    ) -> Optional[str]:
        """
        Uploads a detection image snapshot to Supabase Storage bucket.

        Args:
            file_path (str): Local path to image file.
            bucket_name (str): Storage bucket name. Defaults to 'detection_images'.

        Returns:
            Optional[str]: Public URL of uploaded image if successful.
        """
        client = self._ensure_client()

        if not os.path.exists(file_path):
            logger.error(f"Image file does not exist: {file_path}")
            raise AppError(f"File not found: {file_path}", status_code=404)

        file_name = os.path.basename(file_path)

        try:
            with open(file_path, "rb") as file_obj:
                client.storage.from_(bucket_name).upload(
                    path=file_name,
                    file=file_obj,
                    file_options={"content-type": "image/jpeg", "upsert": "true"}
                )

            # Retrieve public URL
            public_url = client.storage.from_(bucket_name).get_public_url(file_name)
            logger.info(f"Uploaded detection image to Supabase Storage: {public_url}")
            return public_url
        except Exception as e:
            logger.error(f"Failed to upload detection image ({file_name}): {e}")
            raise AppError(f"Image upload failed: {e}", status_code=500)


# Global singleton instance
supabase_service = SupabaseService()
