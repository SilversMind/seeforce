export default function LoginPage() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        gap: "1.5rem",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <h1 style={{ margin: 0, fontSize: "2.5rem", fontWeight: 700, color: "#f0f6fc" }}>
        SeeForce
      </h1>
      <p style={{ margin: 0, color: "#8b949e", fontSize: "1rem" }}>
        Visualize your C4 architecture.
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
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.73.083-.73 1.205.085 1.84 1.237 1.84 1.237 1.07 1.834 2.807 1.304 3.492.997.108-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.31.468-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.3 1.23A11.51 11.51 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.29-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.015 2.898-.015 3.293 0 .322.216.694.825.576C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12z" />
        </svg>
        Se connecter avec GitHub
      </a>
    </div>
  );
}
