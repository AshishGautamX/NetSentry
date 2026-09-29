import React, { useState } from "react";
import {
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Database,
  Loader2,
  ShieldAlert,
  Target,
} from "lucide-react";
import { apiClient } from "../../api/client";
import { SecurityImpactAnalysis as SecurityImpactData } from "../../types";

interface SecurityImpactAnalysisProps {
  auditId: number;
  findingId: number;
}

const ListBlock: React.FC<{
  title: string;
  items: string[];
  icon: React.ElementType;
}> = ({ title, items, icon: Icon }) => (
  <div>
    <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
      <Icon className="h-3.5 w-3.5" />
      {title}
    </div>
    <ul className="mt-1.5 space-y-1">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="text-xs text-slate-700 flex gap-2">
          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-slate-400" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  </div>
);

export const SecurityImpactAnalysis: React.FC<SecurityImpactAnalysisProps> = ({
  auditId,
  findingId,
}) => {
  const [analysis, setAnalysis] = useState<SecurityImpactData | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = async () => {
    if (analysis) {
      setOpen((value) => !value);
      return;
    }

    setLoading(true);
    setError(null);
    setOpen(true);
    try {
      const result = await apiClient.analyzeFindingSecurityImpact(auditId, findingId);
      setAnalysis(result);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Security impact analysis could not be generated.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={analyze}
        disabled={loading}
        className="inline-flex items-center gap-1.5 rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1.5 text-[11px] font-medium text-blue-800 transition-colors hover:bg-blue-100 disabled:cursor-wait disabled:opacity-70"
      >
        {loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <ShieldAlert className="h-3.5 w-3.5" />
        )}
        {analysis && !loading ? "Security Impact" : "Analyze Security Impact"}
        {analysis && !loading && (open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
      </button>

      {open && (
        <div className="mt-2 rounded-lg border border-blue-200 bg-blue-50/40 p-3">
          {loading && (
            <div className="flex items-center gap-2 py-4 text-xs text-slate-600">
              <Loader2 className="h-4 w-4 animate-spin text-blue-700" />
              <span>Analyzing the failed control against its recorded evidence...</span>
            </div>
          )}

          {error && !loading && (
            <div className="flex items-start gap-2 text-xs text-red-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {analysis && !loading && (
            <div className="space-y-3">
              <div className="flex flex-col gap-2 border-b border-blue-200 pb-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-blue-800">
                    <BrainCircuit className="h-3.5 w-3.5" />
                    Security Impact Analysis
                  </div>
                  <p className="mt-1 text-xs font-medium text-slate-900">{analysis.finding}</p>
                </div>
                <span className="shrink-0 rounded border border-slate-200 bg-white px-2 py-1 text-[10px] font-mono uppercase text-slate-500">
                  {analysis.confidence} confidence · {analysis.analysis_provider === "gemini" ? "Gemini" : "Deterministic"}
                </span>
              </div>

              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Why it matters</div>
                <p className="mt-1 text-xs leading-relaxed text-slate-700">{analysis.why_it_matters}</p>
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <ListBlock title="Potential Impacts" items={analysis.potential_impacts} icon={AlertTriangle} />
                <ListBlock title="Potential Attack Categories" items={analysis.potential_attack_categories} icon={Target} />
                <ListBlock title="Affected Assets" items={analysis.affected_assets} icon={ShieldAlert} />
                <ListBlock title="Data at Risk" items={analysis.data_at_risk} icon={Database} />
              </div>

              <div className="rounded-md border border-amber-200 bg-amber-50 p-2.5">
                <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-amber-800">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Required Conditions
                </div>
                <ul className="mt-1.5 space-y-1">
                  {analysis.prerequisites.map((item, index) => (
                    <li key={`${item}-${index}`} className="text-xs text-amber-900 flex gap-2">
                      <span>•</span><span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Recommended Action</div>
                <p className="mt-1 text-xs leading-relaxed text-slate-700">{analysis.recommended_action}</p>
              </div>

              <div className="border-t border-blue-200 pt-2 text-[10px] text-slate-500">
                <span className="font-semibold">Evidence basis:</span> {analysis.evidence_basis}
                <span className="ml-2">Analysis describes potential impact; it does not demonstrate that exploitation occurred.</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
