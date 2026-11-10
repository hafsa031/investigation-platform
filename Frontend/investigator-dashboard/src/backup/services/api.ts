import axios from "axios";

/*
 * =========================================================
 * API CONFIGURATION
 * =========================================================
 */

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

console.log("API BASE URL:", API_BASE_URL);

/*
 * Attach JWT token to every authenticated request.
 */

api.interceptors.request.use((config) => {
  const token =
    localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization =
      `Bearer ${token}`;
  }

  return config;
});

/*
 * =========================================================
 * AUTHENTICATION
 * =========================================================
 */

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export const login = async (
  credentials: LoginRequest
): Promise<LoginResponse> => {
  const response =
    await api.post<LoginResponse>(
      "/auth/login",
      credentials
    );

  return response.data;
};

/*
 * =========================================================
 * CASES
 * =========================================================
 */

export interface BackendCase {
  id: string;
  title: string;
  description: string | null;
  status: string;

  created_at?: string;
  updated_at?: string;
  evidence_count?: number;
}

export interface CreateCaseRequest {
  title: string;
  description?: string;
}

export interface UpdateCaseRequest {
  title?: string;
  description?: string;
  status?: string;
}

/*
 * Get all cases
 */

export const getCases =
  async (): Promise<BackendCase[]> => {
    const response =
      await api.get<BackendCase[]>(
        "/cases"
      );

    return response.data;
  };

/*
 * Get one case
 */

export const getCase = async (
  caseId: string
): Promise<BackendCase> => {
  const response =
    await api.get<BackendCase>(
      `/cases/${caseId}`
    );

  return response.data;
};

/*
 * Create case
 */

export const createCase = async (
  caseData: CreateCaseRequest
): Promise<BackendCase> => {
  const response =
    await api.post<BackendCase>(
      "/cases",
      caseData
    );

  return response.data;
};

/*
 * Update case
 */

export const updateCase = async (
  caseId: string,
  caseData: UpdateCaseRequest
): Promise<BackendCase> => {
  const response =
    await api.patch<BackendCase>(
      `/cases/${caseId}`,
      caseData
    );

  return response.data;
};

/*
 * =========================================================
 * EVIDENCE
 * =========================================================
 */

export interface Evidence {
  id: string;
  evidence_id?: string;

  case_id: string;

  filename: string;

  status: string;

  file_type?: string;

  content_type?: string;

  size?: number;

  size_bytes?: number;

  sha256?: string | null;

  md5?: string | null;

  uploaded_at?: string;

  created_at?: string;

  metadata?: Record<
    string,
    unknown
  >;

  [key: string]: unknown;
}

export interface EvidenceUploadResponse {
  evidence_id: string;
  filename: string;
  case_id: string;
  status: string;

  [key: string]: unknown;
}

/*
 * Upload evidence to a specific case.
 *
 * NEW BACKEND:
 * POST /cases/{case_id}/evidence
 */

export const uploadEvidence = async (
  caseId: string,
  file: File
): Promise<EvidenceUploadResponse> => {
  const formData = new FormData();

  formData.append(
    "file",
    file
  );

  const response =
    await api.post<EvidenceUploadResponse>(
      `/cases/${caseId}/evidence`,
      formData,
      {
        headers: {
          "Content-Type":
            "multipart/form-data",
        },
      }
    );

  return response.data;
};

/*
 * Get all evidence belonging to a case.
 *
 * NEW BACKEND:
 * GET /cases/{case_id}/evidence
 */

export const getCaseEvidence =
  async (
    caseId: string
  ): Promise<Evidence[]> => {
    const response =
      await api.get<Evidence[]>(
        `/cases/${caseId}/evidence`
      );

    return response.data;
  };

/*
 * =========================================================
 * FINDINGS
 * =========================================================
 */

export interface Finding {
  id?: string;

  case_id: string;

  evidence_id?: string;

  title?: string;

  description?: string;

  severity?: string;

  status?: string;

  source?: string;

  created_at?: string;

  [key: string]: unknown;
}

/*
 * Get findings belonging to a case.
 */

export const getCaseFindings =
  async (
    caseId: string
  ): Promise<Finding[]> => {
    const response =
      await api.get<Finding[]>(
        `/cases/${caseId}/findings`
      );

    return response.data;
  };

/*
 * Add a finding to a case.
 */

export interface CreateFindingRequest {
  evidence_id?: string;
  title: string;
  description: string;
  severity?: string;
  source?: string;
}

export const createFinding =
  async (
    caseId: string,
    finding: CreateFindingRequest
  ): Promise<Finding> => {
    const response =
      await api.post<Finding>(
        `/cases/${caseId}/findings`,
        finding
      );

    return response.data;
  };

/*
 * =========================================================
 * CASE IOCs
 * =========================================================
 */

export interface CaseIOC {
  id?: string;

  case_id: string;

  evidence_id?: string;

  type: string;

