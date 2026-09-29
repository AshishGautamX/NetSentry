import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  Search,
  Filter,
  Terminal,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  RefreshCw,
} from "lucide-react";
import { apiClient } from "../api/client";
import { GlobalFinding, AuditRun } from "../types";
import { SeverityBadge } from "../components/common/SeverityBadge";
import { LoadingSkeleton } from "../components/common/LoadingSkeleton";
import { EmptyState } from "../components/common/EmptyState";
import { SecurityImpactAnalysis } from "../components/common/SecurityImpactAnalysis";

interface FindingsPageProps {
  onNavigateAudit?: (auditId: number) => void;
}

export const FindingsPage: React.FC<FindingsPageProps> = ({ onNavigateAudit }) => {
  const [findings, setFindings] = useState<GlobalFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSeverity, setSelectedSeverity] = useState("ALL");
  const [selectedStatus, setSelectedStatus] = useState("FAIL");
  const [selectedFramework, setSelectedFramework] = useState("ALL");
  const [selectedVendor, setSelectedVendor] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const fetchFindings = async () => {
    try {
      setLoading(true);
      // Try backend endpoint first
      let data: GlobalFinding[] = [];
      try {
        data = await apiClient.listAllFindings({
          severity: selectedSeverity !== "ALL" ? selectedSeverity : undefined,
          status: selectedStatus !== "ALL" ? selectedStatus : undefined,
          framework: selectedFramework !== "ALL" ? selectedFramework : undefined,
          vendor: selectedVendor !== "ALL" ? selectedVendor : undefined,
        });
      } catch {
        // Fallback: aggregate from listAudits + getAudit
        const audits = await apiClient.listAudits();
        const findingsAcc: GlobalFinding[] = [];
        for (const a of audits.slice(0, 10)) {
          const detailed = await apiClient.getAudit(a.id);
          for (const f of detailed.findings) {
            findingsAcc.push({
              ...f,
              audit_id: a.id,
              device_hostname: a.device_hostname,
              device_vendor: a.device_vendor,
              filename: a.filename,
              audit_timestamp: a.timestamp,
            });
          }
        }
        data = findingsAcc;
      }
      setFindings(data);
    } catch (err) {
      console.error("Failed to load global findings", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFindings();
  }, [selectedSeverity, selectedStatus, selectedFramework, selectedVendor]);

  const copyRemediation = (id: number, text?: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const filteredFindings = findings.filter((f) => {
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const match =
        f.rule_id.toLowerCase().includes(term) ||
        f.title.toLowerCase().includes(term) ||
        f.normalized_param.toLowerCase().includes(term) ||
        (f.device_hostname && f.device_hostname.toLowerCase().includes(term)) ||
        (f.evidence_text && f.evidence_text.toLowerCase().includes(term));
      if (!match) return false;
    }
    return true;
  });

  const criticalCount = findings.filter((f) => f.severity === "CRITICAL").length;
  const highCount = findings.filter((f) => f.severity === "HIGH").length;
  const failCount = findings.filter((f) => f.status === "FAIL").length;

  return (
    <div className="space-y-6">
      {/* Header & Analyst Summary Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
            Security Analyst Findings Workspace
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Cross-fleet non-compliance telemetry, CVE-aligned configuration vulnerabilities, and CLI remediation.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="text-red-700 font-semibold bg-red-950/60 border border-red-900/60 px-2 py-1 rounded">
            {criticalCount} Critical
          </span>
          <span className="text-orange-700 font-semibold bg-orange-950/60 border border-orange-900/60 px-2 py-1 rounded">
            {highCount} High
          </span>
          <span className="text-slate-700 font-semibold bg-white border border-slate-200 px-2 py-1 rounded">
            {failCount} Non-Compliant
          </span>
          <button
            onClick={fetchFindings}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-white rounded transition-colors"
            title="Refresh findings"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Analyst Filter Toolbar */}
      <div className="bg-white border border-slate-200 rounded-lg p-3 flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex items-center gap-2 flex-grow max-w-sm">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search findings by rule, param, host..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white border border-slate-200 text-xs text-slate-800 pl-8 pr-3 py-1.5 rounded-md focus:outline-none focus:border-slate-500 font-mono"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-white border border-slate-200 text-xs text-slate-700 rounded px-2.5 py-1.5 focus:outline-none focus:border-slate-500 font-mono"
          >
            <option value="FAIL">Status: FAIL Only</option>
            <option value="PASS">Status: PASS Only</option>
            <option value="ALL">Status: All Outcomes</option>
            <option value="NOT_EVALUABLE">Status: Unconfigured / NA</option>
          </select>

          {/* Severity Filter */}
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="bg-white border border-slate-200 text-xs text-slate-700 rounded px-2.5 py-1.5 focus:outline-none focus:border-slate-500 font-mono"
          >
            <option value="ALL">Severity: All</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>

          {/* Framework Filter */}
          <select
            value={selectedFramework}
            onChange={(e) => setSelectedFramework(e.target.value)}
            className="bg-white border border-slate-200 text-xs text-slate-700 rounded px-2.5 py-1.5 focus:outline-none focus:border-slate-500 font-mono"
          >
            <option value="ALL">Framework: All</option>
            <option value="CIS">CIS</option>
            <option value="NIST SP 800-53">NIST 800-53</option>
            <option value="DISA STIG">DISA STIG</option>
            <option value="ISO/IEC 27001">ISO 27001</option>
          </select>

          {/* Vendor Filter */}
          <select
            value={selectedVendor}
            onChange={(e) => setSelectedVendor(e.target.value)}
            className="bg-white border border-slate-200 text-xs text-slate-700 rounded px-2.5 py-1.5 focus:outline-none focus:border-slate-500 font-mono uppercase"
          >
            <option value="ALL">Vendor: All</option>
            <option value="cisco">Cisco</option>
            <option value="juniper">Juniper</option>
            <option value="fortinet">Fortinet</option>
            <option value="paloalto">Palo Alto</option>
            <option value="arista">Arista</option>
            <option value="sonic">SONiC</option>
            <option value="cumulus">Cumulus</option>
          </select>
        </div>
      </div>

      {/* Findings Data Table */}
      {loading ? (
        <LoadingSkeleton type="table" rows={8} />
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-white text-slate-500 uppercase text-[10px] font-semibold border-b border-slate-200">
                <tr>
                  <th className="w-8 px-3 py-2.5"></th>
                  <th className="px-3 py-2.5">Severity</th>
                  <th className="px-3 py-2.5">Rule ID</th>
                  <th className="px-3 py-2.5">Title & Context</th>
                  <th className="px-3 py-2.5">Device Hostname</th>
                  <th className="px-3 py-2.5">Vendor</th>
                  <th className="px-3 py-2.5">Framework</th>
                  <th className="px-3 py-2.5">Expected vs Detected</th>
                  <th className="px-3 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredFindings.map((finding) => {
                  const isExpanded = expandedId === finding.id;
                  const isFail = finding.status === "FAIL";

                  return (
                    <React.Fragment key={finding.id}>
                      <tr
                        onClick={() => setExpandedId(isExpanded ? null : finding.id)}
                        className={`hover:bg-slate-50 transition-colors cursor-pointer ${
                          isExpanded ? "bg-slate-50" : ""
                        }`}
                      >
                        <td className="px-3 py-2.5 text-slate-500">
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5" />
                          )}
                        </td>
                        <td className="px-3 py-2.5">
                          <SeverityBadge severity={finding.severity} size="sm" />
                        </td>
                        <td className="px-3 py-2.5 font-mono text-[11px] font-semibold text-slate-800">
                          {finding.rule_id}
                        </td>
                        <td className="px-3 py-2.5 max-w-sm">
                          <div className="font-medium text-slate-800 truncate" title={finding.title}>
                            {finding.title}
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono truncate">
                            {finding.normalized_param}
                          </div>
                        </td>
                        <td className="px-3 py-2.5 font-mono text-slate-800 font-semibold">
                          {finding.device_hostname || "UNKNOWN"}
                        </td>
                        <td className="px-3 py-2.5 uppercase font-mono text-[11px] text-slate-500">
                          {finding.device_vendor || "—"}
                        </td>
                        <td className="px-3 py-2.5 font-mono text-[11px] text-slate-500">
                          {finding.framework} · {finding.control_id}
                        </td>
                        <td className="px-3 py-2.5 font-mono text-[11px]">
                          <span className="text-emerald-700">{finding.expected_value}</span>
                          <span className="text-slate-600 mx-1">&ne;</span>
                          <span className={isFail ? "text-red-700" : "text-emerald-700"}>
                            {finding.detected_value || "NOT_CONFIGURED"}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-1.5">
                            {finding.remediation_text && (
                              <button
                                onClick={() => copyRemediation(finding.id, finding.remediation_text)}
                                className="bg-white hover:bg-slate-100 text-slate-700 px-2 py-1 rounded text-[11px] font-mono transition-colors flex items-center gap-1"
                                title="Copy CLI remediation"
                              >
                                {copiedId === finding.id ? (
                                  <>
                                    <Check className="w-3 h-3 text-emerald-700" />
                                    <span className="text-emerald-700">Copied</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy className="w-3 h-3" />
                                    <span>Remediate</span>
                                  </>
                                )}
                              </button>
                            )}
                            {onNavigateAudit && (
                              <button
                                onClick={() => onNavigateAudit(finding.audit_id)}
                                className="text-slate-500 hover:text-blue-700 p-1 rounded"
                                title="Open full audit record"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>

                      {/* Expandable Technical Detail Drawer */}
                      {isExpanded && (
                        <tr className="bg-slate-50">
                          <td colSpan={9} className="px-6 py-4 border-b border-slate-200">
                            <div className="space-y-3">
                              {/* Rationale */}
                              {finding.rationale && (
                                <div>
                                  <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                                    Control Rationale
                                  </span>
                                  <p className="text-xs text-slate-700 mt-0.5 leading-relaxed">
                                    {finding.rationale}
                                  </p>
                                </div>
                              )}

                              {/* Evidence Citation */}
                              <div>
                                <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                                  <span className="font-semibold text-slate-700">
                                    Device Configuration Evidence:
                                  </span>
                                  {finding.evidence_line_no && (
                                    <span className="font-mono text-blue-700">
                                      Line {finding.evidence_line_no}
                                    </span>
                                  )}
                                </div>
                                <div className="bg-slate-50 border border-slate-200 rounded p-2.5 font-mono text-xs text-slate-700 overflow-x-auto">
                                  {finding.evidence_text || "No parameter statement found in configuration."}
                                </div>
                              </div>

                              {/* Security Impact Analysis */}
                              {isFail && (
                                <SecurityImpactAnalysis auditId={finding.audit_id} findingId={finding.id} />
                              )}

                              {/* CLI Remediation Commands */}
                              {finding.remediation_text && (
                                <div>
                                  <div className="flex items-center justify-between text-[11px] mb-1">
                                    <span className="font-semibold text-amber-700/90 flex items-center gap-1.5">
                                      <Terminal className="w-3.5 h-3.5" />
                                      <span>Vendor Remediation Syntax ({(finding.device_vendor || "GENERIC").toUpperCase()})</span>
                                    </span>
                                    <button
                                      onClick={() => copyRemediation(finding.id, finding.remediation_text)}
                                      className="text-xs bg-white hover:bg-slate-100 text-slate-700 px-2 py-0.5 rounded transition-colors flex items-center gap-1"
                                    >
                                      {copiedId === finding.id ? (
                                        <Check className="w-3 h-3 text-emerald-700" />
                                      ) : (
                                        <Copy className="w-3 h-3" />
                                      )}
                                      <span>Copy</span>
                                    </button>
                                  </div>
                                  <pre className="bg-slate-50 border border-amber-900/30 text-amber-200/90 rounded p-2.5 font-mono text-xs overflow-x-auto">
                                    {finding.remediation_text}
                                  </pre>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}

                {filteredFindings.length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center">
                      <EmptyState
                        icon={AlertTriangle}
                        title="No Findings Match Filters"
                        description="Try adjusting severity, framework, or vendor parameters to inspect additional findings."
                      />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
