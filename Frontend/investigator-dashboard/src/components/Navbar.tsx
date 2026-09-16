const Navbar = () => {
  return (
    <header className="navbar">
      <div>
        <h1>Investigator Dashboard</h1>
        <p>AI Evidence Correlation & Digital Investigation Platform</p>
      </div>

      <div className="investigator">
        <div className="avatar">IN</div>

        <div>
          <strong>Investigator</strong>
          <span>Active Session</span>
        </div>
      </div>
    </header>
  );
};

export default Navbar;