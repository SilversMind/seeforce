/*
@c2:container
name: Frontend
system: SeeForce
technology: React
description: Display architecture data as a comprehensive graph
uses:
  - Backend: "Fetches workspace and graph data via REST API over HTTP"
*/
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
