import React from "react";

interface LoadingSkeletonProps {
  rows?: number;
  type?: "table" | "card" | "line";
  className?: string;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  rows = 4,
  type = "table",
  className = "",
}) => {
  if (type === "card") {
    return (
      <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="bg-white border border-slate-200 rounded-lg p-4 animate-pulse">
            <div className="h-3 bg-slate-200 rounded w-24 mb-3"></div>
            <div className="h-7 bg-slate-200 rounded w-16 mb-2"></div>
            <div className="h-2.5 bg-slate-200 rounded w-32"></div>
          </div>
        ))}
      </div>
    );
  }

  if (type === "line") {
    return (
      <div className={`space-y-2 animate-pulse ${className}`}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-4 bg-slate-200/80 rounded w-full"></div>
        ))}
      </div>
    );
  }

  return (
    <div className={`bg-white border border-slate-200 rounded-lg overflow-hidden ${className}`}>
      <div className="p-3 bg-white border-b border-slate-200 animate-pulse flex gap-4">
        <div className="h-3.5 bg-slate-200 rounded w-28"></div>
        <div className="h-3.5 bg-slate-200 rounded w-20"></div>
        <div className="h-3.5 bg-slate-200 rounded w-32"></div>
      </div>
      <div className="p-4 space-y-3 animate-pulse">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center justify-between py-2 border-b border-slate-200/40 last:border-none">
            <div className="h-3 bg-slate-200 rounded w-1/4"></div>
            <div className="h-3 bg-slate-200 rounded w-1/6"></div>
            <div className="h-3 bg-slate-200 rounded w-1/5"></div>
            <div className="h-3 bg-slate-200 rounded w-12"></div>
          </div>
        ))}
      </div>
    </div>
  );
};
