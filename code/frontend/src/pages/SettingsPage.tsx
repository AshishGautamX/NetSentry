import React, { useState, useEffect } from "react";
import {
  Sliders,
  Cpu,
  Key,
  Server,
  Check,
  Webhook,
  Copy,
  RefreshCw,
  Trash2,
  AlertCircle,
  Shield,
} from "lucide-react";
import { apiClient } from "../api/client";
import { SystemSettingsResponse } from "../types";

export const SettingsPage: React.FC = () => {
  const [aiProvider, setAiProvider] = useState("deterministic");
  const [geminiKey, setGeminiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("Settings saved successfully.");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [settingsStatus, setSettingsStatus] = useState<SystemSettingsResponse | null>(null);
  const [webhookStatus, setWebhookStatus] = useState<any>(null);
  const [webhookLoading, setWebhookLoading] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  const fetchSettings = async () => {
    try {
      const res = await apiClient.getSettings();
      setSettingsStatus(res);
      setAiProvider(res.ai_provider);
    } catch {
      // Keep defaults
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    try {
      const res = await apiClient.updateSettings({
        ai_provider: aiProvider,
        gemini_api_key: geminiKey.trim() ? geminiKey.trim() : undefined,
      });
      setSettingsStatus(res.settings);
      setAiProvider(res.settings.ai_provider);
      setGeminiKey("");
      setSaveMessage("Settings updated successfully.");
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: any) {
      setSaveError(err.response?.data?.detail || "Failed to update settings.");
    } finally {
      setSaving(false);
    }
  };

  const handleClearKey = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const res = await apiClient.clearGeminiKey();
      setSettingsStatus(res.settings);
      setAiProvider(res.settings.ai_provider);
      setGeminiKey("");
      setSaveMessage("Saved Gemini API key cleared. Reverted to .env or deterministic fallback.");
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: any) {
      setSaveError(err.response?.data?.detail || "Failed to clear key.");
    } finally {
      setSaving(false);
    }
  };

  const fetchWebhookStatus = async () => {
    setWebhookLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/webhooks/status");
      if (res.ok) setWebhookStatus(await res.json());
    } catch {
      setWebhookStatus(null);
    } finally {
      setWebhookLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
    fetchWebhookStatus();
  }, []);

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(null), 1500);
    });
  };

  const vendorStatus = [
    { vendor: "Cisco Systems (IOS / IOS-XE)", status: "Implemented", coverage: "Full parsing & normalization" },
    { vendor: "Juniper Networks (Junos OS)", status: "Implemented", coverage: "Hierarchical braces & set commands" },
    { vendor: "Fortinet (FortiOS)", status: "Implemented", coverage: "Config/edit/set/next/end parsing" },
    { vendor: "Palo Alto Networks (PAN-OS)", status: "Implemented", coverage: "CLI set syntax & management rules" },
    { vendor: "Arista Networks (EOS)", status: "Implemented", coverage: "Management hierarchy & security commands" },
    { vendor: "SONiC (Open Networking)", status: "Implemented", coverage: "config_db.json parsing & normalization" },
    { vendor: "Cumulus Linux", status: "Implemented", coverage: "Debian interfaces & FRRouting parsing" },
    { vendor: "Check Point Gaia", status: "Implemented", coverage: "clish export parsing & normalization" },
    { vendor: "Sophos Firewall (SFOS)", status: "Implemented", coverage: "CLI export parsing & normalization" },
  ];

  const backendBase = "http://localhost:8000";

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Title */}
      <div className="pb-4 border-b border-slate-200">
        <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
          System & Engine Administration
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Configure the semantic evaluation layer, LLM provider credentials, GitOps CI/CD webhooks, and parser coverage.
        </p>
      </div>

      {saved && (
        <div className="p-3 bg-emerald-950/60 border border-emerald-200 rounded-md flex items-center gap-2 text-emerald-700 text-xs font-mono">
          <Check className="w-4 h-4" />
          <span>{saveMessage}</span>
        </div>
      )}

      {saveError && (
        <div className="p-3 bg-red-950/60 border border-red-800 rounded-md flex items-center gap-2 text-red-700 text-xs font-mono">
          <AlertCircle className="w-4 h-4" />
          <span>{saveError}</span>
        </div>
      )}

      {/* Group 1: AI Provider & Semantic Inference */}
      <form onSubmit={handleSave} className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
        <div className="pb-3 border-b border-slate-200">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-slate-500" />
            <span>AI / Semantic Interpretation Layer</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Select between offline deterministic regex tokenization and LLM-assisted unknown syntax interpretation.
          </p>
        </div>

        <div className="space-y-2.5">
          <label className="flex items-start gap-3 p-3 rounded-md border border-slate-200 bg-white cursor-pointer hover:border-slate-300 transition-colors">
            <input
              type="radio"
              name="ai_provider"
              value="deterministic"
              checked={aiProvider === "deterministic"}
              onChange={() => setAiProvider("deterministic")}
              className="mt-0.5 text-blue-600 focus:ring-0"
            />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-800">
                  Deterministic Pattern Core (Default & Offline)
                </span>
                <span className="text-[10px] font-mono font-semibold bg-emerald-950 text-emerald-700 border border-emerald-200 px-1.5 py-0.2 rounded uppercase">
                  Zero Network Exfiltration
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Uses compiled regular expressions, deterministic dictionaries, and the persistent Adaptive Knowledge Base. Runs 100% on-premises without external telemetry.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-3 p-3 rounded-md border border-slate-200 bg-white cursor-pointer hover:border-slate-300 transition-colors">
            <input
              type="radio"
              name="ai_provider"
              value="gemini"
              checked={aiProvider === "gemini"}
              onChange={() => setAiProvider("gemini")}
              className="mt-0.5 text-blue-600 focus:ring-0"
            />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-800">
                  Google Gemini Interactions API (LLM Hypothesis)
                </span>
                <span className="text-[10px] font-mono font-semibold bg-blue-950 text-blue-700 border border-blue-800 px-1.5 py-0.2 rounded uppercase">
                  Adaptive NLP Inference
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Uses Gemini 2.5 Flash for natural-language hypothesis generation when encountering completely unknown vendor command syntax during fleet ingestion.
              </p>
            </div>
          </label>
        </div>

        {aiProvider === "gemini" && (
          <div className="pt-2 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5" />
                <span>Gemini API Key Credential</span>
              </label>

              {settingsStatus?.gemini_api_key_configured && (
                <div className="flex items-center gap-2 font-mono text-[10px]">
                  <span
                    className={`px-1.5 py-0.2 rounded border ${
                      settingsStatus.gemini_api_key_source === "settings"
                        ? "bg-emerald-950 text-emerald-700 border-emerald-200"
                        : "bg-blue-950 text-blue-700 border-blue-800"
                    }`}
                  >
                    Source: {settingsStatus.gemini_api_key_source === "settings" ? "Settings Override" : ".env File"} ({settingsStatus.gemini_api_key_masked})
                  </span>
                  {settingsStatus.gemini_api_key_source === "settings" && (
                    <button
                      type="button"
                      onClick={handleClearKey}
                      disabled={saving}
                      className="text-red-700 hover:text-red-700 flex items-center gap-1 border border-red-900 bg-red-950/40 px-1.5 py-0.2 rounded transition-colors"
                      title="Clear key from settings storage"
                    >
                      <Trash2 className="w-3 h-3" />
                      <span>Clear</span>
                    </button>
                  )}
                </div>
              )}
            </div>

            <div className="relative">
              <input
                type={showKey ? "text" : "password"}
                placeholder={
                  settingsStatus?.gemini_api_key_configured
                    ? `Key configured (${settingsStatus.gemini_api_key_masked}) — enter new key to update`
                    : "AIzaSy..."
                }
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 text-xs text-slate-800 px-3 py-1.5 rounded-md font-mono focus:outline-none focus:border-slate-500"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-2 text-[10px] font-mono text-slate-500 hover:text-white"
              >
                {showKey ? "HIDE" : "SHOW"}
              </button>
            </div>
          </div>
        )}

        <div className="pt-2">
          <button
            type="submit"
            disabled={saving}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-white text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition-colors flex items-center gap-1.5 shadow-sm"
          >
            {saving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
            <span>Save Provider Settings</span>
          </button>
        </div>
      </form>

      {/* Group 2: GitOps CI/CD Webhooks */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <Webhook className="w-4 h-4 text-slate-500" />
              <span>GitOps CI/CD Webhook Endpoints</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Automated compliance auditing on git commit and push events.
            </p>
          </div>
          <button
            onClick={fetchWebhookStatus}
            disabled={webhookLoading}
            className="text-xs text-slate-500 hover:text-white flex items-center gap-1 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${webhookLoading ? "animate-spin" : ""}`} />
            <span>Refresh Status</span>
          </button>
        </div>

        <div className="space-y-2">
          {[
            {
              label: "GitHub Webhook Target",
              key: "github",
              url: `${backendBase}/api/webhooks/github`,
            },
            {
              label: "GitLab Webhook Target",
              key: "gitlab",
              url: `${backendBase}/api/webhooks/gitlab`,
            },
          ].map((ep) => (
            <div
              key={ep.key}
              className="bg-white border border-slate-200 rounded p-2.5 flex items-center justify-between gap-3 text-xs font-mono"
            >
              <div>
                <span className="text-[10px] text-slate-500 uppercase">{ep.label}</span>
                <p className="text-slate-700 mt-0.5">{ep.url}</p>
              </div>
              <button
                onClick={() => copyToClipboard(ep.url, ep.key)}
                className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800 bg-white px-2 py-0.5 rounded transition-colors flex-shrink-0"
              >
                <Copy className="w-3 h-3" />
                <span>{copied === ep.key ? "Copied" : "Copy"}</span>
              </button>
            </div>
          ))}
        </div>

        {webhookStatus && (
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            {[
              { label: "GitHub HMAC Secret", ok: webhookStatus.github_webhook_configured },
              { label: "GitLab Secret Token", ok: webhookStatus.gitlab_webhook_configured },
              { label: "GitHub Private PAT", ok: webhookStatus.github_private_repo_access },
              { label: "GitLab Private Token", ok: webhookStatus.gitlab_private_repo_access },
            ].map((item) => (
              <div
                key={item.label}
                className="bg-white border border-slate-200 rounded p-2 flex items-center gap-2"
              >
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    item.ok ? "bg-emerald-400" : "bg-slate-600"
                  }`}
                />
                <div className="truncate">
                  <span className="text-[10px] text-slate-500">{item.label}</span>
                  <p
                    className={`text-[10px] font-semibold ${
                      item.ok ? "text-emerald-700" : "text-slate-500"
                    }`}
                  >
                    {item.ok ? "ACTIVE" : "DEV_UNSET"}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Group 3: Multi-Vendor Platform Support Status */}
      <div className="bg-white border border-slate-200 rounded-lg p-5">
        <div className="pb-3 mb-3 border-b border-slate-200">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800 flex items-center gap-2">
            <Server className="w-4 h-4 text-slate-500" />
            <span>Multi-Vendor Platform Coverage Matrix</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real implementation status across enterprise network operating system parsers.
          </p>
        </div>

        <div className="space-y-1.5">
          {vendorStatus.map((v) => (
            <div
              key={v.vendor}
              className="flex items-center justify-between p-2.5 bg-white rounded border border-slate-200 text-xs font-mono"
            >
              <div>
                <span className="font-semibold text-slate-800">{v.vendor}</span>
                <p className="text-[10px] text-slate-500">{v.coverage}</p>
              </div>
              <span className="text-[10px] font-semibold bg-emerald-950 text-emerald-700 border border-emerald-200 px-1.5 py-0.2 rounded uppercase">
                {v.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
