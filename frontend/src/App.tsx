import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import LoginPage from "./pages/LoginPage";
import { GraphView } from "./pages/GraphView";
import { HomePage } from "./pages/HomePage";
import { UploadPanel } from "./components/UploadPanel";

function NewProjectShell() {
  const navigate = useNavigate();
  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{ height: 48, background: "#0f172a", display: "flex", alignItems: "center", padding: "0 20px", flexShrink: 0 }}>
        <span onClick={() => navigate("/")} style={{ color: "white", fontWeight: 700, fontSize: 16, cursor: "pointer" }}>SeeForce</span>
      </header>
      <div style={{ flex: 1 }}>
        <UploadPanel />
      </div>
    </div>
  );
}

function AppRoutes() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
        }}
      >
        Loading…
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/project/new" element={<NewProjectShell />} />
      <Route path="/project/:id" element={<GraphView />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
