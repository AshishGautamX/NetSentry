import os
import json
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.models import SystemSetting
from backend.app.services.settings_service import (
    resolve_gemini_api_key,
    resolve_ai_provider,
    get_system_settings_summary,
    delete_setting,
    set_setting,
    invalidate_cache,
)
from backend.app.engine.ai import get_ai_provider
from backend.app.engine.ai.gemini_provider import GeminiAIProvider
from backend.app.engine.ai.deterministic import DeterministicAIProvider


@pytest.fixture(autouse=True)
def clean_settings():
    """Ensure a clean settings state before and after each test."""
    session = SessionLocal()
    try:
        session.query(SystemSetting).delete()
        session.commit()
    finally:
        session.close()

    invalidate_cache()
    orig_env_key = os.environ.get("GEMINI_API_KEY")
    orig_env_provider = os.environ.get("AI_PROVIDER")

    yield

    # Restore environment
    if orig_env_key is not None:
        os.environ["GEMINI_API_KEY"] = orig_env_key
    else:
        os.environ.pop("GEMINI_API_KEY", None)

    if orig_env_provider is not None:
        os.environ["AI_PROVIDER"] = orig_env_provider
    else:
        os.environ.pop("AI_PROVIDER", None)

    session = SessionLocal()
    try:
        session.query(SystemSetting).delete()
        session.commit()
    finally:
        session.close()
    invalidate_cache()


