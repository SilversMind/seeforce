import { useState, useEffect } from "react";
import { mutate } from "swr";
import { type RFNode, type RFEdge, upsertNodeOverlay, upsertEdgeOverlay, upsertLexiconEntry, deleteLexiconEntry } from "../../services/api";
import { useLexicon } from "../../contexts/LexiconContext";

type SidebarTarget =
  | { kind: "node"; node: RFNode }
  | { kind: "edge"; edge: RFEdge };

interface Props {
  target: SidebarTarget | null;
  projectMapId: number;
  onClose: () => void;
  onSaved: () => void;
  onLexiconSaved: () => void;
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

export function OverlaySidebar({ target, projectMapId, onClose, onSaved, onLexiconSaved }: Props) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [edgeLabel, setEdgeLabel] = useState("");
  const [saving, setSaving] = useState(false);

  const { lexicon } = useLexicon();
  const [lexTerm, setLexTerm] = useState("");
  const [lexDef, setLexDef] = useState("");
  const [lexSaving, setLexSaving] = useState(false);

  useEffect(() => {
    setEditing(false);
    setLexTerm("");
    setLexDef("");
  }, [target]);

  async function handleLexiconSave() {
    if (!lexTerm.trim() || !lexDef.trim()) return;
    setLexSaving(true);
    try {
      await upsertLexiconEntry(projectMapId, lexTerm.trim(), lexDef.trim());
      await mutate(`/api/graph/${projectMapId}/lexicon/`);
      onLexiconSaved();
      setLexTerm("");
      setLexDef("");
    } finally {
      setLexSaving(false);
    }
  }

  async function handleLexiconDelete(term: string) {
    try {
      await deleteLexiconEntry(projectMapId, term);
      await mutate(`/api/graph/${projectMapId}/lexicon/`);
      onLexiconSaved();
    } catch (err) {
      console.error("Failed to delete lexicon entry:", err);
    }
  }

  function startEdit() {
    if (!target) return;
    if (target.kind === "node") {
      setName(target.node.data.overlay_label ?? "");
      setDescription(target.node.data.overlay_description ?? "");
    } else {
      setEdgeLabel(target.edge.data?.overlay_label ?? "");
    }
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
  }

  async function handleSave() {
    setSaving(true);
    try {
      if (target!.kind === "node") {
        await upsertNodeOverlay(projectMapId, target!.node.data.overlay_key, name, description);
      } else {
        await upsertEdgeOverlay(projectMapId, target!.edge.id, edgeLabel);
      }
      setEditing(false);
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  const open = target !== null;
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
        width: "clamp(300px, 30vw, 560px)",
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
        {!editing && (
          <button
            onClick={startEdit}
            style={{
              marginLeft: "auto",
              background: "none",
              border: "1px solid var(--c4-sidebar-border, #334155)",
              color: "var(--c4-sidebar-muted, #64748b)",
              borderRadius: 5,
              padding: "3px 10px",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            Edit
          </button>
        )}
        <button
          onClick={onClose}
          style={{
            marginLeft: editing ? "auto" : 0,
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
            <Section label="Name">
              {editing ? (
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={target!.node.data.label}
                  style={inputStyle}
                  autoFocus
                />
              ) : (
                <ReadValue>{target!.node.data.overlay_label || target!.node.data.label}</ReadValue>
              )}
            </Section>
            <Section label="Description">
              {editing ? (
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={target!.node.data.description || "Add a description…"}
                  rows={4}
                  style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
                />
              ) : (
                <ReadValue muted>
                  {target!.node.data.overlay_description || target!.node.data.description || "—"}
                </ReadValue>
              )}
            </Section>
            {/* Lexicon section — only in edit mode for nodes */}
            {editing && (
              <Section label="Lexique">
                {(() => {
                  const desc = target!.node.data.overlay_description || target!.node.data.description || "";
                  const relevant = lexicon.filter((e) =>
                    desc.toLowerCase().includes(e.term.toLowerCase())
                  );
                  return relevant.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
                      {relevant.map((e) => (
                        <div
                          key={e.term}
                          style={{
                            display: "flex",
                            alignItems: "flex-start",
                            gap: 6,
                            padding: "4px 8px",
                            background: "var(--c4-sidebar-input-bg)",
                            borderRadius: 4,
                            border: "1px solid var(--c4-sidebar-border)",
                          }}
                        >
                          <span style={{ fontWeight: 600, color: "var(--c4-system-border)", minWidth: 60, fontSize: 12 }}>
                            {e.term}
                          </span>
                          <span style={{ flex: 1, color: "var(--c4-sidebar-muted)", fontSize: 12 }}>
                            {e.definition}
                          </span>
                          <button
                            onClick={() => handleLexiconDelete(e.term)}
                            style={{ background: "none", border: "none", color: "var(--c4-sidebar-muted)", cursor: "pointer", fontSize: 14, lineHeight: 1, padding: 0 }}
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : null;
                })()}
                <input
                  value={lexTerm}
                  onChange={(e) => setLexTerm(e.target.value)}
                  placeholder="Term (e.g. SM83)"
                  style={{ ...inputStyle, marginBottom: 6 }}
                />
                <textarea
                  value={lexDef}
                  onChange={(e) => setLexDef(e.target.value)}
                  placeholder="Definition…"
                  rows={2}
                  style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit", marginBottom: 6 }}
                />
                <button
                  onClick={handleLexiconSave}
                  disabled={lexSaving || !lexTerm.trim() || !lexDef.trim()}
                  style={{
                    width: "100%",
                    background: "#3b82f6",
                    color: "#fff",
                    border: "none",
                    borderRadius: 6,
                    padding: "6px 0",
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: lexSaving || !lexTerm.trim() || !lexDef.trim() ? "not-allowed" : "pointer",
                    opacity: lexSaving || !lexTerm.trim() || !lexDef.trim() ? 0.6 : 1,
                  }}
                >
                  {lexSaving ? "Saving…" : "Add to lexique"}
                </button>
              </Section>
            )}
          </>
        ) : open ? (
          <>
            <Section label="Label">
              {editing ? (
                <input
                  value={edgeLabel}
                  onChange={(e) => setEdgeLabel(e.target.value)}
                  placeholder={(target!.edge.label as string) || "Override label…"}
                  style={inputStyle}
                  autoFocus
                />
              ) : (
                <ReadValue>
                  {(target!.edge.data?.overlay_label as string) || (target!.edge.label as string) || "—"}
                </ReadValue>
              )}
            </Section>
            {target!.edge.data?.technology && (
              <Section label="Technology">
                <ReadValue>{target!.edge.data.technology}</ReadValue>
              </Section>
            )}
          </>
        ) : null}
      </div>

      {/* Footer — only in edit mode */}
      {editing && (
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
            {saving ? "Saving…" : "Save"}
          </button>
          <button
            onClick={cancelEdit}
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
            Cancel
          </button>
        </div>
      )}
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
