import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import {
  analyzeEvidence, createAuditLog, createEntity, createEvent, createRelationship, createReport, createTimelineItem,
  deleteCase, downloadEvidence, getApiError, getCase, getCaseEntities, getCaseEvidence,
  getCaseEvents, getCaseFindings, getCaseRelationships, getCaseReports, getCaseTimeline,
  getEvidenceAnalysis, getEvidenceHashes, updateCase, uploadEvidence,
  type BackendCase, type Evidence, type EvidenceAnalysisResponse, type EvidenceHash,
  type EntityRecord, type EventRecord, type Finding, type RelationshipRecord, type ReportRecord, type TimelineRecord,
} from "../services/api";

const formatDate = (value?: string) => value ? new Date(value).toLocaleString() : "—";
const pretty = (value: unknown) => value == null ? "—" : typeof value === "object" ? JSON.stringify(value, null, 2) : String(value);
const tabs = ["Evidence", "Forensic Analysis", "Findings", "Entities & Relationships", "Timeline", "Reports"];

const CaseDetails = () => {
  const { caseId = "" } = useParams(); const navigate = useNavigate();
  const [caseItem, setCaseItem] = useState<BackendCase | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]); const [findings, setFindings] = useState<Finding[]>([]);
  const [entities, setEntities] = useState<EntityRecord[]>([]); const [relationships, setRelationships] = useState<RelationshipRecord[]>([]);
  const [events, setEvents] = useState<EventRecord[]>([]); const [timeline, setTimeline] = useState<TimelineRecord[]>([]); const [reports, setReports] = useState<ReportRecord[]>([]);
  const [analysis, setAnalysis] = useState<Record<string, EvidenceAnalysisResponse>>({}); const [hashes, setHashes] = useState<Record<string, EvidenceHash[]>>({});
  const [selectedFile, setSelectedFile] = useState<File | null>(null); const [description, setDescription] = useState(""); const [acquisitionSource, setAcquisitionSource] = useState("");
  const [activeTab, setActiveTab] = useState("Evidence"); const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false); const [analysingId, setAnalysingId] = useState("");
  const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  const [reportTitle, setReportTitle] = useState(""); const [reportSummary, setReportSummary] = useState("");
  const [entityType, setEntityType] = useState("Person"); const [entityName, setEntityName] = useState(""); const [entityAttributes, setEntityAttributes] = useState("");
  const [sourceEntity, setSourceEntity] = useState(""); const [targetEntity, setTargetEntity] = useState(""); const [relationshipType, setRelationshipType] = useState("Associated with"); const [relationshipDescription, setRelationshipDescription] = useState(""); const [confidence, setConfidence] = useState("1");
  const [eventType, setEventType] = useState("Manual observation"); const [eventDescription, setEventDescription] = useState(""); const [eventDate, setEventDate] = useState(""); const [eventEvidence, setEventEvidence] = useState(""); const [eventTimezone, setEventTimezone] = useState("Asia/Kolkata");
  const [editTitle, setEditTitle] = useState(""); const [editDescription, setEditDescription] = useState(""); const [editStatus, setEditStatus] = useState("Open");

  const refresh = useCallback(async () => {
    if (!caseId) return; setLoading(true); setError("");
    try {
      const [c, ev, fi, en, rel, evs, tl, reps] = await Promise.all([
        getCase(caseId), getCaseEvidence(caseId), getCaseFindings(caseId), getCaseEntities(caseId),
        getCaseRelationships(caseId), getCaseEvents(caseId), getCaseTimeline(caseId), getCaseReports(caseId),
      ]);
      setCaseItem(c); setEditTitle(c.title); setEditDescription(c.description || ""); setEditStatus(c.status);
      setEvidence(ev); setFindings(fi); setEntities(en); setRelationships(rel); setEvents(evs); setTimeline(tl); setReports(reps);
      const loaded = await Promise.all(ev.map(async (item) => {
        try { const [result, fileHashes] = await Promise.all([getEvidenceAnalysis(item.id), getEvidenceHashes(item.id)]); return [item.id, result, fileHashes] as const; }
        catch { return [item.id, null, [] as EvidenceHash[]] as const; }
      }));
      const nextAnalysis: Record<string, EvidenceAnalysisResponse> = {}; const nextHashes: Record<string, EvidenceHash[]> = {};
      loaded.forEach(([id, result, fileHashes]) => { if (result) nextAnalysis[id] = result; if (fileHashes.length) nextHashes[id] = fileHashes; });
      setAnalysis(nextAnalysis); setHashes(nextHashes);
    } catch (e) { setError(getApiError(e, "Unable to load this investigation. Check that the backend is running and your account has access.")); }
    finally { setLoading(false); }
  }, [caseId]);
  useEffect(() => { void refresh(); }, [refresh]);

  const handleUpload = async (event: React.FormEvent) => {
    event.preventDefault(); if (!selectedFile) { setNotice("Choose a file before uploading."); return; }
    setBusy(true); setNotice("");
    try { const uploaded = await uploadEvidence(caseId, selectedFile, description, acquisitionSource); try { await createAuditLog({ action: "Evidence uploaded", resource_type: "evidence", resource_id: uploaded.id, details: { filename: uploaded.filename, case_id: caseId } }); } catch (auditError) { console.warn("Audit log could not be saved", auditError); } setSelectedFile(null); setDescription(""); setAcquisitionSource("");
      const input = document.getElementById("case-evidence-file") as HTMLInputElement | null; if (input) input.value = "";
      setNotice("Evidence uploaded successfully."); await refresh();
    } catch (e) { setNotice(getApiError(e, "Evidence upload failed.")); } finally { setBusy(false); }
  };
  const handleAnalysis = async (item: Evidence) => {
    setAnalysingId(item.id); setNotice("");
    try { await analyzeEvidence(item.id); try { await createAuditLog({ action: "Evidence analysed", resource_type: "evidence", resource_id: item.id, details: { filename: item.filename, case_id: caseId } }); } catch (auditError) { console.warn("Audit log could not be saved", auditError); } setActiveTab("Forensic Analysis"); setNotice(`Forensic analysis completed for ${item.filename}.`); await refresh(); }
    catch (e) { setNotice(getApiError(e, `Forensic analysis failed for ${item.filename}.`)); } finally { setAnalysingId(""); }
  };
  const handleSaveCase = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true);
    try { const updated = await updateCase(caseId, { title: editTitle.trim(), description: editDescription.trim() || undefined, status: editStatus as "Open" | "Under Investigation" | "Closed" }); try { await createAuditLog({ action: "Case updated", resource_type: "case", resource_id: caseId, details: { title: updated.title, status: updated.status } }); } catch (auditError) { console.warn("Audit log could not be saved", auditError); } setCaseItem(updated); setNotice("Case details updated."); }
    catch (e) { setNotice(getApiError(e, "Could not update case details.")); } finally { setBusy(false); }
  };
  const handleDeleteCase = async () => {
    if (!window.confirm("Delete this case and its related records? This cannot be undone.")) return;
    setBusy(true); try { try { await createAuditLog({ action: "Case deleted", resource_type: "case", resource_id: caseId }); } catch (auditError) { console.warn("Audit log could not be saved", auditError); } await deleteCase(caseId); navigate("/cases", { replace: true }); } catch (e) { setNotice(getApiError(e, "Could not delete this case.")); } finally { setBusy(false); }
  };
  const handleCreateReport = async (event: React.FormEvent) => {
    event.preventDefault(); if (!reportTitle.trim()) return; setBusy(true);
    try { const report = await createReport({ case_id: caseId, title: reportTitle.trim(), report_type: "investigation_summary", summary: reportSummary.trim() || undefined }); try { await createAuditLog({ action: "Report created", resource_type: "report", resource_id: report.id, details: { case_id: caseId, title: report.title } }); } catch (auditError) { console.warn("Audit log could not be saved", auditError); } setReportTitle(""); setReportSummary(""); setNotice("Report record created."); await refresh(); }
    catch (e) { setNotice(getApiError(e, "Could not create the report record.")); } finally { setBusy(false); }
  };
  const handleCreateEntity = async (event: React.FormEvent) => {
    event.preventDefault(); if (!entityName.trim()) return; setBusy(true);
    try { let attributes: Record<string, unknown> | undefined; if (entityAttributes.trim()) { attributes = JSON.parse(entityAttributes); if (attributes === null || Array.isArray(attributes) || typeof attributes !== "object") throw new Error("Attributes must be a JSON object."); }
      const entity = await createEntity({ case_id: caseId, entity_type: entityType, name: entityName.trim(), normalized_name: entityName.trim().toLowerCase(), attributes }); try { await createAuditLog({ action: "Entity added", resource_type: "entity", resource_id: entity.id, details: { case_id: caseId, name: entity.name } }); } catch (auditError) { console.warn("Audit log could not be saved", auditError); }
      setEntityName(""); setEntityAttributes(""); setNotice("Entity added."); await refresh();
    } catch (e) { setNotice(e instanceof SyntaxError ? "Attributes must be valid JSON." : getApiError(e, e instanceof Error ? e.message : "Could not add entity.")); } finally { setBusy(false); }
  };
  const handleCreateRelationship = async (event: React.FormEvent) => {
    event.preventDefault(); if (!sourceEntity || !targetEntity) return; setBusy(true);
    try { const relationship = await createRelationship({ case_id: caseId, source_entity_id: sourceEntity, target_entity_id: targetEntity, relationship_type: relationshipType.trim(), description: relationshipDescription.trim() || undefined, confidence: Number(confidence) }); try { await createAuditLog({ action: "Relationship added", resource_type: "relationship", resource_id: relationship.id, details: { case_id: caseId, relationship_type: relationship.relationship_type } }); } catch (auditError) { console.warn("Audit log could not be saved", auditError); }
      setRelationshipDescription(""); setNotice("Relationship added."); await refresh();
    } catch (e) { setNotice(getApiError(e, "Could not add relationship.")); } finally { setBusy(false); }
  };
  const handleCreateEvent = async (event: React.FormEvent) => {
    event.preventDefault(); if (!eventDate) return; setBusy(true);
    try { const occurred = new Date(eventDate).toISOString(); const created = await createEvent({ case_id: caseId, source_evidence_id: eventEvidence || undefined, event_type: eventType.trim(), description: eventDescription.trim() || undefined, occurred_at: occurred, source_timezone: eventTimezone });
      await createTimelineItem({ case_id: caseId, event_id: created.id, timestamp: occurred, source_timezone: eventTimezone, label: eventType.trim(), notes: eventDescription.trim() || undefined }); try { await createAuditLog({ action: "Timeline event added", resource_type: "event", resource_id: created.id, details: { case_id: caseId, event_type: eventType.trim() } }); } catch (auditError) { console.warn("Audit log could not be saved", auditError); }
      setEventDescription(""); setEventDate(""); setEventEvidence(""); setNotice("Event added to the investigation timeline."); await refresh();
    } catch (e) { setNotice(getApiError(e, "Could not add event.")); } finally { setBusy(false); }
  };

  if (loading) return <div className="page"><Loading /></div>;
  if (error) return <div className="page"><ErrorMessage message={error} onRetry={refresh} /></div>;
  if (!caseItem) return <div className="page"><ErrorMessage message="Case not found." /></div>;
  const allAnalyses = Object.values(analysis);

  return <div className="page">
    <div className="page-header"><div><button className="text-button" onClick={() => navigate("/cases")}>← Back to cases</button><h2>{caseItem.title}</h2><p>{caseItem.description || "No case description provided."}</p></div><span className={`status-badge ${caseItem.status.toLowerCase().replaceAll(" ", "-")}`}>{caseItem.status}</span></div>
    {notice && <div className="case-notice">{notice}</div>}
    <div className="stats-grid case-detail-stats">
      <div className="stat-card"><span className="stat-label">Evidence files</span><strong>{evidence.length}</strong><span className="stat-description">Uploaded to this case</span></div>
      <div className="stat-card"><span className="stat-label">Analysed files</span><strong>{allAnalyses.length}</strong><span className="stat-description">Forensic analysis completed</span></div>
      <div className="stat-card"><span className="stat-label">Entities</span><strong>{entities.length}</strong><span className="stat-description">Recorded investigation entities</span></div>
      <div className="stat-card"><span className="stat-label">Timeline events</span><strong>{timeline.length || events.length}</strong><span className="stat-description">Recorded events</span></div>
    </div>
    <div className="case-tabs" role="tablist">{tabs.map((tab) => <button key={tab} className={activeTab === tab ? "case-tab active" : "case-tab"} onClick={() => setActiveTab(tab)}>{tab}</button>)}<button className={activeTab === "Case Settings" ? "case-tab active" : "case-tab"} onClick={() => setActiveTab("Case Settings")}>Case Settings</button></div>

    {activeTab === "Evidence" && <section className="case-panel"><div className="section-header"><div><h3>Evidence Management</h3><p>Upload, download and run forensic processing on case files.</p></div></div>
      <form className="report-create-form" onSubmit={handleUpload}><input id="case-evidence-file" type="file" onChange={(e) => setSelectedFile(e.target.files?.[0] || null)} required/><input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Evidence description (optional)"/><input value={acquisitionSource} onChange={(e) => setAcquisitionSource(e.target.value)} placeholder="Acquisition source (optional)"/><button className="primary-button" type="submit" disabled={busy || !selectedFile}>{busy ? "Uploading..." : "Upload Evidence"}</button></form>
      <div className="evidence-list">{evidence.length === 0 ? <div className="empty-state"><h3>No evidence uploaded</h3><p>Upload a file to begin forensic examination.</p></div> : evidence.map((item) => <div className="evidence-row" key={item.id}><div className="evidence-file-icon">{(item.filename.split(".").pop() || "FILE").slice(0, 3).toUpperCase()}</div><div className="evidence-main"><strong>{item.filename}</strong><span>{item.mime_type || "Unknown file type"} · {item.size_bytes ? `${(item.size_bytes / 1024).toFixed(1)} KB` : "Size unavailable"}</span><span>{item.description || "No description"} {item.acquisition_source ? `· Source: ${item.acquisition_source}` : ""}</span><span>{formatDate(item.created_at)}</span></div><div className="evidence-actions"><button className="secondary-button" onClick={() => void downloadEvidence(item.id, item.filename)}>Download</button><button className="primary-button" disabled={analysingId === item.id} onClick={() => void handleAnalysis(item)}>{analysingId === item.id ? "Analysing..." : analysis[item.id] ? "Re-analyse" : "Analyse"}</button></div></div>)}</div>
    </section>}

    {activeTab === "Forensic Analysis" && <section className="case-panel"><div className="section-header"><div><h3>Forensic Analysis</h3><p>Persisted results from the backend forensic engine, including hashes and extracted metadata.</p></div></div>
      {allAnalyses.length === 0 ? <div className="empty-state"><h3>No analysis available</h3><p>Run analysis from the Evidence tab. Completed results are loaded automatically when you reopen this case.</p></div> : allAnalyses.map((entry) => <div className="analysis-result" key={entry.evidence_id}><h4>{evidence.find((item) => item.id === entry.evidence_id)?.filename || entry.evidence_id}</h4><p className="analysis-complete">Analysis status: {entry.status}</p>
        {!!hashes[entry.evidence_id]?.length && <div className="analysis-block"><h5>Evidence hashes</h5>{hashes[entry.evidence_id].map((hash) => <div className="simple-record" key={hash.id}><strong>{hash.algorithm}</strong><p className="hash-value">{hash.hash_value}</p></div>)}</div>}
        {Object.entries(entry.result || {}).map(([key, value]) => <div className="analysis-block" key={key}><h5>{key.replaceAll("_", " ")}</h5><pre>{pretty(value)}</pre></div>)}</div>)}</section>}

    {activeTab === "Findings" && <section className="case-panel"><div className="section-header"><div><h3>Forensic Findings</h3><p>Findings generated by the evidence processing engine.</p></div></div>{findings.length === 0 ? <div className="empty-state"><h3>No findings available</h3><p>Run forensic analysis on evidence to generate findings.</p></div> : findings.map((finding, index) => <div className="simple-record" key={finding.id || index}><strong>{String(finding.title || finding.finding_type || finding.classification || `Finding ${index + 1}`)}</strong><p>{String(finding.description || finding.summary || "No additional description provided.")}</p><span>{String(finding.classification || finding.severity || "Unclassified")}</span></div>)}</section>}

    {activeTab === "Entities & Relationships" && <section className="case-panel"><div className="section-header"><div><h3>Entities & Relationships</h3><p>Build the case graph by recording entities and their connections.</p></div></div>
      <form className="report-create-form" onSubmit={handleCreateEntity}><h4 className="subsection-title">Add entity</h4><input value={entityName} onChange={(e) => setEntityName(e.target.value)} placeholder="Entity name" required/><select value={entityType} onChange={(e) => setEntityType(e.target.value)}><option>Person</option><option>Organization</option><option>Device</option><option>IP Address</option><option>Email Address</option><option>Location</option><option>Account</option><option>File</option><option>Other</option></select><textarea value={entityAttributes} onChange={(e) => setEntityAttributes(e.target.value)} placeholder='Attributes as JSON (optional), e.g. {"role":"suspect"}' rows={3}/><button className="primary-button" disabled={busy || !entityName.trim()}>Add Entity</button></form>
      <h4 className="subsection-title">Entities ({entities.length})</h4>{entities.length === 0 ? <p className="muted-copy">No entities have been recorded.</p> : entities.map((entity) => <div className="simple-record" key={entity.id}><strong>{entity.name}</strong><p>{entity.entity_type} · {entity.normalized_name || "No normalized name"}</p>{entity.attributes && <pre>{pretty(entity.attributes)}</pre>}<span>{entity.id}</span></div>)}
      <form className="report-create-form" onSubmit={handleCreateRelationship}><h4 className="subsection-title">Add relationship</h4><select value={sourceEntity} onChange={(e) => setSourceEntity(e.target.value)} required><option value="">Select source entity</option>{entities.map((entity) => <option key={entity.id} value={entity.id}>{entity.name} ({entity.entity_type})</option>)}</select><select value={targetEntity} onChange={(e) => setTargetEntity(e.target.value)} required><option value="">Select target entity</option>{entities.filter((entity) => entity.id !== sourceEntity).map((entity) => <option key={entity.id} value={entity.id}>{entity.name} ({entity.entity_type})</option>)}</select><input value={relationshipType} onChange={(e) => setRelationshipType(e.target.value)} placeholder="Relationship type" required/><input value={relationshipDescription} onChange={(e) => setRelationshipDescription(e.target.value)} placeholder="Description (optional)"/><label className="form-label">Confidence: {Math.round(Number(confidence) * 100)}%<input type="range" min="0" max="1" step="0.05" value={confidence} onChange={(e) => setConfidence(e.target.value)}/></label><button className="primary-button" disabled={busy || !sourceEntity || !targetEntity || sourceEntity === targetEntity}>Add Relationship</button></form>
      <h4 className="subsection-title">Relationships ({relationships.length})</h4>{relationships.length === 0 ? <p className="muted-copy">No relationships have been recorded.</p> : relationships.map((rel) => <div className="simple-record" key={rel.id}><strong>{rel.relationship_type}</strong><p>{entities.find((entity) => entity.id === rel.source_entity_id)?.name || rel.source_entity_id} → {entities.find((entity) => entity.id === rel.target_entity_id)?.name || rel.target_entity_id}</p><span>{rel.description || "No description"} · Confidence: {(rel.confidence * 100).toFixed(0)}%</span></div>)}
    </section>}

    {activeTab === "Timeline" && <section className="case-panel"><div className="section-header"><div><h3>Investigation Timeline</h3><p>Record a manual event or review events extracted from evidence.</p></div></div>
      <form className="report-create-form" onSubmit={handleCreateEvent}><h4 className="subsection-title">Add timeline event</h4><input value={eventType} onChange={(e) => setEventType(e.target.value)} placeholder="Event type" required/><input type="datetime-local" value={eventDate} onChange={(e) => setEventDate(e.target.value)} required/><textarea value={eventDescription} onChange={(e) => setEventDescription(e.target.value)} placeholder="Event description" rows={3}/><select value={eventEvidence} onChange={(e) => setEventEvidence(e.target.value)}><option value="">No source evidence</option>{evidence.map((item) => <option key={item.id} value={item.id}>{item.filename}</option>)}</select><input value={eventTimezone} onChange={(e) => setEventTimezone(e.target.value)} placeholder="Source timezone (e.g. Asia/Kolkata)"/><button className="primary-button" disabled={busy || !eventDate || !eventType.trim()}>Add Event</button></form>
      {timeline.length ? timeline.map((item) => <div className="timeline-record" key={item.id}><span className="timeline-dot"/><div><strong>{item.label}</strong><p>{item.notes || "No notes"}</p><span>{formatDate(item.timestamp)} · {item.source_timezone}</span></div></div>) : events.length ? events.map((item) => <div className="timeline-record" key={item.id}><span className="timeline-dot"/><div><strong>{item.event_type}</strong><p>{item.description || "No description"}</p><span>{formatDate(item.occurred_at)} · {item.source_timezone}</span></div></div>) : <div className="empty-state"><h3>No timeline events</h3><p>Events will appear here when extracted during forensic analysis or added manually.</p></div>}
    </section>}

    {activeTab === "Reports" && <section className="case-panel"><div className="section-header"><div><h3>Investigation Reports</h3><p>Create and view report records associated with this case.</p></div></div><form className="report-create-form" onSubmit={handleCreateReport}><input value={reportTitle} onChange={(e) => setReportTitle(e.target.value)} placeholder="Report title" required/><textarea value={reportSummary} onChange={(e) => setReportSummary(e.target.value)} placeholder="Report summary (optional)" rows={3}/><button className="primary-button" disabled={busy || !reportTitle.trim()}>{busy ? "Saving..." : "Create Report Record"}</button></form>{reports.length === 0 ? <div className="empty-state"><h3>No reports yet</h3><p>Created report records will appear here.</p></div> : reports.map((report) => <div className="simple-record" key={report.id}><strong>{report.title}</strong><p>{report.summary || "No summary provided."}</p><span>{report.report_type} · {report.status} · {formatDate(report.created_at)}</span></div>)}</section>}

    {activeTab === "Case Settings" && <section className="case-panel"><div className="section-header"><div><h3>Case Settings</h3><p>Update case information or permanently delete this case.</p></div></div><form className="report-create-form" onSubmit={handleSaveCase}><label className="form-label">Case title<input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} required minLength={2}/></label><label className="form-label">Description<textarea value={editDescription} onChange={(e) => setEditDescription(e.target.value)} rows={4}/></label><label className="form-label">Status<select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}><option>Open</option><option>Under Investigation</option><option>Closed</option></select></label><button className="primary-button" disabled={busy || !editTitle.trim()}>Save Changes</button></form><div className="danger-zone"><h4>Delete case</h4><p>This removes the case and related database records. Stored files may need separate cleanup.</p><button className="danger-button" disabled={busy} onClick={() => void handleDeleteCase()}>Delete Case</button></div></section>}
  </div>;
};
export default CaseDetails;
