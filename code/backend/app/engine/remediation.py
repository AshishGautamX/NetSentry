import json
from pathlib import Path
from typing import Dict, Any, Optional
from backend.app.config import APP_DATA_DIR

class RemediationEngine:
    """
    Generates safe, vendor-specific CLI remediation instructions and verification commands.
    Never invents commands if the vendor syntax is uncertain.
    """

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        tpl_file = APP_DATA_DIR / "remediation_templates.json"
        if tpl_file.exists():
            with open(tpl_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_remediation(self, vendor: str, normalized_param: str) -> Dict[str, Any]:
        """
        Retrieves vendor-specific remediation commands and verification command.
        """
        vendor_lower = vendor.lower() if vendor else "unknown"

        # Determine matched vendor key
        matched_vendor = None
        for v_key in self.templates.keys():
            if v_key in vendor_lower:
                matched_vendor = v_key
                break

        if not matched_vendor:
            return {
                "cli_commands": [],
                "remediation_text": "Vendor-specific remediation could not be confidently generated. Manual review required.",
                "verification_cmd": None,
                "safety_notice": "Recommended remediation — validate in a controlled/staging environment before deployment."
            }

        vendor_tpls = self.templates.get(matched_vendor, {})
        param_tpl = vendor_tpls.get(normalized_param)

        if not param_tpl:
            return {
                "cli_commands": [],
                "remediation_text": f"Remediation template for parameter '{normalized_param}' not found for vendor '{vendor}'. Manual review required.",
                "verification_cmd": None,
                "safety_notice": "Recommended remediation — validate in a controlled/staging environment before deployment."
            }

        cli_cmds = param_tpl.get("cli_commands", [])
        return {
            "cli_commands": cli_cmds,
            "remediation_text": "\n".join(cli_cmds),
            "verification_cmd": param_tpl.get("verification_cmd"),
            "explanation": param_tpl.get("explanation", ""),
            "safety_notice": "Recommended remediation — validate in a controlled/staging environment before deployment."
        }
