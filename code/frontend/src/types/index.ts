export interface Configuration {
  id: number;
  filename: string;
  file_hash: string;
  vendor_detected: string;
  device_model_detected: string;
  os_detected: string;
  file_size: number;
  lines_count: number;
  uploaded_at: string;
  sanitized_preview?: string;
}

export interface Device {
  id: number;
  hostname: string;
  vendor: string;
  model: string;
  os_version: string;
  serial_number: string;
  created_at: string;
  last_compliance_score?: number;
  last_risk_score?: number;
}

export interface AuditFinding {
  id: number;
  rule_id: string;
  framework: string;
  control_id: string;
  title: string;
  status: "PASS" | "FAIL" | "NOT_EVALUABLE" | "UNKNOWN";
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
  normalized_param: string;
  detected_value?: string;
  expected_value?: string;
  evidence_line_no?: number;
  evidence_text?: string;
  section_context?: string;
  rationale?: string;
  remediation_text?: string;
  verification_cmd?: string;
  is_learned_mapping_applied: boolean;
}


export interface SecurityImpactAnalysis {
  finding: string;
  why_it_matters: string;
  potential_impacts: string[];
  potential_attack_categories: string[];
  affected_assets: string[];
  data_at_risk: string[];
  prerequisites: string[];
  recommended_action: string;
  confidence: "high" | "medium" | "low" | string;
  evidence_basis: string;
  analysis_provider: "deterministic" | "gemini" | string;
}

export interface GlobalFinding extends AuditFinding {
  audit_id: number;
  device_hostname?: string;
  device_vendor?: string;
  filename?: string;
  audit_timestamp?: string;
}

export interface AuditRun {
  id: number;
  device_id?: number;
  config_id: number;
  timestamp: string;
  compliance_percentage: number;
  risk_score: number;
  risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  total_controls: number;
  passed_count: number;
  failed_count: number;
  not_evaluable_count: number;
  unknown_count: number;
  status: string;
  device_hostname?: string;
  device_vendor?: string;
  filename?: string;
  normalized_baseline?: Record<string, any>;
  findings: AuditFinding[];
}

export interface ComplianceRule {
  id: number;
  rule_id: string;
  framework: string;
  framework_version: string;
  control_id: string;
  title: string;
  description: string;
  parameter: string;
  operator: string;
  expected_value: string;
  severity: string;
  category: string;
  rationale?: string;
}

export interface UnknownCommand {
  id: number;
  config_id: number;
  raw_command: string;
  line_number: number;
  vendor: string;
  ai_suggested_category: string;
  ai_suggested_param: string;
  ai_confidence: number;
  status: "PENDING" | "MAPPED" | "IGNORED";
  created_at: string;
}

export interface LearnedMapping {
  id: number;
  vendor: string;
  command_pattern: string;
  normalized_param: string;
  semantic_category: string;
  value_type: string;
  extraction_regex?: string;
  description?: string;
  source: string;
  confidence: number;
  is_active: boolean;
  created_at: string;
  last_used_at?: string;
  use_count: number;
}

export interface DashboardStats {
  total_devices: number;
  total_audits: number;
  average_compliance_pct: number;
  critical_findings_count: number;
  high_findings_count: number;
  medium_findings_count: number;
  low_findings_count: number;
  framework_distribution: Record<string, { pass: number; fail: number; not_evaluable: number }>;
  vendor_distribution: Record<string, number>;
  unknown_commands_count: number;
  recent_audits: Array<{
    id: number;
    device_hostname: string;
    device_vendor: string;
    filename: string;
    timestamp: string;
    compliance_percentage: number;
    risk_score: number;
    risk_level: string;
    passed_count: number;
    failed_count: number;
    not_evaluable_count: number;
    total_controls: number;
    status: string;
  }>;
}

export interface ValidationTraceStep {
  line_number: number;
  raw_text: string;
  cleaned_text: string;
  section_context: string;
  is_security_relevant: boolean;
  normalized_param: string;
  extracted_value?: string;
  confidence: number;
  mapping_source: string;
  is_learned_mapping: boolean;
  matching_rules_count: number;
  matching_rules: Array<{
    rule_id: string;
    framework: string;
    expected_value: string;
    severity: string;
  }>;
}

// ── Archive / Fleet Upload ────────────────────────────────────────────────────

export interface ArchiveMemberResult {
  filename: string;
  status: "processed" | "skipped" | "error";
  reason?: string;
  config_id?: number;
  vendor_detected?: string;
  lines_count?: number;
}

export interface ArchiveUploadResponse {
  archive_filename: string;
  total_members_in_archive: number;
  successfully_processed: number;
  skipped: number;
  errors: number;
  members: ArchiveMemberResult[];
}

export interface SystemSettingsResponse {
  ai_provider: "deterministic" | "gemini";
  gemini_api_key_configured: boolean;
  gemini_api_key_masked: string;
  gemini_api_key_source: "settings" | "env" | "none";
}
