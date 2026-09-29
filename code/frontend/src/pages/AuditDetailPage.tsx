import React, { useEffect, useState } from "react";
import {
  ArrowLeft,
  Download,
  Terminal,
  Copy,
  Check,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Search,
  AlertTriangle,
  Sparkles,
} from "lucide-react";
import { apiClient } from "../api/client";
import { AuditRun } from "../types";
import { SeverityBadge } from "../components/common/SeverityBadge";
import { LoadingSkeleton } from "../components/common/LoadingSkeleton";
import { EmptyState } from "../components/common/EmptyState";
import { SecurityImpactAnalysis } from "../components/common/SecurityImpactAnalysis";

interface AuditDetailProps {
  auditId: number;
  onBack: () => void;
  onNavigateTrace?: (configId: number) => void;
}

export const AuditDetailPage: React.FC<AuditDetailProps> = ({
  auditId,
  onBack,
  onNavigateTrace,
}) => {
  const [audit, setAudit] = useState<AuditRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFramework, setSelectedFramework] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [copiedFindingId, setCopiedFindingId] = useState<number | null>(null);

  useEffect(() => {
    fetchAudit();
  }, [auditId]);

  const fetchAudit = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getAudit(auditId);
      setAudit(data);
    } catch (err) {
      console.error("Failed to load audit detail", err);
    } finally {
      setLoading(false);
    }
  };

  const copyRemediation = (findingId: number, text?: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedFindingId(findingId);
    setTimeout(() => setCopiedFindingId(null), 2000);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton type="card" rows={4} />
        <LoadingSkeleton type="table" rows={6} />
      </div>
    );
  }

  if (!audit) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Audit Not Found"
        description="The requested audit record could not be loaded from the compliance database."
        actionLabel="Back to Audit Registry"
        onAction={onBack}
      />
    );
  }

  const filteredFindings = audit.findings.filter((f) => {
    if (selectedFramework !== "ALL" && f.framework !== selectedFramework) return false;
    if (selectedStatus !== "ALL" && f.status !== selectedStatus) return false;
    if (selectedSeverity !== "ALL" && f.severity !== selectedSeverity) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const match =
        f.rule_id.toLowerCase().includes(term) ||
        f.title.toLowerCase().includes(term) ||
        f.normalized_param.toLowerCase().includes(term) ||
        (f.evidence_text && f.evidence_text.toLowerCase().includes(term));
      if (!match) return false;
    }
    return true;
  });

  const frameworks = Array.from(new Set(audit.findings.map((f) => f.framework)));

  return (
    <div className="space-y-6">
      {/* Header and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-1.5 rounded-md bg-white border border-slate-200 hover:bg-white text-slate-500 hover:text-slate-800 transition-colors"
            title="Back to Audits"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-slate-900 font-mono tracking-tight">
                {audit.device_hostname}
              </h1>
              <span className="text-[10px] font-mono uppercase bg-white text-slate-700 px-1.5 py-0.2 rounded border border-slate-200">
                {audit.device_vendor}
              </span>
              <span className="text-[10px] text-slate-500 font-mono">
                Audit #{audit.id}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5 font-mono">
              Config: <span className="text-slate-700">{audit.filename}</span> · Run:{" "}
              {new Date(audit.timestamp).toLocaleString()}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onNavigateTrace && (
            <button
              onClick={() => onNavigateTrace(audit.config_id)}
              className="bg-white hover:bg-white text-slate-700 border border-slate-200 text-xs font-medium px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5"
            >
              <Terminal className="w-3.5 h-3.5 text-blue-700" />
              <span>Pipeline Trace</span>
            </button>
          )}

          <a
            href={apiClient.getPdfReportUrl(audit.id)}
            target="_blank"
            rel="noreferrer"
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Audit PDF</span>
          </a>
        </div>
      </div>

      {/* Telemetry Summary Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 bg-white border border-slate-200 rounded-lg p-4">
        <div>
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
            Compliance Score
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span
              className={`text-2xl font-bold font-mono ${
                audit.compliance_percentage >= 80
                  ? "text-emerald-700"
                  : audit.compliance_percentage >= 60
                  ? "text-amber-700"
                  : "text-red-700"
              }`}
            >
              {audit.compliance_percentage}%
            </span>
            <span className="text-[11px] text-slate-500">of controls</span>
          </div>
          <div className="w-full bg-slate-50 rounded-sm h-1.5 mt-2 border border-slate-200">
            <div
              className={`h-full ${
                audit.compliance_percentage >= 80
                  ? "bg-emerald-500"
                  : audit.compliance_percentage >= 60
                  ? "bg-amber-500"
                  : "bg-red-500"
              }`}
              style={{ width: `${Math.min(audit.compliance_percentage, 100)}%` }}
            ></div>
          </div>
        </div>

        <div>
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
            Risk Assessment
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <SeverityBadge severity={audit.risk_level} size="md" />
            <span className="font-mono text-xs text-slate-500">
              ({audit.risk_score} / 100 index)
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1.5">Weighted vulnerability severity</p>
        </div>

        <div>
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
            Evaluation Breakdown
          </span>
          <div className="flex items-center gap-3 mt-1.5 text-xs font-mono">
            <span className="text-emerald-700 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> {audit.passed_count} Pass
            </span>
            <span className="text-rose-700 flex items-center gap-1">
              <XCircle className="w-3.5 h-3.5" /> {audit.failed_count} Fail
            </span>
            <span className="text-slate-500 flex items-center gap-1">
              <HelpCircle className="w-3.5 h-3.5" /> {audit.not_evaluable_count} N/A
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1.5 font-mono">{audit.total_controls} total controls</p>
        </div>

        <div>
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
            Audit Engine Mode
          </span>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span className="text-xs font-medium text-slate-800">
              Deterministic Core + KB
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Zero simulated or mocked findings</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-lg p-3 flex flex-wrap items-center justify-between gap-3">
        {/* Framework Tabs */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setSelectedFramework("ALL")}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              selectedFramework === "ALL"
                ? "bg-blue-600 text-white"
                : "bg-white text-slate-500 hover:text-slate-800 border border-slate-200"
            }`}
          >
            All Frameworks ({audit.findings.length})
          </button>
          {frameworks.map((fw) => {
            const count = audit.findings.filter((f) => f.framework === fw).length;
            return (
              <button
                key={fw}
                onClick={() => setSelectedFramework(fw)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  selectedFramework === fw
                    ? "bg-blue-600 text-white"
                    : "bg-white text-slate-500 hover:text-slate-800 border border-slate-200"
                }`}
              >
                {fw} ({count})
              </button>
            );
          })}
        </div>

        {/* Dropdowns & Search */}
        <div className="flex items-center gap-2">
          <div className="relative w-44">
            <Search className="w-3 h-3 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search findings..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white border border-slate-200 text-xs text-slate-800 pl-7 pr-3 py-1 rounded focus:outline-none focus:border-slate-500 font-mono"
            />
          </div>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-white border border-slate-200 text-xs text-slate-700 rounded px-2.5 py-1 focus:outline-none focus:border-slate-500 font-mono"
          >
            <option value="ALL">All Outcomes</option>
            <option value="FAIL">FAIL Only ({audit.failed_count})</option>
            <option value="PASS">PASS Only ({audit.passed_count})</option>
            <option value="NOT_EVALUABLE">N/A ({audit.not_evaluable_count})</option>
          </select>

          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="bg-white border border-slate-200 text-xs text-slate-700 rounded px-2.5 py-1 focus:outline-none focus:border-slate-500 font-mono"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>
      </div>

      {/* Findings List */}
      <div className="space-y-3">
        {filteredFindings.map((finding) => {
          const isFail = finding.status === "FAIL";
          const isPass = finding.status === "PASS";

          return (
            <div
              key={finding.id}
              className={`bg-white border rounded-lg p-4 transition-colors ${
                isFail
                  ? "border-red-950/80 bg-slate-50"
                  : isPass
                  ? "border-emerald-950/60"
                  : "border-slate-200"
              }`}
            >
              {/* Finding Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2.5 mb-2.5 border-b border-slate-200 gap-2">
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={finding.status} size="sm" />
                  <SeverityBadge severity={finding.severity} size="sm" />
                  <span className="font-mono text-xs font-semibold text-slate-800">
                    {finding.rule_id}
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    ({finding.framework} · {finding.control_id})
                  </span>

                  {finding.is_learned_mapping_applied && (
                    <span className="text-[10px] font-mono bg-blue-950 text-blue-700 px-1.5 py-0.2 rounded border border-blue-800 flex items-center gap-1">
                      <Sparkles className="w-3 h-3 text-blue-700" />
                      <span>Learned Mapping</span>
                    </span>
                  )}
                </div>

                <div className="text-xs text-slate-500 font-mono">
                  Param: <code className="text-slate-700 bg-white px-1 py-0.5 rounded border border-slate-200">{finding.normalized_param}</code>
                </div>
              </div>

              {/* Title & Description */}
              <div>
                <h3 className="text-xs font-semibold text-slate-900">{finding.title}</h3>
                {finding.rationale && (
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    {finding.rationale}
                  </p>
                )}
              </div>

              {/* Expected vs Detected Comparison Box */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3 bg-white p-2.5 rounded border border-slate-200 text-xs font-mono">
                <div>
                  <span className="text-slate-500">Expected State: </span>
                  <span className="font-semibold text-emerald-700">
                    {finding.expected_value}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Detected State: </span>
                  <span
                    className={`font-semibold ${
                      isFail
                        ? "text-red-700"
                        : isPass
                        ? "text-emerald-700"
                        : "text-slate-500"
                    }`}
                  >
                    {finding.detected_value || "NOT_CONFIGURED"}
                  </span>
                </div>
              </div>

              {/* Configuration Evidence Block */}
              <div className="mt-3">
                <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                  <span className="font-medium text-slate-700">Configuration Evidence:</span>
                  {finding.evidence_line_no && (
                    <span className="font-mono text-blue-700">Line {finding.evidence_line_no}</span>
                  )}
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded p-2.5 font-mono text-xs text-slate-700 overflow-x-auto">
                  {finding.evidence_text || "No explicit parameter statement found in configuration."}
                </div>
              </div>

              {/* Security Impact Analysis */}
              {isFail && (
                <SecurityImpactAnalysis auditId={audit.id} findingId={finding.id} />
              )}

              {/* Vendor Remediation CLI Block */}
              {isFail && finding.remediation_text && (
                <div className="mt-3 pt-3 border-t border-slate-200">
                  <div className="flex items-center justify-between text-[11px] mb-1.5">
                    <span className="font-medium text-amber-700/90 flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5" />
                      <span>CLI Remediation ({(audit.device_vendor || "UNKNOWN").toUpperCase()})</span>
                    </span>
                    <button
                      onClick={() => copyRemediation(finding.id, finding.remediation_text)}
                      className="text-xs bg-white hover:bg-slate-100 text-slate-700 px-2 py-0.5 rounded transition-colors flex items-center gap-1"
                    >
                      {copiedFindingId === finding.id ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-700" />
                          <span className="text-emerald-700 font-mono text-[10px]">COPIED</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span className="text-[10px]">Copy Commands</span>
                        </>
                      )}
                    </button>
                  </div>

                  <pre className="bg-slate-50 border border-amber-900/30 text-amber-200/90 rounded p-2.5 font-mono text-xs overflow-x-auto">
                    {finding.remediation_text}
                  </pre>

                  {finding.verification_cmd && (
                    <div className="mt-1 text-[11px] text-slate-500 font-mono">
                      <span className="text-slate-500">Verification CLI: </span>
                      <code className="text-slate-700 bg-slate-50 px-1 py-0.2 rounded border border-slate-200">
                        {finding.verification_cmd}
                      </code>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {filteredFindings.length === 0 && (
          <EmptyState
            title="No Findings Match Filter"
            description="Adjust your search query, framework, or severity filters to view audit findings."
          />
        )}
      </div>
    </div>
  );
};
