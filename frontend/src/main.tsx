/*
@c2:container
name: Frontend
system: SeeForce
technology: React
description: |
  - Renders a project's architecture graph
  - Shows what a pull request changes in the architecture
  - Lets users edit overlays, tags and lexicon entries
  - Gates routes behind sign-in
short_desc: Renders the architecture graph and handles auth-gated routing
uses:
  - Backend:
    - "fetches graph data"
    - "manages the user session"
    short_desc: "fetches graph data, manages session"
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
