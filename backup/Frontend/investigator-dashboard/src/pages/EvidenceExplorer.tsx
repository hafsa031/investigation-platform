import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import { getCases, getCaseEvidence, type BackendCase, type Evidence } from "../services/api";

type EvidenceRow = Evidence & { caseTitle: string; caseStatus: string };

const EvidenceExplorer = () => {
  const navigate = useNavigate();
  const [rows, setRows] = useState<EvidenceRow[]>([]);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      const cases: BackendCase[] = await getCases();
      const groups = await Promise.all(cases.map(async (item) => {
        const evidence = await getCaseEvidence(item.id);
        return evidence.map((file) => ({ ...file, caseTitle: item.title, caseStatus: item.status }));
      }));
      setRows(groups.flat());
    } catch (e) { console.error(e); setError("Unable to load evidence from the backend."); }
    finally { setLoading(false); }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load(); }, []);
  const fileTypes = useMemo(() => Array.from(new Set(rows.map((row) => row.mime_type || row.filename.split(".").pop()?.toUpperCase() || "Unknown"))), [rows]);
  const filtered = useMemo(() => rows.filter((row) => {
    const term = search.toLowerCase();
    const matches = row.filename.toLowerCase().includes(term) || row.id.toLowerCase().includes(term) || row.caseTitle.toLowerCase().includes(term);
    const type = row.mime_type || row.filename.split(".").pop()?.toUpperCase() || "Unknown";
    return matches && (typeFilter === "All" || type === typeFilter);
  }), [rows, search, typeFilter]);

  if (loading) return <div className="page"><Loading /></div>;
  if (error) return <div className="page"><ErrorMessage message={error} onRetry={load} /></div>;

  return <div className="page">
    <div className="page-header"><div><h2>Evidence Explorer</h2><p>Browse evidence uploaded across your investigations.</p></div></div>
    <div className="evidence-controls">
      <div className="search-box"><span>⌕</span><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search evidence or cases..." /></div>
      <select className="status-filter" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}><option value="All">All file types</option>{fileTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select>
    </div>
    <div className="evidence-summary">Showing <strong>{filtered.length}</strong> evidence files</div>
    <div className="explorer-table">
      <div className="explorer-header"><span>Evidence</span><span>Case</span><span>File type</span><span>Size</span><span>Uploaded</span></div>
      {filtered.length === 0 ? <div className="explorer-empty"><div>◈</div><h3>No evidence found</h3><p>Upload evidence from an individual case to see it here.</p></div> : filtered.map((item) => <div className="explorer-row" key={item.id}>
        <div className="explorer-file"><div className="evidence-file-icon">{(item.filename.split(".").pop() || "FILE").slice(0, 3).toUpperCase()}</div><div><strong>{item.filename}</strong><span>{item.id}</span></div></div>
        <button className="case-link" onClick={() => navigate(`/cases/${item.case_id}`)}>{item.caseTitle}</button>
        <span>{item.mime_type || "Unknown"}</span><span>{item.size_bytes ? `${(item.size_bytes / 1024).toFixed(1)} KB` : "—"}</span><span className="uploaded-date">{item.created_at ? new Date(item.created_at).toLocaleDateString() : "—"}</span>
      </div>)}
    </div>
  </div>;
};

export default EvidenceExplorer;
