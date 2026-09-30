"""Structured errors for the profile subsystem."""

from __future__ import annotations


class ProfileError(Exception):
    code = "profile_error"

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "context": self.context}


class ProfileValidationError(ProfileError):
    code = "profile_validation_failed"


class ProfileVersionError(ProfileError):
    code = "profile_version_unsupported"


class ProfileMigrationError(ProfileError):
    code = "profile_migration_failed"


class ProfileIntegrityError(ProfileError):
    code = "profile_integrity_failed"


class ProfileStoreError(ProfileError):
    code = "profile_store_error"
