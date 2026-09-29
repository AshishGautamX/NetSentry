import json
import httpx
from typing import Dict, Any, Optional
from backend.app.engine.ai.base import BaseAIProvider
from backend.app.engine.ai.deterministic import DeterministicAIProvider
from backend.app.services.settings_service import resolve_gemini_api_key

class GeminiAIProvider(BaseAIProvider):
    """
    LLM-powered semantic interpretation provider using Google Gemini API.
    Falls back gracefully to DeterministicAIProvider if the key is unset or unreachable.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.fallback = DeterministicAIProvider()

    async def analyze_security_impact(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Generate evidence-bound security impact analysis with deterministic fallback."""
        api_key = self.api_key or resolve_gemini_api_key()
        if not api_key:
            return await self.fallback.analyze_security_impact(finding)

        safe_finding = {
            "rule_id": finding.get("rule_id"),
            "title": finding.get("title"),
            "severity": finding.get("severity"),
            "normalized_param": finding.get("normalized_param"),
            "detected_value": finding.get("detected_value"),
            "expected_value": finding.get("expected_value"),
            "evidence_text": (finding.get("evidence_text") or "")[:1200],
            "section_context": (finding.get("section_context") or "")[:300],
            "rationale": finding.get("rationale"),
            "vendor": finding.get("vendor"),
            "hostname": finding.get("hostname"),
            "remediation_text": (finding.get("remediation_text") or "")[:800],
        }
        prompt = f"""You are a defensive network-security impact analyst. Analyze ONLY the failed compliance finding below.
Do not claim that an attack will happen. Do not invent vulnerabilities, exposed databases, credentials, services, or attack paths that are not supported by the finding.
Use conditional language such as 'may', 'could', or 'if' when prerequisites are required.
Return valid JSON only. Keep attack categories high-level and defensive; do not provide exploit steps, payloads, commands, or instructions for compromising a system.

Finding evidence:
{json.dumps(safe_finding, ensure_ascii=False)}

Required JSON shape:
{{
  "finding": "string",
  "why_it_matters": "string",
  "potential_impacts": ["string"],
  "potential_attack_categories": ["string"],
  "affected_assets": ["string"],
  "data_at_risk": ["string"],
  "prerequisites": ["string"],
  "recommended_action": "string",
  "confidence": "high|medium|low",
  "evidence_basis": "string"
}}
"""
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    candidate = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(candidate)
                    fallback = await self.fallback.analyze_security_impact(finding)
                    return {
                        **fallback,
                        **{k: parsed[k] for k in fallback.keys() if k in parsed and parsed[k] not in (None, "")},
                    }
        except Exception:
            pass
        return await self.fallback.analyze_security_impact(finding)

    async def interpret_command(self, vendor: str, command: str, context: str = "") -> Dict[str, Any]:
        api_key = self.api_key or resolve_gemini_api_key()
        if not api_key:
            return await self.fallback.interpret_command(vendor, command, context)

        prompt = f"""
You are a senior network security auditor. Analyze this unfamiliar network device configuration command:
Vendor/Platform: {vendor}
Context: {context}
Command: {command}

Respond with valid JSON only in this exact format:
{{
    "suggested_parameter": "security.<category>.<param_name>",
    "suggested_category": "Session Management | Authentication | Remote Access | Web Management | Auditing & Logging | Time Synchronization | Network Management | Cryptography",
    "confidence": 0.85,
    "suggested_value": 300,
    "explanation": "Clear concise explanation of what this command controls"
}}
"""
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    candidate = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(candidate)
                    return {
                        "suggested_parameter": parsed.get("suggested_parameter", "security.custom.param"),
                        "suggested_category": parsed.get("suggested_category", "General"),
                        "confidence": float(parsed.get("confidence", 0.80)),
                        "suggested_value": parsed.get("suggested_value"),
                        "explanation": parsed.get("explanation", "Interpreted via Gemini LLM.")
                    }
                else:
                    return await self.fallback.interpret_command(vendor, command, context)
        except Exception:
            return await self.fallback.interpret_command(vendor, command, context)
