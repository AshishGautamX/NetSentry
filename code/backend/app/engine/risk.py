from typing import List, Dict, Any, Tuple
from backend.app.config import settings

class RiskEngine:
    """
    Computes device compliance percentage and quantitative risk score
    based on finding severities and status outcomes.
    """

    @classmethod
    def calculate_scores(cls, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_controls = len(findings)
        if total_controls == 0:
            return {
                "compliance_percentage": 100.0,
                "risk_score": 0.0,
                "risk_level": "LOW",
                "passed_count": 0,
                "failed_count": 0,
                "not_evaluable_count": 0,
                "unknown_count": 0
            }

        passed = sum(1 for f in findings if f["status"] == "PASS")
        failed = sum(1 for f in findings if f["status"] == "FAIL")
        not_evaluable = sum(1 for f in findings if f["status"] == "NOT_EVALUABLE")
        unknown = sum(1 for f in findings if f["status"] == "UNKNOWN")

        # Compliance percentage is strictly: passed / (passed + failed + not_evaluable) * 100
        # This penalizes unconfigured/not evaluable security requirements
        evaluable_total = passed + failed + not_evaluable
        compliance_pct = round((passed / evaluable_total * 100.0), 1) if evaluable_total > 0 else 0.0

        # Quantitative risk score calculation
        severity_weights = {
            "CRITICAL": settings.RISK_WEIGHT_CRITICAL,
            "HIGH": settings.RISK_WEIGHT_HIGH,
            "MEDIUM": settings.RISK_WEIGHT_MEDIUM,
            "LOW": settings.RISK_WEIGHT_LOW,
            "INFO": settings.RISK_WEIGHT_INFO
        }

        # Sum of failed & not-evaluable finding risk points
        total_risk_points = 0.0
        max_possible_risk = 0.0

        for f in findings:
            w = severity_weights.get(f["severity"].upper(), 1.0)
            max_possible_risk += w
            if f["status"] == "FAIL":
                total_risk_points += w
            elif f["status"] == "NOT_EVALUABLE":
                total_risk_points += (w * 0.5)  # half penalty for unconfigured

        # Normalized risk score on 0 - 100 scale
        risk_score = round((total_risk_points / max_possible_risk * 100.0), 1) if max_possible_risk > 0 else 0.0

        # Qualitative Risk Level
        if any(f["status"] == "FAIL" and f["severity"].upper() == "CRITICAL" for f in findings) or risk_score >= 50:
            risk_level = "CRITICAL"
        elif any(f["status"] == "FAIL" and f["severity"].upper() == "HIGH" for f in findings) or risk_score >= 30:
            risk_level = "HIGH"
        elif risk_score >= 15:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "compliance_percentage": compliance_pct,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "passed_count": passed,
            "failed_count": failed,
            "not_evaluable_count": not_evaluable,
            "unknown_count": unknown
        }
