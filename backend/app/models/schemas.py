"""
Pydantic schemas for data validation and API payloads.
Provides type hinting and validation for requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DetectionPayload(BaseModel):
    """
    Schema for incoming object detection events (e.g., from future YOLO integration).
    """
    camera_id: str = Field(..., description="Unique identifier for the camera source")
    object_class: str = Field(..., description="Detected object class, e.g., 'animal', 'person'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score between 0 and 1")
    timestamp: Optional[datetime] = Field(default=None, description="Time of detection event")

    class Config:
        json_schema_extra = {
            "example": {
                "camera_id": "cam_01",
                "object_class": "wild_boar",
                "confidence": 0.92,
                "timestamp": "2026-08-02T08:35:00Z"
            }
        }

class DetectionResponse(BaseModel):
    """
    Schema for API responses acknowledging detection processing.
    """
    status: str = Field(..., description="Processing status, e.g., 'success', 'error'")
    message: str = Field(..., description="Human-readable response message")
    alert_sent: bool = Field(default=False, description="Flag indicating if a WhatsApp alert was triggered")
