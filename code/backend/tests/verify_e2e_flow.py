import os
import sys
from fastapi.testclient import TestClient
from backend.app.main import app

from backend.app.database import SessionLocal
from backend.app.models.models import UnknownCommand, LearnedMapping

def main():
    print("=== Starting E2E Pipeline Verification ===")
    # Clean up test-specific artifacts from previous runs for idempotency
    db = SessionLocal()
    db.query(UnknownCommand).filter(UnknownCommand.raw_command.like("%abc-session-timeout%")).delete()
    db.query(LearnedMapping).filter(LearnedMapping.command_pattern.like("%abc-session-timeout%")).delete()
    db.commit()
    db.close()

    client = TestClient(app)

    # 1. Health check
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    print("[PASS] API Health: OK")

    # 2. Upload Cisco Compliant Sample
    cisco_comp_path = os.path.join("sample_configs", "cisco_compliant.cfg")
    with open(cisco_comp_path, "rb") as f:
        files = [("files", ("cisco_compliant.cfg", f.read(), "text/plain"))]
    up_resp = client.post("/api/configurations/upload", files=files)
    assert up_resp.status_code == 200, f"Upload failed: {up_resp.text}"
    configs = up_resp.json()
    assert len(configs) == 1
    cisco_comp_id = configs[0]["id"]
    print(f"[PASS] Uploaded Cisco Compliant Config (ID: {cisco_comp_id}, Vendor: {configs[0]['vendor_detected']})")

    # 3. Run Audit on Cisco Compliant Config
    audit_resp = client.post(f"/api/audits/run/{cisco_comp_id}")
    assert audit_resp.status_code == 200, f"Audit failed: {audit_resp.text}"
    comp_audit = audit_resp.json()
    print(f"[PASS] Cisco Compliant Audit: Score = {comp_audit['compliance_percentage']}%, Risk = {comp_audit['risk_level']}")
    assert comp_audit["compliance_percentage"] >= 90.0, "Compliant config should have high compliance score"

    # 4. Upload Cisco Non-Compliant Sample
    cisco_insecure_path = os.path.join("sample_configs", "cisco_non_compliant.cfg")
    with open(cisco_insecure_path, "rb") as f:
        files = [("files", ("cisco_non_compliant.cfg", f.read(), "text/plain"))]
    up_resp2 = client.post("/api/configurations/upload", files=files)
    assert up_resp2.status_code == 200
    cisco_insecure_id = up_resp2.json()[0]["id"]

    # 5. Run Audit on Cisco Non-Compliant Config
    audit_resp2 = client.post(f"/api/audits/run/{cisco_insecure_id}")
    assert audit_resp2.status_code == 200
    insecure_audit = audit_resp2.json()
    print(f"[PASS] Cisco Insecure Audit: Score = {insecure_audit['compliance_percentage']}%, Risk = {insecure_audit['risk_level']}")
    assert insecure_audit["risk_level"] == "CRITICAL", "Insecure config should have CRITICAL risk level due to Telnet & weak auth"
    assert insecure_audit["failed_count"] > 0

    # 6. Upload Unfamiliar Device Sample
    unfam_path = os.path.join("sample_configs", "unfamiliar_custom.cfg")
    with open(unfam_path, "rb") as f:
        files = [("files", ("unfamiliar_custom.cfg", f.read(), "text/plain"))]
    up_resp3 = client.post("/api/configurations/upload", files=files)
    assert up_resp3.status_code == 200
    unfam_id = up_resp3.json()[0]["id"]

    # First Audit of Unfamiliar Config
    audit_unfam_1 = client.post(f"/api/audits/run/{unfam_id}").json()
    print(f"[PASS] First Audit of Unfamiliar Config: Score = {audit_unfam_1['compliance_percentage']}%")

    # Verify Unknown Command was flagged in Training Queue
    unk_resp = client.get("/api/training/unknown")
    assert unk_resp.status_code == 200
    unknowns = unk_resp.json()
    target_unknown = next((u for u in unknowns if "abc-session-timeout" in u["raw_command"]), None)
    assert target_unknown is not None, "Unknown session timeout command was not flagged!"
    print(f"[PASS] Unknown Command detected in Training Queue: '{target_unknown['raw_command']}' (Line {target_unknown['line_number']})")

    # 7. Administrator Trains and Maps the Command
    map_payload = {
        "vendor": target_unknown["vendor"],
        "command_pattern": r"set security abc-session-timeout\s+(?P<seconds>\d+)",
        "normalized_param": "security.session_timeout",
        "semantic_category": "Session Management",
        "value_type": "int",
        "description": "Administrator learned mapping for custom edge gateway session timeout",
        "unknown_id": target_unknown["id"]
    }
    map_resp = client.post(f"/api/training/mapping?unknown_id={target_unknown['id']}", json=map_payload)
    assert map_resp.status_code == 200
    print("[PASS] Administrator Mapping Saved to Knowledge Base")

    # 8. Re-Run Audit on Unfamiliar Config
    audit_unfam_2 = client.post(f"/api/audits/run/{unfam_id}").json()
    findings = audit_unfam_2["findings"]
    session_finding = next((f for f in findings if f["normalized_param"] == "security.session_timeout"), None)
    assert session_finding is not None
    assert session_finding["status"] == "PASS", f"Session timeout should now pass! Detected: {session_finding['detected_value']}"
    assert session_finding["is_learned_mapping_applied"] is True, "Learned mapping flag should be True!"
    print(f"[PASS] Re-Audit Successful! Command recognized via Learned Knowledge Base (is_learned_mapping_applied = True, status = PASS)")

    # 9. Test PDF Report Generation
    pdf_resp = client.get(f"/api/reports/{comp_audit['id']}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF"), "Generated file is not a valid PDF"
    print(f"[PASS] PDF Audit Report Download: OK ({len(pdf_resp.content)} bytes generated)")

    # 10. Test Validation Trace
    trace_resp = client.get(f"/api/validation/trace/{cisco_comp_id}")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()
    assert trace["total_lines_analyzed"] > 0
    print(f"[PASS] Validation Trace: OK ({trace['total_lines_analyzed']} lines analyzed)")

    # 11. Test Dashboard Stats
    dash_resp = client.get("/api/dashboard/stats")
    assert dash_resp.status_code == 200
    dash = dash_resp.json()
    assert dash["total_audits"] >= 4
    print(f"[PASS] Dashboard Stats: Total Audits = {dash['total_audits']}, Devices = {dash['total_devices']}")

    print("\n=======================================================")
    print("ALL 11 END-TO-END WORKFLOW TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    main()
