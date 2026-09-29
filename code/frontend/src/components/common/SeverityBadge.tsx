import React from "react";

export type SeverityType = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO" | "PASS" | "FAIL" | "NOT_EVALUABLE" | "UNKNOWN" | string;

interface SeverityBadgeProps {
  severity: SeverityType;
  size?: "sm" | "md";
  className?: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  severity,
  size = "sm",
  className = "",
}) => {
  const norm = (severity || "").toUpperCase().trim();

  let styles = "bg-white text-slate-700 border-slate-200";

  switch (norm) {
    case "CRITICAL":
      styles = "bg-red-50 text-red-700 border-red-200";
      break;
    case "HIGH":
      styles = "bg-orange-50 text-orange-700 border-orange-200";
      break;
    case "MEDIUM":
      styles = "bg-amber-50 text-amber-700 border-amber-200";
      break;
    case "LOW":
      styles = "bg-blue-50 text-blue-700 border-blue-200";
      break;
    case "INFO":
      styles = "bg-white/80 text-slate-700 border-slate-200";
      break;
    case "PASS":
    case "COMPLIANT":
      styles = "bg-emerald-50 text-emerald-700 border-emerald-200/80";
      break;
    case "FAIL":
    case "NON_COMPLIANT":
      styles = "bg-rose-50 text-rose-700 border-rose-200/80";
      break;
    case "NOT_EVALUABLE":
    case "N/A":
    case "UNCONFIGURED":
      styles = "bg-white/80 text-slate-500 border-slate-200";
      break;
    default:
      styles = "bg-white/80 text-slate-500 border-slate-200";
      break;
  }

  const sizeClass = size === "sm" ? "text-[10px] px-2 py-0.5" : "text-xs px-2.5 py-1";

  return (
    <span
      className={`inline-flex items-center font-mono font-semibold uppercase tracking-wider rounded border ${sizeClass} ${styles} ${className}`}
    >
      {norm === "NOT_EVALUABLE" ? "N/A" : norm}
    </span>
  );
};
