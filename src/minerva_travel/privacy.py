from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from minerva_travel.config import photo_processing_consent_required

CURRENT_PRIVACY_CONSENT_VERSION = "2026-07-09"


class PrivacyConsentError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def as_detail(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class PrivacyConsent:
    version: str
    granted_at: datetime

    def metadata(self) -> dict[str, str]:
        return {
            "version": self.version,
            "granted_at": self.granted_at.astimezone(UTC).isoformat(),
        }


def validate_photo_processing_consent(
    *,
    granted: bool,
    version: str | None,
    granted_at: str | None,
    required: bool | None = None,
    now: datetime | None = None,
) -> PrivacyConsent | None:
    consent_is_required = photo_processing_consent_required() if required is None else required
    if not granted:
        if consent_is_required:
            raise PrivacyConsentError(
                "photo_processing_consent_required",
                "Autorize o processamento da foto para gerar o guia.",
            )
        return None
    if version != CURRENT_PRIVACY_CONSENT_VERSION:
        raise PrivacyConsentError(
            "privacy_consent_version_invalid",
            "A versão do consentimento está desatualizada. Revise a Política de Privacidade.",
        )
    try:
        parsed_at = datetime.fromisoformat(str(granted_at or "").replace("Z", "+00:00"))
    except ValueError as error:
        raise PrivacyConsentError(
            "privacy_consent_timestamp_invalid",
            "O horário do consentimento é inválido.",
        ) from error
    if parsed_at.tzinfo is None:
        raise PrivacyConsentError(
            "privacy_consent_timestamp_invalid",
            "O horário do consentimento deve incluir fuso horário.",
        )
    current = (now or datetime.now(UTC)).astimezone(UTC)
    normalized_at = parsed_at.astimezone(UTC)
    if normalized_at > current + timedelta(minutes=10):
        raise PrivacyConsentError(
            "privacy_consent_timestamp_future",
            "O horário do consentimento está no futuro.",
        )
    if normalized_at < current - timedelta(days=365):
        raise PrivacyConsentError(
            "privacy_consent_timestamp_expired",
            "Revise e confirme novamente a Política de Privacidade.",
        )
    return PrivacyConsent(version=version, granted_at=normalized_at)
