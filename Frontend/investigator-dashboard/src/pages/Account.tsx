import { useEffect, useState } from "react";
import { getApiError, getCurrentUser, getMyAuditLogs, type AuditLogRecord, type UserProfile } from "../services/api";
import Loading from "../components/Loading";

const Account = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [logs, setLogs] = useState<AuditLogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([getCurrentUser(), getMyAuditLogs()]).then(([profile, auditLogs]) => { setUser(profile); setLogs(auditLogs); })
      .catch((e) => setError(getApiError(e, "Unable to load account details."))).finally(() => setLoading(false));
  }, []);
  const email = user?.email || localStorage.getItem("username") || "investigator";
  const initials = (user?.full_name || email).split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((part) => part[0].toUpperCase()).join("") || "IN";
  return <div className="page"><div className="page-header"><div><h2>Account</h2><p>Account information, security and audit history.</p></div></div>
    {error && <div className="case-notice">{error}</div>}
    <div className="account-layout"><div className="account-profile-card"><div className="account-avatar">{initials}</div><div><h3>{user?.full_name || email}</h3><p>{user?.role || "Investigator"}</p></div><span className="account-active"><span className="status-dot"/>Active</span></div>
      <div className="account-section"><div className="section-header"><div><h3>Account Information</h3><p>Information returned by the authenticated backend account.</p></div></div><div className="account-info-grid"><div className="account-info-card"><span>Full name</span><strong>{user?.full_name || "Not provided"}</strong></div><div className="account-info-card"><span>Email</span><strong>{email}</strong></div><div className="account-info-card"><span>Role</span><strong>{user?.role || "—"}</strong></div><div className="account-info-card"><span>User ID</span><strong>{user?.id || "Loading..."}</strong></div></div></div>
      <div className="account-section"><div className="section-header"><div><h3>Security</h3><p>Current authentication status.</p></div></div><div className="security-status"><div className="security-status-icon">✓</div><div><strong>Authenticated Session</strong><p>Your session is validated against the backend using a signed access token.</p></div></div></div>
      <div className="account-section"><div className="section-header"><div><h3>Audit Log</h3><p>Activity entries recorded for your account.</p></div></div>{loading ? <Loading/> : logs.length === 0 ? <p className="muted-copy">No audit entries have been recorded for this account yet.</p> : <div className="audit-list">{logs.map((entry) => <div className="simple-record" key={entry.id}><strong>{entry.action}</strong><p>{entry.resource_type}{entry.resource_id ? ` · ${entry.resource_id}` : ""}</p><span>{new Date(entry.created_at).toLocaleString()}</span>{entry.details && <pre>{JSON.stringify(entry.details, null, 2)}</pre>}</div>)}</div>}</div>
    </div></div>;
};
export default Account;
