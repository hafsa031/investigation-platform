import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getApiError, login, register, requestPasswordReset, resetPassword } from "../services/api";

const Login = () => {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register" | "forgot" | "reset">("login");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(""); setNotice("");
    if (!email.trim()) { setError("Email is required."); return; }
    if (mode === "forgot") {
      setLoading(true);
      try { const result = await requestPasswordReset(email.trim()); setNotice(result.reset_token ? `${result.message} Demo reset token: ${result.reset_token}` : result.message); if (result.reset_token) { setResetToken(result.reset_token); setMode("reset"); } }
      catch (err) { setError(getApiError(err, "Could not request a password reset.")); }
      finally { setLoading(false); }
      return;
    }
    if (mode === "reset") {
      if (!resetToken.trim() || !password) { setError("Reset token and new password are required."); return; }
      if (password.length < 8) { setError("Password must contain at least 8 characters."); return; }
      setLoading(true);
      try { const result = await resetPassword(resetToken.trim(), password); setNotice(result.message); setMode("login"); setPassword(""); setConfirmPassword(""); setResetToken(""); }
      catch (err) { setError(getApiError(err, "Could not reset the password.")); }
      finally { setLoading(false); }
      return;
    }
    if (!password) { setError("Password is required."); return; }
    if (mode === "register" && password.length < 8) { setError("Password must contain at least 8 characters."); return; }
    if (mode === "register" && password !== confirmPassword) { setError("Passwords do not match."); return; }
    setLoading(true);
    try {
      if (mode === "register") {
        await register({ email: email.trim(), password, full_name: fullName.trim() || undefined });
        setNotice("Account created. Sign in with your new credentials."); setMode("login"); setPassword(""); setConfirmPassword("");
      } else {
        const response = await login({ username: email.trim(), password });
        localStorage.setItem("access_token", response.access_token);
        localStorage.setItem("username", email.trim());
        navigate("/dashboard", { replace: true });
      }
    } catch (err) { setError(getApiError(err, mode === "register" ? "Unable to create account." : "Invalid email or password.")); }
    finally { setLoading(false); }
  };

  return <div className="login-page"><div className="login-background-grid"/><div className="login-container">
    <div className="login-brand"><div className="logo-mark">J</div><div><strong>JAGSPIRE</strong><span>INVESTIGATION PLATFORM</span></div></div>
    <div className="login-card"><div className="login-card-header"><div className="login-security-icon">◈</div><div><span className="login-eyebrow">SECURE ACCESS</span><h1>{mode === "login" ? "Investigator Login" : mode === "register" ? "Create your account" : mode === "forgot" ? "Reset your password" : "Choose a new password"}</h1><p>{mode === "login" ? "Sign in to access your investigation workspace." : mode === "register" ? "Register to create a secure investigator workspace." : mode === "forgot" ? "Generate a password reset token for your account." : "Enter the reset token and your new password."}</p></div></div>
      <div className="login-divider"/><form onSubmit={handleSubmit} className="login-form">
        {mode === "register" && <label><span>Full name</span><input type="text" placeholder="Enter your name" value={fullName} onChange={(e) => setFullName(e.target.value)} disabled={loading} autoComplete="name"/></label>}
        <label><span>Email</span><input type="email" placeholder="Enter your email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={loading} autoComplete="email" required/></label>
        {mode !== "forgot" && <label><span>{mode === "reset" ? "New password" : "Password"}</span><input type="password" placeholder={mode === "register" || mode === "reset" ? "At least 8 characters" : "Enter your password"} value={password} onChange={(e) => setPassword(e.target.value)} disabled={loading} autoComplete={mode === "register" || mode === "reset" ? "new-password" : "current-password"} required/></label>}
        {mode === "reset" && <label><span>Reset token</span><input value={resetToken} onChange={(e) => setResetToken(e.target.value)} placeholder="Paste your reset token" disabled={loading} required/></label>}
        {mode === "register" && <label><span>Confirm password</span><input type="password" placeholder="Re-enter your password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} disabled={loading} autoComplete="new-password" required/></label>}
        {error && <div className="login-error"><span>!</span>{error}</div>}{notice && <div className="case-notice">{notice}</div>}
        <button type="submit" className="primary-button login-button" disabled={loading}>{loading ? "Please wait..." : mode === "login" ? "Sign In →" : mode === "register" ? "Create Account →" : mode === "forgot" ? "Generate Reset Token →" : "Reset Password →"}</button>
      </form>
      <div className="auth-switch">{mode === "login" ? <><span>New to Jagspire?</span><button type="button" className="text-button" onClick={() => { setMode("register"); setError(""); setNotice(""); }}>Create account</button><button type="button" className="text-button" onClick={() => { setMode("forgot"); setError(""); setNotice(""); }}>Forgot password?</button></> : <><span>Return to your account?</span><button type="button" className="text-button" onClick={() => { setMode("login"); setError(""); setNotice(""); }}>Sign in</button></>}</div>
      <div className="login-status"><span className="status-dot"/>Investigation services operational</div>
    </div><div className="login-footer"><span>AI Evidence Correlation & Digital Investigation Platform</span><span>V2.0</span></div>
  </div></div>;
};
export default Login;