  value: string;

  normalized_value?: string;

  severity?: string;

  risk_score?: number;

  status?: string;

  mitre_ids?: string[];

  context?: string;

  [key: string]: unknown;
}

/*
 * Get IOCs linked to a case.
 *
 * NEW BACKEND:
 * GET /cases/{case_id}/iocs
 */

export const getCaseIOCs =
  async (
    caseId: string
  ): Promise<CaseIOC[]> => {
    const response =
      await api.get<CaseIOC[]>(
        `/cases/${caseId}/iocs`
      );

    return response.data;
  };

/*
 * =========================================================
 * IOC / SECURITY ANALYSIS
 * =========================================================
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

  text?: string | null;

  source_type: IOCSourceType;

  options?: IOCAnalyzeOptions;
}

export type IOCType =
  | "ip"
  | "domain"
  | "url"
  | "email"
  | "md5"
  | "sha1"
  | "sha256"
  | "sha512";

export type IOCRiskLevel =
  | "low"
  | "medium"
  | "high"
  | "critical";

export type IOCStatus =
  | "new"
  | "triaged"
  | "benign"
  | "malicious";

export interface IOCRecord {
  type: IOCType;

  value_normalized: string;

  raw_found: string;

  line_no?: number;

  context_snippet: string;

  risk_score: number;

  risk_level: IOCRiskLevel;

  reasons: string[];

  mitre_ids: string[];

  status: IOCStatus;

  dedupe_key: string;

  tenant_id?: string | null;

  ai_delta: number;

  ai_justification: string;

  ai_accepted: boolean;

  evidence_id?: string;

  analysis_id?: string;
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

  counts: Record<
    string,
    number
  >;

  iocs: IOCRecord[];
}

/*
 * NEW SECURITY ROUTER PREFIX
 *
 * /ioc/api/v1/iocs
 */

export const analyzeEvidence =
  async (
    request: IOCAnalyzeRequest
  ): Promise<IOCAnalyzeResponse> => {
    const response =
      await api.post<IOCAnalyzeResponse>(
        "/ioc/api/v1/iocs/analyze",
        request
      );

    return response.data;
  };

/*
 * =========================================================
 * IOC LIST
 * =========================================================
 */

export interface IOCListResponse {
  items: IOCRecord[];

  total: number;

  page: number;

  page_size: number;
}

export const getIOCs =
  async (
    page = 1,
    pageSize = 50
  ): Promise<IOCListResponse> => {
    const response =
      await api.get<IOCListResponse>(
        "/ioc/api/v1/iocs/",
        {
          params: {
            page,
            page_size:
              pageSize,
          },
        }
      );

    return response.data;
  };

/*
 * =========================================================
 * IOC HEALTH
 * =========================================================
 */

export const getIOCHealth =
  async (): Promise<{
    status: string;
  }> => {
    const response =
      await api.get<{
        status: string;
      }>(
        "/ioc/api/v1/iocs/health"
      );

    return response.data;
  };

/*
 * =========================================================
 * FORENSIC ANALYSIS
 * =========================================================
 *
 * The forensic engine is currently a Python engine.
 * Keep this connection point until the backend exposes
 * its HTTP endpoint.
 * =========================================================
 */

export interface ForensicHashResult {
  md5?: string;
  sha256?: string;

  [key: string]: unknown;
}

export interface ForensicClassification {
  classification:
    | "Normal"
    | "Suspicious"
    | "Critical"
    | string;

  reasons?: string[];

  [key: string]: unknown;
}

export interface ForensicFinding {
  evidence_id?: string;

  case_id?: string;

  [key: string]: unknown;
}

export interface ForensicAnalysisResponse {
  evidence_id?: string;

  case_id?: string;

  hash?: ForensicHashResult;

  file_identification?: Record<
    string,
    unknown
  >;

  filesystem_metadata?: Record<
    string,
    unknown
  >;

  exif?: Record<
    string,
    unknown
  > | null;

  document_metadata?: Record<
    string,
    unknown
  > | null;

  pe_summary?: Record<
    string,
    unknown
  > | null;

  log_entries?: Array<
    Record<string, unknown>
  >;

  timeline_events?: Array<
    Record<string, unknown>
  >;

  classification?: ForensicClassification;

  forensic_finding?: ForensicFinding;

  backend_send_result?: Record<
    string,
    unknown
  > | null;

  processing_errors?: string[];

  processed_at?: string;
}

export const analyzeEvidenceForensic = async (
  caseId: string,
  evidenceId: string,
  _file: File
): Promise<ForensicAnalysisResponse> => {
  const response = await api.post<ForensicAnalysisResponse>(
    `/cases/${encodeURIComponent(caseId)}/evidence/${encodeURIComponent(evidenceId)}/forensic`
  );

  return response.data;
};

/*
 * =========================================================
 * DEFAULT EXPORT
 * =========================================================
 */

export default api;