"""Tests for app.exceptions module."""

import pytest

from app.exceptions import (
    AppException,
    ExternalAPIException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)


class TestAppException:
    """Test AppException hierarchy."""

    def test_base_exception_defaults(self):
        """Base exception should have default status and detail."""
        exc = AppException()
        assert exc.status_code == 500
        assert exc.detail == "Erro interno do servidor"

    def test_base_exception_custom(self):
        """Base exception should accept custom values."""
        exc = AppException(detail="Custom error", status_code=418)
        assert exc.status_code == 418
        assert exc.detail == "Custom error"

    def test_not_found_defaults(self):
        exc = NotFoundException()
        assert exc.status_code == 404
        assert "não encontrado" in exc.detail.lower()

    def test_not_found_custom(self):
        exc = NotFoundException(detail="Proposição não encontrada")
        assert exc.status_code == 404
        assert exc.detail == "Proposição não encontrada"

    def test_validation_exception(self):
        exc = ValidationException()
        assert exc.status_code == 422
        assert "inválidos" in exc.detail.lower()

    def test_external_api_exception(self):
        exc = ExternalAPIException()
        assert exc.status_code == 502
        assert "externo" in exc.detail.lower()

    def test_external_api_custom(self):
        exc = ExternalAPIException(detail="Câmara API timeout")
        assert exc.status_code == 502
        assert exc.detail == "Câmara API timeout"

    def test_unauthorized_exception(self):
        exc = UnauthorizedException()
        assert exc.status_code == 401
        assert "autorizado" in exc.detail.lower()

    def test_exception_is_exception(self):
        """All custom exceptions should inherit from Exception."""
        exc = NotFoundException("test")
        assert isinstance(exc, Exception)
        assert isinstance(exc, AppException)

    def test_str_representation(self):
        """str() of exception should return the detail."""
        exc = NotFoundException("Recurso 123 não encontrado")
        assert str(exc) == "Recurso 123 não encontrado"
