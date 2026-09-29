import React from "react";
import {
  Shield,
  Activity,
  Server,
  ClipboardCheck,
  AlertTriangle,
  Terminal,
  Cpu,
  Database,
  ShieldCheck,
  Sliders,
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingTrainingCount: number;
  activeEngine?: "deterministic" | "gemini" | "none";
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab, setActiveTab, pendingTrainingCount, activeEngine = "deterministic",
}) => {
  const sections: { title: string; items: NavItem[] }[] = [
    { title: "Workspace", items: [
      { id: "dashboard", label: "Overview", icon: Activity },
      { id: "upload", label: "Configurations", icon: Server },
      { id: "audits", label: "Audits", icon: ClipboardCheck },
      { id: "findings", label: "Findings", icon: AlertTriangle },
    ]},
    { title: "Intelligence", items: [
      { id: "validation", label: "Validation", icon: Terminal },
      { id: "training", label: "Training", icon: Cpu, badge: pendingTrainingCount },
      { id: "knowledge", label: "Knowledge base", icon: Database },
      { id: "frameworks", label: "Rules & frameworks", icon: ShieldCheck },
    ]},
    { title: "System", items: [{ id: "settings", label: "Settings", icon: Sliders }] },
  ];

  return (
    <aside className="app-sidebar h-screen sticky top-0 flex flex-col flex-shrink-0 select-none overflow-hidden z-30">
      <div className="brand h-16 px-5 border-b border-slate-200 flex items-center">
        <button
          onClick={() => setActiveTab("dashboard")}
          className="flex items-center gap-3 min-w-0 text-left"
          title="NetSentry"
        >
          <span className="h-9 w-9 rounded-xl bg-slate-50 flex items-center justify-center text-white flex-shrink-0">
            <Shield className="h-[18px] w-[18px]" />
          </span>
          <span className="brand-copy min-w-0">
            <span className="block text-[15px] font-semibold tracking-[-0.01em] text-slate-900">NetSentry</span>
            <span className="block text-[11px] text-slate-500 truncate">Compliance platform</span>
          </span>
        </button>
      </div>

      <div className="flex-1 px-3 py-5 space-y-6 overflow-y-auto">
        {sections.map((section) => (
          <section key={section.title}>
            <div className="nav-section-title px-3 mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
              {section.title}
            </div>
            <nav className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id || (item.id === "audits" && activeTab === "audit_detail");
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    aria-current={isActive ? "page" : undefined}
                    className={`nav-button w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-[13px] font-medium transition-colors ${
                      isActive
                        ? "bg-slate-100 text-slate-900"
                        : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    <span className="flex items-center gap-3 min-w-0">
                      <Icon className={`nav-icon w-[17px] h-[17px] flex-shrink-0 ${isActive ? "text-blue-600" : "text-slate-500"}`} />
                      <span className="nav-label truncate">{item.label}</span>
                    </span>
                    {item.badge !== undefined && item.badge > 0 && (
                      <span className="ml-2 min-w-5 h-5 px-1.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-semibold inline-flex items-center justify-center">
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </section>
        ))}
      </div>

      <div className="engine-status p-4 border-t border-slate-200 text-[11px] text-slate-500 bg-slate-50">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${
            activeEngine === "gemini" ? "bg-blue-500" :
            activeEngine === "deterministic" ? "bg-emerald-500" : "bg-slate-300"
          }`} />
          <span className="engine-copy">
            {activeEngine === "gemini" ? "AI engine connected" :
             activeEngine === "deterministic" ? "Core engine ready" : "Engine unavailable"}
          </span>
        </div>
      </div>
    </aside>
  );
};
