import re
import hashlib
from typing import Tuple, Dict, Any

# Regex patterns for detecting and masking sensitive credentials
CREDENTIAL_PATTERNS = [
    # Cisco enable secret / password
    (r'(enable\s+secret\s+\d+\s+)(\S+)', r'\1[MASKED_SECRET_HASH]'),
    (r'(enable\s+password\s+(?:\d+\s+)?)(\S+)', r'\1[MASKED_PASSWORD]'),
    (r'(password\s+(?:\d+\s+)?)(\S+)', r'\1[MASKED_PASSWORD]'),
    (r'(username\s+\S+\s+(?:privilege\s+\d+\s+)?(?:secret|password)\s+(?:\d+\s+)?)(\S+)', r'\1[MASKED_USER_SECRET]'),
    # Juniper encrypted-password
    (r'(encrypted-password\s+)"?([^";\s]+)"?', r'encrypted-password "[MASKED_JUNOS_HASH]"'),
    (r'(authentication-key\s+)"?([^";\s]+)"?', r'authentication-key "[MASKED_KEY]"'),
    (r'(privacy-key\s+)"?([^";\s]+)"?', r'privacy-key "[MASKED_KEY]"'),
    # Fortinet encrypted password
    (r'(set\s+password\s+ENC\s+)(\S+)', r'\1[MASKED_FORTI_HASH]'),
    (r'(set\s+private-key\s+)"?([^";\s]+)"?', r'set private-key "[MASKED_PRIVATE_KEY]"'),
    # SNMP communities
    (r'(snmp-server\s+community\s+)(\S+)', r'\1[MASKED_COMMUNITY]'),
    # JSON / key-value NOS exports
    (r'("?(?:auth_password|password|secret|shared_key|psk)"?\s*:\s*")([^"]+)(")', r'\1[MASKED_SECRET]\3'),
    # Generic pre-shared keys
    (r'(pre-shared-key\s+(?:hex\s+)?|preshared-key\s+|psk\s+)(\S+)', r'\1[MASKED_PRESHARED_KEY]'),
]

def sanitize_content(raw_text: str) -> str:
    """
    Masks credentials and sensitive keys while preserving configuration line structure.
    Never exposes raw secrets in reports or UI.
    """
    sanitized = raw_text
    for pattern, replacement in CREDENTIAL_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized

def process_file_content(file_bytes: bytes, filename: str) -> Tuple[str, str, str, int]:
    """
    Detects encoding, decodes content safely, computes hash, sanitizes secrets.
    Returns: (raw_content, sanitized_content, file_hash, file_size)
    """
    encodings_to_try = ["utf-8", "latin-1", "windows-1252", "ascii"]
    raw_text = None

    for enc in encodings_to_try:
        try:
            raw_text = file_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if raw_text is None:
        raw_text = file_bytes.decode("utf-8", errors="replace")

    # Normalize carriage returns
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # Compute SHA-256
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)

    # Sanitize content
    sanitized = sanitize_content(raw_text)

    return raw_text, sanitized, file_hash, file_size
