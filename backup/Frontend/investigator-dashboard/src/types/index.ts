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
  case_id: string;
  filename: string;
  mime_type?: string | null;
  size_bytes?: number | null;
  status?: string;
  created_at?: string;
}
