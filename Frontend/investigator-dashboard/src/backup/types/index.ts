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

/*
 * =========================================================
 * FORENSIC
 * =========================================================
 */

export interface ForensicHash {
  md5?: string;
  sha256?: string;
  [key: string]: unknown;
}

export interface ForensicFileIdentification {
  extension?: string;
  detected_type?: string;
  mime_type?: string;
  size?: number;
  mismatch?: boolean;
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

export interface ForensicAnalysis {
  evidence_id?: string;
  case_id?: string;

  hash?: ForensicHash;

  file_identification?: ForensicFileIdentification;

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

  processing_errors?: string[];

  processed_at?: string;
}

/*
 * =========================================================
 * SECURITY / IOC
 * =========================================================
 */

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

export interface IOC {
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
 * =========================================================
 * THREAT FINDINGS
 * =========================================================
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
 * =========================================================
 * CORRELATION
 * =========================================================
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
 * =========================================================
 * CASE SECURITY SUMMARY
 * =========================================================
 */

export interface CaseSecuritySummary {
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

/*
 * =========================================================
 * CASE-LEVEL IOC RESPONSE
 * =========================================================
 */

export interface CaseIOCResponse {
  case_id: string;

  total: number;

  items: IOC[];
}

export interface CaseFindingsResponse {
  case_id: string;

  total: number;

  items: ThreatFinding[];
}