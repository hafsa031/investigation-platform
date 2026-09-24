import {
  useEffect,
  useState,
} from "react";
import { useParams } from "react-router-dom";

import type {
  Case,
  Evidence,
  ForensicAnalysis,
} from "../types";

import {
  getCases,
  uploadEvidence,
  getAnalysisStatus,
  analyzeEvidence,
  analyzeEvidenceForensic,
  getCaseIOCs,
  getCaseFindings,
  getCaseSecuritySummary,
  type AnalysisStatusResponse,
  type IOCAnalyzeResponse,
  type CaseIOCResponse,
  type CaseFindingsResponse,
} from "../services/api";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

const TEXT_FILE_EXTENSIONS = [
  "txt",
  "log",
  "eml",
  "csv",
  "json",
  "md",
  "xml",
  "yaml",
  "yml",
  "html",
  "htm",
  "conf",
  "cfg",
  "ini",
];

const formatValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return "—";
  }

  if (typeof value === "object") {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }

  return String(value);
};

const DetailGrid = ({
  data,
}: {
  data?: Record<string, unknown> | null;
}) => {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="empty-state">
        <strong>No data available</strong>
        <p>
          This information has not been returned yet.
        </p>
      </div>
    );
  }

  return (
    <div className="analysis-status-grid">
      {Object.entries(data).map(([key, value]) => (
        <div
          className="analysis-status-card"
          key={key}
        >
          <span>
            {key.replace(/_/g, " ")}
          </span>

          <strong className="detail-value">
            {formatValue(value)}
          </strong>
        </div>
      ))}
    </div>
  );
};

