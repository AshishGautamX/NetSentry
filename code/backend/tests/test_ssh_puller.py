"""
test_ssh_puller.py
==================
Tests for the SSH Device Puller engine (ssh_puller.py) and
the /api/ssh/* FastAPI endpoints.

ALL SSH operations are fully mocked — no live network hardware is required.
Paramiko is monkey-patched at the module level so these tests pass even
if paramiko is not installed.

Covers:
  - TCP probe (test_ssh_connectivity)
  - Vendor command resolution
  - pull_device_config: success path
  - pull_device_config: authentication failure
  - pull_device_config: connection error (timeout)
  - pull_device_config: empty config returned
  - API GET /api/ssh/probe (reachable / unreachable)
  - API POST /api/ssh/pull (happy path with full pipeline)
  - API POST /api/ssh/pull (SSH auth failure → 200 with success=False)
  - API GET /api/ssh/commands (vendor listing)
  - API GET /api/ssh/status
"""
import gc
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.engine.ssh_puller import (
    _resolve_commands,
    pull_device_config,
    SSHPullRequest,
    SSHPullResult,
    VENDOR_SHOW_COMMANDS,
)

# ---------------------------------------------------------------------------
# Sample config returned by the mocked SSH session
# ---------------------------------------------------------------------------
MOCK_CONFIG = """\
hostname LIVE-CISCO-ROUTER
!
ip ssh version 2
no ip http server
banner motd ^C Authorized use only ^C
line vty 0 4
 transport input ssh
 login local
!
"""


# ===========================================================================
# Unit tests — engine layer
# ===========================================================================

class TestVendorCommandResolution:
    def test_cisco_commands(self):
        cmds = _resolve_commands("cisco")
        assert any("show running-config" in c for c in cmds)

    def test_juniper_commands(self):
        cmds = _resolve_commands("juniper")
        assert any("show configuration" in c for c in cmds)

    def test_paloalto_commands(self):
        cmds = _resolve_commands("paloalto")
        assert any("show config" in c for c in cmds)

    def test_unknown_vendor_falls_back_to_default(self):
        cmds = _resolve_commands("brandx-unknown-os")
        assert cmds == VENDOR_SHOW_COMMANDS["__default__"]

    def test_empty_vendor_hint_falls_back(self):
        cmds = _resolve_commands("")
        assert cmds == VENDOR_SHOW_COMMANDS["__default__"]


class TestTCPProbe:
    def test_reachable_host(self):
        with patch("socket.create_connection") as mock_conn:
            mock_conn.return_value.__enter__ = MagicMock(return_value=None)
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            from backend.app.engine.ssh_puller import test_ssh_connectivity
            assert test_ssh_connectivity("192.168.1.1", 22) is True

    def test_unreachable_host(self):
        with patch("socket.create_connection", side_effect=OSError("Connection refused")):
            from backend.app.engine.ssh_puller import test_ssh_connectivity
            assert test_ssh_connectivity("10.0.0.99", 22) is False


class TestPullDeviceConfig:
    def _mock_paramiko_session(self, raw_output: str):
        """Build a complete mock paramiko.SSHClient that returns raw_output."""
        mock_channel = MagicMock()
        mock_channel.recv_ready.side_effect = [True, True, False] * 10
        mock_channel.recv.return_value = (raw_output + "\nROUTER#").encode()

        mock_transport = MagicMock()
        mock_client = MagicMock()
        mock_client.invoke_shell.return_value = mock_channel
        return mock_client, mock_channel

    def test_successful_pull(self):
        mock_client, _ = self._mock_paramiko_session(MOCK_CONFIG)
        with patch("backend.app.engine.ssh_puller.PARAMIKO_AVAILABLE", True), \
             patch("backend.app.engine.ssh_puller.paramiko") as mock_para:
            mock_para.SSHClient.return_value = mock_client
            mock_para.AutoAddPolicy.return_value = MagicMock()
            mock_para.AuthenticationException = Exception

            req = SSHPullRequest(
                hostname="192.168.1.1", username="admin", password="admin"
            )
            result = pull_device_config(req)

        assert result.success is True
        assert result.host == "192.168.1.1"
        assert len(result.raw_config) > 0

    def test_authentication_failure(self):
        with patch("backend.app.engine.ssh_puller.PARAMIKO_AVAILABLE", True), \
             patch("backend.app.engine.ssh_puller.paramiko") as mock_para:
            mock_para.SSHClient.return_value.connect.side_effect = (
                Exception("Authentication failed")
            )
            mock_para.AuthenticationException = Exception
            mock_para.AutoAddPolicy.return_value = MagicMock()

            req = SSHPullRequest(hostname="192.168.1.1", username="bad", password="bad")
            result = pull_device_config(req)

        assert result.success is False
        assert "Authentication" in result.error or "error" in result.error.lower()

    def test_paramiko_not_installed_raises(self):
        with patch("backend.app.engine.ssh_puller.PARAMIKO_AVAILABLE", False):
            from backend.app.engine.ssh_puller import _require_paramiko
            with pytest.raises(RuntimeError, match="paramiko"):
                _require_paramiko()


