import type { ReactElement } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import AppShell from "./components/AppShell";
import { getToken } from "./api";
import ClaimsMgmt from "./pages/ClaimsMgmt";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Reports from "./pages/Reports";
import Results from "./pages/Results";
import ResultsList from "./pages/ResultsList";
import Signup from "./pages/Signup";

function RequireAuth({ children }: { children: ReactElement }) {
  const loc = useLocation();
  if (!getToken()) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="claims-mgmt" element={<ClaimsMgmt />} />
        <Route path="results" element={<ResultsList />} />
        <Route path="results/:claimId" element={<Results />} />
        <Route path="reports" element={<Reports />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