const CaseDetails = () => {
  const { caseId } = useParams();

  const [selectedCase, setSelectedCase] =
    useState<Case | null>(null);

  const [evidence, setEvidence] =
    useState<Evidence[]>([]);

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [uploading, setUploading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [uploadError, setUploadError] =
    useState("");

  const [analysisStatus, setAnalysisStatus] =
    useState<AnalysisStatusResponse | null>(null);

  /*
   * =========================================================
   * IOC ANALYSIS
   * =========================================================
   */

  const [iocAnalysis, setIocAnalysis] =
    useState<IOCAnalyzeResponse | null>(null);

  const [analyzingIOC, setAnalyzingIOC] =
    useState(false);

  const [iocError, setIocError] =
    useState("");

  /*
   * =========================================================
   * FORENSIC ANALYSIS
   * =========================================================
   */

  const [forensicAnalysis, setForensicAnalysis] =
    useState<ForensicAnalysis | null>(null);

  const [analyzingForensic, setAnalyzingForensic] =
    useState(false);

  const [forensicError, setForensicError] =
    useState("");

  /*
   * =========================================================
   * CASE-LEVEL SECURITY
   * =========================================================
   */

  const [caseIOCs, setCaseIOCs] =
    useState<CaseIOCResponse | null>(null);

  const [caseFindings, setCaseFindings] =
    useState<CaseFindingsResponse | null>(null);

  const [securitySummary, setSecuritySummary] =
    useState<Awaited<
      ReturnType<typeof getCaseSecuritySummary>
    > | null>(null);

  const [securityLoading, setSecurityLoading] =
    useState(false);

  const [securityError, setSecurityError] =
    useState("");

  /*
   * =========================================================
   * LOAD CASE
   * =========================================================
   */

  const fetchCase = async () => {
    try {
      setLoading(true);
      setError("");

      const cases = await getCases();

      const foundCase = cases.find(
        (item) =>
          String(item.id) ===
          String(caseId)
      );

      if (!foundCase) {
        setError("Case not found.");
        return;
      }

      setSelectedCase({
        id: String(foundCase.id),

        title: foundCase.title,

        description:
          foundCase.description ||
          "No description provided.",

        status:
          foundCase.status === "Active"
            ? "Open"
            : foundCase.status === "Closed"
              ? "Closed"
              : "In Progress",

        created_at:
          new Date()
            .toISOString()
            .split("T")[0],

        evidence_count: 0,
      });
    } catch (err) {
      console.error(err);

      setError(
        "Unable to load case details."
      );
    } finally {
      setLoading(false);
    }
  };

  /*
   * =========================================================
   * LOAD CASE-LEVEL SECURITY DATA
   * =========================================================
   */

  const fetchSecurityData = async () => {
    if (!caseId) {
      return;
    }

    try {
      setSecurityLoading(true);
      setSecurityError("");

      const [
        iocs,
        findings,
        summary,
      ] = await Promise.all([
        getCaseIOCs(String(caseId)),
        getCaseFindings(String(caseId)),
        getCaseSecuritySummary(
          String(caseId)
        ),
      ]);

      setCaseIOCs(iocs);
      setCaseFindings(findings);
      setSecuritySummary(summary);
    } catch (err) {
      console.error(
        "Unable to retrieve case security data:",
        err
      );

      setSecurityError(
        "Case-level security data is not available yet. The backend endpoints may still be under integration."
      );
    } finally {
      setSecurityLoading(false);
    }
  };

  useEffect(() => {
    fetchCase();
  }, [caseId]);

  /*
   * =========================================================
   * FILE SELECTION
   * =========================================================
   */

  const handleFileChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file =
      event.target.files?.[0] || null;

    setSelectedFile(file);

    setUploadError("");
    setIocError("");
    setForensicError("");

    setIocAnalysis(null);
    setForensicAnalysis(null);
  };

  /*
   * =========================================================
   * TEXT FILE CHECK
   * =========================================================
   */

  const isTextFile = (
    file: File
  ): boolean => {
    const extension =
      file.name
        .split(".")
        .pop()
        ?.toLowerCase() || "";

    return (
      TEXT_FILE_EXTENSIONS.includes(
        extension
      ) ||
      file.type.startsWith("text/")
    );
  };

  /*
   * =========================================================
   * FORENSIC ANALYSIS
   * =========================================================
   */

  const handleForensicAnalysis = async (
    file: File,
    evidenceId: string
  ) => {
    try {
      setAnalyzingForensic(true);
      setForensicError("");

      const result =
        await analyzeEvidenceForensic(
          String(caseId),
          evidenceId,
          file
        );

      setForensicAnalysis(result);
    } catch (err) {
      console.error(
        "Unable to analyze evidence forensically:",
        err
      );

      setForensicError(
        err instanceof Error
          ? err.message
          : "Forensic analysis could not be completed."
      );
    } finally {
      setAnalyzingForensic(false);
    }
  };

  /*
   * =========================================================
   * UPLOAD + ANALYSIS PIPELINE
   * =========================================================
   */

  const handleUpload = async () => {
    if (!selectedFile || !caseId) {
      setUploadError(
        "Please select a file first."
      );

      return;
    }

    try {
      setUploading(true);

      setUploadError("");
      setAnalysisStatus(null);

      setIocAnalysis(null);
      setIocError("");

      setForensicAnalysis(null);
      setForensicError("");

      const fileForAnalysis =
        selectedFile;

      /*
       * 1. Upload evidence
       */

      const response =
        await uploadEvidence(
          String(caseId),
          selectedFile
        );

      /*
       * 2. Add evidence to UI
       */

      const newEvidence: Evidence = {
        id: String(
          response.evidence_id
        ),

        filename:
          response.filename,

        file_type:
          selectedFile.name
            .split(".")
            .pop()
            ?.toUpperCase() ||
          "FILE",

        sha256: "Processing...",

        status:
          response.status ===
          "processed"
            ? "Processed"
            : "Processing",

        uploaded_at:
          new Date()
            .toISOString()
            .split("T")[0],
      };

      setEvidence((current) => [
        newEvidence,
        ...current,
      ]);

      setSelectedFile(null);

      const fileInput =
        document.getElementById(
          "evidence-file"
        ) as HTMLInputElement | null;

      if (fileInput) {
        fileInput.value = "";
      }

      /*
       * 3. Get analysis status
       */

      try {
        const status =
          await getAnalysisStatus(
            String(
              response.evidence_id
            )
          );

        setAnalysisStatus(status);
      } catch (statusError) {
        console.error(
          "Unable to retrieve analysis status:",
          statusError
        );
      }

      /*
       * 4. Forensic analysis
       */

      await handleForensicAnalysis(
        fileForAnalysis,
        String(response.evidence_id)
      );

      /*
       * 5. IOC analysis
       *
       * Only text-readable evidence can
       * currently be analyzed by the IOC
       * pipeline directly in the frontend.
       */

      if (
        !isTextFile(
          fileForAnalysis
        )
      ) {
        setIocError(
          "IOC analysis is available for text-readable evidence only."
        );

        await fetchSecurityData();

        return;
      }

      try {
        setAnalyzingIOC(true);
        setIocError("");

        const text =
          await fileForAnalysis.text();

        if (!text.trim()) {
          setIocError(
            "The uploaded text file is empty. No IOC analysis was performed."
          );
        } else {
          const iocResult =
            await analyzeEvidence({
              tenant_id:
                "default-tenant",

              case_id:
                String(caseId),

              evidence_id:
                String(
                  response.evidence_id
                ),

              text,

              source_type:
                "file_text",

              options: {
                enable_fallback:
                  true,

                use_ai: false,
              },
            });

          setIocAnalysis(
            iocResult
          );
        }
      } catch (iocAnalysisError) {
        console.error(
          "Unable to analyze IOCs:",
          iocAnalysisError
        );

        setIocError(
          "IOC analysis could not be completed."
        );
      } finally {
        setAnalyzingIOC(false);
      }

      /*
       * 6. Refresh case-level security
       */

      await fetchSecurityData();
    } catch (err) {
      console.error(err);

      setUploadError(
        "Evidence upload failed. Please try again."
      );
    } finally {
      setUploading(false);
    }
  };

  /*
   * =========================================================
   * LOADING / ERROR STATES
   * =========================================================
   */

  if (loading) {
    return <Loading />;
  }

  if (error) {
    return (
      <div className="page">
        <ErrorMessage
          message={error}
          onRetry={fetchCase}
        />
      </div>
    );
  }

  if (!selectedCase) {
    return (
      <div className="page">
        <ErrorMessage
          message="Case not found."
        />
      </div>
    );
  }

  /*
   * =========================================================
   * DERIVED DATA
   * =========================================================
   */

  const classification =
    forensicAnalysis?.classification;

  const forensicReasons =
    classification?.reasons || [];

  const forensicTimeline =
    forensicAnalysis?.timeline_events ||
    [];

  const securityIocs =
    caseIOCs?.items || [];

  const securityFindings =
    caseFindings?.items || [];

  /*
   * =========================================================
   * PAGE
   * =========================================================
   */

  return (
    <div className="page">
      {/* =====================================================
          CASE HEADER
         ===================================================== */}

      <div className="page-header">
        <div>
          <h2>{selectedCase.title}</h2>

          <p>
            Case details, evidence and
            investigation analysis.
          </p>
        </div>

        <div
          className={`status-badge status-${selectedCase.status
            .toLowerCase()
            .replace(" ", "-")}`}
        >
          {selectedCase.status}
        </div>
      </div>

      {/* =====================================================
          CASE INFORMATION
         ===================================================== */}

      <div className="case-info-grid">
        <div className="case-info-card">
          <span>Case ID</span>
          <strong>
            {selectedCase.id}
          </strong>
        </div>

        <div className="case-info-card">
          <span>Status</span>
          <strong>
            {selectedCase.status}
          </strong>
        </div>

        <div className="case-info-card">
          <span>Created</span>
          <strong>
            {selectedCase.created_at}
          </strong>
        </div>

        <div className="case-info-card">
          <span>Evidence</span>
          <strong>
            {evidence.length}
          </strong>
        </div>
      </div>

      {/* =====================================================
          DESCRIPTION
         ===================================================== */}

      <div className="case-section">
        <div className="section-header">
          <div>
            <h3>Case Description</h3>

            <p>
              Investigation information
              associated with this case.
            </p>
          </div>
        </div>

        <div className="case-description">
          {selectedCase.description}
        </div>
      </div>

      {/* =====================================================
          EVIDENCE UPLOAD
         ===================================================== */}

      <div className="case-section">
        <div className="section-header">
          <div>
            <h3>Upload Evidence</h3>

            <p>
              Add digital evidence to this
              investigation case.
            </p>
          </div>
        </div>

        <div className="upload-box">
          <input
            id="evidence-file"
            type="file"
            onChange={handleFileChange}
          />

          {selectedFile && (
            <div className="selected-file">
              <span>
                Selected file
              </span>

              <strong>
                {selectedFile.name}
              </strong>
            </div>
          )}

          {uploadError && (
            <div className="upload-error">
              {uploadError}
            </div>
          )}

          <button
            className="primary-button"
            onClick={handleUpload}
            disabled={
              uploading ||
              !selectedFile
            }
          >
            {uploading
              ? "Processing..."
              : "Upload Evidence"}
          </button>
        </div>
      </div>

      {/* =====================================================
          ANALYSIS STATUS
         ===================================================== */}

      {analysisStatus && (
        <div className="case-section">
          <div className="section-header">
            <div>
              <h3>Analysis Status</h3>

              <p>
                Current processing status
                for this evidence.
              </p>
            </div>
          </div>

          <div className="analysis-status-grid">
            <div className="analysis-status-card">
              <span>Hashing</span>

              <strong>
                {
                  analysisStatus.hashing_status
                }
              </strong>
            </div>

            <div className="analysis-status-card">
              <span>Metadata</span>

              <strong>
                {
                  analysisStatus.metadata_status
                }
              </strong>
            </div>

            <div className="analysis-status-card">
              <span>AI Analysis</span>

              <strong>
                {
                  analysisStatus.ai_analysis_status
                }
              </strong>
            </div>
          </div>
        </div>
      )}

      {/* =====================================================
          EVIDENCE LIST
         ===================================================== */}

      <div className="case-section">
        <div className="section-header">
          <div>
            <h3>Evidence</h3>

            <p>
              Evidence uploaded to this
              investigation.
            </p>
          </div>
        </div>

        {evidence.length === 0 ? (
          <div className="empty-state">
            <strong>
              No evidence uploaded
            </strong>

            <p>
              Upload evidence to begin
              the investigation.
            </p>
          </div>
        ) : (
          <div className="evidence-list">
            {evidence.map((item) => (
              <div
                className="evidence-card"
                key={item.id}
              >
                <div className="evidence-card-main">
                  <div className="evidence-icon">
                    ◈
                  </div>

                  <div>
                    <h4>
                      {item.filename}
                    </h4>

                    <div className="evidence-meta">
                      <span>
                        {item.file_type}
                      </span>

                      <span>
                        Evidence ID:{" "}
                        {item.id}
                      </span>

                      <span>
                        Uploaded:{" "}
                        {item.uploaded_at}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="evidence-card-side">
                  <span
                    className={`status-badge status-${item.status
                      .toLowerCase()
                      .replace(
                        " ",
                        "-"
                      )}`}
                  >
                    {item.status}
                  </span>

                  <span className="hash-value">
                    {item.sha256}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* =====================================================
          FORENSIC ANALYSIS
         ===================================================== */}

      <div className="case-section">
        <div className="section-header">
          <div>
            <h3>Forensic Analysis</h3>

            <p>
              File identification,
              cryptographic hashes, metadata,
              classification and forensic
              findings.
            </p>
          </div>

          {forensicAnalysis && (
            <div className="ioc-total">
              Analysis complete
            </div>
          )}
        </div>

        {analyzingForensic && (
          <div className="loading">
            <div className="spinner"></div>

            <span>
              Running forensic analysis...
            </span>
          </div>
        )}

        {forensicError && (
          <div className="error-message">
            <div>
              <strong>
                Forensic Analysis
              </strong>

              <p>
                {forensicError}
              </p>

              <p>
                The frontend connection is
                ready; the backend forensic
                HTTP endpoint still needs to
                be exposed.
              </p>
            </div>
          </div>
        )}

        {!forensicAnalysis &&
          !analyzingForensic &&
          !forensicError && (
            <div className="empty-state">
              <strong>
                Forensic analysis ready
              </strong>

              <p>
                Upload evidence to send it
                through the forensic analysis
                connection.
              </p>
            </div>
          )}

        {forensicAnalysis && (
          <>
            {/* Classification */}

            <div className="case-section">
              <div className="section-header">
                <div>
                  <h3>
                    Classification
                  </h3>

                  <p>
                    Classification returned
                    by the forensic engine.
                  </p>
                </div>

                {classification && (
                  <span
                    className={`risk-badge risk-${String(
                      classification.classification
                    ).toLowerCase()}`}
                  >
                    {
                      classification.classification
                    }
                  </span>
                )}
              </div>

              {forensicReasons.length >
              0 ? (
                <div className="ioc-detail-card">
                  <div className="ioc-detail-header">
                    <strong>
                      Classification Reasons
                    </strong>
                  </div>

                  <ul>
                    {forensicReasons.map(
                      (
                        reason,
                        index
                      ) => (
                        <li key={index}>
                          {reason}
                        </li>
                      )
                    )}
                  </ul>
                </div>
              ) : (
                <div className="empty-state">
                  <strong>
                    No classification
                    reasons returned
                  </strong>
                </div>
              )}
            </div>

            {/* Hashes */}

            <div className="case-section">
              <div className="section-header">
                <div>
                  <h3>Hashes</h3>

                  <p>
                    Cryptographic identifiers
                    generated during
                    forensic processing.
                  </p>
                </div>
              </div>

              <DetailGrid
                data={
                  forensicAnalysis.hash
                }
              />
            </div>

            {/* File Identification */}

            <div className="case-section">
              <div className="section-header">
                <div>
                  <h3>
                    File Identification
                  </h3>

                  <p>
                    Detected file type and
                    identification details.
                  </p>
                </div>
              </div>

              <DetailGrid
                data={
                  forensicAnalysis.file_identification
                }
              />
            </div>

            {/* Filesystem Metadata */}

            <div className="case-section">
              <div className="section-header">
                <div>
                  <h3>
                    Filesystem Metadata
                  </h3>

                  <p>
                    Filesystem evidence
                    extracted from the file.
                  </p>
                </div>
              </div>

              <DetailGrid
                data={
                  forensicAnalysis.filesystem_metadata
                }
              />
            </div>

            {/* EXIF */}

            <div className="case-section">
              <div className="section-header">
                <div>
                  <h3>EXIF Metadata</h3>

                  <p>
                    Embedded media metadata
                    when available.
                  </p>
                </div>
              </div>

              <DetailGrid
                data={
                  forensicAnalysis.exif
                }
              />
            </div>

            {/* Document Metadata */}

            <div className="case-section">
              <div className="section-header">
                <div>
                  <h3>
                    Document Metadata
                  </h3>

                  <p>
                    Document properties
                    extracted from evidence.
                  </p>
                </div>
              </div>

              <DetailGrid
                data={
                  forensicAnalysis.document_metadata
                }
              />
            </div>

            {/* PE */}

            <div className="case-section">
              <div className="section-header">
                <div>
                  <h3>
                    PE Analysis
                  </h3>

                  <p>
                    Portable executable
                    information when
                    applicable.
                  </p>
                </div>
              </div>

              <DetailGrid
                data={
                  forensicAnalysis.pe_summary
                }
              />
            </div>

            {/* Log Entries */}

            {forensicAnalysis.log_entries &&
              forensicAnalysis.log_entries.length >
                0 && (
                <div className="case-section">
                  <div className="section-header">
                    <div>
                      <h3>
                        Log Entries
                      </h3>

                      <p>
                        Structured log events
                        extracted from the
                        evidence.
                      </p>
                    </div>
                  </div>

                  <div className="ioc-details-list">
                    {forensicAnalysis.log_entries.map(
                      (
                        entry,
                        index
                      ) => (
                        <div
                          className="ioc-detail-card"
                          key={index}
                        >
                          <strong>
                            Log Entry{" "}
                            {index + 1}
                          </strong>

                          <pre className="ioc-context">
                            {formatValue(
                              entry
                            )}
                          </pre>
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}

            {/* Timeline */}

            <div className="case-section">
              <div className="section-header">
                <div>
                  <h3>
                    Forensic Timeline
                  </h3>

                  <p>
                    Timeline events extracted
                    from the evidence.
                  </p>
                </div>
              </div>

              {forensicTimeline.length ===
              0 ? (
                <div className="empty-state">
                  <strong>
                    No timeline events
                  </strong>

                  <p>
                    No timeline events were
                    returned for this
                    evidence.
                  </p>
                </div>
              ) : (
                <div className="ioc-details-list">
                  {forensicTimeline.map(
                    (
                      event,
                      index
                    ) => (
                      <div
                        className="ioc-detail-card"
                        key={index}
                      >
                        <strong>
                          Event{" "}
                          {index + 1}
                        </strong>

                        <pre className="ioc-context">
                          {formatValue(
                            event
                          )}
                        </pre>
                      </div>
                    )
                  )}
                </div>
              )}
            </div>

            {/* Finding */}

            {forensicAnalysis.forensic_finding && (
              <div className="case-section">
                <div className="section-header">
                  <div>
                    <h3>
                      Forensic Finding
                    </h3>

                    <p>
                      Structured finding
                      generated by the
                      forensic engine.
                    </p>
                  </div>
                </div>

                <pre className="ioc-context">
                  {formatValue(
                    forensicAnalysis.forensic_finding
                  )}
                </pre>
              </div>
            )}

            {/* Processing Errors */}

            {forensicAnalysis.processing_errors &&
              forensicAnalysis.processing_errors
                .length > 0 && (
                <div className="case-section">
                  <div className="error-message">
                    <div>
                      <strong>
                        Processing Warnings
                      </strong>

                      <ul>
                        {forensicAnalysis.processing_errors.map(
                          (
                            item,
                            index
                          ) => (
                            <li
                              key={
                                index
                              }
                            >
                              {item}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
          </>
        )}
      </div>

      {/* =====================================================
          IOC ANALYSIS
         ===================================================== */}

      {(analyzingIOC ||
        iocAnalysis ||
        iocError) && (
        <div className="case-section">
          <div className="section-header">
            <div>
              <h3>IOC Analysis</h3>

              <p>
                Indicators of compromise
                detected directly from the
                uploaded evidence.
              </p>
            </div>

            {iocAnalysis && (
              <div className="ioc-total">
                {iocAnalysis.iocs.length} IOCs
              </div>
            )}
          </div>

          {analyzingIOC && (
            <div className="loading">
              <div className="spinner"></div>

              <span>
                Analyzing evidence for IOCs...
              </span>
            </div>
          )}

          {iocError && (
            <div className="error-message">
              <div>
                <strong>
                  IOC Analysis
                </strong>

                <p>
                  {iocError}
                </p>
              </div>
            </div>
          )}

          {iocAnalysis &&
            iocAnalysis.iocs.length ===
              0 && (
              <div className="empty-state">
                <strong>
                  No IOCs detected
                </strong>

                <p>
                  No supported indicators
                  of compromise were found
                  in this evidence.
                </p>
              </div>
            )}

          {iocAnalysis &&
            iocAnalysis.iocs.length >
              0 && (
              <>
                <div className="ioc-table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>
                          Indicator
                        </th>
                        <th>Risk</th>
                        <th>Score</th>
                        <th>
                          MITRE ATT&CK
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {iocAnalysis.iocs.map(
                        (ioc) => (
                          <tr
                            key={`${ioc.dedupe_key}-${ioc.value_normalized}`}
                          >
                            <td>
                              <span className="ioc-type">
                                {ioc.type.toUpperCase()}
                              </span>
                            </td>

                            <td>
                              <strong>
                                {
                                  ioc.value_normalized
                                }
                              </strong>
                            </td>

                            <td>
                              <span
                                className={`risk-badge risk-${ioc.risk_level}`}
                              >
                                {ioc.risk_level.toUpperCase()}
                              </span>
                            </td>

                            <td>
                              {
                                ioc.risk_score
                              }
                            </td>

                            <td>
                              {ioc.mitre_ids
                                .length >
                              0
                                ? ioc.mitre_ids.join(
                                    ", "
                                  )
                                : "—"}
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="ioc-details-list">
                  {iocAnalysis.iocs.map(
                    (ioc) => (
                      <div
                        className="ioc-detail-card"
                        key={`details-${ioc.dedupe_key}-${ioc.value_normalized}`}
                      >
                        <div className="ioc-detail-header">
                          <strong>
                            {
                              ioc.value_normalized
                            }
                          </strong>

                          <span
                            className={`risk-badge risk-${ioc.risk_level}`}
                          >
                            {ioc.risk_level.toUpperCase()}
                          </span>
                        </div>

                        {ioc.context_snippet && (
                          <div className="ioc-context">
                            <span>
                              Context
                            </span>

                            <p>
                              {
                                ioc.context_snippet
                              }
                            </p>
                          </div>
                        )}

                        {ioc.reasons.length >
                          0 && (
                          <div className="ioc-reasons">
                            <span>
                              Reasons
                            </span>

                            <ul>
                              {ioc.reasons.map(
                                (
                                  reason,
                                  index
                                ) => (
                                  <li
                                    key={
                                      index
                                    }
                                  >
                                    {reason}
                                  </li>
                                )
                              )}
                            </ul>
                          </div>
                        )}

                        {ioc.mitre_ids.length >
                          0 && (
                          <div className="ioc-mitre">
                            <span>
                              MITRE ATT&CK
                            </span>

                            <strong>
                              {ioc.mitre_ids.join(
                                ", "
                              )}
                            </strong>
                          </div>
                        )}

                        {ioc.ai_accepted && (
                          <div className="ioc-mitre">
                            <span>
                              AI Analysis
                            </span>

                            <strong>
                              Accepted
                            </strong>
                          </div>
                        )}
                      </div>
                    )
                  )}
                </div>
              </>
            )}
        </div>
      )}

      {/* =====================================================
          SECURITY SUMMARY
         ===================================================== */}

      <div className="case-section">
        <div className="section-header">
          <div>
            <h3>
              Case Security Summary
            </h3>

            <p>
              Case-level security and
              investigation rollup.
            </p>
          </div>

          <button
            className="secondary-button"
            onClick={fetchSecurityData}
            disabled={
              securityLoading
            }
          >
            {securityLoading
              ? "Refreshing..."
              : "Refresh"}
          </button>
        </div>

        {securityError && (
          <div className="error-message">
            <div>
              <strong>
                Security Integration
              </strong>

              <p>
                {securityError}
              </p>
            </div>
          </div>
        )}

        {securityLoading && (
          <div className="loading">
            <div className="spinner"></div>

            <span>
              Loading case security
              data...
            </span>
          </div>
        )}

        {securitySummary && (
          <>
            <div className="analysis-status-grid">
              <div className="analysis-status-card">
                <span>
                  Total IOCs
                </span>

                <strong>
                  {
                    securitySummary.ioc_count
                  }
                </strong>
              </div>

              <div className="analysis-status-card">
                <span>
                  Worst Severity
                </span>

                <strong>
                  {securitySummary.worst_severity.toUpperCase()}
                </strong>
              </div>

              <div className="analysis-status-card">
                <span>
                  Evidence
                </span>

                <strong>
                  {
                    securitySummary.evidence_count
                  }
                </strong>
              </div>

              <div className="analysis-status-card">
                <span>
                  Forensic Findings
                </span>

                <strong>
                  {
                    securitySummary.forensic_findings
                  }
                </strong>
              </div>

              <div className="analysis-status-card">
                <span>
                  Forensic Flagged
                </span>

                <strong>
                  {
                    securitySummary.forensic_flagged
                  }
                </strong>
              </div>

              <div className="analysis-status-card">
                <span>
                  Hot IOCs
                </span>

                <strong>
                  {
                    securitySummary.hot_iocs
                  }
                </strong>
              </div>
            </div>

            <div className="ioc-detail-card">
              <div className="ioc-detail-header">
                <strong>
                  Case Verdict
                </strong>

                <span className="risk-badge">
                  {
                    securitySummary.verdict
                  }
                </span>
              </div>
            </div>

            <div className="analysis-status-grid">
              {Object.entries(
                securitySummary.by_level
              ).map(
                ([level, count]) => (
                  <div
                    className="analysis-status-card"
                    key={level}
                  >
                    <span>
                      {level.toUpperCase()}
                    </span>

                    <strong>
                      {count}
                    </strong>
                  </div>
                )
              )}
            </div>
          </>
        )}

        {!securitySummary &&
          !securityLoading &&
          !securityError && (
            <div className="empty-state">
              <strong>
                No security summary yet
              </strong>

              <p>
                Upload and analyze
                evidence to populate
                the case-level security
                summary.
              </p>
            </div>
          )}
      </div>

      {/* =====================================================
          THREAT FINDINGS
         ===================================================== */}

      <div className="case-section">
        <div className="section-header">
          <div>
            <h3>
              Threat Findings
            </h3>

            <p>
              Security findings returned
              for this investigation.
            </p>
          </div>
        </div>

        {securityFindings.length ===
        0 ? (
          <div className="empty-state">
            <strong>
              No threat findings
            </strong>

            <p>
              Findings will appear here
              when the Security backend
              returns them.
            </p>
          </div>
        ) : (
          <div className="ioc-details-list">
            {securityFindings.map(
              (finding, index) => (
                <div
                  className="ioc-detail-card"
                  key={`${finding.ioc}-${index}`}
                >
                  <div className="ioc-detail-header">
                    <strong>
                      {finding.ioc}
                    </strong>

                    <span
                      className={`risk-badge risk-${finding.severity}`}
                    >
                      {finding.severity.toUpperCase()}
                    </span>
                  </div>

                  <div className="ioc-context">
                    <span>
                      Observation
                    </span>

                    <p>
                      {
                        finding.observation
                      }
                    </p>
                  </div>

                  <div className="ioc-reasons">
                    <span>
                      Reason
                    </span>

                    <p>
                      {finding.reason}
                    </p>
                  </div>

                  <div className="ioc-mitre">
                    <span>
                      Type
                    </span>

                    <strong>
                      {finding.type}
                    </strong>
                  </div>

                  {finding.mitre_ids
                    .length > 0 && (
                    <div className="ioc-mitre">
                      <span>
                        MITRE ATT&CK
                      </span>

                      <strong>
                        {finding.mitre_ids.join(
                          ", "
                        )}
                      </strong>
                    </div>
                  )}

                  <div className="evidence-meta">
                    <span>
                      Evidence ID:{" "}
                      {
                        finding.source
                          .evidence_id
                      }
                    </span>

                    <span>
                      Source:{" "}
                      {
                        finding.source
                          .source_type
                      }
                    </span>

                    {finding.source
                      .line_no !==
                      undefined &&
                      finding.source
                        .line_no !==
                        null && (
                        <span>
                          Line:{" "}
                          {
                            finding
                              .source
                              .line_no
                          }
                        </span>
                      )}
                  </div>
                </div>
              )
            )}
          </div>
        )}
      </div>

      {/* =====================================================
          CASE-LEVEL IOC CORRELATION
         ===================================================== */}

      <div className="case-section">
        <div className="section-header">
          <div>
            <h3>
              Case IOC Correlation
            </h3>

            <p>
              Indicators aggregated across
              the investigation.
            </p>
          </div>
        </div>

        {securityIocs.length ===
        0 ? (
          <div className="empty-state">
            <strong>
              No case-level IOCs
            </strong>

            <p>
              Case-wide IOC data will
              appear here once the
              Security backend returns
              it.
            </p>
          </div>
        ) : (
          <div className="ioc-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>
                    Indicator
                  </th>
                  <th>Risk</th>
                  <th>Score</th>
                  <th>Status</th>
                  <th>
                    MITRE ATT&CK
                  </th>
                </tr>
              </thead>

              <tbody>
                {securityIocs.map(
                  (ioc) => (
                    <tr
                      key={`${ioc.dedupe_key}-${ioc.value_normalized}`}
                    >
                      <td>
                        <span className="ioc-type">
                          {ioc.type.toUpperCase()}
                        </span>
                      </td>

                      <td>
                        <strong>
                          {
                            ioc.value_normalized
                          }
                        </strong>
                      </td>

                      <td>
                        <span
                          className={`risk-badge risk-${ioc.risk_level}`}
                        >
                          {ioc.risk_level.toUpperCase()}
                        </span>
                      </td>

                      <td>
                        {ioc.risk_score}
                      </td>

                      <td>
                        {ioc.status}
                      </td>

                      <td>
                        {ioc.mitre_ids
                          .length > 0
                          ? ioc.mitre_ids.join(
                              ", "
                            )
                          : "—"}
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* =====================================================
          CORRELATION CONNECTION
         ===================================================== */}

      <div className="case-section">
        <div className="section-header">
          <div>
            <h3>
              Investigation Correlation
            </h3>

            <p>
              Shared IOCs, colocated
              indicators and timeline
              correlation.
            </p>
          </div>
        </div>

        <div className="empty-state">
          <strong>
            Correlation UI ready
          </strong>

          <p>
            The frontend is prepared for
            the updated Security correlation
            payload. The current case-level
            API response does not yet expose
            the shared IOC and colocated-link
            fields.
          </p>
        </div>
      </div>
    </div>
  );
};

export default CaseDetails;