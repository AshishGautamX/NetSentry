import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.engine.reporting import PDFReportGenerator

def test_pdf_report_generator():
    device_info = {
        "hostname": "TEST-RTR-01",
        "vendor": "cisco",
        "model": "Catalyst 9300",
        "os_version": "IOS-XE 17.6"
    }
    audit_info = {
        "filename": "cisco_test.cfg",
        "compliance_percentage": 88.5,
        "risk_score": 12.0,
        "risk_level": "LOW",
        "total_controls": 10,
        "passed_count": 8,
        "failed_count": 1,
        "not_evaluable_count": 1
    }
    findings = [
        {
            "rule_id": "CIS-NET-1.1",
            "framework": "CIS",
            "control_id": "1.1",
            "title": "Ensure SSH Protocol Version 2 is Configured",
            "status": "PASS",
            "severity": "HIGH",
            "normalized_param": "security.ssh.version",
            "detected_value": "2",
            "expected_value": "2",
            "evidence_line_no": 42,
            "evidence_text": "ip ssh version 2",
            "remediation_text": "no remediation needed"
        }
    ]

    buffer = io.BytesIO()
    PDFReportGenerator.generate_report(device_info, audit_info, findings, buffer)
    pdf_bytes = buffer.getvalue()

    # Valid PDF signature
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

def test_api_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_api_rules_and_frameworks():
    client = TestClient(app)
    resp = client.get("/api/compliance/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) > 0

    resp_fw = client.get("/api/compliance/frameworks")
    assert resp_fw.status_code == 200
    fws = resp_fw.json()
    fw_names = [f["name"] for f in fws]
    assert "CIS" in fw_names
    assert "NIST SP 800-53" in fw_names
