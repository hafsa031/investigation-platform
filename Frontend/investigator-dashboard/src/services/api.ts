import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const api = axios.create({ baseURL: API_BASE_URL, timeout: 120000 });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use((response) => response, (error) => {
  if (error.response?.status === 401 && !String(error.config?.url || "").includes("/auth/token")) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    if (window.location.pathname !== "/login") window.location.assign("/login");
  }
  return Promise.reject(error);
});

export const getApiError = (error: unknown, fallback = "Request failed. Please try again.") => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join("; ");
    if (error.message === "Network Error") return "Cannot reach the API. Check that the backend is running and VITE_API_BASE_URL is correct.";
  }
  return fallback;
};

export interface LoginRequest { username: string; password: string }
export interface LoginResponse { access_token: string; token_type: string }
export interface UserProfile { id: string; email: string; full_name?: string | null; role: string }
export const login = async (credentials: LoginRequest): Promise<LoginResponse> => {
  const body = new URLSearchParams(); body.set("username", credentials.username); body.set("password", credentials.password);
  return (await api.post<LoginResponse>("/auth/token", body, { headers: { "Content-Type": "application/x-www-form-urlencoded" } })).data;
};
export const register = async (data: { email: string; password: string; full_name?: string }): Promise<UserProfile> => (await api.post<UserProfile>("/auth/register", data)).data;
export const getCurrentUser = async (): Promise<UserProfile> => (await api.get<UserProfile>("/auth/me")).data;
export const requestPasswordReset = async (email: string): Promise<{ message: string; reset_token?: string }> => (await api.post("/auth/forgot-password", { email })).data;
export const resetPassword = async (token: string, new_password: string): Promise<{ message: string }> => (await api.post("/auth/reset-password", { token, new_password })).data;

export interface BackendCase { id: string; title: string; description: string | null; status: string; created_at?: string; created_by?: string; evidence_count?: number }
export interface CreateCaseRequest { title: string; description?: string }
export interface UpdateCaseRequest { title?: string; description?: string; status?: "Open" | "Under Investigation" | "Closed" }
export const getCases = async (): Promise<BackendCase[]> => (await api.get<BackendCase[]>("/cases/")).data;
export const getCase = async (caseId: string): Promise<BackendCase> => (await api.get<BackendCase>(`/cases/${caseId}`)).data;
export const createCase = async (data: CreateCaseRequest): Promise<BackendCase> => (await api.post<BackendCase>("/cases/", data)).data;
export const updateCase = async (caseId: string, data: UpdateCaseRequest): Promise<BackendCase> => (await api.patch<BackendCase>(`/cases/${caseId}`, data)).data;
export const deleteCase = async (caseId: string): Promise<void> => { await api.delete(`/cases/${caseId}`); };
export const getCaseStats = async (caseId: string): Promise<{ case_id: string; evidence_count: number }> => (await api.get(`/cases/${caseId}/stats`)).data;

export interface Evidence { id: string; case_id: string; uploaded_by?: string; filename: string; storage_key?: string; mime_type?: string | null; size_bytes?: number | null; description?: string | null; acquisition_source?: string | null; created_at?: string }
export interface EvidenceHash { id: string; evidence_id: string; algorithm: string; hash_value: string; created_at?: string }
export interface EvidenceAnalysisResponse { evidence_id: string; case_id: string; status: string; result: Record<string, unknown> }
export const uploadEvidence = async (caseId: string, file: File, description?: string, acquisitionSource?: string): Promise<Evidence> => {
  const form = new FormData(); form.append("file", file);
  if (description?.trim()) form.append("description", description.trim());
  if (acquisitionSource?.trim()) form.append("acquisition_source", acquisitionSource.trim());
  return (await api.post<Evidence>(`/evidence/upload/${caseId}`, form)).data;
};
export const getCaseEvidence = async (caseId: string): Promise<Evidence[]> => (await api.get<Evidence[]>(`/evidence/case/${caseId}`)).data;
export const getEvidence = async (evidenceId: string): Promise<Evidence> => (await api.get<Evidence>(`/evidence/${evidenceId}`)).data;
export const getEvidenceHashes = async (evidenceId: string): Promise<EvidenceHash[]> => (await api.get<EvidenceHash[]>(`/evidence/${evidenceId}/hashes`)).data;
export const analyzeEvidence = async (evidenceId: string): Promise<EvidenceAnalysisResponse> => (await api.post<EvidenceAnalysisResponse>(`/evidence/${evidenceId}/analyze`)).data;
export const getEvidenceAnalysis = async (evidenceId: string): Promise<EvidenceAnalysisResponse> => (await api.get<EvidenceAnalysisResponse>(`/evidence/${evidenceId}/analysis`)).data;
export const downloadEvidence = async (evidenceId: string, filename: string): Promise<void> => {
  const response = await api.get(`/evidence/${evidenceId}/download`, { responseType: "blob" });
  const url = URL.createObjectURL(response.data); const anchor = document.createElement("a");
  anchor.href = url; anchor.download = filename; document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
};

