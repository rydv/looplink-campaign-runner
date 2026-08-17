import re
from dataclasses import dataclass
from enum import StrEnum

from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class IdentityKind(StrEnum):
    EMAIL = "email"
    PHONE = "phone"


@dataclass(frozen=True)
class NormalizedIdentity:
    submitted: str
    normalized: str
    kind: IdentityKind


def normalize_identity(identity):
    if not isinstance(identity, str):
        raise ValidationError("Enter a phone number or email address.")

    submitted = identity.strip()
    if not submitted:
        raise ValidationError("Enter a phone number or email address.")

    if "@" in submitted:
        return _normalize_email(submitted)
    return _normalize_phone(submitted)


def _normalize_email(submitted):
    normalized = submitted.lower()
    try:
        validate_email(normalized)
    except ValidationError as error:
        raise ValidationError("Enter a valid email address.") from error
    return NormalizedIdentity(submitted=submitted, normalized=normalized, kind=IdentityKind.EMAIL)


def _normalize_phone(submitted):
    if re.search(r"[A-Za-z]", submitted):
        raise ValidationError("Enter a valid phone number.")

    normalized = re.sub(r"[^0-9]", "", submitted)
    if not 7 <= len(normalized) <= 15:
        raise ValidationError("Enter a valid phone number.")
    return NormalizedIdentity(submitted=submitted, normalized=normalized, kind=IdentityKind.PHONE)
