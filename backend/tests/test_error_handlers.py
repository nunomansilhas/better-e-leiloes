"""
Tests for Error Handling Module
"""

import pytest
from fastapi import HTTPException


class TestErrorCodes:
    """Tests for ErrorCode constants"""

    def test_all_error_codes_defined(self):
        """Test that all required error codes are defined"""
        from error_handlers import ErrorCode
        required = [
            "VALIDATION_ERROR",
            "NOT_FOUND",
            "DATABASE_ERROR",
            "CONNECTION_ERROR",
            "AUTHENTICATION_ERROR",
            "RATE_LIMIT_EXCEEDED",
            "SCRAPER_ERROR",
            "INTERNAL_ERROR",
            "BAD_REQUEST"
        ]
        for code in required:
            assert hasattr(ErrorCode, code)

    def test_error_codes_are_strings(self):
        """Test that all error codes are strings"""
        from error_handlers import ErrorCode
        for attr in dir(ErrorCode):
            if not attr.startswith("_"):
                assert isinstance(getattr(ErrorCode, attr), str)


class TestCreateErrorResponse:
    """Tests for create_error_response function"""

    def test_creates_json_response(self):
        """Test that function returns JSONResponse"""
        from error_handlers import create_error_response
        from fastapi.responses import JSONResponse

        response = create_error_response(404, "Not found")
        assert isinstance(response, JSONResponse)

    def test_includes_status_code(self):
        """Test that response has correct status code"""
        from error_handlers import create_error_response

        response = create_error_response(404, "Not found")
        assert response.status_code == 404

    def test_includes_error_message(self):
        """Test that response includes error message"""
        from error_handlers import create_error_response
        import json

        response = create_error_response(500, "Something went wrong")
        body = json.loads(response.body)
        assert body["error"]["message"] == "Something went wrong"

    def test_includes_error_code(self):
        """Test that response includes error code"""
        from error_handlers import create_error_response, ErrorCode
        import json

        response = create_error_response(404, "Not found", ErrorCode.NOT_FOUND)
        body = json.loads(response.body)
        assert body["error"]["code"] == ErrorCode.NOT_FOUND

    def test_includes_details_when_provided(self):
        """Test that response includes details when provided"""
        from error_handlers import create_error_response
        import json

        details = {"field": "reference", "reason": "invalid format"}
        response = create_error_response(422, "Validation error", details=details)
        body = json.loads(response.body)
        assert body["error"]["details"] == details

    def test_success_is_false(self):
        """Test that success field is False"""
        from error_handlers import create_error_response
        import json

        response = create_error_response(500, "Error")
        body = json.loads(response.body)
        assert body["success"] is False


class TestAppException:
    """Tests for AppException base class"""

    def test_default_values(self):
        """Test default values for AppException"""
        from error_handlers import AppException, ErrorCode

        exc = AppException("Test error")
        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert exc.error_code == ErrorCode.INTERNAL_ERROR
        assert exc.details is None

    def test_custom_values(self):
        """Test custom values for AppException"""
        from error_handlers import AppException

        exc = AppException(
            message="Custom error",
            status_code=400,
            error_code="CUSTOM_ERROR",
            details={"info": "test"}
        )
        assert exc.message == "Custom error"
        assert exc.status_code == 400
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details == {"info": "test"}

    def test_inherits_from_exception(self):
        """Test that AppException inherits from Exception"""
        from error_handlers import AppException

        exc = AppException("Test")
        assert isinstance(exc, Exception)


class TestNotFoundError:
    """Tests for NotFoundError exception"""

    def test_basic_resource_not_found(self):
        """Test basic resource not found message"""
        from error_handlers import NotFoundError, ErrorCode

        exc = NotFoundError("Event")
        assert exc.message == "Event not found"
        assert exc.status_code == 404
        assert exc.error_code == ErrorCode.NOT_FOUND

    def test_resource_with_identifier(self):
        """Test resource not found with identifier"""
        from error_handlers import NotFoundError

        exc = NotFoundError("Event", "LO-123456")
        assert exc.message == "Event 'LO-123456' not found"

    def test_different_resources(self):
        """Test different resource types"""
        from error_handlers import NotFoundError

        exc1 = NotFoundError("User", "123")
        exc2 = NotFoundError("Rule", "456")

        assert "User '123'" in exc1.message
        assert "Rule '456'" in exc2.message


class TestValidationException:
    """Tests for ValidationException"""

    def test_basic_validation_error(self):
        """Test basic validation error"""
        from error_handlers import ValidationException, ErrorCode

        exc = ValidationException("Invalid input")
        assert exc.message == "Invalid input"
        assert exc.status_code == 422
        assert exc.error_code == ErrorCode.VALIDATION_ERROR

    def test_validation_error_with_details(self):
        """Test validation error with details"""
        from error_handlers import ValidationException

        details = {"field": "email", "error": "invalid format"}
        exc = ValidationException("Validation failed", details=details)
        assert exc.details == details


class TestDatabaseException:
    """Tests for DatabaseException"""

    def test_default_message(self):
        """Test default database error message"""
        from error_handlers import DatabaseException, ErrorCode

        exc = DatabaseException()
        assert exc.message == "Database error occurred"
        assert exc.status_code == 503
        assert exc.error_code == ErrorCode.DATABASE_ERROR

    def test_custom_message(self):
        """Test custom database error message"""
        from error_handlers import DatabaseException

        exc = DatabaseException("Connection timeout")
        assert exc.message == "Connection timeout"

    def test_with_details(self):
        """Test database error with details"""
        from error_handlers import DatabaseException

        details = {"table": "events", "operation": "insert"}
        exc = DatabaseException("Insert failed", details=details)
        assert exc.details == details


class TestScraperException:
    """Tests for ScraperException"""

    def test_scraper_error(self):
        """Test scraper error creation"""
        from error_handlers import ScraperException, ErrorCode

        exc = ScraperException("Failed to scrape page")
        assert exc.message == "Failed to scrape page"
        assert exc.status_code == 500
        assert exc.error_code == ErrorCode.SCRAPER_ERROR

    def test_scraper_error_with_details(self):
        """Test scraper error with details"""
        from error_handlers import ScraperException

        details = {"url": "https://example.com", "status": 403}
        exc = ScraperException("Access denied", details=details)
        assert exc.details == details
