import axios from "axios";
import {
  Configuration,
  Device,
  AuditRun,
  ComplianceRule,
  UnknownCommand,
  LearnedMapping,
  DashboardStats,
  ValidationTraceStep,
  ArchiveUploadResponse,
  SystemSettingsResponse,
  GlobalFinding,
  SecurityImpactAnalysis,
} from "../types";

const API_BASE = "http://localhost:8000/api";

const api = axios.create({
  baseURL: API_BASE,
});

export const apiClient = {
  // Dashboard
  getDashboardStats: async (): Promise<DashboardStats> => {
    const res = await api.get("/dashboard/stats");
    return res.data;
  },

  // Configurations
  uploadConfigurations: async (files: File[]): Promise<Configuration[]> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });
    const res = await api.post("/configurations/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  },

  uploadArchive: async (file: File): Promise<ArchiveUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await api.post("/configurations/upload-archive", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  },

  listConfigurations: async (): Promise<Configuration[]> => {
    const res = await api.get("/configurations");
    return res.data;
  },

  getConfiguration: async (id: number): Promise<Configuration> => {
    const res = await api.get(`/configurations/${id}`);
    return res.data;
  },

  // Audits
  runAudit: async (configId: number): Promise<AuditRun> => {
    const res = await api.post(`/audits/run/${configId}`);
    return res.data;
  },

  listAudits: async (): Promise<AuditRun[]> => {
    const res = await api.get("/audits");
    return res.data;
  },

  getAudit: async (
    auditId: number,
    params?: { framework?: string; status?: string; severity?: string }
  ): Promise<AuditRun> => {
    const res = await api.get(`/audits/${auditId}`, { params });
    return res.data;
  },

  analyzeFindingSecurityImpact: async (auditId: number, findingId: number): Promise<SecurityImpactAnalysis> => {
    const res = await api.post(`/audits/${auditId}/findings/${findingId}/impact`);
    return res.data;
  },

  getLatestAuditForConfig: async (configId: number): Promise<AuditRun> => {
    const res = await api.get(`/audits/config/${configId}/latest`);
    return res.data;
  },

  listAllFindings: async (params?: {
    framework?: string;
    status?: string;
    severity?: string;
    vendor?: string;
    audit_id?: number;
  }): Promise<GlobalFinding[]> => {
    const res = await api.get("/audits/findings/all", { params });
    return res.data;
  },

  // Devices
  listDevices: async (): Promise<Device[]> => {
    const res = await api.get("/devices");
    return res.data;
  },

  getDevice: async (id: number): Promise<Device> => {
    const res = await api.get(`/devices/${id}`);
    return res.data;
  },

  // Compliance
  listFrameworks: async (): Promise<any[]> => {
    const res = await api.get("/compliance/frameworks");
    return res.data;
  },

  listRules: async (params?: { framework?: string; severity?: string }): Promise<ComplianceRule[]> => {
    const res = await api.get("/compliance/rules", { params });
    return res.data;
  },

  // Training Center
  listUnknownCommands: async (status: string = "PENDING"): Promise<UnknownCommand[]> => {
    const res = await api.get("/training/unknown", { params: { status } });
    return res.data;
  },

  createMapping: async (data: {
    vendor: string;
    command_pattern: string;
    normalized_param: string;
    semantic_category: string;
    value_type: string;
    extraction_regex?: string;
    description?: string;
    unknown_id?: number;
  }): Promise<LearnedMapping> => {
    const res = await api.post("/training/mapping", data, {
      params: data.unknown_id ? { unknown_id: data.unknown_id } : undefined,
    });
    return res.data;
  },

  ignoreUnknownCommand: async (id: number): Promise<any> => {
    const res = await api.post(`/training/ignore/${id}`);
    return res.data;
  },

  // Knowledge Base
  listKnowledgeBase: async (): Promise<LearnedMapping[]> => {
    const res = await api.get("/knowledge");
    return res.data;
  },

  toggleKnowledgeMapping: async (id: number): Promise<LearnedMapping> => {
    const res = await api.post(`/knowledge/${id}/toggle`);
    return res.data;
  },

  deleteKnowledgeMapping: async (id: number): Promise<any> => {
    const res = await api.delete(`/knowledge/${id}`);
    return res.data;
  },

  // Reports
  getPdfReportUrl: (auditId: number): string => {
    return `${API_BASE}/reports/${auditId}/pdf`;
  },

  downloadPdfReport: async (auditId: number): Promise<Blob> => {
    const res = await api.get(`/reports/${auditId}/pdf`, { responseType: "blob" });
    return res.data;
  },

  // Validation Trace Mode
  getValidationTrace: async (
    configId: number
  ): Promise<{
    config_id: number;
    filename: string;
    vendor_detected: string;
    total_lines_analyzed: number;
    security_relevant_count: number;
    steps: ValidationTraceStep[];
  }> => {
    const res = await api.get(`/validation/trace/${configId}`);
    return res.data;
  },

  // System Settings
  getSettings: async (): Promise<SystemSettingsResponse> => {
    const res = await api.get("/settings");
    return res.data;
  },

  updateSettings: async (data: {
    ai_provider?: string;
    gemini_api_key?: string;
  }): Promise<{ status: string; message: string; settings: SystemSettingsResponse }> => {
    const res = await api.post("/settings", data);
    return res.data;
  },

  clearGeminiKey: async (): Promise<{ status: string; message: string; settings: SystemSettingsResponse }> => {
    const res = await api.delete("/settings/gemini-key");
    return res.data;
  },
};
