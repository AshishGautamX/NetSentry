import React from "react";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: LucideIcon;
  valueColor?: string;
  badge?: string;
  badgeColor?: string;
  onClick?: () => void;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  icon: Icon,
  valueColor = "text-slate-900",
  badge,
  badgeColor = "bg-white text-slate-700 border-slate-200",
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      } : undefined}
      className={`bg-white border border-slate-200 rounded-lg p-4 transition-colors ${
        onClick ? "cursor-pointer hover:border-slate-300 hover:bg-slate-50" : ""
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
          {label}
        </span>
        {Icon && <Icon className="w-4 h-4 text-slate-500" />}
      </div>

      <div className="mt-2 flex items-baseline gap-2">
        <span className={`text-2xl font-bold font-mono tracking-tight ${valueColor}`}>
          {value}
        </span>
        {badge && (
          <span
            className={`text-[10px] font-mono font-medium px-1.5 py-0.2 rounded border ${badgeColor}`}
          >
            {badge}
          </span>
        )}
      </div>

      {subtext && (
        <p className="text-xs text-slate-500 mt-1.5 truncate">
          {subtext}
        </p>
      )}
    </div>
  );
};
