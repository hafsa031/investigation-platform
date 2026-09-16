
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../services/api";

const Login = () => {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!username.trim() || !password) {
      setError("Username and password are required.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const response = await login({
        username: username.trim(),
        password,
      });

      localStorage.setItem(
  "access_token",
  response.access_token
);

localStorage.setItem(
  "username",
  username.trim()
);

      navigate("/dashboard");
    } catch (err) {
      console.error(err);
      setError("Invalid username or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-background-grid"></div>

      <div className="login-container">
        <div className="login-brand">
          <div className="logo-mark">J</div>

          <div>
            <strong>JAGSPIRE</strong>
            <span>INVESTIGATION PLATFORM</span>
          </div>
        </div>

        <div className="login-card">
          <div className="login-card-header">
            <div className="login-security-icon">◈</div>

            <div>
              <span className="login-eyebrow">
                SECURE ACCESS
              </span>

              <h1>Investigator Login</h1>

              <p>
                Sign in to access your investigation workspace.
              </p>
            </div>
          </div>

          <div className="login-divider"></div>

          <form onSubmit={handleLogin} className="login-form">
            <label>
              <span>Username</span>

              <input
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(event) =>
                  setUsername(event.target.value)
                }
                disabled={loading}
                autoComplete="username"
              />
            </label>

            <label>
              <span>Password</span>

              <input
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                disabled={loading}
                autoComplete="current-password"
              />
            </label>

            {error && (
              <div className="login-error">
                <span>!</span>
                {error}
              </div>
            )}

            <button
              type="submit"
              className="primary-button login-button"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="login-spinner"></span>
                  Authenticating...
                </>
              ) : (
                <>
                  Sign In
                  <span>→</span>
                </>
              )}
            </button>
          </form>

          <div className="login-status">
            <span className="status-dot"></span>
            Investigation services operational
          </div>
        </div>

        <div className="login-footer">
          <span>
            AI Evidence Correlation & Digital Investigation Platform
          </span>

          <span>V1.0</span>
        </div>
      </div>
    </div>
  );
};

export default Login;

