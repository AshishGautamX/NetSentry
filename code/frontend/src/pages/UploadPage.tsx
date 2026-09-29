import React, { useEffect, useState } from "react";
import {
  UploadCloud,
  Download,
  FileCode,
  CheckCircle2,
  AlertCircle,
  Play,
  Archive,
  ChevronDown,
  ChevronUp,
  PackageOpen,
  Server,
  Layers,
  ShieldCheck,
} from "lucide-react";
import { apiClient } from "../api/client";
import { Configuration, ArchiveMemberResult, ArchiveUploadResponse } from "../types";
import { EmptyState } from "../components/common/EmptyState";

interface UploadPageProps {
  onAuditComplete: (auditId: number) => void;
}

export const UploadPage: React.FC<UploadPageProps> = ({ onAuditComplete }) => {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadedConfigs, setUploadedConfigs] = useState<Configuration[]>([]);
  const [uploading, setUploading] = useState(false);
  const [auditingConfigId, setAuditingConfigId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fleet archive upload state
  const [archivePanelOpen, setArchivePanelOpen] = useState(false);
  const [archiveDragOver, setArchiveDragOver] = useState(false);
  const [archiveFile, setArchiveFile] = useState<File | null>(null);
  const [archiveUploading, setArchiveUploading] = useState(false);
  const [archiveResult, setArchiveResult] = useState<ArchiveUploadResponse | null>(null);
  const [archiveError, setArchiveError] = useState<string | null>(null);
  const [archivePdfConfigId, setArchivePdfConfigId] = useState<number | null>(null);
  const [archiveMeta, setArchiveMeta] = useState<{ name: string; size: number } | null>(() => {
    try {
      const saved = sessionStorage.getItem("netsentry.archive.meta");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // Keep the completed fleet result while the user navigates to a report and back.
  // The File object itself cannot be persisted, so only its display metadata/result
  // are stored. The Clear button below removes this saved fleet session.
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem("netsentry.archive.result");
      if (saved) {
        setArchiveResult(JSON.parse(saved));
        setArchivePanelOpen(true);
      }
    } catch {
      sessionStorage.removeItem("netsentry.archive.result");
    }
  }, []);

  // Pre-baked test samples available in sample_configs
  const sampleConfigs = [
    {
      name: "Cisco Compliant Baseline",
      file: "cisco_compliant.cfg",
      vendor: "Cisco",
      desc: "Hardened Catalyst 9300 (SSHv2, AAA, Banner, Syslog, min-length 14)",
    },
    {
      name: "Cisco Non-Compliant",
      file: "cisco_non_compliant.cfg",
      vendor: "Cisco",
      desc: "Legacy Catalyst 3750 (Telnet, HTTP enabled, SSHv1, default SNMP, weak pw)",
    },
    {
      name: "Juniper Junos SRX Gateway",
      file: "juniper_srx.conf",
      vendor: "Juniper",
      desc: "Authentic Junos hierarchical config (services, SSHv2, login classes)",
    },
    {
      name: "Fortinet FortiGate Firewall",
      file: "fortinet_fortigate.conf",
      vendor: "Fortinet",
      desc: "FortiOS syntax (config system global, admin-ssh-v1 disable, syslog)",
    },
    {
      name: "Palo Alto PAN-OS Firewall",
      file: "paloalto_panos.conf",
      vendor: "Palo Alto",
      desc: "PAN-OS CLI set hierarchy (disable-telnet yes, ssh-version-2 yes, banners)",
    },
    {
      name: "Arista EOS Data Center Switch",
      file: "arista_eos.cfg",
      vendor: "Arista",
      desc: "Arista EOS configuration (management ssh, https api, idle-timeout)",
    },
    {
      name: "SONiC Spine Switch",
      file: "sonic_config_db.json",
      vendor: "SONiC",
      desc: "Open networking config_db.json (SSH policy, syslog, NTP, BGP auth)",
    },
    {
      name: "Cumulus Linux Leaf",
      file: "cumulus_switch.conf",
      vendor: "Cumulus",
      desc: "Debian interfaces plus FRRouting config (VTY timeout, BGP auth, syslog)",
    },
    {
      name: "Check Point Gaia Gateway",
      file: "checkpoint_gaia.conf",
      vendor: "Check Point",
      desc: "Gaia clish export (SSHv2, idle timeout, SNMPv3, password policy)",
    },
    {
      name: "Sophos SFOS Firewall",
      file: "sophos_sfos.conf",
      vendor: "Sophos",
      desc: "SFOS CLI export (SSH hardening, NTP, syslog, SNMPv3)",
    },
    {
      name: "Unfamiliar Vendor (Adaptive Demo)",
      file: "unfamiliar_custom.cfg",
      vendor: "Custom Gateway",
      desc: "Intentionally unmapped syntax for Training Center adaptive verification",
    },
  ];

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const filesArray = Array.from(e.dataTransfer.files);
      setSelectedFiles((prev) => [...prev, ...filesArray]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      setSelectedFiles((prev) => [...prev, ...filesArray]);
    }
  };

  const loadSampleConfig = async (sampleFilename: string) => {
    try {
      setErrorMessage(null);
      const res = await fetch(`/sample_configs/${sampleFilename}`);
      let text = "";
      if (res.ok) {
        text = await res.text();
      } else {
        const sampleRes = await fetch(`http://localhost:8000/sample_configs/${sampleFilename}`);
        if (sampleRes.ok) text = await sampleRes.text();
      }

      const blob = new Blob([text], { type: "text/plain" });
      const file = new File([blob], sampleFilename, { type: "text/plain" });

      setUploading(true);
      const uploaded = await apiClient.uploadConfigurations([file]);
      setUploadedConfigs((prev) => [...uploaded, ...prev]);
    } catch {
      setErrorMessage(
        `Could not load sample '${sampleFilename}'. You can also drag-and-drop the file from sample_configs/`
      );
    } finally {
      setUploading(false);
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;
    try {
      setUploading(true);
      setErrorMessage(null);
      const uploaded = await apiClient.uploadConfigurations(selectedFiles);
      setUploadedConfigs((prev) => [...uploaded, ...prev]);
      setSelectedFiles([]);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || "Upload failed. Verify backend service is running.");
    } finally {
      setUploading(false);
    }
  };

  const handleRunAudit = async (configId: number) => {
    try {
      setAuditingConfigId(configId);
      setErrorMessage(null);
      const auditRes = await apiClient.runAudit(configId);
      onAuditComplete(auditRes.id);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || "Audit execution failed.");
      setAuditingConfigId(null);
    }
  };

  const handleArchiveReport = async (member: ArchiveMemberResult) => {
    if (member.status !== "processed" || !member.config_id) return;

    try {
      setArchiveError(null);
      // Reuse the latest audit when one already exists; otherwise run the
      // same compliance pipeline used by the individual-file workflow.
      let audit: Awaited<ReturnType<typeof apiClient.getLatestAuditForConfig>>;
      try {
        audit = await apiClient.getLatestAuditForConfig(member.config_id);
      } catch (err: any) {
        if (err.response?.status !== 404) throw err;
        audit = await apiClient.runAudit(member.config_id);
      }
      onAuditComplete(audit.id);
    } catch (err: any) {
      setArchiveError(
        err.response?.data?.detail ||
          `Unable to generate the report for ${member.filename}.`
      );
    }
  };

  const handleArchivePdf = async (member: ArchiveMemberResult) => {
    if (member.status !== "processed" || !member.config_id) return;

    try {
      setArchiveError(null);
      setArchivePdfConfigId(member.config_id);

      // A PDF needs an audit. Reuse the latest one when available; otherwise
      // execute the same audit pipeline used by the individual upload flow.
      let audit: Awaited<ReturnType<typeof apiClient.getLatestAuditForConfig>>;
      try {
        audit = await apiClient.getLatestAuditForConfig(member.config_id);
      } catch (err: any) {
        if (err.response?.status !== 404) throw err;
        audit = await apiClient.runAudit(member.config_id);
      }

      // Fetch the PDF as a Blob and trigger a real browser download. This avoids
      // opening another tab and is reliable even when the report was just generated.
      const pdfBlob = await apiClient.downloadPdfReport(audit.id);
      const blobUrl = URL.createObjectURL(pdfBlob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `Compliance_Audit_${member.filename.replace(/[^a-zA-Z0-9._-]/g, "_")}_Audit_${audit.id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(blobUrl);
    } catch (err: any) {
      setArchiveError(
        err.response?.data?.detail ||
          `Unable to download the PDF for ${member.filename}.`
      );
    } finally {
      setArchivePdfConfigId(null);
    }
  };

  const clearArchiveSession = () => {
    setArchiveFile(null);
    setArchiveResult(null);
    setArchiveMeta(null);
    setArchiveError(null);
    try {
      sessionStorage.removeItem("netsentry.archive.result");
      sessionStorage.removeItem("netsentry.archive.meta");
    } catch {
      // Ignore storage failures; local UI state is still cleared.
    }
  };

  const handleArchiveUpload = async () => {
    if (!archiveFile) return;
    try {
      setArchiveUploading(true);
      setArchiveError(null);
      setArchiveResult(null);
      try {
        sessionStorage.removeItem("netsentry.archive.result");
        sessionStorage.removeItem("netsentry.archive.meta");
      } catch {
        // Ignore storage failures; the new upload can still proceed.
      }
      const result = await apiClient.uploadArchive(archiveFile);
      setArchiveResult(result);
      const meta = { name: archiveFile.name, size: archiveFile.size };
      setArchiveMeta(meta);
      try {
        sessionStorage.setItem("netsentry.archive.result", JSON.stringify(result));
        sessionStorage.setItem("netsentry.archive.meta", JSON.stringify(meta));
      } catch {
        // The archive still works for the current mount even if storage is unavailable.
      }
    } catch (err: any) {
      setArchiveError(err.response?.data?.detail || "Archive upload failed. Verify backend is running.");
    } finally {
      setArchiveUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="pb-4 border-b border-slate-200">
        <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
          Configuration Ingestion & Ingestion Management
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Ingest raw device configuration dumps (.cfg, .conf, .json, .txt, .log) across multi-vendor fleets.
          Credentials and private secrets are automatically scrubbed prior to analysis.
        </p>
      </div>

      {errorMessage && (
        <div className="p-3 bg-red-950/60 border border-red-800 rounded-md flex items-center gap-2.5 text-red-700 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Main Upload Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          dragOver
            ? "border-blue-500 bg-blue-950/20"
            : "border-slate-200 bg-white hover:border-slate-300"
        }`}
      >
        <UploadCloud className="w-8 h-8 text-slate-500 mx-auto mb-2" />
        <h3 className="text-xs font-semibold text-slate-800">
          Drop network configuration files here
        </h3>
        <p className="text-[11px] text-slate-500 mt-1 mb-3">
          Supports Cisco IOS/XE, Junos, FortiOS, PAN-OS, EOS, SONiC, Cumulus, Gaia, SFOS, and generic syntax
        </p>

        <label className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium px-3.5 py-1.5 rounded-md cursor-pointer transition-colors inline-block shadow-sm">
          <span>Select Files from Storage</span>
          <input
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
            accept=".cfg,.conf,.json,.txt,.log"
          />
        </label>
      </div>

      {/* Selected Files Ready for Ingestion */}
      {selectedFiles.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-200">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
              Selected Configuration Files ({selectedFiles.length})
            </h3>
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-white text-white text-xs font-medium px-3 py-1.5 rounded transition-colors flex items-center gap-1.5"
            >
              {uploading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Sanitizing & Ingesting...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Ingest & Detect Vendors</span>
                </>
              )}
            </button>
          </div>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {selectedFiles.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between bg-white p-2.5 rounded border border-slate-200 text-xs font-mono"
              >
                <div className="flex items-center gap-2 text-slate-700">
                  <FileCode className="w-3.5 h-3.5 text-blue-700" />
                  <span>{file.name}</span>
                </div>
                <span className="text-slate-500">{(file.size / 1024).toFixed(1)} KB</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fleet Archive Upload (.zip / .tar.gz) */}
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <button
          onClick={() => setArchivePanelOpen((p) => !p)}
          className="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition-colors text-left"
        >
          <div className="flex items-center gap-2.5">
            <Archive className="w-4 h-4 text-slate-500" />
            <div>
              <span className="text-xs font-semibold text-slate-800">Fleet Archive Bulk Ingestion</span>
              <span className="text-[10px] text-slate-500 ml-2">(.zip · .tar.gz)</span>
            </div>
          </div>
          {archivePanelOpen ? (
            <ChevronUp className="w-4 h-4 text-slate-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-500" />
          )}
        </button>

        {archivePanelOpen && (
          <div className="px-5 pb-5 pt-2 border-t border-slate-200 space-y-4">
            <p className="text-xs text-slate-500">
              Upload a compressed archive containing configurations for an entire router/switch fleet. Each file is
              unpacked, sanitized, and stored with automatic vendor classification.
            </p>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setArchiveDragOver(true);
              }}
              onDragLeave={() => setArchiveDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setArchiveDragOver(false);
                const f = e.dataTransfer.files[0];
                if (f) setArchiveFile(f);
              }}
              className={`border-2 border-dashed rounded-lg p-5 text-center transition-colors ${
                archiveDragOver
                  ? "border-blue-500 bg-blue-950/20"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
            >
              <PackageOpen className="w-8 h-8 text-slate-500 mx-auto mb-2" />
              {archiveFile || archiveMeta ? (
                <div>
                  <p className="text-xs font-semibold text-slate-800 font-mono">
                    {(archiveFile || archiveMeta)?.name}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {(((archiveFile || archiveMeta)?.size || 0) / 1024).toFixed(1)} KB — {archiveFile ? "ready to unpack" : "archive ingested"}
                  </p>
                  <button
                    onClick={clearArchiveSession}
                    className="mt-1 text-[11px] text-red-700 hover:text-red-700 underline"
                  >
                    Remove archive
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-xs text-slate-700">Drop compressed archive here or</p>
                  <label className="mt-2 inline-block bg-white hover:bg-slate-100 text-slate-800 border border-slate-200 text-xs font-medium px-3 py-1 rounded cursor-pointer transition-colors">
                    Browse File
                    <input
                      type="file"
                      className="hidden"
                      accept=".zip,.tar.gz,.tgz,.tar.bz2"
                      onChange={(e) => {
                        if (e.target.files?.[0]) setArchiveFile(e.target.files[0]);
                      }}
                    />
                  </label>
                  <p className="text-[10px] text-slate-500 mt-2">Supports .zip · .tar.gz · .tgz — up to 50 MB</p>
                </div>
              )}
            </div>

            {archiveError && (
              <div className="p-3 bg-red-950/60 border border-red-800 rounded text-red-700 text-xs">
                {archiveError}
              </div>
            )}

            {archiveFile && !archiveResult && (
              <button
                onClick={handleArchiveUpload}
                disabled={archiveUploading}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-white text-white text-xs font-semibold py-2 rounded transition-colors"
              >
                {archiveUploading ? "Unpacking & Ingesting Fleet..." : "Extract & Ingest Fleet Archive"}
              </button>
            )}

            {archiveResult && (
              <>
              <div className="space-y-3 pt-2">
                <div className="grid grid-cols-4 gap-2 text-center text-xs">
                  <div className="bg-white border border-slate-200 p-2 rounded">
                    <p className="font-mono font-bold text-slate-800">{archiveResult.total_members_in_archive}</p>
                    <p className="text-[10px] text-slate-500">Total in Archive</p>
                  </div>
                  <div className="bg-white border border-slate-200 p-2 rounded">
                    <p className="font-mono font-bold text-emerald-700">{archiveResult.successfully_processed}</p>
                    <p className="text-[10px] text-slate-500">Processed</p>
                  </div>
                  <div className="bg-white border border-slate-200 p-2 rounded">
                    <p className="font-mono font-bold text-amber-700">{archiveResult.skipped}</p>
                    <p className="text-[10px] text-slate-500">Skipped</p>
                  </div>
                  <div className="bg-white border border-slate-200 p-2 rounded">
                    <p className="font-mono font-bold text-red-700">{archiveResult.errors}</p>
                    <p className="text-[10px] text-slate-500">Errors</p>
                  </div>
                </div>

                <div className="bg-white border border-slate-200 rounded overflow-hidden">
                  <div className="grid grid-cols-12 gap-2 px-3 py-1.5 border-b border-slate-200 text-[10px] font-semibold text-slate-500 uppercase">
                    <span className="col-span-5">Filename</span>
                    <span className="col-span-2">Status</span>
                    <span className="col-span-2">Vendor</span>
                    <span className="col-span-1 text-right">Config ID</span>
                    <span className="col-span-1 text-right">Report</span>
                    <span className="col-span-1 text-right">PDF</span>
                  </div>
                  <div className="divide-y divide-slate-200 max-h-48 overflow-y-auto">
                    {archiveResult.members.map((m: ArchiveMemberResult, i: number) => (
                      <div key={i} className="grid grid-cols-12 gap-2 px-3 py-1.5 text-xs font-mono items-center">
                        <span className="col-span-5 text-slate-700 truncate" title={m.filename}>
                          {m.filename}
                        </span>
                        <span className="col-span-2">
                          {m.status === "processed" && <span className="text-emerald-700">OK</span>}
                          {m.status === "skipped" && <span className="text-amber-700">SKIP</span>}
                          {m.status === "error" && <span className="text-red-700">ERR</span>}
                        </span>
                        <span className="col-span-2 text-slate-500 uppercase text-[10px]">
                          {m.vendor_detected || "—"}
                        </span>
                        <span className="col-span-1 text-right text-blue-700 font-mono text-[10px]">
                          {m.config_id ? `#${m.config_id}` : "—"}
                        </span>
                        <span className="col-span-1 text-right">
                          {m.status === "processed" && m.config_id ? (
                            <button
                              type="button"
                              onClick={() => handleArchiveReport(m)}
                              className="text-blue-700 hover:text-blue-700 underline underline-offset-2 text-[10px] font-sans font-medium"
                            >
                              Reports
                            </button>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </span>
                        <span className="col-span-1 text-right">
                          {m.status === "processed" && m.config_id ? (
                            <button
                              type="button"
                              onClick={() => handleArchivePdf(m)}
                              disabled={archivePdfConfigId === m.config_id}
                              className="text-emerald-700 hover:text-emerald-700 disabled:text-slate-600 underline underline-offset-2 text-[10px] font-sans font-medium"
                            >
                              <span className="inline-flex items-center gap-1">
                                <Download className="w-3 h-3" />
                                {archivePdfConfigId === m.config_id ? "PDF…" : "PDF"}
                              </span>
                            </button>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex justify-end pt-1">
                <button
                  type="button"
                  onClick={clearArchiveSession}
                  className="text-[11px] text-red-700 hover:text-red-700 border border-red-900/60 hover:border-red-700 px-3 py-1 rounded transition-colors"
                >
                  Clear Archive & Upload New
                </button>
              </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Ingested Configurations Ready for Audit */}
      {uploadedConfigs.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-200">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
              Ingested Configurations ({uploadedConfigs.length})
            </h2>
            <span className="text-[11px] text-emerald-700 font-medium flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              Credentials Scrubbed & Hash Verified
            </span>
          </div>

          <div className="space-y-2">
            {uploadedConfigs.map((cfg) => (
              <div
                key={cfg.id}
                className="bg-white border border-slate-200 rounded-md p-3 flex flex-col md:flex-row md:items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-900 font-mono">
                      {cfg.filename}
                    </span>
                    <span className="text-[10px] font-mono uppercase bg-white text-slate-700 px-1.5 py-0.2 rounded border border-slate-200">
                      {cfg.vendor_detected}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {cfg.device_model_detected}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-1 font-mono">
                    <span>OS: {cfg.os_detected}</span>
                    <span>·</span>
                    <span>{cfg.lines_count} lines</span>
                    <span>·</span>
                    <span>{(cfg.file_size / 1024).toFixed(1)} KB</span>
                  </div>
                </div>

                <div>
                  <button
                    onClick={() => handleRunAudit(cfg.id)}
                    disabled={auditingConfigId === cfg.id}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-white text-white text-xs font-medium px-3.5 py-1.5 rounded transition-colors flex items-center gap-1.5 shadow-sm"
                  >
                    {auditingConfigId === cfg.id ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>Evaluating Controls...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-current" />
                        <span>Run Compliance Audit</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Authentic Multi-Vendor Test Corpus */}
      <div className="bg-white border border-slate-200 rounded-lg p-5">
        <div className="pb-3 mb-3 border-b border-slate-200">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
            Authentic Multi-Vendor Test Corpus
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Pre-loaded configuration baselines across primary networking operating systems.
            Click to load and verify multi-vendor evaluation.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {sampleConfigs.map((sample) => (
            <div
              key={sample.file}
              className="bg-white border border-slate-200 hover:border-slate-300 p-3 rounded-md transition-colors flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-xs text-slate-800">{sample.name}</span>
                  <span className="text-[10px] font-mono uppercase bg-white text-slate-500 px-1.5 py-0.2 rounded border border-slate-200">
                    {sample.vendor}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 leading-relaxed">{sample.desc}</p>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-500 truncate max-w-[140px]">
                  {sample.file}
                </span>
                <button
                  onClick={() => loadSampleConfig(sample.file)}
                  disabled={uploading}
                  className="text-xs bg-white hover:bg-slate-100 text-slate-800 border border-slate-200 px-2 py-1 rounded transition-colors flex items-center gap-1"
                >
                  <Play className="w-3 h-3" />
                  <span>Load Sample</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
