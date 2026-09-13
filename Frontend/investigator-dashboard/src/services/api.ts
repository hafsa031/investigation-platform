import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

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

export const login = async (
  credentials: LoginRequest
): Promise<LoginResponse> => {
  const response = await api.post<LoginResponse>(
    "/auth/login",
    credentials
  );

  return response.data;
};

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

export const uploadEvidence = async (
  caseId: string,
  file: File
): Promise<EvidenceUploadResponse> => {
  const formData = new FormData();

  formData.append("case_id", caseId);
  formData.append("file", file);

  const response = await api.post<EvidenceUploadResponse>(
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

export const getAnalysisStatus = async (
  evidenceId: string
): Promise<AnalysisStatusResponse> => {
  const response = await api.get<AnalysisStatusResponse>(
    `/analysis/status/${evidenceId}`
  );

  return response.data;
};

export default api;