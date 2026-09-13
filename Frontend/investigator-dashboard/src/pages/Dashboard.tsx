/*import { useNavigate } from "react-router-dom";
import type { Case } from "../types/index.ts";

const mockCases: Case[] = [
  {
    id: "CASE-001",
    title: "Unauthorized Access Investigation",
    description: "Investigation into suspicious account activity.",
    status: "In Progress",
    created_at: "2026-09-10",
    evidence_count: 8,
  },
  {
    id: "CASE-002",
    title: "Network Intrusion Analysis",
    description: "Analysis of network activity and related evidence.",
    status: "Open",
    created_at: "2026-09-09",
    evidence_count: 5,
  },
  {
    id: "CASE-003",
    title: "Data Exfiltration Investigation",
    description: "Investigation involving suspected data transfer.",
    status: "Open",
    created_at: "2026-09-07",
    evidence_count: 12,
  },
  {
    id: "CASE-004",
    title: "Endpoint Activity Review",
    description: "Review of suspicious endpoint activity.",
    status: "Closed",
    created_at: "2026-09-05",
    evidence_count: 6,
  },
];

const Dashboard = () => {
  const navigate = useNavigate();

  const totalCases = mockCases.length;

  const openCases = mockCases.filter(
    (item) => item.status === "Open"
  ).length;

  const inProgressCases = mockCases.filter(
    (item) => item.status === "In Progress"
  ).length;

  const totalEvidence = mockCases.reduce(
    (total, item) => total + item.evidence_count,
    0
  );

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p>Overview of your investigations and evidence.</p>
        </div>

        <button
          className="primary-button"
          onClick={() => navigate("/cases")}
        >
          + Create Case
        </button>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">Total Cases</span>
          <strong>{totalCases}</strong>
          <span className="stat-description">
            All investigations
          </span>
        </div>

        <div className="stat-card">
          <span className="stat-label">Open Cases</span>
          <strong>{openCases}</strong>
          <span className="stat-description">
            Awaiting investigation
          </span>
        </div>

        <div className="stat-card">
          <span className="stat-label">In Progress</span>
          <strong>{inProgressCases}</strong>
          <span className="stat-description">
            Active investigations
          </span>
        </div>

        <div className="stat-card">
          <span className="stat-label">Total Evidence</span>
          <strong>{totalEvidence}</strong>
          <span className="stat-description">
            Across all cases
          </span>
        </div>
      </div>

      <div className="section-header">
        <div>
          <h3>Recent Cases</h3>
          <p>Latest investigations in the system.</p>
        </div>

        <button
          className="text-button"
          onClick={() => navigate("/cases")}
        >
          View all →
        </button>
      </div>

      <div className="cases-table">
        <div className="table-header">
          <span>Case</span>
          <span>Status</span>
          <span>Evidence</span>
          <span>Created</span>
        </div>

        {mockCases.map((item) => (
          <div
            className="table-row"
            key={item.id}
            onClick={() => navigate(`/cases/${item.id}`)}
          >
            <div className="case-name">
              <strong>{item.title}</strong>
              <span>{item.id}</span>
            </div>

            <div>
              <span
                className={`status-badge ${item.status
                  .toLowerCase()
                  .replace(" ", "-")}`}
              >
                {item.status}
              </span>
            </div>

            <span className="evidence-count">
              {item.evidence_count} files
            </span>

            <span className="created-date">
              {item.created_at}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;
*/


import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { Case } from "../types";
import { getCases } from "../services/api";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

const Dashboard = () => {
  const navigate = useNavigate();

  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchCases = async () => {
    try {
      setLoading(true);
      setError("");

      const backendCases = await getCases();

      const formattedCases: Case[] = backendCases.map((item) => ({
        id: String(item.id),
        title: item.title,
        description:
          item.description || "No description provided.",
        status:
          item.status === "Active"
            ? "Open"
            : item.status === "Closed"
              ? "Closed"
              : "In Progress",
        created_at: new Date().toISOString().split("T")[0],
        evidence_count: 0,
      }));

      setCases(formattedCases);
    } catch (err) {
      console.error(err);
      setError("Unable to load cases from the backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  const totalCases = cases.length;

  const openCases = cases.filter(
    (item) => item.status === "Open"
  ).length;

  const inProgressCases = cases.filter(
    (item) => item.status === "In Progress"
  ).length;

  const totalEvidence = cases.reduce(
    (total, item) => total + item.evidence_count,
    0
  );

  if (loading) {
    return (
      <div className="page">
        <Loading />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <ErrorMessage
          message={error}
          onRetry={fetchCases}
        />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p>
            Overview of your investigations and evidence.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={() => navigate("/cases")}
        >
          + Create Case
        </button>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">Total Cases</span>
          <strong>{totalCases}</strong>
          <span className="stat-description">
            All investigations
          </span>
        </div>

        <div className="stat-card">
          <span className="stat-label">Open Cases</span>
          <strong>{openCases}</strong>
          <span className="stat-description">
            Awaiting investigation
          </span>
        </div>

        <div className="stat-card">
          <span className="stat-label">In Progress</span>
          <strong>{inProgressCases}</strong>
          <span className="stat-description">
            Active investigations
          </span>
        </div>

        <div className="stat-card">
          <span className="stat-label">Total Evidence</span>
          <strong>{totalEvidence}</strong>
          <span className="stat-description">
            Across all cases
          </span>
        </div>
      </div>

      <div className="section-header">
        <div>
          <h3>Recent Cases</h3>
          <p>Latest investigations in the system.</p>
        </div>

        <button
          className="text-button"
          onClick={() => navigate("/cases")}
        >
          View all →
        </button>
      </div>

      <div className="cases-table">
        <div className="table-header">
          <span>Case</span>
          <span>Status</span>
          <span>Evidence</span>
          <span>Created</span>
        </div>

        {cases.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">◫</div>
            <h3>No cases yet</h3>
            <p>
              Create your first investigation to get started.
            </p>
          </div>
        ) : (
          cases.map((item) => (
            <div
              className="table-row"
              key={item.id}
              onClick={() =>
                navigate(`/cases/${item.id}`)
              }
            >
              <div className="case-name">
                <strong>{item.title}</strong>
                <span>{item.id}</span>
              </div>

              <div>
                <span
                  className={`status-badge ${item.status
                    .toLowerCase()
                    .replace(" ", "-")}`}
                >
                  {item.status}
                </span>
              </div>

              <span className="evidence-count">
                {item.evidence_count} files
              </span>

              <span className="created-date">
                {item.created_at}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Dashboard;

