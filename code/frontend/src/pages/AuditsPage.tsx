import React, { useEffect, useState } from "react";
import { Search, Server, Download, FileCheck, RefreshCw } from "lucide-react";
import { apiClient } from "../api/client";
import { AuditRun } from "../types";
import { SeverityBadge } from "../components/common/SeverityBadge";
import { LoadingSkeleton } from "../components/common/LoadingSkeleton";
import { EmptyState } from "../components/common/EmptyState";

interface AuditsPageProps {
  onSelectAudit: (auditId: number) => void;
}

export const AuditsPage: React.FC<AuditsPageProps> = ({ onSelectAudit }) => {
  const [audits, setAudits] = useState<AuditRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedRisk, setSelectedRisk] = useState("ALL");

  useEffect(() => {
    fetchAudits();
  }, []);

  const fetchAudits = async () => {
    try {
      setLoading(true);
      const data = await apiClient.listAudits();
      setAudits(data);
    } catch (err) {
      console.error("Failed to load audits", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredAudits = audits.filter((a) => {
    if (selectedRisk !== "ALL" && a.risk_level !== selectedRisk) return false;
    const term = searchTerm.toLowerCase();
    return (
      a.device_hostname?.toLowerCase().includes(term) ||
      a.device_vendor?.toLowerCase().includes(term) ||
      a.filename?.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header and Filter Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
            Compliance Audit Registry
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit history, quantitative risk indices, and verifiable compliance records across all managed devices.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Search Box */}
          <div className="relative w-56">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search hostname, vendor, file..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white border border-slate-200 text-xs text-slate-800 pl-8 pr-3 py-1.5 rounded-md focus:outline-none focus:border-slate-500 font-mono"
            />
          </div>

          {/* Risk Filter */}
          <select
            value={selectedRisk}
            onChange={(e) => setSelectedRisk(e.target.value)}
            className="bg-white border border-slate-200 text-xs text-slate-700 px-2.5 py-1.5 rounded-md focus:outline-none focus:border-slate-500 font-mono"
          >
            <option value="ALL">All Risk Levels</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>

          <button
            onClick={fetchAudits}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-white rounded-md transition-colors border border-slate-200/60"
            title="Refresh audits"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingSkeleton type="table" rows={6} />
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-white text-slate-500 uppercase text-[10px] font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2.5">Hostname</th>
                  <th className="px-4 py-2.5">Vendor</th>
                  <th className="px-4 py-2.5">Configuration</th>
                  <th className="px-4 py-2.5">Compliance Score</th>
                  <th className="px-4 py-2.5">Risk Score</th>
                  <th className="px-4 py-2.5">Risk Posture</th>
                  <th className="px-4 py-2.5">Evaluations</th>
                  <th className="px-4 py-2.5">Audit Timestamp</th>
                  <th className="px-4 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredAudits.map((audit) => (
                  <tr key={audit.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-semibold text-slate-900 font-mono">
                      {audit.device_hostname}
                    </td>
                    <td className="px-4 py-3 uppercase font-mono text-slate-500 text-[11px]">
                      {audit.device_vendor}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-500 text-[11px] max-w-xs truncate" title={audit.filename}>
                      {audit.filename}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`font-mono font-bold ${
                          audit.compliance_percentage >= 80
                            ? "text-emerald-700"
                            : audit.compliance_percentage >= 60
                            ? "text-amber-700"
                            : "text-red-700"
                        }`}
                      >
                        {audit.compliance_percentage}%
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono font-medium text-slate-700">
                      {audit.risk_score} / 100
                    </td>
                    <td className="px-4 py-3">
                      <SeverityBadge severity={audit.risk_level} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-[11px] font-mono">
                      <span className="text-emerald-700 font-medium">{audit.passed_count}P</span>
                      <span className="text-slate-600 mx-1">/</span>
                      <span className="text-rose-700 font-medium">{audit.failed_count}F</span>
                      <span className="text-slate-600 mx-1">/</span>
                      <span className="text-slate-500">{audit.not_evaluable_count}NA</span>
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-[11px]">
                      {new Date(audit.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => onSelectAudit(audit.id)}
                          className="bg-blue-600/20 hover:bg-blue-600/30 text-blue-700 border border-blue-500/30 px-2.5 py-1 rounded text-xs transition-colors"
                        >
                          Inspect
                        </button>
                        <a
                          href={apiClient.getPdfReportUrl(audit.id)}
                          target="_blank"
                          rel="noreferrer"
                          className="bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 px-2 py-1 rounded text-xs transition-colors flex items-center gap-1"
                          title="Download Verifiable PDF Audit Report"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>PDF</span>
                        </a>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredAudits.length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center">
                      <EmptyState
                        icon={FileCheck}
                        title="No Audits Found"
                        description={
                          searchTerm || selectedRisk !== "ALL"
                            ? "No audit records match the current filter criteria."
                            : "Upload network configurations to execute automated compliance audits."
                        }
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
