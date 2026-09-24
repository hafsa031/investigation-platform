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

/*
 * =========================================================
 * Authentication
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
  const response = await api.post<LoginResponse>(
    "/auth/login",
    credentials
  );

  return response.data;
};

/*
 * =========================================================
 * Cases
 * =========================================================
 */

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

export const getCases = async (): Promise<BackendCase[]> => {
  const response = await api.get<BackendCase[]>("/cases/");
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
 * =========================================================
 * Evidence
 * =========================================================
 */

export interface EvidenceUploadResponse {
  evidence_id: string;
  filename: string;
  case_id: string;
  status: string;
}

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
 * =========================================================
 * Evidence Analysis Status
 * =========================================================
 */

export interface AnalysisStatusResponse {
  evidence_id: string;
  hashing_status: string;
  metadata_status: string;
  ai_analysis_status: string;
}

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
 * =========================================================
 * FORENSIC ANALYSIS
 *
 * IMPORTANT:
 * The current Forensic module is a Python engine
 * (Forensic/forensic_engine.py).
 *
 * It does NOT currently expose a FastAPI endpoint in
 * Backend/app.
 *
 * Therefore we keep the frontend connection point here,
 * but do not invent a backend endpoint.
 *
 * Set VITE_FORENSIC_ANALYZE_PATH once Intern-1 exposes it.
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

  exif?: Record<string, unknown> | null;

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

/*
 * Backend connection point for the Forensic engine.
 *
 * Example .env once backend route exists:
 *
 * VITE_FORENSIC_ANALYZE_PATH=/api/v1/forensic/analyze
 *
 * Until that exists, this function intentionally tells us
 * that the backend route has not been connected yet.
 */

export const analyzeEvidenceForensic = async (
  caseId: string,
  evidenceId: string,
  file: File
): Promise<ForensicAnalysisResponse> => {
  const forensicPath =
    import.meta.env.VITE_FORENSIC_ANALYZE_PATH;

  if (!forensicPath) {
    throw new Error(
      "Forensic backend endpoint is not configured. " +
        "Set VITE_FORENSIC_ANALYZE_PATH in the frontend .env file."
    );
  }

  const formData = new FormData();

  formData.append("case_id", caseId);
  formData.append("evidence_id", evidenceId);
  formData.append("file", file);

  const response =
    await api.post<ForensicAnalysisResponse>(
      forensicPath,
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

/*
 * Sprint-2 Threat Finding
 */

export interface ThreatFindingSource {
  case_id: string;
  evidence_id: string;
  source_type: string;
  line_no?: number | null;
}

export interface ThreatFinding {
  ioc: string;
  type: string;
  source: ThreatFindingSource;
  severity: IOCRiskLevel;
  timestamp: string;
  reason: string;
  observation: string;
  risk_score: number;
  mitre_ids: string[];
}

/*
 * Sprint-2 Correlation
 */

export interface SharedIOC {
  ioc: string;
  type: string;
  evidence_count: number;
  max_severity: IOCRiskLevel;
  note: string;
}

export interface ColocatedLink {
  line_no: number;
  iocs: string[];
  note: string;
}

export interface CorrelationTimelineItem {
  line_no?: number | null;
  ioc: string;
  type: string;
  severity: IOCRiskLevel;
}

export interface CaseRollup {
  ioc_count: number;
  worst_severity: IOCRiskLevel;
  by_level: Record<
    IOCRiskLevel,
    number
  >;
  forensic_findings: number;
  forensic_flagged: number;
  hot_iocs: number;
  verdict: string;
}

export interface IOCCorrelations {
  shared_iocs: SharedIOC[];
  colocated_links: ColocatedLink[];
  timeline: CorrelationTimelineItem[];
  rollup: CaseRollup;
}

/*
 * IOC analysis response.
 *
 * findings and correlations are optional because the older
 * backend response did not contain them.
 *
 * This allows the frontend to work with both versions while
 * the backend integration is being completed.
 */

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

  findings?: ThreatFinding[];

  correlations?: IOCCorrelations;
}

/*
 * Run IOC analysis for one evidence file.
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

export const getIOCs = async (
  page = 1,
  pageSize = 50
): Promise<IOCListResponse> => {
  const response =
    await api.get<IOCListResponse>(
      "/api/v1/iocs/",
      {
        params: {
          page,
          page_size: pageSize,
        },
      }
    );

  return response.data;
};

/*
 * =========================================================
 * CASE-LEVEL SECURITY DATA
 *
 * These endpoints are present in the updated Security
 * module and are intended to be mounted behind the main
 * backend/gateway.
 * =========================================================
 */

export interface CaseIOCResponse {
  case_id: string;
  total: number;
  items: IOCRecord[];
}

export const getCaseIOCs = async (
  caseId: string,
  level?: IOCRiskLevel
): Promise<CaseIOCResponse> => {
  const response =
    await api.get<CaseIOCResponse>(
      `/api/v1/iocs/by-case/${caseId}/iocs`,
      {
        params: level ? { level } : undefined,
      }
    );

  return response.data;
};

export interface CaseFindingsResponse {
  case_id: string;
  total: number;
  items: ThreatFinding[];
}

export const getCaseFindings = async (
  caseId: string,
  severity?: IOCRiskLevel
): Promise<CaseFindingsResponse> => {
  const response =
    await api.get<CaseFindingsResponse>(
      `/api/v1/iocs/by-case/${caseId}/findings`,
      {
        params: severity
          ? { severity }
          : undefined,
      }
    );

  return response.data;
};

export interface CaseSummaryResponse {
  case_id: string;
  evidence_count: number;

  ioc_count: number;

  worst_severity: IOCRiskLevel;

  by_level: Record<
    IOCRiskLevel,
    number
  >;

  forensic_findings: number;

  forensic_flagged: number;

  hot_iocs: number;

  verdict: string;
}

export const getCaseSecuritySummary = async (
  caseId: string
): Promise<CaseSummaryResponse> => {
  const response =
    await api.get<CaseSummaryResponse>(
      `/api/v1/iocs/by-case/${caseId}/summary`
    );

  return response.data;
};

/*
 * =========================================================
 * HEALTH
 * =========================================================
 */

export const getIOCHealth = async (): Promise<{
  status: string;
}> => {
  const response =
    await api.get<{ status: string }>(
      "/api/v1/iocs/health"
    );

  return response.data;
};

export default api;