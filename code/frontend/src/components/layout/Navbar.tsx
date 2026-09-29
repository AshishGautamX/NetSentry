import React from "react";
import { Shield, UploadCloud, FileCheck, Layers, BookOpen, Database, Sliders, Activity, Cpu } from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingTrainingCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, pendingTrainingCount }) => {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: Activity },
    { id: "upload", label: "Upload Configs", icon: UploadCloud },
    { id: "audits", label: "Audits & Devices", icon: FileCheck },
    { id: "frameworks", label: "Frameworks & Rules", icon: Layers },
    { id: "training", label: "Training Center", icon: Cpu, badge: pendingTrainingCount },
    { id: "knowledge", label: "Knowledge Base", icon: Database },
    { id: "validation", label: "Validation Trace", icon: BookOpen },
    { id: "settings", label: "Settings", icon: Sliders },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Product Title */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab("dashboard")}>
            <div className="h-10 w-10 rounded-lg bg-blue-600 flex items-center justify-center shadow-lg shadow-sm">
              <Shield className="h-6 w-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-white tracking-wide">NetSec Auditor</span>
                <span className="bg-blue-900/60 text-blue-700 text-[10px] font-semibold uppercase px-2 py-0.5 rounded border border-blue-700/50">
                  SIH 2026 PS 26155
                </span>
              </div>
              <p className="text-xs text-slate-500">AI-Driven Multi-Vendor Compliance Engine</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-xs font-medium transition-all ${
                    isActive
                      ? "bg-blue-600/15 text-blue-700 border border-blue-500/30"
                      : "text-slate-700 hover:bg-white/80 hover:text-white"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? "text-blue-700" : "text-slate-500"}`} />
                  <span>{item.label}</span>
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="ml-1 bg-amber-500 text-slate-950 text-[10px] font-bold px-1.5 py-0.2 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Engine Status Banner */}
          <div className="flex items-center space-x-2 border-l border-slate-200 pl-4">
            <div className="flex items-center space-x-1.5 bg-emerald-950/40 border border-emerald-200/40 px-2.5 py-1 rounded text-[11px] text-emerald-700">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Deterministic Core: Online</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
