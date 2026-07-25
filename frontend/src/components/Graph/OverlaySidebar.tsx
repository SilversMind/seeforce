import { useState, useEffect } from "react";
import { type RFNode, type RFEdge, upsertNodeOverlay, upsertEdgeOverlay } from "../../services/api";

type SidebarTarget =
  | { kind: "node"; node: RFNode }
  | { kind: "edge"; edge: RFEdge };

interface Props {
  target: SidebarTarget | null;
  projectMapId: number;
  onClose: () => void;
  onSaved: () => void;
}

const TYPE_LABELS: Record<string, string> = {
  system: "System",
  container: "Container",
  component: "Component",
  person: "Person",
  external: "External",
};

const TYPE_COLORS: Record<string, string> = {
  system: "var(--c4-system-border)",
  container: "var(--c4-container-border)",
  component: "var(--c4-component-border)",
  person: "var(--c4-person-border)",
  external: "var(--c4-external-border)",
};

export function OverlaySidebar({ target, projectMapId, onClose, onSaved }: Props) {
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [edgeLabel, setEdgeLabel] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!target) return;
    if (target.kind === "node") {
      setDisplayName(target.node.data.overlay_label ?? "");
      setDescription(target.node.data.overlay_description ?? "");
    } else {
      setEdgeLabel(target.edge.data?.overlay_label ?? "");
    }
  }, [target]);

  const open = target !== null;

  async function handleSave() {
    setSaving(true);
    try {
      if (target!.kind === "node") {
        await upsertNodeOverlay(
          projectMapId,
          target!.node.data.overlay_key,
          displayName,
          description,
        );
      } else {
        await upsertEdgeOverlay(projectMapId, target!.edge.id, edgeLabel);
      }
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  const isNode = open && target!.kind === "node";
  const nodeType = isNode ? target!.node.type : "";
  const typeColor = TYPE_COLORS[nodeType] ?? "var(--c4-external-border)";
  const typeLabel = TYPE_LABELS[nodeType] ?? "Relationship";

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        right: 0,
        width: 300,
        transform: open ? "translateX(0)" : "translateX(100%)",
        transition: "transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
        height: "100%",
        background: "var(--c4-sidebar-bg, #1e293b)",
        borderLeft: "1px solid var(--c4-sidebar-border, #334155)",
        display: "flex",
        flexDirection: "column",
        zIndex: 20,
        fontSize: 13,
        color: "var(--c4-sidebar-text, #e2e8f0)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "12px 16px",
          borderBottom: "1px solid var(--c4-sidebar-border, #334155)",
          gap: 8,
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            padding: "2px 8px",
            borderRadius: 4,
            background: typeColor,
            color: "#fff",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          {isNode ? typeLabel : "Relationship"}
        </span>
        <button
          onClick={onClose}
          style={{
            marginLeft: "auto",
            background: "none",
            border: "none",
            color: "var(--c4-sidebar-muted, #64748b)",
            fontSize: 18,
            cursor: "pointer",
            lineHeight: 1,
          }}
        >
          ×
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 16 }}>
        {open && isNode ? (
          <>
            <Section label="Code name">
              <ReadValue>{target!.node.data.label}</ReadValue>
            </Section>
            {target!.node.data.description && (
              <Section label="Code description">
                <ReadValue muted>{target!.node.data.description}</ReadValue>
              </Section>
            )}
            <div style={{ borderTop: "1px solid var(--c4-sidebar-border, #334155)", paddingTop: 16 }}>
              <p style={{ fontSize: 11, color: "var(--c4-sidebar-muted, #64748b)", marginBottom: 12 }}>
                OVERLAY — overrides displayed values
              </p>
              <Section label="Display name">
                <input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder={target!.node.data.label}
                  style={inputStyle}
                />
              </Section>
              <Section label="Description" style={{ marginTop: 12 }}>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={target!.node.data.description || "Add a description…"}
                  rows={4}
                  style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
                />
              </Section>
            </div>
          </>
        ) : open ? (
          <>
            <Section label="Code label">
              <ReadValue>{(target!.edge.label as string) || "—"}</ReadValue>
            </Section>
            <div style={{ borderTop: "1px solid var(--c4-sidebar-border, #334155)", paddingTop: 16 }}>
              <p style={{ fontSize: 11, color: "var(--c4-sidebar-muted, #64748b)", marginBottom: 12 }}>
                OVERLAY — overrides displayed label
              </p>
              <Section label="Label">
                <input
                  value={edgeLabel}
                  onChange={(e) => setEdgeLabel(e.target.value)}
                  placeholder={(target!.edge.label as string) || "Override label…"}
                  style={inputStyle}
                />
              </Section>
            </div>
          </>
        ) : null}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: "12px 16px",
          borderTop: "1px solid var(--c4-sidebar-border, #334155)",
          display: "flex",
          gap: 8,
        }}
      >
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            flex: 1,
            background: "#3b82f6",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            padding: "8px 0",
            fontSize: 13,
            fontWeight: 600,
            cursor: saving ? "not-allowed" : "pointer",
            opacity: saving ? 0.7 : 1,
          }}
        >
          {saving ? "Saving…" : "Save overlay"}
        </button>
        <button
          onClick={() => {
            if (isNode) { setDisplayName(""); setDescription(""); }
            else setEdgeLabel("");
          }}
          style={{
            background: "none",
            color: "var(--c4-sidebar-muted, #64748b)",
            border: "1px solid var(--c4-sidebar-border, #334155)",
            borderRadius: 6,
            padding: "8px 12px",
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          Reset
        </button>
      </div>
    </div>
  );
}

function Section({ label, children, style }: { label: string; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={style}>
      <label style={{ display: "block", fontSize: 11, color: "var(--c4-sidebar-muted, #64748b)", marginBottom: 4, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {label}
      </label>
      {children}
    </div>
  );
}

function ReadValue({ children, muted }: { children: React.ReactNode; muted?: boolean }) {
  return (
    <div style={{ fontSize: 13, color: muted ? "var(--c4-sidebar-muted, #64748b)" : "var(--c4-sidebar-text, #e2e8f0)" }}>
      {children}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "var(--c4-sidebar-input-bg, #0f172a)",
  border: "1px solid var(--c4-sidebar-border, #334155)",
  borderRadius: 6,
  padding: "6px 10px",
  fontSize: 13,
  color: "var(--c4-sidebar-text, #e2e8f0)",
  outline: "none",
  boxSizing: "border-box",
};
