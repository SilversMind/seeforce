/** The SeeForce lockup — eye mark plus wordmark — as it appears in every app header. */
export function BrandMark({ onClick }: { onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        cursor: onClick ? "pointer" : "default",
        userSelect: "none",
      }}
    >
      <img src="/logo-mark.svg" alt="" width={26} height={20} style={{ display: "block" }} />
      <span style={{ color: "white", fontWeight: 700, fontSize: 16 }}>SeeForce</span>
    </div>
  );
}
