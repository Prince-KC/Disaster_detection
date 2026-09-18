# KhetRakshak Backend Service

Production-ready Python backend for the **KhetRakshak** crop protection system built using **FastAPI** and **Clean Architecture**.

---

## 📌 Architecture & Features

This project follows **Clean Architecture** and SOLID principles to maintain complete decoupling between HTTP routing, business logic, data persistence, and hardware services:

- **Independent Backend**: Fully separated from frontend interfaces and machine learning model training scripts.
- **FastAPI**: Asynchronous web API with built-in Pydantic validation.
- **Supabase Service**: Manages cloud database interactions for logging detection events.
- **Arduino Service**: Serial communication client for triggering physical hardware alarms/actuators.
- **Telegram Service**: Farmer alert system using Telegram Bot API.
- **Logging & Exceptions**: Reusable centralized logging and exception handling middleware.

---

## 📁 Directory Structure

```
backend/
│
├── app/
│   ├── config/          # Environment configuration settings
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   ├── controllers/     # Business logic orchestrators
│   │   ├── __init__.py
│   │   └── detection_controller.py
│   │
│   ├── models/          # Pydantic schemas and data transfer objects
│   │   ├── __init__.py
│   │   └── schemas.py
│   │
│   ├── routes/          # FastAPI API endpoint definitions
│   │   ├── __init__.py
│   │   └── api.py
│   │
│   ├── services/        # External integrations (Supabase, Arduino, Telegram)
│   │   ├── __init__.py
│   │   ├── arduino_service.py
│   │   ├── detector_service.py
│   │   ├── supabase_service.py
│   │   └── telegram_service.py
│   │
│   ├── utils/           # Reusable logging & exception utilities
│   │   ├── __init__.py
│   │   ├── exceptions.py
│   │   └── logger.py
│   │
│   └── __init__.py
│
├── .env.example         # Environment variable template
├── main.py              # Application entry point
├── README.md            # Documentation
└── requirements.txt     # Project dependencies
```

---

## 🚀 Quickstart Guide

### 1. Environment Setup

Copy `.env.example` to create your local `.env` file:

```bash
cp .env.example .env
```

Fill in your configuration details (Supabase URL/Service Key, Arduino COM Port, Telegram Bot Token & Chat ID).

### 2. Install Dependencies

It is recommended to use a Python virtual environment:

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the Backend

```bash
python main.py
```

Or using Uvicorn directly:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at: `http://localhost:8000`
- Interactive API Docs (Swagger): `http://localhost:8000/docs`
- Redoc Documentation: `http://localhost:8000/redoc`

---

## 🔌 API Endpoints

### Health Check
- `GET /api/health`
  - Returns `200 OK` with service status information.

### Detection Event Handler (YOLO Integration Ready)
- `POST /api/detect`
  - **Payload Example**:
    ```json
    {
      "camera_id": "cam_01",
      "object_class": "wild_boar",
      "confidence": 0.95,
      "timestamp": "2026-08-02T08:35:00Z"
    }
    ```
  - **Response Example**:
    ```json
    {
      "status": "success",
      "message": "Detection event processed successfully.",
      "alert_sent": true
    }
    ```
