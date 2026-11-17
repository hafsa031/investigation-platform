import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { getDatabaseHealth, getServiceHealth } from "../services/api";

const Sidebar = () => {
  const navigate = useNavigate();
  const [serviceOnline, setServiceOnline] = useState<boolean | null>(null);
  useEffect(() => {
    Promise.all([getServiceHealth(), getDatabaseHealth()]).then(() => setServiceOnline(true)).catch(() => setServiceOnline(false));
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    navigate("/login");
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-mark">J</div>
        <span>JAGSPIRE</span>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/dashboard"
          className={({ isActive }) =>
            isActive
              ? "nav-item active"
              : "nav-item"
          }
        >
          <span>▦</span>
          Dashboard
        </NavLink>

        <NavLink
          to="/cases"
          className={({ isActive }) =>
            isActive
              ? "nav-item active"
              : "nav-item"
          }
        >
          <span>◫</span>
          Cases
        </NavLink>

        

        <NavLink
          to="/evidence"
          className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}
        >
          <span>◈</span>
          Evidence Explorer
        </NavLink>

        <NavLink
          to="/account"
          className={({ isActive }) =>
            isActive
              ? "nav-item active"
              : "nav-item"
          }
        >
          <span>◎</span>
          Account
        </NavLink>
      </nav>

      <div className="sidebar-bottom">
        <div className="system-status">
          <span className="status-dot" style={{ background: serviceOnline === false ? "#e16d78" : serviceOnline === true ? "#43d17b" : "#7f8a9b" }}></span>
          {serviceOnline === true ? "API & Database Online" : serviceOnline === false ? "Backend Unavailable" : "Checking Services..."}
        </div>

        <button
          className="logout-button"
          onClick={handleLogout}
        >
          Logout
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
