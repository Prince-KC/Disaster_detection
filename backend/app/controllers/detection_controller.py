"""
Detection Controller module.
Coordinates business logic between API routes and underlying services (Supabase, Arduino, Telegram).
Follows Clean Architecture by keeping endpoint handlers clean and delegating logic here.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from app.models.schemas import DetectionPayload, DetectionResponse
from app.services.telegram_service import TelegramService
from app.services.arduino_service import ArduinoController as ArduinoService
from app.services.supabase_service import SupabaseService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DetectionController:
    """Controller class managing object detection workflows and system state requests."""

    def __init__(self) -> None:
        self.telegram_service = TelegramService()
        self.arduino_service = ArduinoService()
        self.supabase_service = SupabaseService()
        
        # Attempt to open serial connection to Arduino on startup
        try:
            self.arduino_service.connect()
        except Exception as e:
            logger.warning(f"Arduino initial connection pending: {e}")

    async def process_detection(self, payload: DetectionPayload) -> DetectionResponse:
        """
        Processes an incoming detection payload:
        1. Logs detection event to Supabase.
        2. Sends hardware signal/command to Arduino.
        3. Dispatches Telegram alert message to registered farmer.
        """
        logger.info(f"Processing detection: {payload.object_class} (Confidence: {payload.confidence}) from {payload.camera_id}")
        
        # 1. Save event record to Supabase database
        try:
            self.supabase_service.insert_detection(
                device_id=payload.camera_id,
                object_class=payload.object_class,
                confidence=payload.confidence * 100 if payload.confidence <= 1.0 else payload.confidence,
                image_url=None,
                metadata={"source": "api_payload"}
            )
        except Exception as e:
            logger.error(f"Failed to record detection in database: {e}")

        # 2. Command Arduino serial interface (e.g., sound alarm, turn on lights)
        try:
            self.arduino_service.speaker_on()
            self.arduino_service.flash_on()
        except Exception as e:
            logger.error(f"Failed to trigger Arduino hardware: {e}")

        # 3. Send Telegram notification
        telegram_sent = False
        try:
            res = self.telegram_service.send_detection_alert(
                camera_name=payload.camera_id,
                zone="Field",
                confidence=payload.confidence * 100 if payload.confidence <= 1.0 else payload.confidence,
                device_status="ALERT",
                speaker_activated=True,
                flash_activated=True
            )
            telegram_sent = res.get("success", False)
        except Exception as e:
            logger.error(f"Telegram notification dispatch error: {e}")

        return DetectionResponse(
            status="success",
            message="Detection event processed successfully.",
            alert_sent=telegram_sent
        )

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Returns consolidated live metrics for dashboard display."""
        total_detections = 0
        today_detections = 0
        system_health = "100%"
        last_detection_time = "N/A"

        try:
            if self.supabase_service.client:
                # Total detections count
                res_all = self.supabase_service.client.table("detections").select("id", count="exact").execute()
                total_detections = res_all.count if res_all.count is not None else len(res_all.data or [])

                # Latest detection
                res_last = self.supabase_service.client.table("detections").select("*").order("created_at", desc=True).limit(1).execute()
                if res_last.data:
                    created = res_last.data[0].get("created_at", "")
                    last_detection_time = created[:16].replace("T", " ") if created else "N/A"

                # Today count
                today_str = date.today().isoformat()
                res_today = self.supabase_service.client.table("detections").select("id", count="exact").gte("created_at", today_str).execute()
                today_detections = res_today.count if res_today.count is not None else len(res_today.data or [])
        except Exception as e:
            logger.error(f"Error fetching dashboard summary from Supabase: {e}")

        return {
            "total_cameras": 2,
            "active_cameras": 2,
            "total_speakers": 4,
            "total_detections": total_detections,
            "today_detections": today_detections,
            "sms_alerts": today_detections,
            "system_health": system_health,
            "last_detection_time": last_detection_time,
            "arduino_connected": self.arduino_service.is_connected if hasattr(self.arduino_service, 'is_connected') else True
        }

    def get_detections_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches detection records for detection-history.html."""
        try:
            if self.supabase_service.client:
                res = self.supabase_service.client.table("detections").select("*").order("created_at", desc=True).limit(limit).execute()
                return res.data or []
        except Exception as e:
            logger.error(f"Error fetching detections history: {e}")
        return []

    def get_speaker_status(self) -> List[Dict[str, Any]]:
        """Fetches speaker status and logs."""
        try:
            if self.supabase_service.client:
                res = self.supabase_service.client.table("speakers").select("*").execute()
                if res.data:
                    return res.data
        except Exception as e:
            logger.error(f"Error fetching speaker status: {e}")

        # Default fallback
        return [
            {"id": "SPK-01", "name": "East Speaker", "zone": "East Boundary", "status": "active", "health": "Healthy"},
            {"id": "SPK-02", "name": "North Speaker", "zone": "North Field", "status": "active", "health": "Healthy"},
            {"id": "SPK-03", "name": "South Speaker", "zone": "South Entrance", "status": "idle", "health": "Healthy"},
            {"id": "SPK-04", "name": "West Speaker", "zone": "West Boundary", "status": "idle", "health": "Healthy"}
        ]

    def trigger_speaker(self, action: str) -> Dict[str, Any]:
        """Manual speaker activation override."""
        try:
            if action.upper() == "ON":
                self.arduino_service.speaker_on()
                return {"status": "success", "message": "Speaker activated successfully."}
            else:
                self.arduino_service.speaker_off()
                return {"status": "success", "message": "Speaker deactivated successfully."}
        except Exception as e:
            logger.error(f"Manual speaker control error: {e}")
            return {"status": "error", "message": str(e)}

    def trigger_light(self, action: str) -> Dict[str, Any]:
        """Manual warning light activation override."""
        try:
            if action.upper() == "ON":
                self.arduino_service.flash_on()
                return {"status": "success", "message": "Flash light activated successfully."}
            else:
                self.arduino_service.flash_off()
                return {"status": "success", "message": "Flash light deactivated successfully."}
        except Exception as e:
            logger.error(f"Manual flash light control error: {e}")
            return {"status": "error", "message": str(e)}

    def get_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches notification history logs."""
        try:
            if self.supabase_service.client:
                res = self.supabase_service.client.table("notifications").select("*").order("created_at", desc=True).limit(limit).execute()
                return res.data or []
        except Exception as e:
            logger.error(f"Error fetching notifications: {e}")
        return []

    def get_analytics(self) -> Dict[str, Any]:
        """Fetches analytics data for analytics.html."""
        try:
            if self.supabase_service.client:
                res_daily = self.supabase_service.client.table("analytics_daily").select("*").order("date", desc=True).limit(30).execute()
                daily_records = res_daily.data or []
                
                res_all = self.supabase_service.client.table("detections").select("id", count="exact").execute()
                total_cnt = res_all.count or len(res_all.data or [])

                return {
                    "total_detections": total_cnt,
                    "daily_records": daily_records
                }
        except Exception as e:
            logger.error(f"Error fetching analytics: {e}")
            
        return {"total_detections": 0, "daily_records": []}


# Global controller instance for dependency injection into routes
detection_controller = DetectionController()
