"""Structured error types for the geo subsystem."""

from __future__ import annotations


class GeoError(Exception):
    """Base error for the geo subsystem."""

    code = "geo_error"

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "context": self.context}


class InvalidCoordinateError(GeoError):
    code = "geo_invalid_coordinate"


class InvalidRadiusError(GeoError):
    code = "geo_invalid_radius"


class ProviderUnavailableError(GeoError):
    code = "geo_provider_unavailable"


class PhysicalFallbackForbiddenError(GeoError):
    code = "geo_physical_fallback_forbidden"


class ProfileResolutionError(GeoError):
    code = "geo_profile_resolution_failed"


class EnvironmentConflictError(GeoError):
    code = "geo_environment_conflict"
