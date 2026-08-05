import { BrowserRouter, Routes, Route } from "react-router-dom";
import { GraphView } from "./pages/GraphView";
import { HomePage } from "./pages/HomePage";
import { UploadPanel } from "./components/UploadPanel";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route
          path="/project/new"
          element={
            <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column" }}>
              <header style={{ height: 48, background: "#0f172a", display: "flex", alignItems: "center", padding: "0 20px", flexShrink: 0 }}>
                <span style={{ color: "white", fontWeight: 700, fontSize: 16 }}>SeeForce</span>
              </header>
              <div style={{ flex: 1 }}>
                <UploadPanel />
              </div>
            </div>
          }
        />
        <Route path="/project/:id" element={<GraphView />} />
      </Routes>
    </BrowserRouter>
  );
}
