"""
SSH Device Puller Engine
=========================
Provides a read-only SSH bridge to pull live `show running-config` (or
vendor-equivalent) from network devices on demand.

Security constraints (ADR-04 / ADR-07):
  ─ Credentials are NEVER persisted to the database or any log file.
  ─ Every connection is torn down immediately after pulling the config.
  ─ The pulled config text is treated as untrusted input and sanitized by
    the standard ingestion pipeline before any storage or analysis.
  ─ Only read-only show commands are sent; no configuration changes are made.

Dependencies:
  - `paramiko` for SSH transport (pure-Python, no Netmiko/Scrapli required).
  - Graceful ImportError: if paramiko is not installed, all functions raise
    a clear RuntimeError so the rest of the API is unaffected.

Install:
    pip install paramiko
"""
from __future__ import annotations

import socket
import re
import io
from dataclasses import dataclass, field
from typing import Optional, Dict, List

# Lazy import so the rest of the codebase is unaffected when paramiko is absent
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:  # pragma: no cover
    paramiko = None
    PARAMIKO_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_SSH_PORT = 22
DEFAULT_TIMEOUT_SECONDS = 15   # TCP connection + banner exchange
DEFAULT_COMMAND_TIMEOUT = 30   # seconds to wait for show command to complete

# Vendor → show running-config command mapping (read-only, deterministic)
VENDOR_SHOW_COMMANDS: Dict[str, List[str]] = {
    "cisco": [
        "terminal length 0",          # disable paging
        "show running-config",
    ],
    "juniper": [
        "set cli screen-length 0",
        "show configuration | no-more",
    ],
    "fortinet": [
        "config system global",
        "end",
        "show",
    ],
    "paloalto": [
        "set cli scripting-mode on",
        "show config running format text",
    ],
    "arista": [
        "terminal width 512",
        "terminal length 0",
        "show running-config",
    ],
    "sonic": [
        "show runningconfiguration all",
    ],
    "cumulus": [
        "net show configuration commands",
    ],
    "checkpoint": [
        "show configuration",
    ],
    "sophos": [
        "show running-config",
    ],
    # Default fallback for unknown vendors
    "__default__": [
        "terminal length 0",
        "show running-config",
    ],
}

# CLI prompts we consider "ready for input" (regex)
PROMPT_PATTERN = re.compile(
    r"[\w\-\.@]+[>#\$]\s*$",
    re.MULTILINE,
)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class SSHPullRequest:
    """Validated parameters for a one-shot SSH config pull."""
    hostname: str
    port: int = DEFAULT_SSH_PORT
    username: str = ""
    password: str = ""
    vendor_hint: str = ""       # optional: skip vendor-autodetect on fetched config
    use_key_auth: bool = False  # if True, username + SSH agent key is used
    key_passphrase: str = ""    # optional key passphrase (not stored)
    timeout: int = DEFAULT_TIMEOUT_SECONDS


@dataclass
class SSHPullResult:
    """Result of a single SSH config pull."""
    host: str
    port: int
    success: bool
    raw_config: str = ""             # the raw show output
    error: str = ""
    commands_sent: List[str] = field(default_factory=list)
    elapsed_ms: int = 0


# ── Core Engine ───────────────────────────────────────────────────────────────

def _require_paramiko() -> None:
    if not PARAMIKO_AVAILABLE:
        raise RuntimeError(
            "The `paramiko` package is required for SSH Device Puller. "
            "Install it with: pip install paramiko"
        )


def _resolve_commands(vendor_hint: str) -> List[str]:
    """Return the list of show commands for a given vendor hint."""
    hint = vendor_hint.lower().strip() if vendor_hint else ""
    for key, cmds in VENDOR_SHOW_COMMANDS.items():
        if key != "__default__" and key in hint:
            return cmds
    return VENDOR_SHOW_COMMANDS["__default__"]


def _read_until_prompt(
    channel: "paramiko.Channel",
    timeout: int = DEFAULT_COMMAND_TIMEOUT,
) -> str:
    """
    Read output from an interactive SSH channel until a CLI prompt is detected
    or the timeout elapses. Returns the accumulated output as a string.
    """
    buf = b""
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if channel.recv_ready():
            chunk = channel.recv(65536)
            if not chunk:
                break
            buf += chunk
            text = buf.decode("utf-8", errors="replace")
            if PROMPT_PATTERN.search(text):
                break
        else:
            time.sleep(0.05)
    return buf.decode("utf-8", errors="replace")


def pull_device_config(req: SSHPullRequest) -> SSHPullResult:
    """
    Open a read-only SSH session to the target device, send the appropriate
    `show running-config` command sequence, and return the raw output.

    The SSH connection is guaranteed to be closed regardless of outcome.
    Credentials are not stored or logged anywhere in this function.

    Args:
        req: SSHPullRequest with all connection parameters.

    Returns:
        SSHPullResult with success status and raw config text.
    """
    import time

    _require_paramiko()

    commands = _resolve_commands(req.vendor_hint)
    start = time.monotonic()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        connect_kwargs: dict = {
            "hostname": req.hostname,
            "port": req.port,
            "username": req.username,
            "timeout": req.timeout,
            "look_for_keys": req.use_key_auth,
            "allow_agent": req.use_key_auth,
        }
        if not req.use_key_auth:
            connect_kwargs["password"] = req.password
        if req.key_passphrase:
            connect_kwargs["passphrase"] = req.key_passphrase

        client.connect(**connect_kwargs)

        channel = client.invoke_shell(width=512, height=40000)
        channel.settimeout(req.timeout)

        # Drain initial banner / MOTD
        _read_until_prompt(channel, timeout=req.timeout)

        collected_output: List[str] = []
        sent: List[str] = []

        for cmd in commands:
            channel.send(cmd + "\n")
            sent.append(cmd)
            out = _read_until_prompt(channel, timeout=DEFAULT_COMMAND_TIMEOUT)
            collected_output.append(out)

        channel.close()
        raw_config = "\n".join(collected_output)

        elapsed = int((time.monotonic() - start) * 1000)
        return SSHPullResult(
            host=req.hostname,
            port=req.port,
            success=True,
            raw_config=raw_config,
            commands_sent=sent,
            elapsed_ms=elapsed,
        )

    except paramiko.AuthenticationException as exc:
        return SSHPullResult(
            host=req.hostname, port=req.port, success=False,
            error=f"Authentication failed: {exc}",
        )
    except (socket.timeout, paramiko.SSHException, OSError) as exc:
        return SSHPullResult(
            host=req.hostname, port=req.port, success=False,
            error=f"SSH connection error: {exc}",
        )
    finally:
        # Guaranteed credential teardown — clear sensitive refs
        client.close()
        try:
            del connect_kwargs["password"]
        except Exception:
            pass


def test_ssh_connectivity(hostname: str, port: int = DEFAULT_SSH_PORT, timeout: int = 5) -> bool:
    """
    TCP-level connectivity probe (no credentials). Returns True if port is reachable.
    Safe to call before attempting a full pull to give users faster feedback.
    """
    try:
        with socket.create_connection((hostname, port), timeout=timeout):
            return True
    except (socket.timeout, OSError):
        return False
