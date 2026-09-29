"""
Webhook Processor Engine
========================
Parses GitHub and GitLab push event payloads to identify added/modified
network configuration files, and fetches their raw content for ingestion
into the compliance pipeline.

No live device connections are made. Configurations are fetched as plain
text over HTTPS from the public GitHub / GitLab raw-content CDN, then
treated exactly like an uploaded file: sanitized, parsed, normalized, and
audited deterministically.
"""
import re
import urllib.request
import urllib.error
from typing import List, Tuple, Optional
from dataclasses import dataclass, field

# Extensions treated as network configuration files in a git repo
CONFIG_EXTENSIONS = {".cfg", ".conf", ".txt", ".json", ".set", ""}

# Extensionless files that are explicitly NOT network configs
SKIP_BASENAMES = {
    "Makefile", "makefile", "GNUmakefile",
    "Dockerfile", "dockerfile",
    "Vagrantfile", "Jenkinsfile",
    "LICENSE", "LICENCE", "README",
    "CHANGELOG", "AUTHORS", "NOTICE",
}

# Maximum size of a single config file fetched from a remote URL (5 MB)
MAX_REMOTE_FILE_BYTES = 5 * 1024 * 1024

# HTTP timeout for raw file fetch (seconds)
FETCH_TIMEOUT_SECONDS = 10


@dataclass
class ChangedConfigFile:
    """Represents a network config file identified in a push event."""
    filename: str          # e.g. "configs/cisco_core.cfg"
    raw_url: str           # direct URL to raw file content
    status: str            # "added" | "modified" | "removed"
    sha: str = ""          # git blob SHA (from GitHub) or commit id fragment


@dataclass
class WebhookParseResult:
    """Structured result of parsing a push webhook payload."""
    platform: str                                   # "github" | "gitlab"
    repository: str                                  # owner/repo or namespace/project
    branch: str
    commit_sha: str
    commit_message: str
    pusher: str
    config_files: List[ChangedConfigFile] = field(default_factory=list)
    ignored_files: List[str] = field(default_factory=list)  # non-config file paths
    parse_errors: List[str] = field(default_factory=list)


def _is_config_file(path: str) -> bool:
    """Return True if the file path has a recognised network config extension."""
    import os
    basename = os.path.basename(path.replace("\\", "/"))
    _, ext = os.path.splitext(basename)
    ext_lower = ext.lower()
    # Explicitly skip known build/meta files even if they have no extension
    if not ext and basename in SKIP_BASENAMES:
        return False
    return ext_lower in CONFIG_EXTENSIONS


def parse_github_payload(payload: dict) -> WebhookParseResult:
    """
    Parse a GitHub `push` event webhook payload.

    Extracts repository info, branch, commit metadata, and identifies all
    added/modified config files with their raw GitHub CDN URLs.

    Reference: https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#push
    """
    repo_full_name = payload.get("repository", {}).get("full_name", "unknown/unknown")
    branch_ref = payload.get("ref", "refs/heads/main")
    branch = branch_ref.replace("refs/heads/", "").replace("refs/tags/", "")
    commits = payload.get("commits", [])

    # Use the head commit for metadata
    head_commit = payload.get("head_commit") or (commits[-1] if commits else {})
    commit_sha = payload.get("after", head_commit.get("id", ""))[:40]
    commit_message = head_commit.get("message", "")[:200]
    pusher = payload.get("pusher", {}).get("name", "unknown")

    result = WebhookParseResult(
        platform="github",
        repository=repo_full_name,
        branch=branch,
        commit_sha=commit_sha,
        commit_message=commit_message,
        pusher=pusher,
    )

    # Collect unique added/modified files across all commits in the push
    seen: set = set()
    for commit in commits:
        commit_id = commit.get("id", commit_sha)
        for status in ("added", "modified"):
            for path in commit.get(status, []):
                if path in seen:
                    continue
                seen.add(path)
                if not _is_config_file(path):
                    result.ignored_files.append(path)
                    continue
                # Build GitHub raw CDN URL
                raw_url = (
                    f"https://raw.githubusercontent.com/"
                    f"{repo_full_name}/{commit_id}/{path}"
                )
                result.config_files.append(ChangedConfigFile(
                    filename=path,
                    raw_url=raw_url,
                    status=status,
                    sha=commit_id[:12],
                ))

    return result


def parse_gitlab_payload(payload: dict) -> WebhookParseResult:
    """
    Parse a GitLab `Push Hook` webhook payload.

    Reference: https://docs.gitlab.com/ce/user/project/integrations/webhook_events.html#push-events
    """
    project = payload.get("project", {})
    repo_full_name = project.get("path_with_namespace", "unknown/unknown")
    homepage = project.get("homepage", "")

    branch_ref = payload.get("ref", "refs/heads/main")
    branch = branch_ref.replace("refs/heads/", "").replace("refs/tags/", "")
    commit_sha = payload.get("after", "")[:40]
    commits = payload.get("commits", [])
    head_commit = commits[-1] if commits else {}
    commit_message = head_commit.get("message", "")[:200]
    pusher = payload.get("user_name", "unknown")

    result = WebhookParseResult(
        platform="gitlab",
        repository=repo_full_name,
        branch=branch,
        commit_sha=commit_sha,
        commit_message=commit_message,
        pusher=pusher,
    )

    seen: set = set()
    for commit in commits:
        commit_id = commit.get("id", commit_sha)
        for status in ("added", "modified"):
            for path in commit.get(status, []):
                if path in seen:
                    continue
                seen.add(path)
                if not _is_config_file(path):
                    result.ignored_files.append(path)
                    continue
                # Build GitLab raw file URL
                # Format: <homepage>/-/raw/<commit_sha>/<path>
                raw_url = f"{homepage.rstrip('/')}/-/raw/{commit_id}/{path}"
                result.config_files.append(ChangedConfigFile(
                    filename=path,
                    raw_url=raw_url,
                    status=status,
                    sha=commit_id[:12],
                ))

    return result


def fetch_raw_file(url: str, token: Optional[str] = None) -> bytes:
    """
    Fetch a raw configuration file from a GitHub/GitLab CDN URL.

    Args:
        url:   HTTPS URL to the raw file content.
        token: Optional GitHub/GitLab personal access token for private repos.

    Returns:
        Raw bytes of the file content.

    Raises:
        ValueError: If the file is too large or the URL is unreachable.
    """
    headers = {"User-Agent": "MultiVendorAuditor/2.0 (SIH-2026)"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_SECONDS) as resp:
            # Stream with size guard
            chunks: List[bytes] = []
            total = 0
            while True:
                chunk = resp.read(65536)  # 64 KB chunks
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_REMOTE_FILE_BYTES:
                    raise ValueError(
                        f"Remote file exceeds maximum allowed size "
                        f"({MAX_REMOTE_FILE_BYTES // (1024*1024)} MB): {url}"
                    )
                chunks.append(chunk)
            return b"".join(chunks)
    except urllib.error.HTTPError as exc:
        raise ValueError(f"HTTP {exc.code} fetching {url}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Network error fetching {url}: {exc.reason}") from exc
    except TimeoutError:
        raise ValueError(f"Timeout fetching {url} after {FETCH_TIMEOUT_SECONDS}s")


def simulate_fetch_raw_file(content: str, _url: str = "") -> bytes:
    """
    Test/demo substitute for fetch_raw_file.
    Returns the content encoded as UTF-8 bytes without making any network call.
    Used in test suites and the offline demo mode.
    """
    return content.encode("utf-8")