export interface Finding { id?: string; classification?: string; title?: string; description?: string; severity?: string; [key: string]: unknown }
export const getCaseFindings = async (caseId: string): Promise<Finding[]> => (await api.get<Finding[]>(`/cases/${caseId}/findings`)).data;
export interface EntityRecord { id: string; case_id: string; entity_type: string; name: string; normalized_name?: string | null; attributes?: Record<string, unknown> | null; created_at?: string }
export interface RelationshipRecord { id: string; case_id: string; source_entity_id: string; target_entity_id: string; relationship_type: string; description?: string | null; confidence: number; created_at?: string }
export const getCaseEntities = async (caseId: string): Promise<EntityRecord[]> => (await api.get<EntityRecord[]>(`/graph/entities/${caseId}`)).data;
export const createEntity = async (data: { case_id: string; entity_type: string; name: string; normalized_name?: string; attributes?: Record<string, unknown> }): Promise<EntityRecord> => (await api.post<EntityRecord>("/graph/entities", data)).data;
export const getCaseRelationships = async (caseId: string): Promise<RelationshipRecord[]> => (await api.get<RelationshipRecord[]>(`/graph/relationships/${caseId}`)).data;
export const createRelationship = async (data: { case_id: string; source_entity_id: string; target_entity_id: string; relationship_type: string; description?: string; confidence: number }): Promise<RelationshipRecord> => (await api.post<RelationshipRecord>("/graph/relationships", data)).data;

export interface EventRecord { id: string; case_id: string; source_evidence_id?: string | null; event_type: string; description?: string | null; occurred_at: string; source_timezone?: string; attributes?: Record<string, unknown> | null; created_at?: string }
export interface TimelineRecord { id: string; case_id: string; event_id: string; timestamp: string; source_timezone: string; label: string; notes?: string | null; created_at?: string }
export const getCaseEvents = async (caseId: string): Promise<EventRecord[]> => (await api.get<EventRecord[]>(`/timeline/events/${caseId}`)).data;
export const createEvent = async (data: { case_id: string; source_evidence_id?: string; event_type: string; description?: string; occurred_at: string; source_timezone: string; attributes?: Record<string, unknown> }): Promise<EventRecord> => (await api.post<EventRecord>("/timeline/events", data)).data;
export const getCaseTimeline = async (caseId: string): Promise<TimelineRecord[]> => (await api.get<TimelineRecord[]>(`/timeline/items/${caseId}`)).data;
export const createTimelineItem = async (data: { case_id: string; event_id: string; timestamp: string; source_timezone: string; label: string; notes?: string }): Promise<TimelineRecord> => (await api.post<TimelineRecord>("/timeline/timeline-items", data)).data;

export interface ReportRecord { id: string; case_id: string; title: string; report_type: string; summary?: string | null; storage_key?: string | null; status: string; created_at?: string }
export const getCaseReports = async (caseId: string): Promise<ReportRecord[]> => (await api.get<ReportRecord[]>(`/reports/case/${caseId}`)).data;
export const createReport = async (data: { case_id: string; title: string; report_type?: string; summary?: string; storage_key?: string }): Promise<ReportRecord> => (await api.post<ReportRecord>("/reports/", data)).data;
export default api;

export interface AuditLogRecord { id: string; user_id?: string | null; action: string; resource_type: string; resource_id?: string | null; details?: Record<string, unknown> | null; ip_address?: string | null; created_at: string }
export const getMyAuditLogs = async (limit = 100): Promise<AuditLogRecord[]> => (await api.get<AuditLogRecord[]>(`/audit/me?limit=${limit}`)).data;
export const createAuditLog = async (data: { action: string; resource_type: string; resource_id?: string; details?: Record<string, unknown> }): Promise<AuditLogRecord> => (await api.post<AuditLogRecord>("/audit/", data)).data;
export const getServiceHealth = async (): Promise<{ status: string; service: string; version: string }> => (await api.get("/")).data;
export const getDatabaseHealth = async (): Promise<{ status: string; database: string }> => (await api.get("/health/db")).data;