def test_settings_save_and_persistence():
    """
    Test that a Gemini API key can be saved through the settings API,
    persists in SQLite, and is retrievable internally while never exposing
    the raw secret in GET responses.
    """
    client = TestClient(app)
    test_key = "AIzaSy_TEST_SETTINGS_SECRET_KEY_1234"

    # Save via POST /api/settings
    resp = client.post("/api/settings", json={
        "ai_provider": "gemini",
        "gemini_api_key": test_key
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["message"] == "Settings saved successfully"
    # Never expose raw key in response
    assert "gemini_api_key" not in data["settings"]
    assert test_key not in json.dumps(data)

    # Verify GET /api/settings preserves persistence across calls
    get_resp = client.get("/api/settings")
    assert get_resp.status_code == 200
    summary = get_resp.json()
    assert summary["ai_provider"] == "gemini"
    assert summary["gemini_api_key_configured"] is True
    assert summary["gemini_api_key_source"] == "settings"
    assert test_key not in json.dumps(summary)
    # Masked representation contains first 6 and last 4
    assert summary["gemini_api_key_masked"] == "AIzaSy********1234"

    # Internally, the real key is resolved correctly
    resolved = resolve_gemini_api_key()
    assert resolved == test_key


def test_precedence_settings_over_env():
    """
    Test C: When both Settings DB and .env are configured,
    Settings UI value takes precedence over .env.
    """
    settings_key = "SETTINGS_OVERRIDE_KEY_9999"
    env_key = "ENV_FALLBACK_KEY_1111"

    os.environ["GEMINI_API_KEY"] = env_key
    set_setting("gemini_api_key", settings_key)
    set_setting("ai_provider", "gemini")

    # The resolver must return the Settings key, NOT the .env key
    resolved = resolve_gemini_api_key()
    assert resolved == settings_key
    assert resolved != env_key

    provider_type = resolve_ai_provider()
    assert provider_type == "gemini"

    summary = get_system_settings_summary()
    assert summary["gemini_api_key_source"] == "settings"


def test_fallback_to_env():
    """
    Test A: When no Settings UI key exists, .env GEMINI_API_KEY is used.
    """
    env_key = "ENV_DEPLOYMENT_KEY_5555"
    os.environ["GEMINI_API_KEY"] = env_key

    # DB has no settings
    resolved = resolve_gemini_api_key()
    assert resolved == env_key

    provider_type = resolve_ai_provider()
    assert provider_type == "gemini"

    summary = get_system_settings_summary()
    assert summary["gemini_api_key_configured"] is True
    assert summary["gemini_api_key_source"] == "env"

    provider = get_ai_provider()
    assert isinstance(provider, GeminiAIProvider)
    assert provider.api_key == env_key


def test_deterministic_fallback():
    """
    Test D: When neither Settings nor .env is configured,
    gracefully fall back to local/deterministic mode with no crash.
    """
    os.environ["GEMINI_API_KEY"] = ""
    os.environ.pop("GEMINI_API_KEY", None)

    resolved = resolve_gemini_api_key()
    assert resolved is None

    provider_type = resolve_ai_provider()
    assert provider_type == "deterministic"

    provider = get_ai_provider()
    assert isinstance(provider, DeterministicAIProvider)

    summary = get_system_settings_summary()
    assert summary["gemini_api_key_configured"] is False
    assert summary["gemini_api_key_source"] == "none"


def test_explicit_deterministic_setting_overrides_env_key():
    """
    When the user explicitly saves ai_provider = "deterministic",
    deterministic mode is respected even if .env has a key.
    """
    os.environ["GEMINI_API_KEY"] = "SOME_ENV_KEY_1234"
    set_setting("ai_provider", "deterministic")

    provider_type = resolve_ai_provider()
    assert provider_type == "deterministic"

    provider = get_ai_provider()
    assert isinstance(provider, DeterministicAIProvider)


def test_runtime_change_affects_next_ai_request():
    """
    Changing the Settings API key immediately affects subsequent Gemini usage
    without restarting the backend.
    """
    client = TestClient(app)

    # State 1: KEY_A
    client.post("/api/settings", json={"ai_provider": "gemini", "gemini_api_key": "KEY_A_TEST_KEY_1111"})
    provider_1 = get_ai_provider()
    assert isinstance(provider_1, GeminiAIProvider)
    assert provider_1.api_key == "KEY_A_TEST_KEY_1111"

    # State 2: KEY_B
    client.post("/api/settings", json={"ai_provider": "gemini", "gemini_api_key": "KEY_B_TEST_KEY_2222"})
    provider_2 = get_ai_provider()
    assert isinstance(provider_2, GeminiAIProvider)
    assert provider_2.api_key == "KEY_B_TEST_KEY_2222"

    # State 3: Clear key -> Fallback to env or deterministic
    client.delete("/api/settings/gemini-key")
    provider_3 = get_ai_provider()
    assert isinstance(provider_3, DeterministicAIProvider)


def test_whitespace_and_empty_keys_treated_as_unconfigured():
    """Empty strings and whitespace-only strings must be treated as not configured."""
    set_setting("gemini_api_key", "   ")
    assert resolve_gemini_api_key() is None

    set_setting("gemini_api_key", "")
    assert resolve_gemini_api_key() is None


def test_clear_saved_key_reverts_to_env():
    """Clearing the saved key allows falling back to .env if present."""
    client = TestClient(app)
    os.environ["GEMINI_API_KEY"] = "ENV_KEY_ACTIVE_7777"

    # First override with settings
    client.post("/api/settings", json={"gemini_api_key": "SETTINGS_TEMP_KEY_8888"})
    assert resolve_gemini_api_key() == "SETTINGS_TEMP_KEY_8888"

    # Now clear saved key
    del_resp = client.delete("/api/settings/gemini-key")
    assert del_resp.status_code == 200
    assert del_resp.json()["settings"]["gemini_api_key_source"] == "env"

    # Resolver now returns env key
    assert resolve_gemini_api_key() == "ENV_KEY_ACTIVE_7777"


@pytest.mark.anyio
async def test_gemini_http_authentication_header_and_url():
    """
    Constraint 11: The actual Gemini request must use:
    x-goog-api-key: <resolved-key>
    and the URL must NOT contain ?key=<api-key>.
    """
    test_key = "AIzaSy_UNIT_TEST_AUTHENTICATION_KEY_9999"
    provider = GeminiAIProvider(api_key=test_key)

    captured_request = {}

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": json.dumps({
                                "suggested_parameter": "security.auth.session_timeout",
                                "suggested_category": "Session Management",
                                "confidence": 0.95,
                                "suggested_value": 300,
                                "explanation": "Session idle timeout setting"
                            })
                        }]
                    }
                }]
            }

    async def mock_post(self, url, json=None, headers=None, **kwargs):
        captured_request["url"] = str(url)
        captured_request["headers"] = headers
        captured_request["json"] = json
        return MockResponse()

    with patch("httpx.AsyncClient.post", new=mock_post):
        result = await provider.interpret_command(
            vendor="cisco",
            command="exec-timeout 5 0",
            context="line vty"
        )

    # 1. Header contains expected key
    assert "x-goog-api-key" in captured_request["headers"]
    assert captured_request["headers"]["x-goog-api-key"] == test_key

    # 2. URL does NOT contain key
    assert "?key=" not in captured_request["url"]
    assert test_key not in captured_request["url"]
    assert captured_request["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    # 3. Valid parsed response returned
    assert result["suggested_parameter"] == "security.auth.session_timeout"
    assert result["confidence"] == 0.95


def test_audit_flow_with_persisted_settings_key():
    """
    End-to-End Test: Verify that an audit run on unfamiliar config syntax
    uses the Settings-configured Gemini API key, correctly authenticates
    via header, and records the Gemini AI interpretation in the unknown_commands table.
    """
    import uuid
    client = TestClient(app)
    persisted_key = "AIzaSy_SETTINGS_PERSISTED_AUDIT_KEY_8888"

    # 1. Save settings via API
    resp = client.post("/api/settings", json={
        "ai_provider": "gemini",
        "gemini_api_key": persisted_key
    })
    assert resp.status_code == 200

    # 2. Upload configuration with unique unfamiliar command
    unique_tag = uuid.uuid4().hex[:8]
    config_content = (
        f"hostname TEST-ROUTER-{unique_tag}\n"
        "ip ssh version 2\n"
        f"custom-vendor-syntax-{unique_tag} security-level max\n"
    )
    files = {"files": (f"test_unfamiliar_{unique_tag}.cfg", config_content, "text/plain")}
    up_resp = client.post("/api/configurations/upload", files=files)
    assert up_resp.status_code == 200
    config_id = up_resp.json()[0]["id"]

    captured_headers = {}

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": json.dumps({
                                "suggested_parameter": "security.custom.level",
                                "suggested_category": "Cryptography",
                                "confidence": 0.92,
                                "suggested_value": "max",
                                "explanation": "Vendor custom security parameter"
                            })
                        }]
                    }
                }]
            }

    async def mock_post(self, url, json=None, headers=None, **kwargs):
        captured_headers.update(headers or {})
        return MockResponse()

    with patch("httpx.AsyncClient.post", new=mock_post):
        audit_resp = client.post(f"/api/audits/run/{config_id}")
        assert audit_resp.status_code == 200

    # Verify that the Gemini provider received the persisted Settings key
    assert "x-goog-api-key" in captured_headers
    assert captured_headers["x-goog-api-key"] == persisted_key

    # Verify that unknown commands were recorded with the Gemini suggestion
    unknown_resp = client.get("/api/training/unknown")
    assert unknown_resp.status_code == 200
    unknowns = [u for u in unknown_resp.json() if u["config_id"] == config_id]
    assert len(unknowns) > 0
    assert any(u["ai_suggested_param"] == "security.custom.level" for u in unknowns)
