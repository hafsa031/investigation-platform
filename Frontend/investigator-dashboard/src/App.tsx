import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Cases from "./pages/Cases";
import CaseDetails from "./pages/CaseDetails";

import Account from "./pages/Account";

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route
          path="*"
          element={
            <div className="app">
              <Sidebar />

              <main className="main-content">
                <Navbar />

                <Routes>
                  <Route
                    path="/"
                    element={<Navigate to="/dashboard" replace />}
                  />

                  <Route
                    path="/dashboard"
                    element={<Dashboard />}
                  />

                  <Route
                    path="/cases"
                    element={<Cases />}
                  />

                  <Route
                    path="/cases/:caseId"
                    element={<CaseDetails />}
                  />

                  

                  <Route
  path="/account"
  element={<Account />}
/>

                  <Route
                    path="*"
                    element={<Navigate to="/dashboard" replace />}
                  />

                </Routes>
              </main>
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  );
};

export default App;