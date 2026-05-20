import type { ReactElement } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import AppShell from "./components/AppShell";
import { getToken } from "./api";
import Accounts from "./pages/Accounts";
import ClaimsMgmt from "./pages/ClaimsMgmt";
import Cats from "./pages/Cats";
import Dashboard from "./pages/Dashboard";
import DataWarehouse from "./pages/DataWarehouse";
import Expenses from "./pages/Expenses";
import Login from "./pages/Login";
import Reports from "./pages/Reports";
import Results from "./pages/Results";

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
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="claims-mgmt" element={<ClaimsMgmt />} />
        <Route path="cats" element={<Cats />} />
        <Route path="expenses" element={<Expenses />} />
        <Route path="accounts" element={<Accounts />} />
        <Route path="data-warehouse" element={<DataWarehouse />} />
        <Route path="reports" element={<Reports />} />
        <Route path="results/:claimId" element={<Results />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
