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
      <h1 style={{ margin: 0 }}>SeeForce</h1>
      <p style={{ margin: 0, color: "#666" }}>Visualize your C4 architecture.</p>
      <a
        href="/accounts/github/login/"
        style={{
          padding: "0.6rem 1.4rem",
          background: "#24292f",
          color: "#fff",
          borderRadius: "6px",
          textDecoration: "none",
          fontWeight: 500,
        }}
      >
        Se connecter avec GitHub
      </a>
    </div>
  );
}
