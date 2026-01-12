"""
Centralized Error Handling Module
Provides consistent error responses across the API
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from typing import Optional
import traceback
from logger import log_error, log_exception, log_warning


# ============== Error Codes ==============

class ErrorCode:
    """Standard error codes for API responses"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    DATABASE_ERROR = "DATABASE_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    AUTHENTICATION_ERROR = "AUTH_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT"
    SCRAPER_ERROR = "SCRAPER_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    BAD_REQUEST = "BAD_REQUEST"


# ============== Error Response ==============

def create_error_response(
    status_code: int,
    message: str,
    error_code: str = None,
    details: Optional[dict] = None
) -> JSONResponse:
    """Create a standardized error response"""
    content = {
        "success": False,
        "error": {
            "message": message,
            "code": error_code or "ERROR",
            "status_code": status_code
        }
    }
    if details:
        content["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=content)


# ============== Custom Exceptions ==============

class AppException(Exception):
    """Base exception for application errors"""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = ErrorCode.INTERNAL_ERROR,
        details: dict = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found"""
    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code=ErrorCode.NOT_FOUND
        )


class ValidationException(AppException):
    """Input validation error"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details
        )


class DatabaseException(AppException):
    """Database operation error"""
    def __init__(self, message: str = "Database error occurred", details: dict = None):
        super().__init__(
            message=message,
            status_code=503,
            error_code=ErrorCode.DATABASE_ERROR,
            details=details
        )


class ScraperException(AppException):
    """Scraper operation error"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code=ErrorCode.SCRAPER_ERROR,
            details=details
        )


# ============== Exception Handlers ==============

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions"""
    log_warning(f"AppException: {exc.error_code} - {exc.message}")
    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException"""
    error_code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.BAD_REQUEST
    if exc.status_code == 401:
        error_code = ErrorCode.AUTHENTICATION_ERROR
    elif exc.status_code == 429:
        error_code = ErrorCode.RATE_LIMIT_EXCEEDED

    return create_error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        error_code=error_code
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })

    log_warning(f"Validation error: {errors}")
    return create_error_response(
        status_code=422,
        message="Validation error",
        error_code=ErrorCode.VALIDATION_ERROR,
        details={"errors": errors}
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors"""
    log_exception(f"Database error: {exc}")

    # Don't expose internal details in production
    message = "Database operation failed"

    if isinstance(exc, IntegrityError):
        message = "Data integrity error - possibly duplicate entry"
    elif isinstance(exc, OperationalError):
        message = "Database connection error"

    return create_error_response(
        status_code=503,
        message=message,
        error_code=ErrorCode.DATABASE_ERROR
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all uncaught exceptions"""
    log_exception(f"Unhandled exception: {exc}\n{traceback.format_exc()}")

    return create_error_response(
        status_code=500,
        message="An unexpected error occurred",
        error_code=ErrorCode.INTERNAL_ERROR
    )


# ============== Setup Function ==============

def setup_error_handlers(app: FastAPI):
    """Register all error handlers with the FastAPI app"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    # Generic handler for uncaught exceptions
    app.add_exception_handler(Exception, generic_exception_handler)
