import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { Case } from "../types";
import {
  createCase,
  getCases,
  type BackendCase,
} from "../services/api";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

const formatCase = (item: BackendCase): Case => ({
  id: String(item.id),
  title: item.title,
  description: item.description || "No description provided.",
  status:
    item.status === "Active"
      ? "Open"
      : item.status === "Closed"
        ? "Closed"
        : "In Progress",
  created_at: new Date().toISOString().split("T")[0],
  evidence_count: 0,
});

const Cases = () => {
  const navigate = useNavigate();

  const [cases, setCases] = useState<Case[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showModal, setShowModal] = useState(false);

  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");

  const [formError, setFormError] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchCases = async () => {
    try {
      setLoading(true);
      setError("");

      const backendCases = await getCases();

      setCases(backendCases.map(formatCase));
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

  const filteredCases = useMemo(() => {
    return cases.filter((item) => {
      const searchValue = search.toLowerCase();

      const matchesSearch =
        item.title.toLowerCase().includes(searchValue) ||
        item.id.toLowerCase().includes(searchValue);

      const matchesStatus =
        statusFilter === "All" ||
        item.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [cases, search, statusFilter]);

  const handleCreateCase = async (
    event: React.FormEvent
  ) => {
    event.preventDefault();

    if (!newTitle.trim()) {
      setFormError("Case title is required.");
      return;
    }

    try {
      setCreating(true);
      setFormError("");

      const created = await createCase({
        title: newTitle.trim(),
        description:
          newDescription.trim() || undefined,
      });

      const formattedCase = formatCase(created);

      setCases((current) => [
        formattedCase,
        ...current,
      ]);

      setNewTitle("");
      setNewDescription("");
      setShowModal(false);
    } catch (err) {
      console.error(err);

      setFormError(
        "Unable to create the case. Please try again."
      );
    } finally {
      setCreating(false);
    }
  };

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
          <h2>Cases</h2>
          <p>
            Manage and investigate active cases.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={() => {
            setFormError("");
            setShowModal(true);
          }}
        >
          + Create Case
        </button>
      </div>

      <div className="case-controls">
        <div className="search-box">
          <span>⌕</span>

          <input
            type="text"
            placeholder="Search cases..."
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
          />
        </div>

        <select
          className="status-filter"
          value={statusFilter}
          onChange={(event) =>
            setStatusFilter(event.target.value)
          }
        >
          <option value="All">All statuses</option>
          <option value="Open">Open</option>
          <option value="In Progress">
            In Progress
          </option>
          <option value="Closed">Closed</option>
        </select>
      </div>

      <div className="cases-list">
        {filteredCases.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">◫</div>

            <h3>No cases found</h3>

            <p>
              Try changing your search or create a new
              investigation.
            </p>
          </div>
        ) : (
          filteredCases.map((item) => (
            <div
              className="case-card"
              key={item.id}
              onClick={() =>
                navigate(`/cases/${item.id}`)
              }
            >
              <div className="case-card-main">
                <div className="case-card-icon">
                  ◫
                </div>

                <div className="case-card-info">
                  <div className="case-card-title">
                    <h3>{item.title}</h3>

                    <span
                      className={`status-badge ${item.status
                        .toLowerCase()
                        .replace(" ", "-")}`}
                    >
                      {item.status}
                    </span>
                  </div>

                  <p>{item.description}</p>

                  <div className="case-card-meta">
                    <span>{item.id}</span>

                    <span>•</span>

                    <span>
                      Created {item.created_at}
                    </span>

                    <span>•</span>

                    <span>
                      {item.evidence_count} evidence
                      files
                    </span>
                  </div>
                </div>
              </div>

              <span className="case-arrow">
                →
              </span>
            </div>
          ))
        )}
      </div>

      {showModal && (
        <div
          className="modal-overlay"
          onClick={() => {
            if (!creating) {
              setShowModal(false);
            }
          }}
        >
          <div
            className="create-case-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >
            <div className="modal-header">
              <div>
                <h3>Create New Case</h3>

                <p>
                  Create an investigation case to begin.
                </p>
              </div>

              <button
                className="modal-close"
                onClick={() => {
                  if (!creating) {
                    setShowModal(false);
                  }
                }}
                disabled={creating}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleCreateCase}>
              <label>
                Case Title

                <input
                  type="text"
                  placeholder="Enter case title"
                  value={newTitle}
                  onChange={(event) =>
                    setNewTitle(event.target.value)
                  }
                  disabled={creating}
                />
              </label>

              <label>
                Description

                <textarea
                  placeholder="Briefly describe the investigation..."
                  value={newDescription}
                  onChange={(event) =>
                    setNewDescription(
                      event.target.value
                    )
                  }
                  rows={4}
                  disabled={creating}
                />
              </label>

              {formError && (
                <div className="form-error">
                  {formError}
                </div>
              )}

              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() =>
                    setShowModal(false)
                  }
                  disabled={creating}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="primary-button"
                  disabled={creating}
                >
                  {creating
                    ? "Creating..."
                    : "Create Case"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Cases;
