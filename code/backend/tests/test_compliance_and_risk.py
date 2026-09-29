import pytest
from backend.app.engine.compliance import ComplianceEngine
from backend.app.engine.risk import RiskEngine

def test_compliant_evaluation():
    compliant_baseline = {
        "parameters": {
            "security.ssh.version": 2,
            "security.telnet.enabled": False,
            "security.http_server.enabled": False,
            "security.https_server.enabled": True,
            "security.password_policy.min_length": 14,
            "security.session_timeout": 300,
            "security.banner.login_banner_configured": True,
            "security.logging.syslog_enabled": True,
            "security.ntp.configured": True,
            "security.snmp.v3_only": True,
            "security.aaa.authentication_login": True,
            "security.ftp.disabled": True,
            "security.aux_port.disabled": True,
            "security.password_policy.encryption_service": True,
            "security.password_policy.login_lockout": True,
            "security.ip.source_routing_disabled": True,
            "security.ip.redirects_disabled": True,
            "security.ip.directed_broadcast_disabled": True,
            "security.ip.proxy_arp_disabled": True,
            "security.ip.urpf_enabled": True,
            "security.logging.timestamp_detail": True,
            "security.logging.buffered_level": True,
            "security.ntp.auth_enabled": True,
            "security.snmp.v3_encryption": True,
            "security.control_plane.copp_enabled": True,
            "security.routing.bgp_auth_enabled": True,
            "security.routing.bgp_max_prefix": True,
            "security.routing.ospf_auth_enabled": True,
            "security.aaa.accounting_enabled": True,
            "security.discovery.cdp_lldp_restricted": True,
            "security.snmp.acl_restricted": True,
            "security.ssh.rekey_limit": True
        },
        "evidence": {}
    }

    engine = ComplianceEngine()
    findings = engine.evaluate(compliant_baseline, "cisco")
    
    # Check that all rules pass
    fails = [f for f in findings if f["status"] == "FAIL"]
    assert len(fails) == 0

    scores = RiskEngine.calculate_scores(findings)
    assert scores["compliance_percentage"] == 100.0
    assert scores["risk_score"] == 0.0
    assert scores["risk_level"] == "LOW"

def test_non_compliant_evaluation():
    insecure_baseline = {
        "parameters": {
            "security.ssh.version": 1,          # FAIL (expected 2)
            "security.telnet.enabled": True,     # FAIL (expected False - CRITICAL)
            "security.http_server.enabled": True,# FAIL (expected False)
            "security.password_policy.min_length": 6, # FAIL (expected >= 14)
            "security.session_timeout": 3600     # FAIL (expected <= 600)
        },
        "evidence": {}
    }

    engine = ComplianceEngine()
    findings = engine.evaluate(insecure_baseline, "cisco")

    fails = [f for f in findings if f["status"] == "FAIL"]
    assert len(fails) > 0

    # Ensure critical telnet failure exists
    telnet_fails = [f for f in fails if f["normalized_param"] == "security.telnet.enabled"]
    assert len(telnet_fails) > 0
    assert any(f["severity"] == "CRITICAL" for f in telnet_fails)

    scores = RiskEngine.calculate_scores(findings)
    assert scores["compliance_percentage"] < 50.0
    assert scores["risk_level"] == "CRITICAL"
