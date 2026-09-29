import React, { useEffect, useState } from "react";
import { Layers, Search, ShieldCheck, RefreshCw } from "lucide-react";
import { apiClient } from "../api/client";
import { ComplianceRule } from "../types";
import { SeverityBadge } from "../components/common/SeverityBadge";
import { LoadingSkeleton } from "../components/common/LoadingSkeleton";
import { EmptyState } from "../components/common/EmptyState";

export const FrameworksPage: React.FC = () => {
  const [rules, setRules] = useState<ComplianceRule[]>([]);
  const [frameworks, setFrameworks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFramework, setSelectedFramework] = useState("ALL");
  const [selectedSeverity, setSelectedSeverity] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    fetchFrameworksAndRules();
  }, []);

  const fetchFrameworksAndRules = async () => {
    try {
      setLoading(true);
      const [fwData, rulesData] = await Promise.all([
        apiClient.listFrameworks(),
        apiClient.listRules(),
      ]);
      setFrameworks(fwData);
      setRules(rulesData);
    } catch (err) {
      console.error("Failed to load compliance data", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredRules = rules.filter((r) => {
    if (selectedFramework !== "ALL" && r.framework !== selectedFramework) return false;
    if (selectedSeverity !== "ALL" && r.severity !== selectedSeverity) return false;
    const term = searchTerm.toLowerCase();
    return (
      r.rule_id.toLowerCase().includes(term) ||
      r.title.toLowerCase().includes(term) ||
      r.parameter.toLowerCase().includes(term) ||
      r.description.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
            Security Compliance Policy & Rules Catalog
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Official benchmark controls mapped to canonical parameters across CIS, NIST SP 800-53, DISA STIG, and ISO/IEC 27001.
          </p>
        </div>

        <button
          onClick={fetchFrameworksAndRules}
          className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-white rounded transition-colors self-start sm:self-auto border border-slate-200/60"
          title="Refresh rules"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Framework Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {frameworks.map((fw) => {
          const isSelected = selectedFramework === fw.name;
          return (
            <div
              key={fw.name}
              onClick={() => setSelectedFramework(isSelected ? "ALL" : fw.name)}
              className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                isSelected
                  ? "bg-slate-50 border-blue-500"
                  : "bg-white border-slate-200 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-slate-900">{fw.name}</span>
                <span className="text-[10px] font-mono text-slate-500 bg-white px-1.5 py-0.2 rounded">
                  {fw.version || "Official"}
                </span>
              </div>
              <div className="mt-2.5 flex items-baseline gap-2">
                <span className="text-xl font-bold font-mono text-slate-900">
                  {fw.total_controls}
                </span>
                <span className="text-[11px] text-slate-500">rules</span>
              </div>
              <div className="mt-2 flex items-center gap-1.5 text-[10px] font-mono">
                <span className="text-red-700">{fw.severities?.CRITICAL || 0} Crit</span>
                <span className="text-slate-600">·</span>
                <span className="text-orange-700">{fw.severities?.HIGH || 0} High</span>
                <span className="text-slate-600">·</span>
                <span className="text-amber-700">{fw.severities?.MEDIUM || 0} Med</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-lg p-3 flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex items-center gap-2 flex-grow max-w-sm">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search by rule ID, title, parameter..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white border border-slate-200 text-xs text-slate-800 pl-8 pr-3 py-1.5 rounded-md focus:outline-none focus:border-slate-500 font-mono"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedFramework}
            onChange={(e) => setSelectedFramework(e.target.value)}
            className="bg-white border border-slate-200 text-xs text-slate-700 rounded px-2.5 py-1.5 focus:outline-none focus:border-slate-500 font-mono"
          >
            <option value="ALL">All Frameworks</option>
            {frameworks.map((f) => (
              <option key={f.name} value={f.name}>
                {f.name}
              </option>
            ))}
          </select>

          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="bg-white border border-slate-200 text-xs text-slate-700 rounded px-2.5 py-1.5 focus:outline-none focus:border-slate-500 font-mono"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>
      </div>

      {/* Rules Table */}
      {loading ? (
        <LoadingSkeleton type="table" rows={8} />
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-white text-slate-500 uppercase text-[10px] font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2.5">Severity</th>
                  <th className="px-4 py-2.5">Rule ID</th>
                  <th className="px-4 py-2.5">Framework & Control</th>
                  <th className="px-4 py-2.5">Title & Description</th>
                  <th className="px-4 py-2.5">Canonical Parameter</th>
                  <th className="px-4 py-2.5">Operator</th>
                  <th className="px-4 py-2.5">Expected State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredRules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <SeverityBadge severity={rule.severity} size="sm" />
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold text-slate-800 text-[11px]">
                      {rule.rule_id}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-500 text-[11px]">
                      {rule.framework} · {rule.control_id}
                    </td>
                    <td className="px-4 py-3 max-w-sm">
                      <div className="font-semibold text-slate-800 text-xs">{rule.title}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
                        {rule.description}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <code className="text-slate-700 bg-white px-1 py-0.5 rounded border border-slate-200 font-mono text-[11px]">
                        {rule.parameter}
                      </code>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-700 text-[11px]">
                      {rule.operator}
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold text-emerald-700 text-[11px]">
                      {rule.expected_value}
                    </td>
                  </tr>
                ))}
                {filteredRules.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center">
                      <EmptyState
                        icon={Layers}
                        title="No Rules Match Filter"
                        description="Try selecting a different framework or severity level."
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
