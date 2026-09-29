import re
from typing import Dict, Any
from backend.app.engine.ai.base import BaseAIProvider

class DeterministicAIProvider(BaseAIProvider):
    """
    Offline deterministic semantic interpretation engine.
    Uses structural heuristics, security lexicons, and token association.
    Guarantees reliable operation when no external AI API is available.
    """


    async def analyze_security_impact(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evidence-bound offline impact analysis. This intentionally describes
        plausible consequences and prerequisites rather than claiming exploitation.
        """
        title = (finding.get("title") or "").lower()
        param = (finding.get("normalized_param") or "").lower()
        evidence = finding.get("evidence_text") or ""
        vendor = finding.get("vendor") or "UNKNOWN"
        hostname = finding.get("hostname") or "UNKNOWN"

        result = {
            "finding": finding.get("title") or finding.get("rule_id") or "Failed control",
            "why_it_matters": finding.get("rationale") or "The observed configuration does not meet the selected security control.",
            "potential_impacts": ["Security control weakness", "Increased attack surface"],
            "potential_attack_categories": ["Unauthorized access attempts"],
            "affected_assets": [hostname, f"{vendor} network device"],
            "data_at_risk": ["Device configuration and management-plane information"],
            "prerequisites": ["An attacker must have a reachable attack path to the affected service or management plane."],
            "recommended_action": finding.get("remediation_text") or "Apply the documented remediation and verify the control after the change.",
            "confidence": "medium",
            "evidence_basis": evidence[:500] if evidence else "No explicit configuration evidence was recorded.",
        }

        if any(x in param or x in title for x in ["telnet", "insecure_remote", "remote_access"]):
            result.update(
                why_it_matters="Unencrypted or weakly protected remote management can expose administrative sessions to interception when traffic is observable.",
                potential_impacts=["Credential exposure", "Session exposure", "Unauthorized administrative access", "Increased lateral-movement risk"],
                potential_attack_categories=["Credential interception", "Credential reuse", "Man-in-the-Middle", "Unauthorized access"],
                data_at_risk=["Administrative credentials", "Management-session data", "Device configuration"],
                prerequisites=["Attacker can observe or influence management traffic", "Management traffic traverses a network path accessible to the attacker"],
            )
        elif "ssh" in param or "ssh" in title:
            result.update(
                why_it_matters="The management protocol configuration does not explicitly establish the required secure SSH version, which may permit weaker or unintended protocol handling depending on device/software behavior.",
                potential_impacts=["Management-session exposure", "Credential exposure", "Unauthorized administrative access"],
                potential_attack_categories=["Protocol downgrade", "Credential interception", "Unauthorized access"],
                data_at_risk=["Administrative credentials", "Management-session metadata", "Device configuration"],
                prerequisites=["The device/software accepts an unintended or weaker protocol mode", "Attacker can reach the management service"],
            )
        elif any(x in param or x in title for x in ["password", "authentication", "account"]):
            result.update(
                why_it_matters="A weak authentication policy can make account credentials easier to guess or compromise.",
                potential_impacts=["Credential compromise", "Unauthorized login", "Account takeover", "Device compromise"],
                potential_attack_categories=["Password guessing", "Brute-force attempts", "Credential stuffing"],
                data_at_risk=["Administrative account access", "Device configuration", "Accessible network-management data"],
                prerequisites=["A remotely or locally reachable authentication interface exists", "Attacker has an account target or valid username information"],
            )
        elif "snmp" in param or "snmp" in title:
            result.update(
                why_it_matters="Weak SNMP configuration can expose management and topology information; write access, if also exposed, can increase the potential impact.",
                potential_impacts=["Information disclosure", "Network reconnaissance", "Attack-surface mapping", "Potential configuration manipulation if write access is exposed"],
                potential_attack_categories=["Network reconnaissance", "Information disclosure", "Credential/community-string guessing"],
                data_at_risk=["Interface information", "Routing and topology information", "Device/system details"],
                prerequisites=["SNMP is reachable from an attacker-controlled network path", "The exposed community or credentials are discoverable or known"],
            )
        elif any(x in param or x in title for x in ["http", "web_management"]):
            result.update(
                why_it_matters="Unencrypted web management can expose authentication or session data to network interception.",
                potential_impacts=["Credential exposure", "Session exposure", "Unauthorized administrative access"],
                potential_attack_categories=["Man-in-the-Middle", "Credential interception", "Session interception"],
                data_at_risk=["Administrative credentials", "Session cookies/tokens", "Device configuration"],
                prerequisites=["HTTP management is reachable", "Attacker can observe or influence the traffic path"],
            )
        elif any(x in param or x in title for x in ["logging", "syslog", "audit"]):
            result.update(
                why_it_matters="Missing centralized logging reduces the ability to detect, correlate and investigate security events.",
                potential_impacts=["Reduced security visibility", "Delayed detection", "Delayed incident response", "Longer potential attacker dwell time"],
                potential_attack_categories=["Detection evasion", "Persistence without timely detection"],
                data_at_risk=["Security telemetry and audit evidence"],
                prerequisites=["A security incident occurs that would otherwise have been detected or investigated through centralized logs"],
            )

        return result

    async def interpret_command(self, vendor: str, command: str, context: str = "") -> Dict[str, Any]:
        cmd_lower = command.lower()

        # Session timeout heuristics
        if any(token in cmd_lower for token in ["session-timeout", "idle-timeout", "admintimeout", "exec-timeout", "timeout"]):
            num_match = re.search(r'\b(\d+)\b', command)
            val_hint = num_match.group(1) if num_match else "unknown"
            return {
                "suggested_parameter": "security.session_timeout",
                "suggested_category": "Session Management",
                "confidence": 0.78,
                "suggested_value": int(val_hint) if val_hint.isdigit() else None,
                "explanation": f"Pattern suggests administrative or shell session inactivity termination duration ({val_hint})."
            }

        # Password length / complexity heuristics
        if any(token in cmd_lower for token in ["min-length", "pwd-len", "password-length", "pwd_len", "complexity"]):
            num_match = re.search(r'\b(\d+)\b', command)
            val_hint = num_match.group(1) if num_match else "unknown"
            return {
                "suggested_parameter": "security.password_policy.min_length",
                "suggested_category": "Authentication",
                "confidence": 0.82,
                "suggested_value": int(val_hint) if val_hint.isdigit() else None,
                "explanation": f"Syntax resembles authenticator minimum length specification ({val_hint} chars)."
            }

        # Crypto / Ciphers heuristics
        if any(token in cmd_lower for token in ["crypto", "cipher", "encryption", "sha384", "aes", "algorithm"]):
            return {
                "suggested_parameter": "security.crypto.algorithm_strength",
                "suggested_category": "Cryptography",
                "confidence": 0.72,
                "suggested_value": command.split()[-1],
                "explanation": "Directive specifies cryptographic cipher suites, algorithms, or integrity hashing."
            }

        # Banner heuristics
        if any(token in cmd_lower for token in ["banner", "login-banner", "motd", "greeting", "legal-notice"]):
            return {
                "suggested_parameter": "security.banner.login_banner_configured",
                "suggested_category": "Access Warning",
                "confidence": 0.85,
                "suggested_value": True,
                "explanation": "Command provisions a user access agreement or pre-authentication legal warning banner."
            }

        # Logging / Audit heuristics
        if any(token in cmd_lower for token in ["audit", "syslog", "logging", "event-log", "log-server"]):
            return {
                "suggested_parameter": "security.logging.syslog_enabled",
                "suggested_category": "Auditing & Logging",
                "confidence": 0.75,
                "suggested_value": True,
                "explanation": "Directs security audit trails or operational event logging."
            }

        # SSH / Remote Access heuristics
        if any(token in cmd_lower for token in ["ssh", "v2-only", "protocol-version"]):
            return {
                "suggested_parameter": "security.ssh.version",
                "suggested_category": "Remote Access",
                "confidence": 0.79,
                "suggested_value": 2,
                "explanation": "Configures secure remote access protocol version parameters."
            }

        # SNMP heuristics
        if "snmp" in cmd_lower:
            return {
                "suggested_parameter": "security.snmp.v3_only",
                "suggested_category": "Network Management",
                "confidence": 0.70,
                "suggested_value": True if "v3" in cmd_lower else False,
                "explanation": "Network management protocol security parameter."
            }

        # Default fallback for unknown security parameters
        return {
            "suggested_parameter": "security.custom.unclassified",
            "suggested_category": "Unclassified Security Directive",
            "confidence": 0.45,
            "suggested_value": None,
            "explanation": "Syntax contains potential security semantics but requires administrator classification."
        }
