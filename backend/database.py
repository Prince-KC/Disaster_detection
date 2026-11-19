import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set. Please add it to your .env file."
    )


# ============================================================
# 2. DATABASE CONNECTION
# ============================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


# ============================================================
# 3. DEVICE TABLE
# ============================================================

class Device(Base):
    __tablename__ = "devices"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    device_code = Column(
        String(100),
        unique=True,
        nullable=False,
    )

    device_name = Column(
        String(200)
    )

    device_type = Column(
        String(50)
    )

    location_name = Column(
        String(255)
    )

    latitude = Column(
        Float
    )

    longitude = Column(
        Float
    )

    status = Column(
        String(50),
        default="Active",
    )

    last_seen_at = Column(
        DateTime
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


# ============================================================
# 4. AI MODEL VERSION TABLE
# ============================================================

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    model_name = Column(
        String(100),
        nullable=False,
    )

    version = Column(
        String(50)
    )

    model_type = Column(
        String(100)
    )

    description = Column(
        Text
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


# ============================================================
# 5. INCIDENT TABLE
# ============================================================

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # Type of disaster
    disaster_type = Column(
        String(100),
        nullable=False,
        index=True,
    )

    # Severity: Low / Medium / High / Critical
    severity = Column(
        String(50),
        nullable=False,
        index=True,
    )

    # Overall incident status
    status = Column(
        String(50),
        default="Alerted",
        index=True,
    )

    # Alert status
    # Pending / Sent / Partially Sent / Failed
    alert_status = Column(
        String(50),
        default="Pending",
        index=True,
    )

    description = Column(
        Text
    )

    # Location information
    location_name = Column(
        String(255)
    )

    district = Column(
        String(100)
    )

    province = Column(
        String(100)
    )

    latitude = Column(
        Float
    )

    longitude = Column(
        Float
    )

    # AI confidence
    ai_confidence = Column(
        Float
    )

    # Detection time
    detected_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

    # Time when authorities were alerted
    alert_sent_at = Column(
        DateTime
    )

    # Time incident was resolved
    resolved_at = Column(
        DateTime
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Device that detected the incident
    source_device_id = Column(
        Integer,
        ForeignKey("devices.id"),
        nullable=True,
    )


# ============================================================
# 6. AI DETECTION TABLE
# ============================================================

class Detection(Base):
    __tablename__ = "detections"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    incident_id = Column(
        Integer,
        ForeignKey("incidents.id"),
        nullable=False,
    )

    device_id = Column(
        Integer,
        ForeignKey("devices.id"),
        nullable=True,
    )

    model_version_id = Column(
        Integer,
        ForeignKey("model_versions.id"),
        nullable=True,
    )

    # Object/class detected by AI
    detected_class = Column(
        String(100),
        nullable=False,
    )

    # AI confidence score
    confidence = Column(
        Float,
        nullable=False,
    )

    # Bounding box
    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)

    frame_number = Column(
        Integer
    )

    detected_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    # Complete raw prediction from AI
    raw_prediction = Column(
        JSON
    )


# ============================================================
# 7. MEDIA TABLE
# ============================================================

class Media(Base):
    __tablename__ = "media"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    incident_id = Column(
        Integer,
        ForeignKey("incidents.id"),
        nullable=False,
    )

    detection_id = Column(
        Integer,
        nullable=True,
    )

    # image / video / evidence
    media_type = Column(
        String(50)
    )

    # Path inside Supabase Storage
    file_path = Column(
        String(500)
    )

    # Public/signed URL
    file_url = Column(
        String(1000)
    )

    captured_at = Column(
        DateTime
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


# ============================================================
# 8. SENSOR READING TABLE
# ============================================================

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    device_id = Column(
        Integer,
        ForeignKey("devices.id"),
        nullable=False,
    )

    incident_id = Column(
        Integer,
        ForeignKey("incidents.id"),
        nullable=True,
    )

    sensor_type = Column(
        String(100)
    )

    value = Column(
        Float
    )

    unit = Column(
        String(50)
    )

    recorded_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    raw_data = Column(
        JSON
    )


# ============================================================
# 9. AUTHORITY TABLE
# ============================================================

class Authority(Base):
    __tablename__ = "authorities"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String(200),
        nullable=False,
    )

    organization = Column(
        String(200)
    )

    # Police / Hospital / Municipality /
    # Road Department / Disaster Management etc.
    authority_type = Column(
        String(100)
    )

    phone = Column(
        String(50)
    )

    email = Column(
        String(255)
    )

    location_name = Column(
        String(255)
    )

    district = Column(
        String(100)
    )

    province = Column(
        String(100)
    )

    latitude = Column(
        Float
    )

    longitude = Column(
        Float
    )

    is_active = Column(
        Boolean,
        default=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


# ============================================================
# 10. ALERT TABLE
# ============================================================

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    incident_id = Column(
        Integer,
        ForeignKey("incidents.id"),
        nullable=False,
    )

    authority_id = Column(
        Integer,
        ForeignKey("authorities.id"),
        nullable=True,
    )

    # SMS / Email / API / Dashboard / Push
    channel = Column(
        String(50)
    )

    recipient = Column(
        String(255)
    )

    message = Column(
        Text
    )

    # When alert was sent
    sent_at = Column(
        DateTime
    )

    # When delivery was confirmed
    delivered_at = Column(
        DateTime
    )

    # Pending / Sent / Delivered / Failed
    delivery_status = Column(
        String(50),
        default="Pending",
    )

    error_message = Column(
        Text
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


# ============================================================
# 11. INCIDENT UPDATE TABLE
# ============================================================

class IncidentUpdate(Base):
    __tablename__ = "incident_updates"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    incident_id = Column(
        Integer,
        ForeignKey("incidents.id"),
        nullable=False,
    )

    previous_status = Column(
        String(50)
    )

    new_status = Column(
        String(50)
    )

    note = Column(
        Text
    )

    updated_by = Column(
        String(100)
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


# ============================================================
# 12. CREATE ALL TABLES
# ============================================================

Base.metadata.create_all(
    bind=engine
)


# ============================================================
# 13. TEST DATABASE CONNECTION
# ============================================================

try:

    with engine.connect() as connection:

        print("========================================")
        print("Database connection successful!")
        print("Supabase PostgreSQL connected.")
        print("All database tables are ready!")
        print("========================================")

except Exception as e:

    print("========================================")
    print("Database connection failed!")
    print("----------------------------------------")
    print(e)
    print("========================================")