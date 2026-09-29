"""
test_webhooks.py
================
Tests for the GitOps Webhook Auditing engine (webhook_processor.py) and
the POST /api/webhooks/github and /api/webhooks/gitlab FastAPI endpoints.

Tests run fully offline — no real network calls are made. The
`fetch_raw_file` function is monkeypatched to return in-memory config bytes.

Covers:
  - GitHub payload parsing (push event with added/modified files)
  - GitLab payload parsing (push hook)
  - Extension filtering (non-config files skipped)
  - HMAC-SHA256 signature validation (GitHub)
  - GitLab token validation
  - Missing/wrong signature returns 401
  - Non-push event type returns 200 acknowledgement
  - API endpoint happy-path: end-to-end audit triggered from payload
  - /webhooks/status configuration endpoint
"""
import hashlib
import hmac
import json
import gc
import os
import pytest
from fastapi.testclient import TestClient

from backend.app.engine.webhook_processor import (
    parse_github_payload,
    parse_gitlab_payload,
    simulate_fetch_raw_file,
    WebhookParseResult,
)

# ---------------------------------------------------------------------------
# Sample payloads
# ---------------------------------------------------------------------------

CISCO_CONFIG = """\
hostname WEBHOOK-CISCO
!
ip ssh version 2
no ip http server
banner motd ^C Authorized use only ^C
line vty 0 4
 transport input ssh
!
"""

def _make_github_payload(files_added=None, files_modified=None) -> dict:
    return {
        "ref": "refs/heads/main",
        "after": "abc123def456abc123def456abc123def456abc1",
        "before": "0" * 40,
        "repository": {"full_name": "sih-org/network-configs"},
        "pusher": {"name": "netops-engineer"},
        "head_commit": {
            "id": "abc123def456abc123def456abc123def456abc1",
            "message": "chore: harden core router configs",
        },
        "commits": [
            {
                "id": "abc123def456abc123def456abc123def456abc1",
                "message": "chore: harden core router configs",
                "added": files_added or [],
                "modified": files_modified or [],
                "removed": [],
            }
        ],
    }


def _make_gitlab_payload(files_added=None, files_modified=None) -> dict:
    return {
        "ref": "refs/heads/main",
        "after": "deadbeef1234deadbeef1234deadbeef12345678",
        "before": "0" * 40,
        "user_name": "devops-lead",
        "project": {
            "path_with_namespace": "sih-org/network-configs",
            "homepage": "https://gitlab.example.com/sih-org/network-configs",
        },
        "commits": [
            {
                "id": "deadbeef1234deadbeef1234deadbeef12345678",
                "message": "feat: add juniper srx config",
                "added": files_added or [],
                "modified": files_modified or [],
                "removed": [],
            }
        ],
    }


