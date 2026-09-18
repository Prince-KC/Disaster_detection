"""
Reusable error handling module.
Defines custom exceptions and exception handlers for FastAPI.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

class AppError(Exception):
    """Base class for custom application exceptions."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    FastAPI exception handler for AppError.
    Returns a standardized JSON response.
    """
    logger.error(f"AppError occurred: {exc.message} (Status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "status": exc.status_code}
    )

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    FastAPI exception handler for unhandled exceptions.
    """
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status": 500}
    )
