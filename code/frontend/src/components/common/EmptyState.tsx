import React from "react";
import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className = "",
}) => {
  return (
    <div
      className={`bg-white border border-slate-200 rounded-lg p-8 text-center flex flex-col items-center justify-center max-w-lg mx-auto my-6 ${className}`}
    >
      {Icon && (
        <div className="w-10 h-10 rounded-md bg-slate-50 flex items-center justify-center text-slate-500 mb-3 border border-slate-200/60">
          <Icon className="w-5 h-5" />
        </div>
      )}
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      <p className="text-xs text-slate-500 mt-1.5 leading-relaxed max-w-sm">
        {description}
      </p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-4 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};
