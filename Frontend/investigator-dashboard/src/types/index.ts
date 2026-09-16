// Frontend/src/types/index.ts

export interface Case {
  id: string;
  title: string;
  description: string;
  status: "Open" | "In Progress" | "Closed";
  created_at: string;
  evidence_count: number;
}

export interface Evidence {
  id: string;
  filename: string;
  file_type: string;
  sha256: string;
  status:
    | "Processing"
    | "Processed"
    | "Failed";
  uploaded_at: string;
}

export interface IOC {
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