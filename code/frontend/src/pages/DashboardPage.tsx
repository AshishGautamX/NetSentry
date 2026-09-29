import React, { useEffect, useState } from "react";
import {
  Server,
  ShieldAlert,
  ArrowRight,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Cpu,
  Layers,
  FileCheck,
  AlertOctagon,
  RefreshCw,
} from "lucide-react";
import { apiClient } from "../api/client";
import { DashboardStats } from "../types";
import { MetricCard } from "../components/common/MetricCard";
import { SeverityBadge } from "../components/common/SeverityBadge";
import { LoadingSkeleton } from "../components/common/LoadingSkeleton";
import { EmptyState } from "../components/common/EmptyState";

interface DashboardProps {
  onNavigate: (tab: string, auditId?: number) => void;
}

export const DashboardPage: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getDashboardStats();
      setStats(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Failed to fetch dashboard stats", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading && !stats) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton type="card" rows={4} />
        <LoadingSkeleton type="table" rows={6} />
      </div>
    );
  }

  const avgCompliance = stats?.average_compliance_pct ?? 0;
  const criticalFindings = stats?.critical_findings_count ?? 0;
  const highFindings = stats?.high_findings_count ?? 0;
  const mediumFindings = stats?.medium_findings_count ?? 0;
  const lowFindings = stats?.low_findings_count ?? 0;
  const totalFindings = criticalFindings + highFindings + mediumFindings + lowFindings;

  return (
    <div className="space-y-6">
      {/* Header Operational Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
            Network Security Posture
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Continuous compliance evaluation across heterogeneous network device configurations.
            {lastUpdated && <span className="ml-2 text-slate-500">· Telemetry sync: {lastUpdated}</span>}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigate("upload")}
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <span>Ingest Config</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={fetchStats}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-white rounded-md transition-colors border border-slate-200/60"
            title="Refresh statistics"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* KPI Metric Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Compliance */}
        <MetricCard
          label="Mean Compliance"
          value={`${avgCompliance}%`}
          subtext="Across all evaluated benchmarks"
          valueColor={
            avgCompliance >= 80
              ? "text-emerald-700"
              : avgCompliance >= 60
              ? "text-amber-700"
              : "text-red-700"
          }
          icon={FileCheck}
          badge={avgCompliance >= 80 ? "HEALTHY" : avgCompliance >= 60 ? "WARNING" : "CRITICAL"}
          badgeColor={
            avgCompliance >= 80
              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
              : avgCompliance >= 60
              ? "bg-amber-50 text-amber-700 border-amber-800"
              : "bg-red-50 text-red-700 border-red-800"
          }
        />

        {/* Severe Findings */}
        <MetricCard
          label="Severe Vulnerabilities"
          value={criticalFindings + highFindings}
          subtext={`${criticalFindings} Critical · ${highFindings} High`}
          valueColor={criticalFindings > 0 ? "text-red-700" : highFindings > 0 ? "text-orange-700" : "text-slate-900"}
          icon={ShieldAlert}
          onClick={() => onNavigate("findings")}
        />

        {/* Audited Nodes */}
        <MetricCard
          label="Device Inventory"
          value={stats?.total_devices ?? 0}
          subtext={`${stats?.total_audits ?? 0} total audit runs completed`}
          valueColor="text-slate-900"
          icon={Server}
          onClick={() => onNavigate("audits")}
        />

        {/* Training Queue */}
        <MetricCard
          label="Unknown Syntax Queue"
          value={stats?.unknown_commands_count ?? 0}
          subtext={
            stats?.unknown_commands_count
              ? "Unmapped vendor syntax pending review"
              : "All observed syntax mapped"
          }
          valueColor={stats?.unknown_commands_count ? "text-amber-700" : "text-emerald-700"}
          icon={Cpu}
          onClick={() => onNavigate("training")}
        />
      </div>

      {/* Two-Column Operational Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Compliance by Framework */}
        <div className="lg:col-span-8 bg-white border border-slate-200 rounded-lg p-5">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-200">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-slate-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
                Compliance by Regulatory Framework
              </h2>
            </div>
            <button
              onClick={() => onNavigate("frameworks")}
              className="text-xs text-blue-700 hover:text-blue-700 font-medium"
            >
              View Rules Catalog &rarr;
            </button>
          </div>

          <div className="space-y-4">
            {stats &&
              Object.entries(stats.framework_distribution).map(([framework, counts]) => {
                const total = counts.pass + counts.fail + counts.not_evaluable;
                const passPct = total > 0 ? Math.round((counts.pass / total) * 100) : 0;
                const failPct = total > 0 ? Math.round((counts.fail / total) * 100) : 0;
                const naPct = total > 0 ? 100 - passPct - failPct : 0;

                return (
                  <div
                    key={framework}
                    className="p-3 bg-white border border-slate-200 rounded-md"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-800">
                          {framework}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">
                          ({total} rules evaluated)
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs font-mono">
                        <span className="text-emerald-700 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> {counts.pass} Pass
                        </span>
                        <span className="text-rose-700 flex items-center gap-1">
                          <XCircle className="w-3.5 h-3.5" /> {counts.fail} Fail
                        </span>
                        <span className="text-slate-500 flex items-center gap-1">
                          <HelpCircle className="w-3.5 h-3.5" /> {counts.not_evaluable} N/A
                        </span>
                        <span className="font-bold text-slate-900 ml-1">
                          {passPct}%
                        </span>
                      </div>
                    </div>

                    {/* Segmented Progress Bar */}
                    <div className="w-full bg-slate-50 rounded-sm h-2 flex overflow-hidden border border-slate-200">
                      <div
                        style={{ width: `${passPct}%` }}
                        className="bg-emerald-600 h-full transition-all"
                        title={`Pass: ${passPct}%`}
                      ></div>
                      <div
                        style={{ width: `${failPct}%` }}
                        className="bg-rose-600 h-full transition-all"
                        title={`Fail: ${failPct}%`}
                      ></div>
                      <div
                        style={{ width: `${naPct}%` }}
                        className="bg-slate-700 h-full transition-all"
                        title={`Not Configured / NA: ${naPct}%`}
                      ></div>
                    </div>
                  </div>
                );
              })}

            {(!stats || Object.keys(stats.framework_distribution).length === 0) && (
              <EmptyState
                icon={Layers}
                title="No Framework Data Available"
                description="Upload and audit network device configurations to generate framework compliance metrics."
                actionLabel="Ingest Configuration"
                onAction={() => onNavigate("upload")}
              />
            )}
          </div>
        </div>

        {/* Right Column: Risk & Vendor Distribution */}
        <div className="lg:col-span-4 space-y-6">
          {/* Findings Severity Breakdown */}
          <div className="bg-white border border-slate-200 rounded-lg p-5">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-200">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
                Risk Distribution
              </h2>
              <button
                onClick={() => onNavigate("findings")}
                className="text-xs text-blue-700 hover:text-blue-700 font-medium"
              >
                All Findings &rarr;
              </button>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between p-2.5 bg-white border border-slate-200 rounded">
                <SeverityBadge severity="CRITICAL" size="sm" />
                <span className="font-mono text-xs font-bold text-red-700">
                  {criticalFindings}
                </span>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-white border border-slate-200 rounded">
                <SeverityBadge severity="HIGH" size="sm" />
                <span className="font-mono text-xs font-bold text-orange-700">
                  {highFindings}
                </span>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-white border border-slate-200 rounded">
                <SeverityBadge severity="MEDIUM" size="sm" />
                <span className="font-mono text-xs font-bold text-amber-700">
                  {mediumFindings}
                </span>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-white border border-slate-200 rounded">
                <SeverityBadge severity="LOW" size="sm" />
                <span className="font-mono text-xs font-bold text-blue-700">
                  {lowFindings}
                </span>
              </div>
            </div>
          </div>

          {/* Multi-Vendor Fleet Coverage */}
          <div className="bg-white border border-slate-200 rounded-lg p-5">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800 pb-3 mb-3 border-b border-slate-200">
              Multi-Vendor Fleet Coverage
            </h2>
            <div className="space-y-1.5">
              {stats &&
                Object.entries(stats.vendor_distribution).map(([vendor, count]) => (
                  <div
                    key={vendor}
                    className="flex items-center justify-between p-2 bg-white rounded border border-slate-200/80 text-xs"
                  >
                    <span className="font-mono text-slate-700 capitalize">{vendor}</span>
                    <span className="font-mono text-slate-500 font-medium">
                      {count} {count === 1 ? "device" : "devices"}
                    </span>
                  </div>
                ))}
              {(!stats || Object.keys(stats.vendor_distribution).length === 0) && (
                <p className="text-xs text-slate-500 italic py-2">
                  No devices ingested yet.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Audits Table */}
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
              Recent Network Audits
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Latest deterministic evaluation runs across managed nodes
            </p>
          </div>
          <button
            onClick={() => onNavigate("audits")}
            className="text-xs text-blue-700 hover:text-blue-700 font-medium"
          >
            View All Audits ({stats?.total_audits ?? 0}) &rarr;
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-white text-slate-500 uppercase text-[10px] font-semibold border-b border-slate-200">
              <tr>
                <th className="px-4 py-2.5">Hostname</th>
                <th className="px-4 py-2.5">Vendor</th>
                <th className="px-4 py-2.5">Configuration</th>
                <th className="px-4 py-2.5">Compliance</th>
                <th className="px-4 py-2.5">Risk Level</th>
                <th className="px-4 py-2.5">Evaluations</th>
                <th className="px-4 py-2.5">Date</th>
                <th className="px-4 py-2.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {stats?.recent_audits.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-semibold text-slate-900 font-mono">
                    {a.device_hostname}
                  </td>
                  <td className="px-4 py-3 uppercase text-slate-500 font-mono text-[11px]">
                    {a.device_vendor}
                  </td>
                  <td className="px-4 py-3 text-slate-500 font-mono text-[11px] max-w-xs truncate" title={a.filename}>
                    {a.filename}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`font-mono font-bold ${
                        a.compliance_percentage >= 80
                          ? "text-emerald-700"
                          : a.compliance_percentage >= 60
                          ? "text-amber-700"
                          : "text-red-700"
                      }`}
                    >
                      {a.compliance_percentage}%
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={a.risk_level} size="sm" />
                  </td>
                  <td className="px-4 py-3 font-mono text-[11px]">
                    <span className="text-emerald-700">{a.passed_count}P</span>{" "}
                    <span className="text-slate-600">/</span>{" "}
                    <span className="text-rose-700">{a.failed_count}F</span>{" "}
                    <span className="text-slate-600">/</span>{" "}
                    <span className="text-slate-500">{a.not_evaluable_count}NA</span>
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-[11px]">
                    {new Date(a.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => onNavigate("audit_detail", a.id)}
                      className="text-xs bg-white hover:bg-slate-100 text-slate-800 border border-slate-200 px-2.5 py-1 rounded transition-colors"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
              {(!stats?.recent_audits || stats.recent_audits.length === 0) && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center">
                    <EmptyState
                      icon={FileCheck}
                      title="No Audits Executed"
                      description="Upload and analyze network configuration files to view compliance findings."
                      actionLabel="Ingest First Configuration"
                      onAction={() => onNavigate("upload")}
                    />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
