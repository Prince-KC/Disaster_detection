"""
Re-export EmailService from app.services.email_service.
"""
from app.services.email_service import EmailService, email_service

__all__ = ["EmailService", "email_service"]
