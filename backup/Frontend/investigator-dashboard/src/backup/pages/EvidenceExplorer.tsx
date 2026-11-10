import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Evidence } from "../types";

interface EvidenceWithCase extends Evidence {
  caseId: string;
  caseTitle: string;
}

const mockEvidence: EvidenceWithCase[] = [
  {
    id: "EVD-001",
    filename: "system_logs.txt",
    file_type: "TXT",
    sha256: "a8f4c9d1...72e91",
    status: "Processed",
    uploaded_at: "2026-09-10",
    caseId: "CASE-001",
    caseTitle: "Unauthorized Access Investigation",
  },
  {
    id: "EVD-002",
    filename: "network_capture.pcap",
    file_type: "PCAP",
    sha256: "91c2ab83...41fd2",
    status: "Processed",
    uploaded_at: "2026-09-10",
    caseId: "CASE-001",
    caseTitle: "Unauthorized Access Investigation",
  },
  {
    id: "EVD-003",
    filename: "firewall.log",
    file_type: "LOG",
    sha256: "4e91ac72...82bc1",
    status: "Processed",
    uploaded_at: "2026-09-09",
    caseId: "CASE-002",
    caseTitle: "Network Intrusion Analysis",
  },
  {
    id: "EVD-004",
    filename: "suspicious_email.eml",
    file_type: "EML",
    sha256: "7bc91de4...11fa8",
    status: "Processing",
    uploaded_at: "2026-09-09",
    caseId: "CASE-002",
    caseTitle: "Network Intrusion Analysis",
  },
  {
    id: "EVD-005",
    filename: "disk_image.dd",
    file_type: "DD",
    sha256: "c71fa291...a9e42",
    status: "Processed",
    uploaded_at: "2026-09-07",
    caseId: "CASE-003",
    caseTitle: "Data Exfiltration Investigation",
  },
];

const EvidenceExplorer = () => {
  const navigate = useNavigate();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");

  const fileTypes = useMemo(() => {
    return Array.from(
      new Set(mockEvidence.map((item) => item.file_type))
    );
  }, []);

  const filteredEvidence = useMemo(() => {
    return mockEvidence.filter((item) => {
      const searchValue = search.toLowerCase();

      const matchesSearch =
        item.filename.toLowerCase().includes(searchValue) ||
        item.id.toLowerCase().includes(searchValue) ||
        item.caseTitle.toLowerCase().includes(searchValue);

      const matchesStatus =
        statusFilter === "All" || item.status === statusFilter;

      const matchesType =
        typeFilter === "All" || item.file_type === typeFilter;

      return matchesSearch && matchesStatus && matchesType;
    });
  }, [search, statusFilter, typeFilter]);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Evidence Explorer</h2>
          <p>
            Browse and search evidence across investigations.
          </p>
        </div>
      </div>

      <div className="evidence-controls">
        <div className="search-box">
          <span>⌕</span>

          <input
            type="text"
            placeholder="Search evidence or cases..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <select
          className="status-filter"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
        >
          <option value="All">All statuses</option>
          <option value="Processed">Processed</option>
          <option value="Processing">Processing</option>
          <option value="Failed">Failed</option>
        </select>

        <select
          className="status-filter"
          value={typeFilter}
          onChange={(event) => setTypeFilter(event.target.value)}
        >
          <option value="All">All file types</option>

          {fileTypes.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </div>

      <div className="evidence-summary">
        <span>
          Showing <strong>{filteredEvidence.length}</strong> evidence files
        </span>
      </div>

      <div className="explorer-table">
        <div className="explorer-header">
          <span>Evidence</span>
          <span>Case</span>
          <span>SHA-256</span>
          <span>Status</span>
          <span>Uploaded</span>
        </div>

        {filteredEvidence.length === 0 ? (
          <div className="explorer-empty">
            <div>◈</div>
            <h3>No evidence found</h3>
            <p>Try changing your search or filters.</p>
          </div>
        ) : (
          filteredEvidence.map((item) => (
            <div className="explorer-row" key={item.id}>
              <div className="explorer-file">
                <div className="evidence-file-icon">
                  {item.file_type.slice(0, 3)}
                </div>

                <div>
                  <strong>{item.filename}</strong>
                  <span>{item.id}</span>
                </div>
              </div>

              <button
                className="case-link"
                onClick={() =>
                  navigate(`/cases/${item.caseId}`)
                }
              >
                {item.caseTitle}
              </button>

              <code>{item.sha256}</code>

              <span
                className={`evidence-status ${item.status.toLowerCase()}`}
              >
                {item.status}
              </span>

              <span className="uploaded-date">
                {item.uploaded_at}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default EvidenceExplorer;