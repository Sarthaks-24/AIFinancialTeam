import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/Common/ProtectedRoute";
import MainLayout from "./layout/MainLayout";
import { ChatProvider } from "./context/ChatContext";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Tasks from "./pages/Tasks";
import Reports from "./pages/Reports";
import KPI from "./pages/KPI";
import Chat from "./pages/Chat";
import History from "./pages/History";
import Settings from "./pages/Settings";
import FinanceData from "./pages/FinanceData";
import Reconciliation from "./pages/Reconciliation";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ChatProvider>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="tasks" element={<Tasks />} />
            <Route path="reports" element={<Reports />} />
            <Route path="kpi" element={<KPI />} />
            <Route path="chat" element={<Navigate to="/talk" replace />} />
            <Route path="talk" element={<Chat />} />
            <Route path="history" element={<History />} />
            <Route path="financial-data" element={<FinanceData />} />
            <Route path="reconciliation" element={<Reconciliation />} />
            <Route path="settings" element={<Settings />} />
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        </ChatProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;