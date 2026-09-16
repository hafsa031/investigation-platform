// Frontend/src/services/api.ts

import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach JWT token to every authenticated request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface BackendCase {
  id: string;
  title: string;
  description: string | null;
  status: string;
}

export interface CreateCaseRequest {
  title: string;
  description?: string;
}

export interface EvidenceUploadResponse {
  evidence_id: string;
  filename: string;
  case_id: string;
  status: string;
}

export interface AnalysisStatusResponse {
  evidence_id: string;
  hashing_status: string;
  metadata_status: string;
  ai_analysis_status: string;
}

/*
 * IOC Analysis
 */

export type IOCSourceType =
  | "syslog"
  | "auth_log"
  | "firewall"
  | "pcap_text"
  | "email_header"
  | "file_text"
  | "generic";

export interface IOCAnalyzeOptions {
  max_bytes?: number;
  context_window?: number;
  enable_fallback?: boolean;
  use_ai?: boolean;
}

export interface IOCAnalyzeRequest {
  tenant_id: string;
  case_id: string;
  evidence_id: string;
  text: string;
  source_type: IOCSourceType;
  options?: IOCAnalyzeOptions;
}

export interface IOCRecord {
  type:
    | "ip"
    | "domain"
    | "url"
    | "email"
    | "md5"
    | "sha1"
    | "sha256"
    | "sha512";

  value_normalized: string;

  raw_found: string;

  line_no?: number;

  context_snippet: string;

  risk_score: number;

  risk_level:
    | "low"
    | "medium"
    | "high"
    | "critical";

  reasons: string[];

  mitre_ids: string[];

  status:
    | "new"
    | "triaged"
    | "benign"
    | "malicious";

  dedupe_key: string;

  tenant_id?: string | null;

  ai_delta: number;

  ai_justification: string;

  ai_accepted: boolean;
}

export interface IOCAnalyzeResponse {
  analysis_id: string;

  tenant_id: string;

  case_id: string;

  evidence_id: string;

  source_type: string;

  fallback_used: boolean;

  text_bytes: number;

  text_truncated: boolean;

  counts: Record<string, number>;

  iocs: IOCRecord[];
}

/*
 * Authentication
 */

export const login = async (
  credentials: LoginRequest
): Promise<LoginResponse> => {
  const response = await api.post<LoginResponse>(
    "/auth/login",
    credentials
  );

  return response.data;
};

/*
 * Cases
 */

export const getCases = async (): Promise<
  BackendCase[]
> => {
  const response = await api.get<BackendCase[]>(
    "/cases/"
  );

  return response.data;
};

export const createCase = async (
  caseData: CreateCaseRequest
): Promise<BackendCase> => {
  const response = await api.post<BackendCase>(
    "/cases/",
    caseData
  );

  return response.data;
};

/*
 * Evidence
 */

export const uploadEvidence = async (
  caseId: string,
  file: File
): Promise<EvidenceUploadResponse> => {
  const formData = new FormData();

  formData.append("case_id", caseId);
  formData.append("file", file);

  const response =
    await api.post<EvidenceUploadResponse>(
      "/evidence/upload",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );

  return response.data;
};

/*
 * Analysis Status
 */

export const getAnalysisStatus = async (
  evidenceId: string
): Promise<AnalysisStatusResponse> => {
  const response =
    await api.get<AnalysisStatusResponse>(
      `/analysis/status/${evidenceId}`
    );

  return response.data;
};

/*
 * IOC Analysis
 */

export const analyzeEvidence = async (
  request: IOCAnalyzeRequest
): Promise<IOCAnalyzeResponse> => {
  const response =
    await api.post<IOCAnalyzeResponse>(
      "/api/v1/iocs/analyze",
      request
    );

  return response.data;
};

export const getIOCs = async (
  page = 1,
  pageSize = 50
): Promise<IOCAnalyzeResponse[]> => {
  const response = await api.get<
    IOCAnalyzeResponse[]
  >("/api/v1/iocs/", {
    params: {
      page,
      page_size: pageSize,
    },
  });

  return response.data;
};

export default api;