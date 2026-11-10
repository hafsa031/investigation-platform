const Account = () => {
  const username =
    localStorage.getItem("username") ||
    "investigator";

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Account</h2>
          <p>
            Manage your investigator session and account
            information.
          </p>
        </div>
      </div>

      <div className="account-layout">
        <div className="account-profile-card">
          <div className="account-avatar">
            IN
          </div>

          <div>
            <h3>{username}</h3>
            <p>Investigator</p>
          </div>

          <span className="account-active">
            <span className="status-dot"></span>
            Active
          </span>
        </div>

        <div className="account-section">
          <div className="section-header">
            <div>
              <h3>Account Information</h3>
              <p>
                Information associated with the current
                investigation session.
              </p>
            </div>
          </div>

          <div className="account-info-grid">
            <div className="account-info-card">
              <span>Username</span>
              <strong>{username}</strong>
            </div>

            <div className="account-info-card">
              <span>Role</span>
              <strong>Investigator</strong>
            </div>

            <div className="account-info-card">
              <span>Session</span>
              <strong>Authenticated</strong>
            </div>

            <div className="account-info-card">
              <span>Platform</span>
              <strong>Jagspire Investigation Platform</strong>
            </div>
          </div>
        </div>

        <div className="account-section">
          <div className="section-header">
            <div>
              <h3>Security</h3>
              <p>
                Current authentication status.
              </p>
            </div>
          </div>

          <div className="security-status">
            <div className="security-status-icon">
              ✓
            </div>

            <div>
              <strong>Authenticated Session</strong>
              <p>
                Your session is authenticated using a
                secure access token.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Account;
