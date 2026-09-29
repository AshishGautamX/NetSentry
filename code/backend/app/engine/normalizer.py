import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from backend.app.config import APP_DATA_DIR
from backend.app.engine.parsers.base import ParsedLine

class NormalizationEngine:
    """
    Normalizes vendor-specific configuration syntax into a canonical,
    vendor-neutral security baseline model.
    Evaluates both built-in mappings and administrator-trained learned mappings.
    Optimized with pre-compiled regex dispatch and vendor indexing for carrier-grade throughput.
    """

    _SECURITY_TERMS_RE = re.compile(
        r'(?:timeout|session|pwd|password|crypto|cipher|banner|audit|auth|restrict|sec-|security|v3-only|radius|tacacs|lockout|min-length|admintimeout|bgp|ospf|snmp|logging|ntp|access-list|firewall)',
        re.IGNORECASE
    )
    _EXCLUDE_TERMS_RE = re.compile(
        r'(?:description\s+|interface\s+ethernet|vlan\s+|ip\s+address\s+)',
        re.IGNORECASE
    )

    def __init__(self):
        self.initial_mappings = self._load_initial_mappings()
        self._compiled_cache: Dict[str, re.Pattern] = {}
        self._vendor_indexed_mappings: Dict[str, List[Dict[str, Any]]] = {}
        self._precompile_and_index_mappings()

    def _load_initial_mappings(self) -> List[Dict[str, Any]]:
        mappings_file = APP_DATA_DIR / "initial_mappings.json"
        if mappings_file.exists():
            with open(mappings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _precompile_and_index_mappings(self):
        for m in self.initial_mappings:
            pattern_str = m["command_pattern"]
            try:
                m["_compiled"] = re.compile(pattern_str, re.IGNORECASE)
            except re.error:
                m["_compiled"] = None

    def _get_applicable_mappings(self, vendor_lower: str) -> List[Dict[str, Any]]:
        if vendor_lower in self._vendor_indexed_mappings:
            return self._vendor_indexed_mappings[vendor_lower]

        applicable = []
        for m in self.initial_mappings:
            m_vendor = m["vendor"].lower()
            if m_vendor == "all" or m_vendor in vendor_lower or vendor_lower in m_vendor:
                applicable.append(m)
        
        self._vendor_indexed_mappings[vendor_lower] = applicable
        return applicable

    def _get_compiled_pattern(self, pattern_str: str) -> Optional[re.Pattern]:
        if pattern_str in self._compiled_cache:
            return self._compiled_cache[pattern_str]
        try:
            compiled = re.compile(pattern_str, re.IGNORECASE)
            self._compiled_cache[pattern_str] = compiled
            return compiled
        except re.error:
            return None

    def normalize(
        self,
        parsed_lines: List[ParsedLine],
        vendor: str,
        learned_mappings: Optional[List[Any]] = None
    ) -> Tuple[List[ParsedLine], Dict[str, Any], List[Dict[str, Any]]]:
        """
        Processes parsed lines against learned mappings and built-in rules.
        Returns:
            - modified parsed_lines
            - canonical_baseline dictionary
            - list of unmapped candidate commands for training
        """
        canonical_params: Dict[str, Any] = {}
        evidence_map: Dict[str, ParsedLine] = {}
        unknown_candidates: List[Dict[str, Any]] = []

        active_learned = learned_mappings or []
        vendor_lower = vendor.lower() if vendor else "unknown"
        applicable_builtin = self._get_applicable_mappings(vendor_lower)

        # Pre-filter learned mappings for vendor
        applicable_learned = []
        for lm in active_learned:
            lm_vendor = lm.vendor.lower()
            if lm_vendor == "all" or lm_vendor == "generic" or lm_vendor in vendor_lower or vendor_lower in lm_vendor:
                compiled_pat = self._get_compiled_pattern(lm.command_pattern)
                if compiled_pat:
                    applicable_learned.append((lm, compiled_pat))

        for line in parsed_lines:
            if line.is_blank or line.is_comment:
                continue

            cmd = line.cleaned_text
            matched = False

            # 1. Check persistent learned mappings first
            for lm, pat in applicable_learned:
                match = pat.search(cmd)
                if match:
                    matched = True
                    val = self._extract_value(cmd, match, lm.value_type, lm.extraction_regex)
                    line.normalized_param = lm.normalized_param
                    line.extracted_value = val
                    line.confidence = float(lm.confidence)
                    line.is_security_relevant = True
                    line.mapping_source = "LEARNED_KNOWLEDGE_BASE"
                    
                    canonical_params[lm.normalized_param] = val
                    evidence_map[lm.normalized_param] = line
                    break

            if matched:
                continue

            # 2. Check built-in seeded mappings
            for mapping in applicable_builtin:
                pat = mapping.get("_compiled")
                if pat is None:
                    continue

                match = pat.search(cmd)
                if match:
                    matched = True
                    val = self._extract_value(cmd, match, mapping.get("value_type", "string"), None)
                    param_name = mapping["normalized_param"]
                    
                    line.normalized_param = param_name
                    line.extracted_value = val
                    line.confidence = 0.98
                    line.is_security_relevant = True
                    line.mapping_source = "BUILTIN_MAPPING"

                    # Handle special precedence
                    if param_name == "security.telnet.enabled":
                        if param_name in canonical_params and canonical_params[param_name] is True and val is False:
                            pass
                        else:
                            canonical_params[param_name] = val
                            evidence_map[param_name] = line
                    elif param_name == "security.session_timeout":
                        if param_name in canonical_params:
                            try:
                                canonical_params[param_name] = min(int(canonical_params[param_name]), int(val))
                                evidence_map[param_name] = line
                            except (ValueError, TypeError):
                                canonical_params[param_name] = val
                        else:
                            canonical_params[param_name] = val
                            evidence_map[param_name] = line
                    else:
                        canonical_params[param_name] = val
                        evidence_map[param_name] = line
                    break

            if matched:
                continue

            # 3. Detect potentially security-relevant unknown commands
            if self._is_potential_security_command(cmd):
                unknown_candidates.append({
                    "raw_command": cmd,
                    "line_number": line.line_number,
                    "vendor": vendor,
                    "section_context": line.section_context
                })

        canonical_baseline = self._build_canonical_model(canonical_params, evidence_map)
        return parsed_lines, canonical_baseline, unknown_candidates

    def _extract_value(self, cmd: str, match: re.Match, value_type: str, custom_regex: Optional[str]) -> Any:
        if custom_regex:
            try:
                c_match = re.search(custom_regex, cmd)
                if c_match:
                    groups = c_match.groupdict()
                    if "value" in groups:
                        return self._cast_val(groups["value"], value_type)
                    return self._cast_val(c_match.group(1), value_type)
            except Exception:
                pass

        groups = match.groupdict() if match else {}

        if value_type == "int":
            for k in ["version", "v2", "length", "seconds", "val"]:
                if k in groups and groups[k] is not None:
                    return int(groups[k])
            num = re.search(r'\b(\d+)\b', cmd)
            return int(num.group(1)) if num else 0

        elif value_type == "boolean_true":
            return True

        elif value_type == "boolean_false":
            return False

        elif value_type == "eval_inverted_no":
            # "no ip http server" -> False (disabled)
            # "ip http server" -> True (enabled)
            return not cmd.strip().lower().startswith("no ")

        elif value_type == "eval_inverted_yes":
            # "disable-telnet yes" -> False (telnet not enabled)
            # "disable-telnet no" -> True (telnet is enabled)
            state = groups.get("state", "").lower()
            return state != "yes"

        elif value_type == "eval_telnet_cisco":
            # "transport input telnet" or "transport input all" -> telnet enabled
            # "transport input ssh" or "transport input none" -> telnet disabled
            proto = groups.get("proto", "").lower()
            return ("telnet" in proto) or ("all" in proto)

        elif value_type == "eval_exec_timeout_cisco":
            minutes = int(groups.get("min", 0) or 0)
            seconds = int(groups.get("sec", 0) or 0)
            total = minutes * 60 + seconds
            return total if total > 0 else 999999  # 0 0 means never timeout in Cisco

        elif value_type == "eval_minutes_to_seconds":
            minutes = int(groups.get("minutes", 0) or 0)
            return minutes * 60

        elif value_type == "eval_fortinet_ssh":
            # admin-ssh-v1 disable -> SSHv2 only (version=2)
            state = groups.get("state", "").lower()
            return 2 if state == "disable" else 1

        elif value_type == "eval_paloalto_ssh":
            state = groups.get("state", "").lower()
            return 2 if state == "yes" else 1

        # Default string extraction
        if groups:
            return next(iter(groups.values()))
        return cmd

    def _cast_val(self, val_str: str, value_type: str) -> Any:
        if value_type == "int":
            try:
                return int(val_str)
            except ValueError:
                return 0
        elif value_type == "boolean_true":
            return True
        elif value_type == "boolean_false":
            return False
        return val_str

    def _is_potential_security_command(self, cmd: str) -> bool:
        if self._EXCLUDE_TERMS_RE.search(cmd):
            return False
        return bool(self._SECURITY_TERMS_RE.search(cmd))

    def _build_canonical_model(self, flat_params: Dict[str, Any], evidence_map: Dict[str, ParsedLine]) -> Dict[str, Any]:
        """
        Builds the universal security baseline model with parameter values and evidence lines.
        """
        return {
            "parameters": flat_params,
            "evidence": {
                k: {
                    "line_number": v.line_number,
                    "raw_text": v.raw_text,
                    "section_context": v.section_context,
                    "confidence": v.confidence,
                    "mapping_source": v.mapping_source
                }
                for k, v in evidence_map.items()
            }
        }
