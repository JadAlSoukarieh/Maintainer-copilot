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


class ConfigurationError(DomainError):
    code = "configuration_error"
    message = "The model server is not configured correctly."
    status_code = 503
