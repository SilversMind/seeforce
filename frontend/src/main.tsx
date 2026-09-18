/*
@c2:container
name: Frontend
system: SeeForce
technology: React
description: Display architecture data as a comprehensive graph; handles auth-gated routing
short_desc: Renders the architecture graph and handles auth-gated routing
uses:
  - Backend: "Fetches graph data and manages user session (auth)"
    technology: REST
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
