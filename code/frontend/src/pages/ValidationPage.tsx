import React, { useEffect, useState } from "react";
import { Terminal, Shield, ArrowRight, CheckCircle2, ChevronRight, Filter } from "lucide-react";
import { apiClient } from "../api/client";
import { Configuration, ValidationTraceStep } from "../types";
import { LoadingSkeleton } from "../components/common/LoadingSkeleton";
import { EmptyState } from "../components/common/EmptyState";

interface ValidationPageProps {
  initialConfigId?: number;
}

export const ValidationPage: React.FC<ValidationPageProps> = ({ initialConfigId }) => {
  const [configs, setConfigs] = useState<Configuration[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<number | null>(initialConfigId || null);
  const [traceData, setTraceData] = useState<{
    config_id: number;
    filename: string;
    vendor_detected: string;
    total_lines_analyzed: number;
    security_relevant_count: number;
    steps: ValidationTraceStep[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [securityOnly, setSecurityOnly] = useState(true);

  useEffect(() => {
    fetchConfigs();
  }, []);

  useEffect(() => {
    if (selectedConfigId) {
      fetchTrace(selectedConfigId);
    }
  }, [selectedConfigId]);

  const fetchConfigs = async () => {
    try {
      const data = await apiClient.listConfigurations();
      setConfigs(data);
      if (data.length > 0 && !selectedConfigId) {
        setSelectedConfigId(data[0].id);
      }
    } catch (err) {
      console.error("Failed to load configs for validation", err);
    }
  };

  const fetchTrace = async (configId: number) => {
    try {
      setLoading(true);
      const trace = await apiClient.getValidationTrace(configId);
      setTraceData(trace);
    } catch (err) {
      console.error("Failed to load trace", err);
    } finally {
      setLoading(false);
    }
  };

  const displayedSteps = (traceData?.steps || []).filter((s) =>
    securityOnly ? s.is_security_relevant : true
  );

  return (
    <div className="space-y-6">
      {/* Title & Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
            Full-Chain Pipeline Validation Trace
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Cryptographic and semantic audit trace: line-by-line inspection of how raw syntax is ingested, sanitized,
            normalized into canonical parameters, and matched against compliance baselines.
          </p>
        </div>

        {/* Configuration Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-mono">Audited Target:</span>
          <select
            value={selectedConfigId || ""}
            onChange={(e) => setSelectedConfigId(Number(e.target.value))}
            className="bg-white border border-slate-200 text-xs text-slate-800 px-3 py-1.5 rounded-md focus:outline-none focus:border-slate-500 font-mono"
          >
            {configs.map((c) => (
              <option key={c.id} value={c.id}>
                {c.filename} ({c.vendor_detected})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Pipeline Technical Architecture Steps */}
      <div className="bg-white border border-slate-200 rounded-lg p-3 overflow-x-auto">
        <div className="flex items-center justify-between min-w-[680px] text-xs font-mono">
          {[
            { step: "01", name: "Raw Ingestion" },
            { step: "02", name: "Secret Scrubbing" },
            { step: "03", name: "Vendor Tokenizer" },
            { step: "04", name: "Semantic Normalizer" },
            { step: "05", name: "Canonical Baseline" },
            { step: "06", name: "Rule Verification" },
          ].map((s, idx, arr) => (
            <React.Fragment key={s.step}>
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded bg-white border border-slate-200 text-slate-700 text-[10px] font-bold flex items-center justify-center">
                  {s.step}
                </span>
                <span className="text-slate-700 text-[11px] font-medium">{s.name}</span>
              </div>
              {idx < arr.length - 1 && (
                <ChevronRight className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Summary KPI Strip */}
      {traceData && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-white border border-slate-200 rounded-lg p-3.5 text-xs font-mono">
          <div>
            <span className="text-slate-500">Target File:</span>
            <p className="font-semibold text-slate-800 truncate mt-0.5" title={traceData.filename}>
              {traceData.filename}
            </p>
          </div>
          <div>
            <span className="text-slate-500">Classified Vendor:</span>
            <p className="font-semibold text-blue-700 uppercase mt-0.5">
              {traceData.vendor_detected}
            </p>
          </div>
          <div>
            <span className="text-slate-500">Lines Tokenized:</span>
            <p className="font-semibold text-slate-800 mt-0.5">
              {traceData.total_lines_analyzed} lines
            </p>
          </div>
          <div>
            <span className="text-slate-500">Security Parameters:</span>
            <p className="font-semibold text-emerald-700 mt-0.5">
              {traceData.security_relevant_count} normalized
            </p>
          </div>
        </div>
      )}

      {/* Trace Table Filter Bar */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSecurityOnly(true)}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              securityOnly
                ? "bg-blue-600 text-white"
                : "bg-white text-slate-500 border border-slate-200"
            }`}
          >
            Security-Relevant Lines Only ({traceData?.security_relevant_count || 0})
          </button>
          <button
            onClick={() => setSecurityOnly(false)}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              !securityOnly
                ? "bg-blue-600 text-white"
                : "bg-white text-slate-500 border border-slate-200"
            }`}
          >
            All Tokenized Lines ({traceData?.total_lines_analyzed || 0})
          </button>
        </div>
      </div>

      {/* Trace Data Table */}
      {loading ? (
        <LoadingSkeleton type="table" rows={10} />
      ) : traceData ? (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-white text-slate-500 uppercase text-[10px] font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-3 py-2.5 w-16">Line #</th>
                  <th className="px-3 py-2.5">Scrubbed Configuration Line</th>
                  <th className="px-3 py-2.5">Context</th>
                  <th className="px-3 py-2.5">Normalized Canonical Param</th>
                  <th className="px-3 py-2.5">Extracted Value</th>
                  <th className="px-3 py-2.5">Confidence</th>
                  <th className="px-3 py-2.5">Source</th>
                  <th className="px-3 py-2.5 text-right">Matching Rules</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 font-mono text-[11px]">
                {displayedSteps.map((step) => {
                  const isSec = step.is_security_relevant;

                  return (
                    <tr
                      key={step.line_number}
                      className={`hover:bg-slate-50 transition-colors ${
                        step.is_learned_mapping
                          ? "bg-blue-950/20"
                          : !isSec
                          ? "opacity-50 text-slate-500"
                          : ""
                      }`}
                    >
                      <td className="px-3 py-2 text-slate-500">{step.line_number}</td>
                      <td className="px-3 py-2 text-slate-800 max-w-sm truncate" title={step.cleaned_text}>
                        {step.cleaned_text}
                      </td>
                      <td className="px-3 py-2 text-slate-500 truncate max-w-[120px]">
                        {step.section_context || "global"}
                      </td>
                      <td className="px-3 py-2">
                        {isSec ? (
                          <code className="text-slate-700 bg-white px-1 py-0.2 rounded border border-slate-200">
                            {step.normalized_param}
                          </code>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2 font-semibold text-emerald-700">
                        {step.extracted_value !== null ? String(step.extracted_value) : "—"}
                      </td>
                      <td className="px-3 py-2">
                        {isSec ? (
                          <span
                            className={
                              step.confidence >= 90
                                ? "text-emerald-700"
                                : "text-amber-700"
                            }
                          >
                            {step.confidence}%
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {step.is_learned_mapping ? (
                          <span className="text-[10px] font-semibold bg-blue-950 text-blue-700 px-1 py-0.2 rounded border border-blue-800">
                            Learned KB
                          </span>
                        ) : isSec ? (
                          <span className="text-[10px] bg-white text-slate-700 px-1 py-0.2 rounded border border-slate-200">
                            Built-in
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {step.matching_rules_count > 0 ? (
                          <span className="text-[10px] font-semibold bg-emerald-950 text-emerald-700 px-1.5 py-0.2 rounded border border-emerald-200">
                            {step.matching_rules_count} rules
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <EmptyState
          icon={Terminal}
          title="No Trace Data"
          description="Select or upload a network device configuration to view line-by-line pipeline execution."
        />
      )}
    </div>
  );
};