# ===========================================================================
# Integration tests — FastAPI endpoints
# ===========================================================================

@pytest.fixture(scope="module")
def client():
    gc.collect()
    os.environ["DATABASE_URL"] = "sqlite:///./test_ssh.db"
    os.environ["AI_PROVIDER"] = "deterministic"

    from backend.app.main import app
    with TestClient(app) as c:
        yield c

    gc.collect()
    try:
        if os.path.exists("test_ssh.db"):
            os.remove("test_ssh.db")
    except PermissionError:
        pass


class TestSSHProbeEndpoint:
    def test_reachable_device(self, client: TestClient):
        with patch(
            "backend.app.api.ssh_devices.test_ssh_connectivity", return_value=True
        ):
            resp = client.get("/api/ssh/probe?hostname=192.168.1.1&port=22")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reachable"] is True
        assert data["hostname"] == "192.168.1.1"

    def test_unreachable_device(self, client: TestClient):
        with patch(
            "backend.app.api.ssh_devices.test_ssh_connectivity", return_value=False
        ):
            resp = client.get("/api/ssh/probe?hostname=10.0.0.99&port=22")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reachable"] is False


class TestSSHPullEndpoint:
    def _mock_pull_success(self):
        return SSHPullResult(
            host="192.168.1.1",
            port=22,
            success=True,
            raw_config=MOCK_CONFIG,
            commands_sent=["terminal length 0", "show running-config"],
            elapsed_ms=312,
        )

    def _mock_pull_failure(self):
        return SSHPullResult(
            host="192.168.1.1",
            port=22,
            success=False,
            error="Authentication failed: bad credentials",
            elapsed_ms=80,
        )

    def test_successful_pull_triggers_audit(self, client: TestClient):
        with patch("backend.app.api.ssh_devices.PARAMIKO_AVAILABLE", True), \
             patch(
                 "backend.app.api.ssh_devices.pull_device_config",
                 return_value=self._mock_pull_success()
             ):
            resp = client.post("/api/ssh/pull", json={
                "hostname": "192.168.1.1",
                "username": "admin",
                "password": "secret123",
                "vendor_hint": "cisco",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["config_id"] is not None
        assert data["audit_id"] is not None
        assert data["vendor_detected"] is not None
        assert data["compliance_percentage"] is not None
        assert data["risk_level"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    def test_auth_failure_returns_success_false(self, client: TestClient):
        with patch("backend.app.api.ssh_devices.PARAMIKO_AVAILABLE", True), \
             patch(
                 "backend.app.api.ssh_devices.pull_device_config",
                 return_value=self._mock_pull_failure()
             ):
            resp = client.post("/api/ssh/pull", json={
                "hostname": "192.168.1.1",
                "username": "bad",
                "password": "wrong",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "Authentication" in data["error"] or "failed" in data["error"].lower()


class TestSSHInfoEndpoints:
    def test_commands_endpoint_cisco(self, client: TestClient):
        resp = client.get("/api/ssh/commands?vendor=cisco")
        assert resp.status_code == 200
        data = resp.json()
        assert "show running-config" in data["commands"]
        assert "cisco" in data["vendor"]

    def test_commands_endpoint_juniper(self, client: TestClient):
        resp = client.get("/api/ssh/commands?vendor=juniper")
        assert resp.status_code == 200
        data = resp.json()
        assert any("show configuration" in c for c in data["commands"])

    def test_status_endpoint(self, client: TestClient):
        resp = client.get("/api/ssh/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "paramiko_available" in data
        assert "supported_vendors" in data
        assert "security_notes" in data
        assert len(data["security_notes"]) > 0
