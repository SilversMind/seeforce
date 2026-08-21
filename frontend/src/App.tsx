import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import LoginPage from "./pages/LoginPage";
import { GraphView } from "./pages/GraphView";
import { HomePage } from "./pages/HomePage";
import { PreviewPage } from "./pages/PreviewPage";
import { SharePage } from "./pages/SharePage";

function AppRoutes() {
  const { user, isLoading } = useAuth();

  return (
    <Routes>
      {/* Public share route — no auth required */}
      <Route path="/share/:token" element={<SharePage />} />

      {/* Auth-gated routes */}
      <Route path="*" element={
        isLoading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
            Loading…
          </div>
        ) : !user ? (
          <LoginPage />
        ) : (
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/project/:id" element={<GraphView />} />
            <Route path="/preview" element={<PreviewPage />} />
          </Routes>
        )
      } />
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
