import React, { useState, useEffect } from "react";
import { Sidebar } from "./components/layout/Sidebar";
import { TopBar } from "./components/layout/TopBar";
import { DashboardPage } from "./pages/DashboardPage";
import { UploadPage } from "./pages/UploadPage";
import { AuditsPage } from "./pages/AuditsPage";
import { AuditDetailPage } from "./pages/AuditDetailPage";
import { FindingsPage } from "./pages/FindingsPage";
import { FrameworksPage } from "./pages/FrameworksPage";
import { TrainingPage } from "./pages/TrainingPage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { ValidationPage } from "./pages/ValidationPage";
import { SettingsPage } from "./pages/SettingsPage";
import { apiClient } from "./api/client";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [selectedAuditId, setSelectedAuditId] = useState<number | null>(null);
  const [validationConfigId, setValidationConfigId] = useState<number | undefined>(undefined);
  const [pendingTrainingCount, setPendingTrainingCount] = useState<number>(0);
  const [activeEngine, setActiveEngine] = useState<"deterministic" | "gemini" | "none">("deterministic");
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window === "undefined") return "light";
    const saved = window.localStorage.getItem("netsentry-theme");
    if (saved === "dark" || saved === "light") return saved;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.style.colorScheme = theme;
    window.localStorage.setItem("netsentry-theme", theme);
  }, [theme]);

  const refreshPendingCount = async () => {
    try {
      const unknowns = await apiClient.listUnknownCommands("PENDING");
      setPendingTrainingCount(unknowns.length);
    } catch {
      // Backend might be initializing
    }
  };

  const refreshEngineStatus = async () => {
    try {
      const res = await apiClient.getSettings();
      if (res && res.ai_provider) {
        if (res.ai_provider === "gemini") {
          setActiveEngine(res.gemini_api_key_configured ? "gemini" : "deterministic");
        } else if (res.ai_provider === "deterministic") {
          setActiveEngine("deterministic");
        } else {
          setActiveEngine("none");
        }
      } else {
        setActiveEngine("none");
      }
    } catch {
      setActiveEngine("none");
    }
  };

  useEffect(() => {
    refreshPendingCount();
    refreshEngineStatus();
    const interval = setInterval(() => {
      refreshPendingCount();
      refreshEngineStatus();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleNavigate = (tab: string, auditId?: number) => {
    if (tab === "audit_detail" && auditId) {
      setSelectedAuditId(auditId);
      setActiveTab("audit_detail");
    } else {
      setActiveTab(tab);
    }
    refreshPendingCount();
    refreshEngineStatus();
  };

  const handleAuditComplete = (auditId: number) => {
    setSelectedAuditId(auditId);
    setActiveTab("audit_detail");
    refreshPendingCount();
    refreshEngineStatus();
  };

  const handleNavigateTrace = (configId: number) => {
    setValidationConfigId(configId);
    setActiveTab("validation");
  };

  return (
    <div className="app-shell h-screen w-screen overflow-hidden bg-slate-50 text-slate-900 flex flex-row font-sans antialiased">
      {/* Enterprise Left Sidebar — Constant, pinned, non-scrolling */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          refreshPendingCount();
          refreshEngineStatus();
        }}
        pendingTrainingCount={pendingTrainingCount}
        activeEngine={activeEngine}
      />

      {/* Main Content Workspace — Only inner main area scrolls */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <TopBar
          activeTab={activeTab}
          selectedAuditId={selectedAuditId}
          activeEngine={activeEngine}
          onRefresh={() => {
            refreshPendingCount();
            refreshEngineStatus();
          }}
          theme={theme}
          onToggleTheme={() => setTheme((current) => current === "light" ? "dark" : "light")}
        />

        <main className="app-main-content flex-1 w-full p-6 overflow-y-auto">
          <div className="max-w-[1600px] w-full mx-auto">
            {activeTab === "dashboard" && <DashboardPage onNavigate={handleNavigate} />}
            {activeTab === "upload" && <UploadPage onAuditComplete={handleAuditComplete} />}
            {activeTab === "audits" && (
              <AuditsPage
                onSelectAudit={(id) => {
                  setSelectedAuditId(id);
                  setActiveTab("audit_detail");
                }}
              />
            )}
            {activeTab === "audit_detail" && selectedAuditId && (
              <AuditDetailPage
                auditId={selectedAuditId}
                onBack={() => setActiveTab("audits")}
                onNavigateTrace={handleNavigateTrace}
              />
            )}
            {activeTab === "findings" && (
              <FindingsPage
                onNavigateAudit={(id) => {
                  setSelectedAuditId(id);
                  setActiveTab("audit_detail");
                }}
              />
            )}
            {activeTab === "frameworks" && <FrameworksPage />}
            {activeTab === "training" && (
              <TrainingPage
                onNavigateKnowledge={() => setActiveTab("knowledge")}
                onNavigateUpload={() => setActiveTab("upload")}
              />
            )}
            {activeTab === "knowledge" && <KnowledgePage />}
            {activeTab === "validation" && (
              <ValidationPage initialConfigId={validationConfigId} />
            )}
            {activeTab === "settings" && <SettingsPage />}
          </div>
        </main>

        <footer className="border-t border-slate-200 bg-white py-3 text-slate-500 text-xs px-6 flex-shrink-0">
          <div className="max-w-[1600px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
            <span>NetSentry · Smart India Hackathon 2026 (Problem Statement 26155)</span>
            <span>Heterogeneous Multi-Vendor Compliance Verification Core &copy; 2026</span>
            <span className="text-slate-500 font-mono text-[10px]">
              Engine: {activeEngine.toUpperCase()}
            </span>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default App;
