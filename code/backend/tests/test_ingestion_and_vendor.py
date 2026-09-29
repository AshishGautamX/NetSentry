import pytest
from backend.app.engine.ingestion import process_file_content, sanitize_content
from backend.app.engine.vendor_detector import VendorDetector

def test_secret_sanitization():
    raw_cfg = """
    enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7m0
    password cisco123
    snmp-server community public RO
    "auth_password": "SonicSecretKey123"
    """
    sanitized = sanitize_content(raw_cfg)
    assert "$1$mERr$hx5rVt7rPNoS4wqbXKX7m0" not in sanitized
    assert "cisco123" not in sanitized
    assert "SonicSecretKey123" not in sanitized
    assert "[MASKED_SECRET_HASH]" in sanitized
    assert "[MASKED_PASSWORD]" in sanitized
    assert "[MASKED_COMMUNITY]" in sanitized
    assert "[MASKED_SECRET]" in sanitized

def test_cisco_vendor_detection():
    sample = """
    ! Current Configuration - Cisco Catalyst 9300
    version 17.6
    hostname CORE-SW-01
    ip ssh version 2
    """
    res = VendorDetector.detect(sample)
    assert res["vendor"] == "cisco"
    assert res["hostname"] == "CORE-SW-01"
    assert "17.6" in res["os_version"]

def test_juniper_vendor_detection():
    sample = """
    ## Last changed: 2026-02-14
    version 21.4R3.15;
    system {
        host-name EDGE-SRX-01;
    }
    """
    res = VendorDetector.detect(sample)
    assert res["vendor"] == "juniper"
    assert res["hostname"] == "EDGE-SRX-01"
    assert "21.4R3.15" in res["os_version"]

def test_fortinet_vendor_detection():
    sample = """
    #build-version: FGT60E-6.4.8-build1914
    config system global
        set hostname "CORP-FG-01"
    end
    """
    res = VendorDetector.detect(sample)
    assert res["vendor"] == "fortinet"
    assert res["hostname"] == "CORP-FG-01"

def test_paloalto_vendor_detection():
    sample = """
    set deviceconfig system hostname PA-NGFW-01
    set deviceconfig system service disable-telnet yes
    """
    res = VendorDetector.detect(sample)
    assert res["vendor"] == "paloalto"
    assert res["hostname"] == "PA-NGFW-01"

def test_arista_vendor_detection():
    sample = """
    ! Command: show running-config
    ! device: DC-SPINE-01 (vEOS-lab, EOS-4.28.2F)
    hostname DC-SPINE-01
    """
    res = VendorDetector.detect(sample)
    assert res["vendor"] == "arista"
    assert res["hostname"] == "DC-SPINE-01"
