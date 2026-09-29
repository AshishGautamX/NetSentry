import React, { useEffect, useState } from "react";
import {
  Cpu,
  CheckCircle2,
  AlertCircle,
  Save,
  BookOpen,
  EyeOff,
  ArrowRight,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import { apiClient } from "../api/client";
import { UnknownCommand } from "../types";
import { LoadingSkeleton } from "../components/common/LoadingSkeleton";
import { EmptyState } from "../components/common/EmptyState";

interface TrainingPageProps {
  onNavigateKnowledge: () => void;
  onNavigateUpload?: () => void;
}

export const TrainingPage: React.FC<TrainingPageProps> = ({
  onNavigateKnowledge,
  onNavigateUpload,
}) => {
  const [unknowns, setUnknowns] = useState<UnknownCommand[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUnknown, setSelectedUnknown] = useState<UnknownCommand | null>(null);

  // Form states
  const [vendor, setVendor] = useState("");
  const [commandPattern, setCommandPattern] = useState("");
  const [normalizedParam, setNormalizedParam] = useState("security.session_timeout");
  const [semanticCategory, setSemanticCategory] = useState("Session Management");
  const [valueType, setValueType] = useState("int");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchUnknowns();
  }, []);

  const fetchUnknowns = async () => {
    try {
      setLoading(true);
      const data = await apiClient.listUnknownCommands("PENDING");
      setUnknowns(data);
      if (data.length > 0 && !selectedUnknown) {
        selectCommandForTraining(data[0]);
      }
    } catch (err) {
      console.error("Failed to load unknown commands", err);
    } finally {
      setLoading(false);
    }
  };

  const selectCommandForTraining = (cmd: UnknownCommand) => {
    setSelectedUnknown(cmd);
    setVendor(cmd.vendor || "generic");
    const raw = cmd.raw_command.trim();
    if (/\d+/.test(raw)) {
      setCommandPattern(raw.replace(/\d+/, "(?P<val>\\d+)"));
    } else {
      setCommandPattern(raw);
    }
    setNormalizedParam(cmd.ai_suggested_param || "security.session_timeout");
    setSemanticCategory(cmd.ai_suggested_category || "Session Management");
    setValueType("int");
    setDescription(`Administrator learned mapping for ${cmd.vendor}: ${cmd.raw_command}`);
    setSaveSuccessMessage(null);
    setErrorMessage(null);
  };

  const handleSaveMapping = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUnknown) return;

    try {
      setSaving(true);
      setErrorMessage(null);
      setSaveSuccessMessage(null);

      await apiClient.createMapping({
        vendor,
        command_pattern: commandPattern,
        normalized_param: normalizedParam,
        semantic_category: semanticCategory,
        value_type: valueType,
        description,
        unknown_id: selectedUnknown.id,
      });

      setSaveSuccessMessage(
        `Mapping persisted to Adaptive Knowledge Base. All subsequent audit runs will normalize this syntax.`
      );

      const updated = await apiClient.listUnknownCommands("PENDING");
      setUnknowns(updated);
      if (updated.length > 0) {
        selectCommandForTraining(updated[0]);
      } else {
        setSelectedUnknown(null);
      }
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || "Failed to persist mapping.");
    } finally {
      setSaving(false);
    }
  };

  const handleIgnore = async (id: number) => {
    try {
      await apiClient.ignoreUnknownCommand(id);
      fetchUnknowns();
    } catch (err) {
      console.error("Failed to ignore command", err);
    }
  };

  const commonParameters = [
    { param: "security.session_timeout", cat: "Session Management", type: "int" },
    { param: "security.password_policy.min_length", cat: "Authentication", type: "int" },
    { param: "security.ssh.version", cat: "Remote Access", type: "int" },
    { param: "security.telnet.enabled", cat: "Remote Access", type: "boolean_false" },
    { param: "security.http_server.enabled", cat: "Web Management", type: "boolean_false" },
    { param: "security.https_server.enabled", cat: "Web Management", type: "boolean_true" },
    { param: "security.banner.login_banner_configured", cat: "Access Warning", type: "boolean_true" },
    { param: "security.logging.syslog_enabled", cat: "Auditing & Logging", type: "boolean_true" },
    { param: "security.ntp.configured", cat: "Time Synchronization", type: "boolean_true" },
    { param: "security.snmp.v3_only", cat: "Network Management", type: "boolean_true" },
    { param: "security.aaa.authentication_login", cat: "Identity & Access", type: "boolean_true" },
  ];

  return (
    <div className="space-y-6">
      {/* Title & Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
            Human-in-the-Loop Adaptive Training Center
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Review unmapped syntax detected across multi-vendor device configurations. Define canonical normalization
            rules and persist them into the enterprise knowledge base.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onNavigateKnowledge}
            className="bg-white hover:bg-white text-slate-700 border border-slate-200 text-xs font-medium px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5"
          >
            <BookOpen className="w-3.5 h-3.5 text-blue-700" />
            <span>Knowledge Base</span>
          </button>
          <button
            onClick={fetchUnknowns}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-white rounded transition-colors"
            title="Refresh queue"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {saveSuccessMessage && (
        <div className="p-3 bg-emerald-950/60 border border-emerald-200 rounded-md flex items-center justify-between gap-3 text-emerald-700 text-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
            <span>{saveSuccessMessage}</span>
          </div>
          {onNavigateUpload && (
            <button
              onClick={onNavigateUpload}
              className="text-xs text-emerald-700 hover:text-white underline flex items-center gap-1"
            >
              <span>Re-run Audit</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>
      )}

      {errorMessage && (
        <div className="p-3 bg-red-950/60 border border-red-800 rounded-md flex items-center gap-2 text-red-700 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Two-Column Workbench Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Unknown Commands Queue */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Pending Unknown Commands ({unknowns.length})
            </h2>
          </div>

          {loading ? (
            <LoadingSkeleton type="line" rows={5} />
          ) : unknowns.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="Queue Clear"
              description="All observed vendor syntax has been normalized or classified. Ingest unfamiliar configs (e.g. unfamiliar_custom.cfg) to trigger new training candidates."
              actionLabel="Ingest Test Config"
              onAction={onNavigateUpload}
            />
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {unknowns.map((cmd) => {
                const isSelected = selectedUnknown?.id === cmd.id;
                return (
                  <div
                    key={cmd.id}
                    onClick={() => selectCommandForTraining(cmd)}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-slate-50 border-blue-500/80"
                        : "bg-white border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-mono uppercase bg-white text-slate-700 px-1.5 py-0.2 rounded border border-slate-200">
                        {cmd.vendor}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        Line {cmd.line_number}
                      </span>
                    </div>

                    <div className="font-mono text-xs text-slate-800 bg-slate-50 p-2 rounded border border-slate-200 truncate" title={cmd.raw_command}>
                      {cmd.raw_command}
                    </div>

                    <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                      <span className="truncate max-w-[200px]">
                        AI: {cmd.ai_suggested_param || "Unclassified"}
                      </span>
                      <span className="text-slate-500">
                        {Math.round(cmd.ai_confidence * 100)}% conf
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Training Workbench */}
        <div className="lg:col-span-7">
          {selectedUnknown ? (
            <form
              onSubmit={handleSaveMapping}
              className="bg-white border border-slate-200 rounded-lg p-5 space-y-4"
            >
              <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                <div>
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
                    Administrator Normalization Workbench
                  </h2>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Define canonical normalization regex for this syntax
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleIgnore(selectedUnknown.id)}
                  className="text-xs bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-800 px-2 py-1 rounded transition-colors flex items-center gap-1"
                >
                  <EyeOff className="w-3 h-3" />
                  <span>Ignore</span>
                </button>
              </div>

              {/* Raw Command */}
              <div>
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                  Target Raw Syntax
                </label>
                <div className="mt-1 bg-slate-50 border border-slate-200 rounded p-2.5 font-mono text-xs text-amber-700/90 truncate">
                  {selectedUnknown.raw_command}
                </div>
              </div>

              {/* Vendor & Category */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                    Vendor / Platform
                  </label>
                  <input
                    type="text"
                    value={vendor}
                    onChange={(e) => setVendor(e.target.value)}
                    required
                    className="w-full mt-1 bg-slate-50 border border-slate-200 text-xs text-slate-800 px-3 py-1.5 rounded focus:outline-none focus:border-slate-500 font-mono"
                  />
                </div>

                <div>
                  <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                    Domain Category
                  </label>
                  <input
                    type="text"
                    value={semanticCategory}
                    onChange={(e) => setSemanticCategory(e.target.value)}
                    required
                    className="w-full mt-1 bg-slate-50 border border-slate-200 text-xs text-slate-800 px-3 py-1.5 rounded focus:outline-none focus:border-slate-500 font-mono"
                  />
                </div>
              </div>

              {/* Normalized Parameter & Value Type */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                    Canonical Baseline Parameter
                  </label>
                  <input
                    type="text"
                    value={normalizedParam}
                    onChange={(e) => setNormalizedParam(e.target.value)}
                    required
                    list="param-suggestions"
                    className="w-full mt-1 bg-slate-50 border border-slate-200 text-xs text-slate-800 px-3 py-1.5 rounded focus:outline-none focus:border-slate-500 font-mono"
                  />
                  <datalist id="param-suggestions">
                    {commonParameters.map((p) => (
                      <option key={p.param} value={p.param} />
                    ))}
                  </datalist>
                </div>

                <div>
                  <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                    Extracted Value Type
                  </label>
                  <select
                    value={valueType}
                    onChange={(e) => setValueType(e.target.value)}
                    className="w-full mt-1 bg-slate-50 border border-slate-200 text-xs text-slate-800 px-3 py-1.5 rounded focus:outline-none focus:border-slate-500 font-mono"
                  >
                    <option value="int">Integer (seconds, version, digits)</option>
                    <option value="boolean_true">Boolean: True (Feature active)</option>
                    <option value="boolean_false">Boolean: False (Feature disabled)</option>
                    <option value="string">String (Arbitrary text)</option>
                  </select>
                </div>
              </div>

              {/* Regex Matching Pattern */}
              <div>
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                  Command Matching Regex Pattern
                </label>
                <input
                  type="text"
                  value={commandPattern}
                  onChange={(e) => setCommandPattern(e.target.value)}
                  required
                  className="w-full mt-1 bg-slate-50 border border-slate-200 text-xs text-emerald-700 px-3 py-1.5 rounded focus:outline-none focus:border-slate-500 font-mono"
                />
                <p className="text-[10px] text-slate-500 mt-1 font-mono">
                  Python regex syntax. Named capture groups like <code>(?P&lt;val&gt;\d+)</code> will be parsed into canonical parameters.
                </p>
              </div>

              {/* Description */}
              <div>
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                  Description & Context
                </label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full mt-1 bg-slate-50 border border-slate-200 text-xs text-slate-800 p-2 rounded focus:outline-none focus:border-slate-500"
                />
              </div>

              {/* Submit */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-white text-white font-medium py-2 px-4 rounded text-xs transition-colors flex items-center justify-center gap-1.5 shadow-sm"
                >
                  {saving ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Persisting to Knowledge Base...</span>
                    </>
                  ) : (
                    <>
                      <Save className="w-3.5 h-3.5" />
                      <span>Save & Persist Learned Mapping</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          ) : (
            <EmptyState
              icon={Cpu}
              title="Select Command to Train"
              description="Choose an unmapped command candidate from the queue on the left to configure semantic normalization."
            />
          )}
        </div>
      </div>
    </div>
  );
};
