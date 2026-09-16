import {
  useEffect,
  useState,
} from "react";
import { useParams } from "react-router-dom";

import type {
  Case,
  Evidence,
} from "../types";

import {
  getCases,
  uploadEvidence,
  getAnalysisStatus,
  analyzeEvidence,
  type AnalysisStatusResponse,
  type IOCAnalyzeResponse,
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
    useState<AnalysisStatusResponse | null>(
      null
    );

  const [iocAnalysis, setIocAnalysis] =
    useState<IOCAnalyzeResponse | null>(
      null
    );

  const [analyzingIOC, setAnalyzingIOC] =
    useState(false);

  const [iocError, setIocError] =
    useState("");

  const fetchCase = async () => {
    try {
      setLoading(true);
      setError("");

      const cases = await getCases();

      const foundCase = cases.find(
        (item) =>
          String(item.id) === String(caseId)
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

  useEffect(() => {
    fetchCase();
  }, [caseId]);

  const handleFileChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file =
      event.target.files?.[0] || null;

    setSelectedFile(file);
    setUploadError("");
    setIocError("");
    setIocAnalysis(null);
  };

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

      const fileForAnalysis =
        selectedFile;

      const response =
        await uploadEvidence(
          String(caseId),
          selectedFile
        );

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
       * Retrieve the backend analysis status.
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
       * IOC analysis is currently performed
       * directly on text-readable evidence.
       *
       * Binary forensic evidence should be
       * processed by the backend forensic
       * pipeline instead of calling File.text()
       * in the browser.
       */
      if (!isTextFile(fileForAnalysis)) {
        setIocError(
          "IOC analysis is available for text-readable evidence only."
        );
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
          return;
        }

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
    } catch (err) {
      console.error(err);

      setUploadError(
        "Evidence upload failed. Please try again."
      );
    } finally {
      setUploading(false);
    }
  };

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

  return (
    <div className="page">

      {/* Case Header */}

      <div className="page-header">
        <div>
          <h2>
            {selectedCase.title}
          </h2>

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


      {/* Case Information */}

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


      {/* Description */}

      <div className="case-section">

        <div className="section-header">
          <div>
            <h3>
              Case Description
            </h3>

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


      {/* Evidence Upload */}

      <div className="case-section">

        <div className="section-header">
          <div>
            <h3>
              Upload Evidence
            </h3>

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
            onChange={
              handleFileChange
            }
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
              ? "Uploading..."
              : "Upload Evidence"}
          </button>

        </div>

      </div>


      {/* Analysis Status */}

      {analysisStatus && (
        <div className="case-section">

          <div className="section-header">
            <div>

              <h3>
                Analysis Status
              </h3>

              <p>
                Current processing status
                for this evidence.
              </p>

            </div>
          </div>

          <div className="analysis-status-grid">

            <div className="analysis-status-card">
              <span>
                Hashing
              </span>

              <strong>
                {
                  analysisStatus.hashing_status
                }
              </strong>
            </div>

            <div className="analysis-status-card">
              <span>
                Metadata
              </span>

              <strong>
                {
                  analysisStatus.metadata_status
                }
              </strong>
            </div>

            <div className="analysis-status-card">
              <span>
                AI Analysis
              </span>

              <strong>
                {
                  analysisStatus.ai_analysis_status
                }
              </strong>
            </div>

          </div>

        </div>
      )}


      {/* Evidence List */}

      <div className="case-section">

        <div className="section-header">

          <div>
            <h3>
              Evidence
            </h3>

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
                      .replace(" ", "-")}`}
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


      {/* IOC Analysis */}

      {(analyzingIOC ||
        iocAnalysis ||
        iocError) && (

        <div className="case-section">

          <div className="section-header">

            <div>

              <h3>
                IOC Analysis
              </h3>

              <p>
                Indicators of compromise
                detected in the uploaded
                evidence.
              </p>

            </div>

            {iocAnalysis && (
              <div className="ioc-total">
                {
                  iocAnalysis.iocs
                    .length
                }{" "}
                IOCs
              </div>
            )}

          </div>


          {/* IOC Loading */}

          {analyzingIOC && (

            <div className="loading">

              <div className="spinner"></div>

              <span>
                Analyzing evidence for
                IOCs...
              </span>

            </div>

          )}


          {/* IOC Error */}

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


          {/* No IOCs */}

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


          {/* IOC Table */}

          {iocAnalysis &&
            iocAnalysis.iocs.length >
              0 && (

              <div className="ioc-table-wrapper">

                <table className="data-table">

                  <thead>

                    <tr>

                      <th>
                        Type
                      </th>

                      <th>
                        Indicator
                      </th>

                      <th>
                        Risk
                      </th>

                      <th>
                        Score
                      </th>

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
                            {ioc.risk_score}
                          </td>

                          <td>
                            {ioc.mitre_ids.length >
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

            )}


          {/* IOC Details */}

          {iocAnalysis &&
            iocAnalysis.iocs.length >
              0 && (

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
                            {
                              ioc.mitre_ids.join(
                                ", "
                              )
                            }
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

            )}

        </div>

      )}

    </div>
  );
};

export default CaseDetails;