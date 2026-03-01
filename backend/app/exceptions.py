"""Custom exception hierarchy for the application."""


class AppException(Exception):
    """Base exception for all application errors."""

    status_code: int = 500
    detail: str = "Erro interno do servidor"

    def __init__(self, detail: str | None = None, status_code: int | None = None) -> None:
        self.detail = detail or self.__class__.detail
        self.status_code = status_code or self.__class__.status_code
        super().__init__(self.detail)


class NotFoundException(AppException):
    """Resource not found."""

    status_code = 404
    detail = "Recurso não encontrado"


class ValidationException(AppException):
    """Input validation failed."""

    status_code = 422
    detail = "Dados inválidos"


class ExternalAPIException(AppException):
    """External API call failed."""

    status_code = 502
    detail = "Erro ao comunicar com serviço externo"


class UnauthorizedException(AppException):
    """Authentication/authorization failed."""

    status_code = 401
    detail = "Não autorizado"
