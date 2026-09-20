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
    JSON
)

from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime


# ============================================================
# DATABASE CONNECTION
# ============================================================

DATABASE_URL = "postgresql+psycopg://postgres:1123@localhost:5432/disaster_alert"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# ============================================================
# 1. DEVICES
# Cameras, Arduino, IoT devices, etc.
# ============================================================

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)

    device_code = Column(String(100), unique=True, nullable=False)
    device_name = Column(String(200))

    device_type = Column(String(50))
    # Example: camera, arduino, sensor

    location_name = Column(String(255))

    latitude = Column(Float)
    longitude = Column(Float)

    status = Column(String(50), default="Active")
    # Active / Offline / Maintenance

    last_seen_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 2. MODEL VERSIONS
# Keeps track of which AI model detected something
# ============================================================

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)

    model_name = Column(String(100), nullable=False)
    # Example: YOLOv8

    version = Column(String(50))

    model_type = Column(String(100))
    # Example: object_detection

    description = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 3. INCIDENTS
# One real-world disaster event
# ============================================================

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)

    disaster_type = Column(String(100), nullable=False)
    # Fire / Flood / Accident / Landslide / etc.

    severity = Column(String(50))
    # Low / Medium / High / Critical

    status = Column(String(50), default="Detected")
    # Detected / Alerted / Responding / Resolved / False Alarm

    description = Column(Text)

    location_name = Column(String(255))

    latitude = Column(Float)
    longitude = Column(Float)

    detected_at = Column(DateTime, default=datetime.utcnow)

    resolved_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    source_device_id = Column(
        Integer,
        ForeignKey("devices.id"),
        nullable=True
    )


# ============================================================
# 4. DETECTIONS
# Every individual AI prediction
# ============================================================

class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)

    incident_id = Column(
        Integer,
        ForeignKey("incidents.id"),
        nullable=False
    )

    device_id = Column(
        Integer,
        ForeignKey("devices.id"),
        nullable=True
    )

    model_version_id = Column(
        Integer,
        ForeignKey("model_versions.id"),
        nullable=True
    )

    detected_class = Column(String(100), nullable=False)
    # Example: fire, person, vehicle, smoke

    confidence = Column(Float, nullable=False)

    # Bounding box from object detection
    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)

    frame_number = Column(Integer)

    detected_at = Column(DateTime, default=datetime.utcnow)

    # Stores any additional AI output
    raw_prediction = Column(JSON)


# ============================================================
# 5. MEDIA
# Images / videos / snapshots
# ============================================================

class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)

    incident_id = Column(
        Integer,
        ForeignKey("incidents.id"),
        nullable=False
    )

    detection_id = Column(
        Integer,
        ForeignKey("detections.id"),
        nullable=True
    )

    media_type = Column(String(50))
    # image / video / snapshot

    file_path = Column(String(500))

    file_url = Column(String(1000))

    captured_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 6. SENSOR READINGS
# Arduino / IoT sensor data
# ============================================================

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)

    device_id = Column(
        Integer,
        ForeignKey("devices.id"),
        nullable=False
    )

    incident_id = Column(
        Integer,
        ForeignKey("incidents.id"),
        nullable=True
    )

    sensor_type = Column(String(100))
    # temperature / smoke / water / gas / humidity etc.

    value = Column(Float)

    unit = Column(String(50))
    # Celsius / ppm / percentage etc.

    recorded_at = Column(DateTime, default=datetime.utcnow)

    raw_data = Column(JSON)


# ============================================================
# 7. AUTHORITIES
# People/organizations who receive alerts
# ============================================================

class Authority(Base):
    __tablename__ = "authorities"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(200), nullable=False)

    organization = Column(String(200))

    authority_type = Column(String(100))
    # Police / Fire / Municipality / Hospital / Disaster Management

    phone = Column(String(50))

    email = Column(String(255))

    location_name = Column(String(255))

    latitude = Column(Float)
    longitude = Column(Float)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 8. ALERTS
# Every alert sent by the system
# ============================================================

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)

    incident_id = Column(
        Integer,
        ForeignKey("incidents.id"),
        nullable=False
    )

    authority_id = Column(
        Integer,
        ForeignKey("authorities.id"),
        nullable=True
    )

    channel = Column(String(50))
    # SMS / WhatsApp / Email / Push Notification

    recipient = Column(String(255))

    message = Column(Text)

    sent_at = Column(DateTime)

    delivery_status = Column(String(50))
    # Pending / Sent / Delivered / Failed

    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 9. INCIDENT UPDATES
# Keeps history of what happened to an incident
# ============================================================

class IncidentUpdate(Base):
    __tablename__ = "incident_updates"

    id = Column(Integer, primary_key=True, index=True)

    incident_id = Column(
        Integer,
        ForeignKey("incidents.id"),
        nullable=False
    )

    previous_status = Column(String(50))

    new_status = Column(String(50))

    note = Column(Text)

    updated_by = Column(String(100))
    # AI / System / Authority / Admin

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# CREATE ALL TABLES
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# TEST CONNECTION
# ============================================================

try:

    with engine.connect() as connection:
        print("Database connection successful!")
        print("All database tables are ready!")

except Exception as e:

    print("Database connection failed!")
    print(e)