def _sign_github(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ===========================================================================
# Unit tests — webhook_processor engine
# ===========================================================================

class TestGitHubPayloadParser:
    def test_parse_push_with_cfg_files(self):
        payload = _make_github_payload(
            files_added=["configs/cisco_core.cfg"],
            files_modified=["routers/juniper_edge.conf"],
        )
        result = parse_github_payload(payload)
        assert result.platform == "github"
        assert result.repository == "sih-org/network-configs"
        assert result.branch == "main"
        assert result.pusher == "netops-engineer"
        assert len(result.config_files) == 2
        assert all("raw.githubusercontent.com" in cf.raw_url for cf in result.config_files)

    def test_parse_filters_non_config_extensions(self):
        payload = _make_github_payload(
            files_added=["configs/cisco.cfg", "docs/README.md", "scripts/deploy.sh"],
        )
        result = parse_github_payload(payload)
        assert len(result.config_files) == 1
        assert len(result.ignored_files) == 2

    def test_parse_deduplicates_across_commits(self):
        """Same file appearing in two commits should only be processed once."""
        payload = _make_github_payload()
        payload["commits"] = [
            {"id": "aaa", "added": ["router.cfg"], "modified": [], "removed": []},
            {"id": "bbb", "added": ["router.cfg"], "modified": [], "removed": []},
        ]
        result = parse_github_payload(payload)
        assert len(result.config_files) == 1

    def test_parse_empty_commit_returns_no_files(self):
        payload = _make_github_payload()
        result = parse_github_payload(payload)
        assert len(result.config_files) == 0
        assert len(result.ignored_files) == 0


class TestGitLabPayloadParser:
    def test_parse_push_hook(self):
        payload = _make_gitlab_payload(files_added=["switches/arista_spine.cfg"])
        result = parse_gitlab_payload(payload)
        assert result.platform == "gitlab"
        assert result.repository == "sih-org/network-configs"
        assert result.pusher == "devops-lead"
        assert len(result.config_files) == 1
        assert "/-/raw/" in result.config_files[0].raw_url

    def test_parse_non_config_files_ignored(self):
        payload = _make_gitlab_payload(
            files_modified=["fw.conf", "Makefile", "ci.yml"]
        )
        result = parse_gitlab_payload(payload)
        assert len(result.config_files) == 1
        assert len(result.ignored_files) == 2


class TestSimulateFetch:
    def test_simulate_returns_encoded_bytes(self):
        data = simulate_fetch_raw_file(CISCO_CONFIG)
        assert isinstance(data, bytes)
        assert b"hostname WEBHOOK-CISCO" in data


# ===========================================================================
# Integration tests — FastAPI endpoints
# ===========================================================================

@pytest.fixture(scope="module")
def client():
    """TestClient with offline file fetching and isolated SQLite DB."""
    import gc
    from unittest.mock import patch

    os.environ["DATABASE_URL"] = "sqlite:///./test_webhooks.db"
    os.environ["AI_PROVIDER"] = "deterministic"
    os.environ["GITHUB_WEBHOOK_SECRET"] = ""
    os.environ["GITLAB_WEBHOOK_SECRET"] = ""

    def _mock_fetch(url: str, token=None) -> bytes:
        return CISCO_CONFIG.encode("utf-8")

    with patch("backend.app.api.webhooks.fetch_raw_file", side_effect=_mock_fetch):
        from backend.app.main import app
        with TestClient(app) as c:
            yield c

    gc.collect()
    try:
        if os.path.exists("test_webhooks.db"):
            os.remove("test_webhooks.db")
    except PermissionError:
        pass


class TestGitHubEndpoint:
    def test_github_push_triggers_audit(self, client: TestClient):
        payload = _make_github_payload(files_added=["configs/cisco.cfg"])
        body = json.dumps(payload).encode()
        response = client.post(
            "/api/webhooks/github",
            content=body,
            headers={"Content-Type": "application/json", "X-Github-Event": "push"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "github"
        assert data["repository"] == "sih-org/network-configs"
        assert data["audited"] == 1
        assert data["errors"] == 0
        # Verify the audited file has a real audit_id
        assert data["files"][0]["audit_id"] is not None
        assert data["files"][0]["compliance_percentage"] is not None

    def test_github_non_push_event_acknowledged(self, client: TestClient):
        response = client.post(
            "/api/webhooks/github",
            content=b"{}",
            headers={"Content-Type": "application/json", "X-Github-Event": "ping"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["audited"] == 0

    def test_github_invalid_signature_returns_401(self, client: TestClient):
        # Set a temporary secret for this test
        import backend.app.api.webhooks as wh_module
        from backend.app.config import settings
        original = settings.GITHUB_WEBHOOK_SECRET
        settings.GITHUB_WEBHOOK_SECRET = "super-secret"
        try:
            response = client.post(
                "/api/webhooks/github",
                content=b'{"ref":"refs/heads/main"}',
                headers={
                    "Content-Type": "application/json",
                    "X-Github-Event": "push",
                    "X-Hub-Signature-256": "sha256=wrongsignature",
                },
            )
            assert response.status_code == 401
        finally:
            settings.GITHUB_WEBHOOK_SECRET = original

    def test_github_valid_hmac_passes(self, client: TestClient):
        from backend.app.config import settings
        secret = "my-test-secret"
        original = settings.GITHUB_WEBHOOK_SECRET
        settings.GITHUB_WEBHOOK_SECRET = secret
        try:
            body = json.dumps(_make_github_payload(files_added=["r.cfg"])).encode()
            sig = _sign_github(body, secret)
            response = client.post(
                "/api/webhooks/github",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Github-Event": "push",
                    "X-Hub-Signature-256": sig,
                },
            )
            assert response.status_code == 200
        finally:
            settings.GITHUB_WEBHOOK_SECRET = original

    def test_github_non_config_files_skipped(self, client: TestClient):
        payload = _make_github_payload(
            files_added=["README.md", "Makefile", "ci.yml"]
        )
        response = client.post(
            "/api/webhooks/github",
            content=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "X-Github-Event": "push"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["audited"] == 0
        assert data["skipped"] == 3


class TestGitLabEndpoint:
    def test_gitlab_push_triggers_audit(self, client: TestClient):
        payload = _make_gitlab_payload(files_added=["devices/fw.conf"])
        response = client.post(
            "/api/webhooks/gitlab",
            content=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "X-Gitlab-Event": "Push Hook"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "gitlab"
        assert data["audited"] == 1

    def test_gitlab_invalid_token_returns_401(self, client: TestClient):
        from backend.app.config import settings
        original = settings.GITLAB_WEBHOOK_SECRET
        settings.GITLAB_WEBHOOK_SECRET = "correct-secret"
        try:
            response = client.post(
                "/api/webhooks/gitlab",
                content=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "X-Gitlab-Event": "Push Hook",
                    "X-Gitlab-Token": "wrong-token",
                },
            )
            assert response.status_code == 401
        finally:
            settings.GITLAB_WEBHOOK_SECRET = original


class TestWebhookStatus:
    def test_status_endpoint_returns_config(self, client: TestClient):
        response = client.get("/api/webhooks/status")
        assert response.status_code == 200
        data = response.json()
        assert "github_endpoint" in data
        assert "gitlab_endpoint" in data
        assert "supported_extensions" in data
        assert ".cfg" in data["supported_extensions"]
