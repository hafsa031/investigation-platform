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
  status: "Processing" | "Processed" | "Failed";
  uploaded_at: string;
}