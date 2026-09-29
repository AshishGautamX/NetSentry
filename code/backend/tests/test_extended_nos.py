import os
import pytest
from backend.app.engine.vendor_detector import VendorDetector
from backend.app.engine.parsers import get_parser_for_vendor
from backend.app.engine.normalizer import NormalizationEngine

def test_sonic_detection_and_parsing():
    sample_path = os.path.join("sample_configs", "sonic_config_db.json")
    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Detection
    detected = VendorDetector.detect(content)
    assert detected["vendor"] == "sonic"
    assert detected["hostname"] == "SONIC-SPINE-01"
    assert "SONiC" in detected["os_version"]

    # 2. Parsing
    parser = get_parser_for_vendor("sonic")
    parsed_lines = parser.parse(content)
    assert len(parsed_lines) > 20
    assert any("DEVICE_METADATA" in p.section_context for p in parsed_lines)

    # 3. Normalization
    normalizer = NormalizationEngine()
    processed, baseline, unknown = normalizer.normalize(parsed_lines, "sonic")
    params = baseline["parameters"]
    assert params.get("security.ssh.version") == 2
    assert params.get("security.session_timeout") == 300
    assert params.get("security.ntp.configured") is True
    assert params.get("security.logging.syslog_enabled") is True
    assert params.get("security.routing.bgp_auth_enabled") is True
    assert params.get("security.routing.bgp_max_prefix") is True

def test_cumulus_detection_and_parsing():
    sample_path = os.path.join("sample_configs", "cumulus_switch.conf")
    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Detection
    detected = VendorDetector.detect(content)
    assert detected["vendor"] == "cumulus"
    assert detected["hostname"] == "CUMULUS-LEAF-01"

    # 2. Parsing
    parser = get_parser_for_vendor("cumulus")
    parsed_lines = parser.parse(content)
    assert len(parsed_lines) > 15
    assert any("router bgp" in p.section_context for p in parsed_lines)

    # 3. Normalization
    normalizer = NormalizationEngine()
    processed, baseline, unknown = normalizer.normalize(parsed_lines, "cumulus")
    params = baseline["parameters"]
    assert params.get("security.password_policy.encryption_service") is True
    assert params.get("security.routing.bgp_auth_enabled") is True
    assert params.get("security.routing.bgp_max_prefix") is True
    assert params.get("security.session_timeout") == 300
    assert params.get("security.telnet.enabled") is False
    assert params.get("security.ip.source_routing_disabled") is True
    assert params.get("security.ip.redirects_disabled") is True

def test_checkpoint_detection_and_parsing():
    sample_path = os.path.join("sample_configs", "checkpoint_gaia.conf")
    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Detection
    detected = VendorDetector.detect(content)
    assert detected["vendor"] == "checkpoint"
    assert detected["hostname"] == "CP-GW-PRIMARY"
    assert "Gaia" in detected["os_version"]

    # 2. Parsing
    parser = get_parser_for_vendor("checkpoint")
    parsed_lines = parser.parse(content)
    assert len(parsed_lines) > 5

    # 3. Normalization
    normalizer = NormalizationEngine()
    processed, baseline, unknown = normalizer.normalize(parsed_lines, "checkpoint")
    params = baseline["parameters"]
    assert params.get("security.ssh.version") == 2
    assert params.get("security.session_timeout") == 600  # 10 min * 60
    assert params.get("security.password_policy.min_length") == 14
    assert params.get("security.ntp.configured") is True
    assert params.get("security.snmp.v3_only") is True
    assert params.get("security.aaa.authentication_login") is True

def test_sophos_detection_and_parsing():
    sample_path = os.path.join("sample_configs", "sophos_sfos.conf")
    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Detection
    detected = VendorDetector.detect(content)
    assert detected["vendor"] == "sophos"
    assert detected["hostname"] == "SOPHOS-CORP-FW"
    assert "SFOS" in detected["os_version"]

    # 2. Parsing
    parser = get_parser_for_vendor("sophos")
    parsed_lines = parser.parse(content)
    assert len(parsed_lines) > 5

    # 3. Normalization
    normalizer = NormalizationEngine()
    processed, baseline, unknown = normalizer.normalize(parsed_lines, "sophos")
    params = baseline["parameters"]
    assert params.get("security.ssh.version") == 2
    assert params.get("security.session_timeout") == 600
    assert params.get("security.password_policy.min_length") == 14
    assert params.get("security.ntp.configured") is True
    assert params.get("security.logging.syslog_enabled") is True
    assert params.get("security.snmp.v3_only") is True
