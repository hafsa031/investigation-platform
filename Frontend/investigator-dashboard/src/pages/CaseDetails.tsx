import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import type { Case, Evidence } from "../types";
import {
  getCases,
  uploadEvidence,
  getAnalysisStatus,
  type AnalysisStatusResponse,
} from "../services/api";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

const CaseDetails = () => {
  const { caseId } = useParams();
  const navigate = useNavigate();

  const [selectedCase, setSelectedCase] = useState<Case | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [uploadError, setUploadError] = useState("");

  const [analysisStatus, setAnalysisStatus] =
    useState<AnalysisStatusResponse | null>(null);

  const fetchCase = async () => {
    try {
      setLoading(true);
      setError("");

      const cases = await getCases();

      const foundCase = cases.find(
        (item) => String(item.id) === String(caseId)
      );

      if (!foundCase) {
        setError("Case not found.");
        return;
      }

      setSelectedCase({
        id: String(foundCase.id),
        title: foundCase.title,
        description:
          foundCase.description || "No description provided.",
        status:
          foundCase.status === "Active"
            ? "Open"
            : foundCase.status === "Closed"
              ? "Closed"
              : "In Progress",
        created_at: new Date().toISOString().split("T")[0],
        evidence_count: 0,
      });
    } catch (err) {
      console.error(err);
      setError("Unable to load case details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCase();
  }, [caseId]);

  const handleUpload = async () => {
    if (!selectedFile || !caseId) {
      setUploadError("Please select a file first.");
      return;
    }

    try {
      setUploading(true);
      setUploadError("");
      setAnalysisStatus(null);

      const response = await uploadEvidence(
        String(caseId),
        selectedFile
      );

      const newEvidence: Evidence = {
        id: String(response.evidence_id),
        filename: response.filename,
        file_type:
          selectedFile.name.split(".").pop()?.toUpperCase() ||
          "FILE",
        sha256: "Processing...",
        status:
          response.status === "processed"
            ? "Processed"
            : "Processing",
        uploaded_at: new Date()
          .toISOString()
          .split("T")[0],
      };

      setEvidence((current) => [
        newEvidence,
        ...current,
      ]);

      setSelectedFile(null);

      const fileInput = document.getElementById(
        "evidence-file"
      ) as HTMLInputElement | null;

      if (fileInput) {
        fileInput.value = "";
      }

      // Check the analysis status after upload.
      try {
        const status = await getAnalysisStatus(
          String(response.evidence_id)
        );

        setAnalysisStatus(status);
      } catch (statusError) {
        console.error(
          "Unable to retrieve analysis status:",
          statusError
        );
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
    return (
      <div className="page">
        <Loading />
      </div>
    );
  }

  if (error || !selectedCase) {
    return (
      <div className="page">
        <ErrorMessage
          message={error || "Case not found."}
          onRetry={fetchCase}
        />
      </div>
    );
  }

  return (
    <div className="page">
      <button
        className="back-button"
        onClick={() => navigate("/cases")}
      >
        ← Back to Cases
      </button>

      <div className="case-details-header">
        <div>
          <div className="case-id">
            {selectedCase.id}
          </div>

          <h2>{selectedCase.title}</h2>

          <p>{selectedCase.description}</p>
        </div>

        <span
          className={`status-badge ${selectedCase.status
            .toLowerCase()
            .replace(" ", "-")}`}
        >
          {selectedCase.status}
        </span>
      </div>

      <div className="case-info-grid">
        <div className="case-info-card">
          <span>Case ID</span>
          <strong>{selectedCase.id}</strong>
        </div>

        <div className="case-info-card">
          <span>Created</span>
          <strong>{selectedCase.created_at}</strong>
        </div>

        <div className="case-info-card">
          <span>Evidence</span>
          <strong>{evidence.length} files</strong>
        </div>

        <div className="case-info-card">
          <span>Investigator</span>
          <strong>Current User</strong>
        </div>
      </div>

      <div className="evidence-section">
        <div className="section-header">
          <div>
            <h3>Evidence</h3>
            <p>
              Files associated with this investigation.
            </p>
          </div>
        </div>

        <div className="upload-box">
          <div className="upload-icon">↑</div>

          <div className="upload-content">
            <h4>Upload Evidence</h4>

            <p>
              Select a file to add it to this investigation.
            </p>

            <input
              id="evidence-file"
              type="file"
              onChange={(event) => {
                setSelectedFile(
                  event.target.files?.[0] ?? null
                );
                setUploadError("");
              }}
              disabled={uploading}
            />

            {selectedFile && (
              <div className="selected-file">
                <span>{selectedFile.name}</span>

                <span>
                  {(selectedFile.size / 1024 / 1024).toFixed(
                    2
                  )}{" "}
                  MB
                </span>
              </div>
            )}

            {uploadError && (
              <div className="form-error">
                {uploadError}
              </div>
            )}

            <button
              className="primary-button upload-button"
              onClick={handleUpload}
              disabled={uploading}
            >
              {uploading
                ? "Uploading..."
                : "Upload Evidence"}
            </button>
          </div>
        </div>

        {analysisStatus && (
          <div className="analysis-status-card">
            <div>
              <h4>Evidence Processing</h4>
              <p>
                Evidence processing status from the
                investigation backend.
              </p>
            </div>

            <div className="analysis-status-grid">
              <div>
                <span>Hashing</span>
                <strong>
                  {analysisStatus.hashing_status}
                </strong>
              </div>

              <div>
                <span>Metadata</span>
                <strong>
                  {analysisStatus.metadata_status}
                </strong>
              </div>

              <div>
                <span>AI Analysis</span>
                <strong>
                  {analysisStatus.ai_analysis_status}
                </strong>
              </div>
            </div>
          </div>
        )}

        <div className="evidence-list">
          {evidence.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">◈</div>

              <h3>No evidence uploaded</h3>

              <p>
                Upload evidence to begin processing.
              </p>
            </div>
          ) : (
            evidence.map((item) => (
              <div
                className="evidence-row"
                key={item.id}
              >
                <div className="evidence-file-icon">
                  {item.file_type.slice(0, 3)}
                </div>

                <div className="evidence-main">
                  <strong>{item.filename}</strong>

                  <span>
                    {item.id} • Uploaded{" "}
                    {item.uploaded_at}
                  </span>
                </div>

                <div className="evidence-hash">
                  <span>SHA-256</span>
                  <code>{item.sha256}</code>
                </div>

                <span
                  className={`evidence-status ${item.status.toLowerCase()}`}
                >
                  {item.status}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default CaseDetails;
