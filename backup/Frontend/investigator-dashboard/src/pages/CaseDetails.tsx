import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import {
  analyzeEvidence, createReport, downloadEvidence, getCase, getCaseEntities,
  getCaseEvidence, getCaseEvents, getCaseFindings, getCaseRelationships,
  getCaseReports, getCaseTimeline, uploadEvidence,
  type BackendCase, type Evidence, type EvidenceAnalysisResponse,
  type EntityRecord, type EventRecord, type Finding, type RelationshipRecord,
  type ReportRecord, type TimelineRecord,
} from "../services/api";

const formatDate = (value?: string) => value ? new Date(value).toLocaleString() : "—";
const pretty = (value: unknown) => value == null ? "—" : typeof value === "object" ? JSON.stringify(value, null, 2) : String(value);

const CaseDetails = () => {
  const { caseId = "" } = useParams();
  const [caseItem, setCaseItem] = useState<BackendCase | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [entities, setEntities] = useState<EntityRecord[]>([]);
  const [relationships, setRelationships] = useState<RelationshipRecord[]>([]);
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [timeline, setTimeline] = useState<TimelineRecord[]>([]);
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [analysis, setAnalysis] = useState<Record<string, EvidenceAnalysisResponse>>({});
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activeTab, setActiveTab] = useState("Evidence");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [analysingId, setAnalysingId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reportTitle, setReportTitle] = useState("");
  const [reportSummary, setReportSummary] = useState("");

  const refresh = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    setError("");
    try {
      const [c, ev, fi, en, rel, evs, tl, reps] = await Promise.all([
        getCase(caseId), getCaseEvidence(caseId), getCaseFindings(caseId),
        getCaseEntities(caseId), getCaseRelationships(caseId), getCaseEvents(caseId),
        getCaseTimeline(caseId), getCaseReports(caseId),
      ]);
      setCaseItem(c); setEvidence(ev); setFindings(fi); setEntities(en);
      setRelationships(rel); setEvents(evs); setTimeline(tl); setReports(reps);
    } catch (e) {
      console.error(e);
      setError("Unable to load this investigation. Check that the backend is running and the account has access to this case.");
    } finally { setLoading(false); }
  }, [caseId]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void refresh(); }, [refresh]);

  const handleUpload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedFile) { setNotice("Choose a file before uploading."); return; }
    setBusy(true); setNotice("");
    try {
      await uploadEvidence(caseId, selectedFile);
      setSelectedFile(null);
      const input = document.getElementById("case-evidence-file") as HTMLInputElement | null;
      if (input) input.value = "";
      setNotice("Evidence uploaded successfully.");
      await refresh();
    } catch (e) { console.error(e); setNotice("Evidence upload failed. Check the file size and backend response."); }
    finally { setBusy(false); }
  };

  const handleAnalysis = async (item: Evidence) => {
    setAnalysingId(item.id); setNotice("");
    try {
      const result = await analyzeEvidence(item.id);
      setAnalysis((current) => ({ ...current, [item.id]: result }));
      setActiveTab("Forensic Analysis");
      setNotice(`Forensic analysis completed for ${item.filename}.`);
      await refresh();
    } catch (e) { console.error(e); setNotice(`Forensic analysis failed for ${item.filename}.`); }
    finally { setAnalysingId(""); }
  };

  const handleCreateReport = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!reportTitle.trim()) return;
    setBusy(true);
    try {
      await createReport({ case_id: caseId, title: reportTitle.trim(), report_type: "investigation_summary", summary: reportSummary.trim() || undefined });
      setReportTitle(""); setReportSummary(""); setNotice("Report record created."); await refresh();
    } catch (e) { console.error(e); setNotice("Could not create the report record."); }
    finally { setBusy(false); }
  };

  if (loading) return <Loading />;
  if (error) return <div className="page"><ErrorMessage message={error} onRetry={refresh} /></div>;
  if (!caseItem) return <div className="page"><ErrorMessage message="Case not found." /></div>;

  const tabs = ["Evidence", "Forensic Analysis", "Findings", "Entities & Relationships", "Timeline", "Reports"];
  const allAnalyses = Object.values(analysis);

  return <div className="page">
    <div className="page-header">
      <div>
        <button className="text-button" onClick={() => window.history.back()}>← Back to cases</button>
        <h2>{caseItem.title}</h2>
        <p>{caseItem.description || "No case description provided."}</p>
      </div>
      <span className={`status-badge ${caseItem.status.toLowerCase().replaceAll(" ", "-")}`}>{caseItem.status}</span>
    </div>

    {notice && <div className="case-notice">{notice}</div>}

    <div className="stats-grid case-detail-stats">
      <div className="stat-card"><span className="stat-label">Evidence files</span><strong>{evidence.length}</strong><span className="stat-description">Uploaded to this case</span></div>
      <div className="stat-card"><span className="stat-label">Forensic findings</span><strong>{findings.length}</strong><span className="stat-description">Extracted from analysis</span></div>
      <div className="stat-card"><span className="stat-label">Entities</span><strong>{entities.length}</strong><span className="stat-description">Recorded investigation entities</span></div>
      <div className="stat-card"><span className="stat-label">Timeline events</span><strong>{timeline.length || events.length}</strong><span className="stat-description">Recorded events</span></div>
    </div>

    <div className="case-tabs" role="tablist">
      {tabs.map((tab) => <button key={tab} className={activeTab === tab ? "case-tab active" : "case-tab"} onClick={() => setActiveTab(tab)}>{tab}</button>)}
    </div>

    {activeTab === "Evidence" && <section className="case-panel">
      <div className="section-header"><div><h3>Evidence Management</h3><p>Upload and manage files associated with this investigation.</p></div></div>
      <form className="evidence-upload-form" onSubmit={handleUpload}>
        <input id="case-evidence-file" type="file" onChange={(e) => setSelectedFile(e.target.files?.[0] || null)} />
        <button className="primary-button" type="submit" disabled={busy || !selectedFile}>{busy ? "Uploading..." : "Upload Evidence"}</button>
      </form>
      <div className="evidence-list">
        {evidence.length === 0 ? <div className="empty-state"><h3>No evidence uploaded</h3><p>Upload a file to begin forensic examination.</p></div> : evidence.map((item) => <div className="evidence-row" key={item.id}>
          <div className="evidence-file-icon">{(item.filename.split(".").pop() || "FILE").slice(0, 3).toUpperCase()}</div>
          <div className="evidence-main"><strong>{item.filename}</strong><span>{item.mime_type || "Unknown file type"} · {item.size_bytes ? `${(item.size_bytes / 1024).toFixed(1)} KB` : "Size unavailable"}</span><span>{formatDate(item.created_at)}</span></div>
          <div className="evidence-actions"><button className="secondary-button" onClick={() => void downloadEvidence(item.id, item.filename)}>Download</button><button className="primary-button" disabled={analysingId === item.id} onClick={() => void handleAnalysis(item)}>{analysingId === item.id ? "Analysing..." : "Analyse"}</button></div>
        </div>)}</div>
    </section>}

    {activeTab === "Forensic Analysis" && <section className="case-panel">
      <div className="section-header"><div><h3>Forensic Analysis</h3><p>Hash calculation, file identification, metadata extraction and log/timestamp analysis.</p></div></div>
      {allAnalyses.length === 0 ? <div className="empty-state"><h3>No analysis loaded in this session</h3><p>Run analysis from the Evidence tab. Previously saved results are available through the backend analysis endpoint.</p></div> : allAnalyses.map((entry) => <div className="analysis-result" key={entry.evidence_id}>
        <h4>Evidence {entry.evidence_id}</h4><p className="analysis-complete">Analysis status: {entry.status}</p>
        {Object.entries(entry.result || {}).filter(([key]) => !["timeline_events", "log_entries"].includes(key)).map(([key, value]) => <div className="analysis-block" key={key}><h5>{key.replaceAll("_", " ")}</h5><pre>{pretty(value)}</pre></div>)}
        {!!(entry.result?.timeline_events as unknown[] | undefined)?.length && <div className="analysis-block"><h5>Extracted timeline events</h5><pre>{pretty(entry.result.timeline_events)}</pre></div>}
        {!!(entry.result?.log_entries as unknown[] | undefined)?.length && <div className="analysis-block"><h5>Parsed log entries</h5><pre>{pretty(entry.result.log_entries)}</pre></div>}
      </div>)}
    </section>}

    {activeTab === "Findings" && <section className="case-panel"><div className="section-header"><div><h3>Forensic Findings</h3><p>Findings generated by the evidence processing engine.</p></div></div>
      {findings.length === 0 ? <div className="empty-state"><h3>No findings available</h3><p>Run forensic analysis on evidence to populate findings.</p></div> : findings.map((finding, index) => <div className="simple-record" key={finding.id || index}><strong>{String(finding.title || finding.finding_type || finding.classification || `Finding ${index + 1}`)}</strong><p>{String(finding.description || finding.summary || "No additional description provided.")}</p><span>{String(finding.classification || finding.severity || "Unclassified")}</span></div>)}</section>} 

    {activeTab === "Entities & Relationships" && <section className="case-panel"><div className="section-header"><div><h3>Entities & Relationships</h3><p>Entities and links recorded for this case.</p></div></div>
      <h4 className="subsection-title">Entities ({entities.length})</h4>
      {entities.length === 0 ? <p className="muted-copy">No entities have been recorded.</p> : entities.map((entity) => <div className="simple-record" key={entity.id}><strong>{entity.name}</strong><p>{entity.entity_type} · {entity.normalized_name || "No normalized name"}</p></div>)}
      <h4 className="subsection-title">Relationships ({relationships.length})</h4>
      {relationships.length === 0 ? <p className="muted-copy">No relationships have been recorded.</p> : relationships.map((relationship) => <div className="simple-record" key={relationship.id}><strong>{relationship.relationship_type}</strong><p>{relationship.source_entity_id} → {relationship.target_entity_id}</p><span>Confidence: {(relationship.confidence * 100).toFixed(0)}%</span></div>)}
    </section>}

    {activeTab === "Timeline" && <section className="case-panel"><div className="section-header"><div><h3>Investigation Timeline</h3><p>Chronological events extracted or recorded for this case.</p></div></div>
      {timeline.length ? timeline.map((item) => <div className="timeline-record" key={item.id}><span className="timeline-dot"/><div><strong>{item.label}</strong><p>{item.notes || "No notes"}</p><span>{formatDate(item.timestamp)} · {item.source_timezone}</span></div></div>) : events.length ? events.map((item) => <div className="timeline-record" key={item.id}><span className="timeline-dot"/><div><strong>{item.event_type}</strong><p>{item.description || "No description"}</p><span>{formatDate(item.occurred_at)}</span></div></div>) : <div className="empty-state"><h3>No timeline events</h3><p>Events will appear here when extracted during forensic analysis.</p></div>}
    </section>}

    {activeTab === "Reports" && <section className="case-panel"><div className="section-header"><div><h3>Investigation Reports</h3><p>Create and view report records for this case. PDF generation is not part of this application.</p></div></div>
      <form className="report-create-form" onSubmit={handleCreateReport}><input value={reportTitle} onChange={(e) => setReportTitle(e.target.value)} placeholder="Report title" required/><textarea value={reportSummary} onChange={(e) => setReportSummary(e.target.value)} placeholder="Report summary (optional)" rows={3}/><button className="primary-button" disabled={busy || !reportTitle.trim()}>{busy ? "Saving..." : "Create Report Record"}</button></form>
      {reports.length === 0 ? <div className="empty-state"><h3>No reports yet</h3><p>Created report records will appear here.</p></div> : reports.map((report) => <div className="simple-record" key={report.id}><strong>{report.title}</strong><p>{report.summary || "No summary provided."}</p><span>{report.report_type} · {report.status} · {formatDate(report.created_at)}</span></div>)}
    </section>}
  </div>;
};

export default CaseDetails;
