import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from backend.app.config import APP_DATA_DIR

class ComplianceEngine:
    """
    Deterministic compliance rule evaluation engine.
    Evaluates canonical parameters against CIS Benchmarks, NIST SP 800-53,
    DISA STIG, and ISO/IEC 27001 rules without simulating or fabricating results.
    """

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        rules: List[Dict[str, Any]] = []
        rules_dir = APP_DATA_DIR / "rules"
        if rules_dir.exists():
            for rule_file in rules_dir.glob("*.json"):
                try:
                    with open(rule_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            rules.extend(data)
                except Exception as e:
                    print(f"Error loading rule file {rule_file}: {e}")
        return rules

    def evaluate(self, baseline_model: Dict[str, Any], vendor: str) -> List[Dict[str, Any]]:
        """
        Evaluates the normalized configuration parameters against all loaded compliance rules.
        Returns a list of finding dictionaries.
        """
        params = baseline_model.get("parameters", {})
        evidence_dict = baseline_model.get("evidence", {})
        findings: List[Dict[str, Any]] = []

        for rule in self.rules:
            rule_id = rule["rule_id"]
            param_key = rule["parameter"]
            operator = rule["operator"].lower()
            expected = rule["expected_value"]
            framework = rule["framework"]
            control_id = rule["control_id"]
            title = rule["title"]
            severity = rule["severity"]
            category = rule.get("category", "General")
            rationale = rule.get("rationale", "")

            # Check if parameter was extracted in configuration
            if param_key not in params:
                findings.append({
                    "rule_id": rule_id,
                    "framework": framework,
                    "control_id": control_id,
                    "title": title,
                    "status": "NOT_EVALUABLE",
                    "severity": severity,
                    "normalized_param": param_key,
                    "detected_value": "NOT_CONFIGURED",
                    "expected_value": str(expected),
                    "evidence_line_no": None,
                    "evidence_text": f"Configuration parameter '{param_key}' is not explicitly defined in the provided configuration.",
                    "section_context": "Global",
                    "rationale": rationale,
                    "is_learned_mapping_applied": False
                })
                continue

            detected_val = params[param_key]
            ev_info = evidence_dict.get(param_key, {})
            ev_line = ev_info.get("line_number")
            ev_text = ev_info.get("raw_text")
            ev_section = ev_info.get("section_context", "")
            is_learned = ev_info.get("mapping_source") == "LEARNED_KNOWLEDGE_BASE"

            # Deterministic operator evaluation
            passed = self._eval_condition(detected_val, operator, expected)
            status = "PASS" if passed else "FAIL"

            findings.append({
                "rule_id": rule_id,
                "framework": framework,
                "control_id": control_id,
                "title": title,
                "status": status,
                "severity": severity,
                "normalized_param": param_key,
                "detected_value": str(detected_val),
                "expected_value": str(expected),
                "evidence_line_no": ev_line,
                "evidence_text": ev_text,
                "section_context": ev_section,
                "rationale": rationale,
                "is_learned_mapping_applied": is_learned
            })

        return findings

    def _eval_condition(self, detected: Any, operator: str, expected: Any) -> bool:
        if operator == "equals":
            # Cast type if boolean string or int
            if isinstance(expected, bool):
                return bool(detected) is expected
            if isinstance(expected, int):
                try:
                    return int(detected) == expected
                except (ValueError, TypeError):
                    return False
            return str(detected).strip().lower() == str(expected).strip().lower()

        elif operator == "not_equals":
            if isinstance(expected, bool):
                return bool(detected) is not expected
            return str(detected).strip().lower() != str(expected).strip().lower()

        elif operator == "greater_or_equal":
            try:
                return float(detected) >= float(expected)
            except (ValueError, TypeError):
                return False

        elif operator == "less_or_equal":
            try:
                return float(detected) <= float(expected)
            except (ValueError, TypeError):
                return False

        elif operator == "contains":
            return str(expected).lower() in str(detected).lower()

        elif operator == "not_contains":
            return str(expected).lower() not in str(detected).lower()

        elif operator == "enabled":
            return bool(detected) is True

        elif operator == "disabled":
            return bool(detected) is False

        elif operator == "exists":
            return detected is not None

        return False
