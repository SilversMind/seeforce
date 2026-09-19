const FEATURES: { icon: React.ReactNode; title: string; desc: string }[] = [
  {
    icon: (
      <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
    ),
    title: "Get your product's codebase map",
    desc: "Point it at your repo. AI drafts C4 annotations describing how it works. Review or correct as needed.",
  },
  {
    icon: (
      <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    ),
    title: "Always in sync",
    desc: "Annotations live right in your source files, so they move with the code instead of drifting into a stale wiki.",
  },
  {
    icon: (
      <>
        <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
        <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
        <line x1="6" y1="6" x2="6.01" y2="6" />
        <line x1="6" y1="18" x2="6.01" y2="18" />
      </>
    ),
    title: "MCP server built-in",
    desc: "Your AI assistant gets live architecture context instantly. Prevent bad implementation decisions. Keep the codebase readable. Save tokens.",
  },
  {
    icon: (
      <>
        <line x1="6" y1="3" x2="6" y2="15" />
        <circle cx="18" cy="6" r="3" />
        <circle cx="6" cy="18" r="3" />
        <path d="M18 9a9 9 0 0 1-9 9" />
      </>
    ),
    title: "GitHub-native",
    desc: "Import and sync your architecture straight from your repo.",
  },
];

export default function LoginPage() {
  return (
    <div style={{ position: "relative", minHeight: "100vh", overflow: "hidden", background: "var(--c4-page-bg)" }}>
      <div className="login-bg-grid" aria-hidden="true" />
      <div className="login-bg-sweep" aria-hidden="true" />
      <div
        style={{
          position: "relative",
          zIndex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "4rem 1.5rem",
          gap: "3rem",
          fontFamily: "system-ui, sans-serif",
          color: "var(--c4-text-primary)",
        }}
      >
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1.5rem" }}>
        <h1 style={{ margin: 0, fontSize: "2.5rem", fontWeight: 700 }}>SeeForce</h1>
        <p style={{ margin: 0, color: "var(--c4-text-muted)", fontSize: "1.1rem", textAlign: "center", maxWidth: "28rem" }}>
          See what your project's codebase really looks like. AI adds the blocks, but you build the product.
        </p>

        <a
          href="/accounts/github/login/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.6rem",
            padding: "0.65rem 1.4rem",
            background: "#238636",
            color: "#fff",
            borderRadius: "6px",
            textDecoration: "none",
            fontWeight: 500,
            fontSize: "0.95rem",
            border: "1px solid rgba(240,246,252,0.1)",
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.73.083-.73 1.205.085 1.84 1.237 1.84 1.237 1.07 1.834 2.807 1.304 3.492.997.108-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.31.468-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.3 1.23A11.51 11.51 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.29-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.015 2.898-.015 3.293 0 .322.216.694.825.576C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12z" />
          </svg>
          Connect with GitHub
        </a>

        <button
          disabled
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.6rem",
            padding: "0.6rem 1.3rem",
            background: "transparent",
            color: "var(--c4-text-muted)",
            borderRadius: "6px",
            fontWeight: 500,
            fontSize: "0.9rem",
            border: "1px solid var(--c4-border)",
            cursor: "not-allowed",
          }}
        >
          Connect with GitLab
          <span
            style={{
              fontSize: "0.7rem",
              fontWeight: 600,
              letterSpacing: "0.03em",
              textTransform: "uppercase",
              padding: "0.15rem 0.45rem",
              borderRadius: "999px",
              border: "1px solid var(--c4-border)",
            }}
          >
            Soon
          </span>
        </button>
      </div>

      <ul
        style={{
          listStyle: "none",
          margin: 0,
          padding: 0,
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "1.75rem",
          maxWidth: "50rem",
          width: "100%",
        }}
      >
        {FEATURES.map((f) => (
          <li
            key={f.title}
            style={{ display: "flex", gap: "0.85rem", alignItems: "flex-start", flex: "1 1 15rem", maxWidth: "15rem" }}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ flexShrink: 0, marginTop: "0.15rem", color: "var(--c4-text-muted)" }}
              aria-hidden="true"
            >
              {f.icon}
            </svg>
            <div>
              <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>{f.title}</div>
              <div style={{ color: "var(--c4-text-muted)", fontSize: "0.85rem", lineHeight: 1.4 }}>{f.desc}</div>
            </div>
          </li>
        ))}
      </ul>
      </div>
    </div>
  );
}
