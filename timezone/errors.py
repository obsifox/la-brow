"""Structured errors for the timezone subsystem."""

from __future__ import annotations


class TimezoneError(Exception):
    code = "timezone_error"

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "context": self.context}


class InvalidTimezoneError(TimezoneError):
    code = "timezone_invalid_zone"


class TimezoneResolutionError(TimezoneError):
    code = "timezone_resolution_failed"
