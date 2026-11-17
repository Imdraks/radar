"""Run the actual VPS deployment probe against the pinned FastAPI application."""
import importlib.util
from pathlib import Path
import pytest
from app.main import app
from app.core.passwords import POLICY


def probe():
    file = Path(__file__).resolve().parents[2] / 'integrations/deploy-mfa/update_password_recovery.py'
    spec = importlib.util.spec_from_file_location('deployment_probe', file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BACKEND_CHECK


def test_real_fastapi_included_routers_are_supported():
    # This application contains _IncludedRouter instances without .path in
    # FastAPI 0.149; the old production probe raised AttributeError here.
    assert any(not hasattr(route, 'path') for route in app.routes)
    exec(probe(), {})


def test_missing_required_route_is_not_silently_ignored(monkeypatch):
    monkeypatch.setattr(app, 'openapi', lambda: {'paths': {}})
    with pytest.raises(AssertionError, match='Route forgot-password absente'):
        exec(probe(), {})


def test_wrong_link_expiration_is_not_silently_ignored(monkeypatch):
    monkeypatch.setitem(POLICY, 'reset_expiry_minutes', 60)
    with pytest.raises(AssertionError, match='Expiration de récupération incorrecte'):
        exec(probe(), {})
