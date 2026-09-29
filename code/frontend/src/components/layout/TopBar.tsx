import React from "react";
import { ShieldCheck, ChevronRight, RefreshCw, Cpu, Moon, Sun } from "lucide-react";

interface TopBarProps {
  activeTab: string;
  selectedAuditId?: number | null;
  activeEngine?: "deterministic" | "gemini" | "none";
  onRefresh?: () => void;
  refreshing?: boolean;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

const tabTitles: Record<string, string> = {
  dashboard: "Overview",
  upload: "Configurations",
  audits: "Audits",
  audit_detail: "Audit details",
  findings: "Findings",
  validation: "Validation",
  training: "Training",
  knowledge: "Knowledge base",
  frameworks: "Rules & frameworks",
  settings: "Settings",
};

export const TopBar: React.FC<TopBarProps> = ({
  activeTab, selectedAuditId, activeEngine = "deterministic", onRefresh, refreshing = false, theme, onToggleTheme,
}) => {
  const currentTitle = tabTitles[activeTab] || "NetSentry";
  return (
    <header className="app-topbar h-16 border-b px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-2 text-sm min-w-0">
        <span className="text-slate-500 hidden sm:inline">NetSentry</span>
        <ChevronRight className="w-4 h-4 text-slate-700 hidden sm:inline" />
        <span className="text-slate-800 font-semibold truncate">{currentTitle}</span>
        {activeTab === "audit_detail" && selectedAuditId && (
          <>
            <ChevronRight className="w-4 h-4 text-slate-700" />
            <span className="text-blue-600 font-medium">#{selectedAuditId}</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden xl:flex items-center gap-2 text-[11px] text-slate-500">
          <ShieldCheck className="w-4 h-4 text-slate-500" />
          <span>CIS · NIST 800-53 · STIG · ISO 27001</span>
        </div>
        <div className="h-5 w-px bg-slate-200 hidden xl:block" />
        <div className="flex items-center gap-2 text-[11px] text-slate-600">
          <Cpu className={`w-3.5 h-3.5 ${activeEngine === "gemini" ? "text-blue-500" : activeEngine === "deterministic" ? "text-emerald-500" : "text-slate-500"}`} />
          <span className="hidden sm:inline">{activeEngine === "gemini" ? "AI engine" : activeEngine === "deterministic" ? "Core engine" : "Engine"}</span>
          <span className="font-medium text-slate-800">{activeEngine === "gemini" ? "Gemini" : activeEngine === "deterministic" ? "Ready" : "Offline"}</span>
        </div>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={refreshing}
            className="h-8 w-8 inline-flex items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-50 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
          </button>
        )}
        <button
          type="button"
          onClick={onToggleTheme}
          className="h-8 w-8 inline-flex items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-50 transition-colors"
          title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
        >
          {theme === "light" ? <Moon className="w-3.5 h-3.5" /> : <Sun className="w-3.5 h-3.5" />}
        </button>
      </div>
    </header>
  );
};
