import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import { ChatWidget } from "@/components/ChatWidget";
import Landing from "@/pages/Landing";
import AuthPage from "@/pages/AuthPage";
import AuthPortal from "@/pages/AuthPortal";
import Overview from "@/pages/Overview";
import UrlScanner from "@/pages/UrlScanner";
import AiDetector from "@/pages/AiDetector";
import EmailDetector from "@/pages/EmailDetector";
import History from "@/pages/History";
import Embed from "@/pages/Embed";
import Extension from "@/pages/Extension";
import BulkScanner from "@/pages/BulkScanner";
import SafeSites from "@/pages/SafeSites";
import Settings from "@/pages/Settings";

import DeepfakeScanner from "@/components/DeepfakeScanner";
import AdminUsers from "@/pages/AdminUsers";
 
function Protected({ children }) {
  const { user } = useAuth();
  if (user === null) return <div className="min-h-screen flex items-center justify-center text-slate-400">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AdminOnly({ children }) {
  const { user } = useAuth();
  if (!user || user.role !== "admin") return <Navigate to="/console" replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<AuthPortal />} />
          <Route path="/login/admin" element={<AuthPage mode="login" role="admin" />} />
          <Route path="/login/user" element={<AuthPage mode="login" role="user" />} />
          <Route path="/register/user" element={<AuthPage mode="register" role="user" />} />
          <Route path="/register" element={<Navigate to="/login" replace />} />
          <Route path="/console" element={<Protected><Layout /></Protected>}>
            <Route index element={<Overview />} />
            <Route path="url" element={<UrlScanner />} />
            <Route path="ai" element={<AiDetector />} />
            <Route path="email" element={<EmailDetector />} />
            <Route path="deepfake" element={<DeepfakeScanner />} />
            <Route path="history" element={<History />} />
            <Route path="embed" element={<Embed />} />
            <Route path="extension" element={<Extension />} />
            <Route path="bulk" element={<BulkScanner />} />
            <Route path="safe-sites" element={<SafeSites />} />
            <Route path="settings" element={<Settings />} />
            <Route path="admin" element={<AdminOnly><AdminUsers /></AdminOnly>} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <ChatWidget />
        <Toaster theme="dark" position="top-right" richColors />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
