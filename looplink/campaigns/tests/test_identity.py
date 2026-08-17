import pytest
from django.core.exceptions import ValidationError

from looplink.campaigns.services.identity import IdentityKind, normalize_identity


def test_normalizes_email_case_and_surrounding_space():
    identity = normalize_identity("  Shopper@Example.COM ")

    assert identity.kind == IdentityKind.EMAIL
    assert identity.submitted == "Shopper@Example.COM"
    assert identity.normalized == "shopper@example.com"


def test_normalizes_phone_punctuation_and_spaces():
    identity = normalize_identity("+1 (415) 555-0123")

    assert identity.kind == IdentityKind.PHONE
    assert identity.normalized == "14155550123"


@pytest.mark.parametrize("identity", ["", "not-an-email@", "12345", "call-me-1234567"])
def test_rejects_invalid_identity(identity):
    with pytest.raises(ValidationError):
        normalize_identity(identity)
