from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ConfigurationLineSchema(BaseModel):
    line_number: int
    raw_text: str
    section_context: Optional[str] = ""
    is_security_relevant: bool = False
    normalized_param: Optional[str] = None

class ConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_hash: str
    vendor_detected: str
    device_model_detected: str
    os_detected: str
    file_size: int
    lines_count: int
    uploaded_at: datetime
    sanitized_preview: Optional[str] = None

class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hostname: str
    vendor: str
    model: str
    os_version: str
    serial_number: str
    created_at: datetime
    last_compliance_score: Optional[float] = None
    last_risk_score: Optional[float] = None

class AuditFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_id: str
    framework: str
    control_id: str
    title: str
    status: str
    severity: str
    normalized_param: str
    detected_value: Optional[str] = None
    expected_value: Optional[str] = None
    evidence_line_no: Optional[int] = None
    evidence_text: Optional[str] = None
    section_context: Optional[str] = None
    rationale: Optional[str] = None
    remediation_text: Optional[str] = None
    verification_cmd: Optional[str] = None
    is_learned_mapping_applied: bool = False


class SecurityImpactResponse(BaseModel):
    finding: str
    why_it_matters: str
    potential_impacts: List[str] = Field(default_factory=list)
    potential_attack_categories: List[str] = Field(default_factory=list)
    affected_assets: List[str] = Field(default_factory=list)
    data_at_risk: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    recommended_action: str
    confidence: str
    evidence_basis: str
    analysis_provider: str = "deterministic"

class GlobalFindingResponse(AuditFindingResponse):
    audit_id: int
    device_hostname: Optional[str] = "UNKNOWN"
    device_vendor: Optional[str] = "UNKNOWN"
    filename: Optional[str] = "N/A"
    audit_timestamp: Optional[datetime] = None

class AuditRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: Optional[int]
    config_id: int
    timestamp: datetime
    compliance_percentage: float
    risk_score: float
    risk_level: str
    total_controls: int
    passed_count: int
    failed_count: int
    not_evaluable_count: int
    unknown_count: int
    status: str
    device_hostname: Optional[str] = None
    device_vendor: Optional[str] = None
    filename: Optional[str] = None
    normalized_baseline: Optional[Dict[str, Any]] = None
    findings: List[AuditFindingResponse] = Field(default_factory=list)

class ComplianceRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_id: str
    framework: str
    framework_version: str
    control_id: str
    title: str
    description: str
    parameter: str
    operator: str
    expected_value: str
    severity: str
    category: str
    rationale: Optional[str] = None

class UnknownCommandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    config_id: int
    raw_command: str
    line_number: int
    vendor: str
    ai_suggested_category: str
    ai_suggested_param: str
    ai_confidence: float
    status: str
    created_at: datetime

class MappingCreateRequest(BaseModel):
    vendor: str
    command_pattern: str
    normalized_param: str
    semantic_category: str = "General"
    value_type: str = "string"
    extraction_regex: Optional[str] = None
    description: Optional[str] = ""
    remediation_template: Optional[str] = None

class LearnedMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor: str
    command_pattern: str
    normalized_param: str
    semantic_category: str
    value_type: str
    extraction_regex: Optional[str] = None
    description: Optional[str] = None
    source: str
    confidence: float
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    use_count: int

class DashboardStatsResponse(BaseModel):
    total_devices: int
    total_audits: int
    average_compliance_pct: float
    critical_findings_count: int
    high_findings_count: int
    medium_findings_count: int
    low_findings_count: int
    framework_distribution: Dict[str, Dict[str, int]]
    vendor_distribution: Dict[str, int]
    unknown_commands_count: int
    recent_audits: List[AuditRunResponse]

class ValidationTraceStep(BaseModel):
    line_number: int
    raw_command: str
    vendor: str
    parsed_meaning: str
    normalized_parameter: str
    extracted_value: Any
    confidence: float
    is_learned: bool = False
    matching_rules: List[str] = Field(default_factory=list)


# ── Archive / Fleet Upload ─────────────────────────────────────────────────────

class ArchiveMemberResult(BaseModel):
    """Per-file result inside a bulk archive upload."""
    filename: str
    status: str                        # "processed" | "skipped" | "error"
    reason: Optional[str] = None       # skip/error reason when applicable
    config_id: Optional[int] = None    # DB id if successfully stored
    vendor_detected: Optional[str] = None
    lines_count: Optional[int] = None


class ArchiveUploadResponse(BaseModel):
    """Fleet-level summary returned by POST /configurations/upload-archive."""
    archive_filename: str
    total_members_in_archive: int
    successfully_processed: int
    skipped: int
    errors: int
    members: List[ArchiveMemberResult] = Field(default_factory=list)


# ── GitOps Webhook ────────────────────────────────────────────────────────────

class WebhookConfigFileResult(BaseModel):
    """Per-file ingestion result inside a webhook audit trigger."""
    filename: str
    raw_url: str
    status: str                       # "audited" | "ingested_only" | "skipped" | "error"
    reason: Optional[str] = None
    config_id: Optional[int] = None
    audit_id: Optional[int] = None
    vendor_detected: Optional[str] = None
    compliance_percentage: Optional[float] = None
    risk_level: Optional[str] = None


class WebhookAuditResponse(BaseModel):
    """Response returned by the GitHub/GitLab webhook endpoints."""
    platform: str                     # "github" | "gitlab"
    repository: str
    branch: str
    commit_sha: str
    pusher: str
    commit_message: str
    total_config_files_found: int
    audited: int
    skipped: int
    errors: int
    files: List[WebhookConfigFileResult] = Field(default_factory=list)


# ── SSH Device Puller ─────────────────────────────────────────────────────────

class SSHPullRequestSchema(BaseModel):
    """Request body for POST /api/ssh/pull."""
    hostname: str                          # IP or FQDN of target device
    port: int = 22
    username: str
    password: str = ""                     # Never stored, used in-memory only
    vendor_hint: str = ""                  # Optional: "cisco" | "juniper" | etc.
    use_key_auth: bool = False             # True → use SSH agent (no password)
    timeout: int = 15


class SSHConnectivityResponse(BaseModel):
    """Response for GET /api/ssh/probe."""
    hostname: str
    port: int
    reachable: bool
    message: str


class SSHPullResponse(BaseModel):
    """Response for POST /api/ssh/pull — audit summary after live pull."""
    host: str
    port: int
    success: bool
    error: Optional[str] = None
    config_id: Optional[int] = None
    audit_id: Optional[int] = None
    vendor_detected: Optional[str] = None
    compliance_percentage: Optional[float] = None
    risk_level: Optional[str] = None
    lines_pulled: Optional[int] = None
    elapsed_ms: int = 0
    commands_sent: List[str] = Field(default_factory=list)


