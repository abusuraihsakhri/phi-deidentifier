"""Operational API must not accept unauthenticated requests."""
import pytest
from fastapi import HTTPException
from agents.api import require_api_key


def test_api_denies_access_without_configured_key(monkeypatch):
    monkeypatch.delenv("PHI_DEID_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_api_key(None)
    assert exc.value.status_code == 503


def test_api_rejects_invalid_bearer_token(monkeypatch):
    monkeypatch.setenv("PHI_DEID_API_KEY", "synthetic-test-secret")
    with pytest.raises(HTTPException) as exc:
        require_api_key("Bearer wrong")
    assert exc.value.status_code == 401
    assert require_api_key("Bearer synthetic-test-secret") is None
