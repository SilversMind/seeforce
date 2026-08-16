import { useEffect } from "react";
import type { LexiconEntry } from "../../lib/lexicon";

interface Props {
  entry: LexiconEntry | null;
  onClose: () => void;
}

export function LexiconBottomPanel({ entry, onClose }: Props) {
  useEffect(() => {
    if (!entry) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [entry, onClose]);

  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        height: "clamp(100px, 18vh, 180px)",
        transform: entry ? "translateY(0)" : "translateY(100%)",
        transition: "transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
        background: "var(--c4-sidebar-bg)",
        borderTop: "1px solid var(--c4-sidebar-border)",
        zIndex: 30,
        display: "flex",
        flexDirection: "column",
        fontSize: 13,
        color: "var(--c4-sidebar-text)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "8px 16px",
          borderBottom: "1px solid var(--c4-sidebar-border)",
          gap: 8,
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontWeight: 700,
            fontSize: 13,
            color: "var(--c4-system-border)",
          }}
        >
          {entry?.term}
        </span>
        <button
          onClick={onClose}
          style={{
            marginLeft: "auto",
            background: "none",
            border: "none",
            color: "var(--c4-sidebar-muted)",
            fontSize: 18,
            cursor: "pointer",
            lineHeight: 1,
          }}
        >
          ×
        </button>
      </div>
      <div
        style={{
          flex: 1,
          padding: "8px 16px",
          overflowY: "auto",
          color: "var(--c4-sidebar-text)",
        }}
      >
        {entry?.definition}
      </div>
    </div>
  );
}
