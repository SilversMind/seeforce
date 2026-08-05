import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
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

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/project/new" element={<NewProjectShell />} />
        <Route path="/project/:id" element={<GraphView />} />
      </Routes>
    </BrowserRouter>
  );
}
