from __future__ import annotations


class DomainError(Exception):
    code = "domain_error"
    message = "A domain error occurred."
    status_code = 400

    def __init__(self, message: str | None = None, *, code: str | None = None, status_code: int | None = None) -> None:
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(DomainError):
    code = "not_found"
    message = "The requested resource was not found."
    status_code = 404


class DependencyUnavailableError(DomainError):
    code = "dependency_unavailable"
    message = "A required dependency is unavailable."
    status_code = 503


class ValidationDomainError(DomainError):
    code = "validation_error"
    message = "The request is not valid for this operation."
    status_code = 422

