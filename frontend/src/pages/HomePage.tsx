/*
@c3:component
name: Project Library
container: Frontend
technology: React
description: The signed-in landing screen — lists the projects a user owns and those shared with them, and is where a project enters SeeForce in the first place, either by uploading a scanned workspace.json or by importing one from a GitHub repo. Also handles rename, delete, re-sync from GitHub, linking a project to a repo, and the GitHub App install prompt.
short_desc: Lists projects and is where upload or GitHub import creates one
uses:
- Auth Context: "reads the signed-in user and the GitHub App installation status that gates private-repo import"
- Backend: "lists owned and shared projects, uploads or imports a workspace, then renames, deletes, re-syncs or links one to a repo"
  technology: REST
*/
import { useState, useEffect, useRef, useCallback } from "react";
import useSWR, { mutate } from "swr";
import { useNavigate } from "react-router-dom";
import { deleteProjectMap, fetchProjectMaps, fetchSharedProjects, renameProjectMap, importFromGitHub, syncFromGitHub, uploadProjectMap, linkProjectToGithub, type ProjectMapMeta } from "../services/api";
import { useAuth } from "../contexts/AuthContext";
import { BrandMark } from "../components/BrandMark";

function GitHubAppLink({ url, children }: { url: string; children: React.ReactNode }) {
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: "#3b82f6", textDecoration: "none" }}>
      {children}
    </a>
  );
}

function relativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) {
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    return hours === 1 ? "1 hour ago" : `${hours} hours ago`;
  }
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  if (months === 1) return "1 month ago";
  if (months < 12) return `${months} months ago`;
  return `${Math.floor(months / 12)} years ago`;
}

function ProjectCard({
  project,
  onClick,
  onDelete,
  onEdit,
  onSync,
}: {
  project: ProjectMapMeta;
  onClick: () => void;
  onDelete: () => void;
  onEdit: () => void;
  onSync?: () => void;
}) {
  function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (!window.confirm(`Delete "${project.name}"?`)) return;
    onDelete();
  }

  function handleEdit(e: React.MouseEvent) {
    e.stopPropagation();
    onEdit();
  }

  function handleSync(e: React.MouseEvent) {
    e.stopPropagation();
    onSync?.();
  }

  const isGitHub = project.project_id?.startsWith("github:");

  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--c4-sidebar-bg)",
        border: "1px solid var(--c4-sidebar-border)",
        borderRadius: 8,
        padding: 20,
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        transition: "border-color 0.15s",
        position: "relative",
      }}
      onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "var(--c4-system-border)")}
      onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "var(--c4-sidebar-border)")}
    >
      <div style={{ position: "absolute", top: 10, right: 10, display: "flex", gap: 4 }}>
        {isGitHub && onSync && (
          <button
            onClick={handleSync}
            title="Sync from GitHub"
            style={{ background: "none", border: "none", color: "var(--c4-sidebar-muted)", cursor: "pointer", fontSize: 12, lineHeight: 1, padding: 2 }}
          >
            ↻
          </button>
        )}
        <button
          onClick={handleEdit}
          title="Rename project"
          style={{ background: "none", border: "none", color: "var(--c4-sidebar-muted)", cursor: "pointer", fontSize: 13, lineHeight: 1, padding: 2 }}
        >
          ✎
        </button>
        <button
          onClick={handleDelete}
          title="Delete project"
          style={{ background: "none", border: "none", color: "var(--c4-sidebar-muted)", cursor: "pointer", fontSize: 16, lineHeight: 1, padding: 2 }}
        >
          ×
        </button>
      </div>
      <div style={{ fontWeight: 700, fontSize: 14, color: "var(--c4-sidebar-text)", paddingRight: 44 }}>
        {project.name}
      </div>
      <div style={{ fontSize: 12, color: "var(--c4-sidebar-muted)" }}>
        Updated {relativeDate(project.updated_at)}
      </div>
      {project.last_synced_at && (
        <div
          style={{ fontSize: 11, color: "var(--c4-sidebar-muted)", opacity: 0.7 }}
          title={new Date(project.last_synced_at).toLocaleString()}
        >
          Synced from GitHub {relativeDate(project.last_synced_at)}
        </div>
      )}
    </div>
  );
}

async function deleteProject(id: number) {
  // A failed DELETE used to pass silently: the card came back on the next
  // revalidation with no explanation.
  try {
    await deleteProjectMap(id);
  } catch {
    window.alert("Could not delete this project. It may belong to someone else.");
  }
  await mutate("/api/graph/");
}

type NewProjectTab = "github" | "upload";

function NewProjectSidebar({ open, initialTab, onClose, onDone }: { open: boolean; initialTab: NewProjectTab; onClose: () => void; onDone: (id: number) => void }) {
  const { user } = useAuth();
  const [tab, setTab] = useState<NewProjectTab>("github");
  const [repo, setRepo] = useState("");
  const [branch, setBranch] = useState("main");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setTab(initialTab);
    } else {
      setRepo(""); setBranch("main"); setError(null); setLoading(false);
    }
  }, [open, initialTab]);

  async function handleImport() {
    setError(null);
    setLoading(true);
    try {
      const meta = await importFromGitHub(repo.trim(), branch.trim());
      await mutate("/api/graph/");
      onDone(meta.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setLoading(true);
    try {
      const text = await file.text();
      const workspace = JSON.parse(text);
      const name = workspace.name || file.name.replace(".json", "");
      const meta = await uploadProjectMap(name, workspace);
      await mutate("/api/graph/");
      onDone(meta.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  const tabBtn = (t: NewProjectTab, label: string) => (
    <button
      onClick={() => { setTab(t); setError(null); }}
      style={{
        flex: 1, background: "none", border: "none", borderBottom: `2px solid ${tab === t ? "#3b82f6" : "transparent"}`,
        color: tab === t ? "var(--c4-sidebar-text)" : "var(--c4-sidebar-muted)",
        fontWeight: tab === t ? 600 : 400, fontSize: 13, padding: "8px 0", cursor: "pointer",
      }}
    >
      {label}
    </button>
  );

  return (
    <div style={{
      position: "fixed", top: 48, right: 0,
      width: "clamp(280px, 28vw, 420px)", height: "calc(100vh - 48px)",
      transform: open ? "translateX(0)" : "translateX(100%)",
      transition: "transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
      background: "var(--c4-sidebar-bg)", borderLeft: "1px solid var(--c4-sidebar-border)",
      display: "flex", flexDirection: "column", zIndex: 20, fontSize: 13, color: "var(--c4-sidebar-text)",
    }}>
      <div style={{ display: "flex", alignItems: "center", padding: "12px 16px", borderBottom: "1px solid var(--c4-sidebar-border)", gap: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--c4-sidebar-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          New project
        </span>
        <button onClick={onClose} style={{ marginLeft: "auto", background: "none", border: "none", color: "var(--c4-sidebar-muted)", fontSize: 18, cursor: "pointer", lineHeight: 1 }}>×</button>
      </div>

      <div style={{ display: "flex", borderBottom: "1px solid var(--c4-sidebar-border)" }}>
        {tabBtn("github", "Import from GitHub")}
        {tabBtn("upload", "Upload file")}
      </div>

      <div style={{ flex: 1, padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
        {tab === "github" && (
          <>
            {user && !user.github_app_installed && user.github_app_install_url && (
              <div style={{ fontSize: 12, color: "var(--c4-sidebar-text)", background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.3)", borderRadius: 6, padding: "8px 10px" }}>
                Public repos work as-is. To import a private repo, install the GitHub App first —{" "}
                <GitHubAppLink url={user.github_app_install_url}>Install GitHub App ↗</GitHubAppLink>
              </div>
            )}
            <div>
              <label style={{ display: "block", fontSize: 11, color: "var(--c4-sidebar-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
                Repository
              </label>
              <input
                value={repo} onChange={(e) => setRepo(e.target.value)}
                placeholder="owner/repo"
                style={inputStyle} autoFocus={open && tab === "github"}
                onKeyDown={(e) => e.key === "Enter" && handleImport()}
              />
              <div style={{ fontSize: 11, color: "var(--c4-sidebar-muted)", marginTop: 4 }}>
                Repo must contain <code style={{ fontFamily: "monospace" }}>.seeforce/workspace.json</code> — run <code style={{ fontFamily: "monospace" }}>seeforce scan .</code> first.
                {user?.github_app_install_url && (
                  <>
                    {" "}Private repo not showing up? <GitHubAppLink url={user.github_app_install_url}>Manage GitHub App access ↗</GitHubAppLink>
                  </>
                )}
              </div>
            </div>
            <div>
              <label style={{ display: "block", fontSize: 11, color: "var(--c4-sidebar-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
                Branch
              </label>
              <input
                value={branch} onChange={(e) => setBranch(e.target.value)}
                placeholder="main"
                style={inputStyle}
                onKeyDown={(e) => e.key === "Enter" && handleImport()}
              />
            </div>
          </>
        )}

        {tab === "upload" && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, gap: 12 }}>
            <div style={{ fontSize: 12, color: "var(--c4-sidebar-muted)", textAlign: "center" }}>
              Upload a <code style={{ fontFamily: "monospace" }}>workspace.json</code> generated by <code style={{ fontFamily: "monospace" }}>seeforce scan .</code>.
            </div>
            <div style={{ fontSize: 11, color: "var(--c4-sidebar-muted)", background: "rgba(148,163,184,0.1)", border: "1px solid var(--c4-sidebar-border)", borderRadius: 6, padding: "8px 10px", textAlign: "center" }}>
              This creates a real project you can keep working from — but it won't stay in sync with your repo. Prefer <strong style={{ color: "var(--c4-sidebar-text)" }}>Import from GitHub</strong> for long-term use, or link this project to a repo later from its settings.
            </div>
            <label style={{ cursor: "pointer", background: "#3b82f6", color: "#fff", padding: "8px 20px", borderRadius: 6, fontSize: 13, fontWeight: 600, opacity: loading ? 0.7 : 1 }}>
              {loading ? "Uploading…" : "Choose workspace.json"}
              <input ref={fileRef} type="file" accept=".json" onChange={handleFile} style={{ display: "none" }} disabled={loading} />
            </label>
          </div>
        )}

        {error && (
          <div style={{ fontSize: 12, color: "#ef4444", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 6, padding: "8px 10px" }}>
            {error}
          </div>
        )}
      </div>

      {tab === "github" && (
        <div style={{ padding: "12px 16px", borderTop: "1px solid var(--c4-sidebar-border)", display: "flex", gap: 8 }}>
          <button
            onClick={handleImport} disabled={loading || !repo.trim()}
            style={{ flex: 1, background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "8px 0", fontSize: 13, fontWeight: 600, cursor: loading || !repo.trim() ? "not-allowed" : "pointer", opacity: loading || !repo.trim() ? 0.7 : 1 }}
          >
            {loading ? "Importing…" : "Import"}
          </button>
          <button onClick={onClose} style={{ background: "none", color: "var(--c4-sidebar-muted)", border: "1px solid var(--c4-sidebar-border)", borderRadius: 6, padding: "8px 12px", fontSize: 13, cursor: "pointer" }}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "var(--c4-sidebar-input-bg)",
  border: "1px solid var(--c4-sidebar-border)",
  borderRadius: 6,
  padding: "6px 10px",
  fontSize: 13,
  color: "var(--c4-sidebar-text)",
  outline: "none",
  boxSizing: "border-box",
};

function EditSidebar({
  project,
  onClose,
}: {
  project: ProjectMapMeta | null;
  onClose: () => void;
}) {
  const [name, setName] = useState(project?.name ?? "");
  const [saving, setSaving] = useState(false);
  const [linkRepo, setLinkRepo] = useState("");
  const [linkBranch, setLinkBranch] = useState("main");
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  useEffect(() => {
    setName(project?.name ?? "");
    setLinkRepo("");
    setLinkBranch("main");
    setLinkError(null);
  }, [project]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") handleSave();
    if (e.key === "Escape") onClose();
  }

  async function handleSave() {
    if (!project || !name.trim()) return;
    setSaving(true);
    try {
      await renameProjectMap(project.id, name.trim());
      await mutate("/api/graph/");
      onClose();
    } finally {
      setSaving(false);
    }
  }

  async function handleLink() {
    if (!project || !linkRepo.trim()) return;
    setLinking(true);
    setLinkError(null);
    try {
      await linkProjectToGithub(project.id, linkRepo.trim(), linkBranch.trim() || "main");
      await mutate("/api/graph/");
      onClose();
    } catch (e) {
      setLinkError(e instanceof Error ? e.message : "Link failed");
    } finally {
      setLinking(false);
    }
  }

  const open = project !== null;
  const isGitHub = project?.project_id?.startsWith("github:") ?? false;

  return (
    <div
      style={{
        position: "fixed",
        top: 48,
        right: 0,
        width: "clamp(280px, 28vw, 420px)",
        height: "calc(100vh - 48px)",
        transform: open ? "translateX(0)" : "translateX(100%)",
        transition: "transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
        background: "var(--c4-sidebar-bg)",
        borderLeft: "1px solid var(--c4-sidebar-border)",
        display: "flex",
        flexDirection: "column",
        zIndex: 20,
        fontSize: 13,
        color: "var(--c4-sidebar-text)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", padding: "12px 16px", borderBottom: "1px solid var(--c4-sidebar-border)", gap: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--c4-sidebar-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Rename project
        </span>
        <button
          onClick={onClose}
          style={{ marginLeft: "auto", background: "none", border: "none", color: "var(--c4-sidebar-muted)", fontSize: 18, cursor: "pointer", lineHeight: 1 }}
        >
          ×
        </button>
      </div>

      <div style={{ flex: 1, padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
        <label style={{ fontSize: 11, color: "var(--c4-sidebar-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Name
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={handleKeyDown}
          style={inputStyle}
          autoFocus={open}
          disabled={!open}
        />

        {!isGitHub && (
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--c4-sidebar-border)", display: "flex", flexDirection: "column", gap: 8 }}>
            <label style={{ fontSize: 11, color: "var(--c4-sidebar-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Link to GitHub
            </label>
            <div style={{ fontSize: 11, color: "var(--c4-sidebar-muted)" }}>
              Uploads aren't kept in sync automatically. Link this project to a repo to pull updates with one click instead of re-uploading — this keeps the same project, it doesn't create a new one.
            </div>
            <input
              value={linkRepo}
              onChange={(e) => setLinkRepo(e.target.value)}
              placeholder="owner/repo"
              style={inputStyle}
            />
            <input
              value={linkBranch}
              onChange={(e) => setLinkBranch(e.target.value)}
              placeholder="main"
              style={inputStyle}
            />
            <button
              onClick={handleLink}
              disabled={linking || !linkRepo.trim()}
              style={{ background: "#1e293b", color: "var(--c4-sidebar-text)", border: "1px solid var(--c4-sidebar-border)", borderRadius: 6, padding: "6px 0", fontSize: 12, fontWeight: 600, cursor: linking || !linkRepo.trim() ? "not-allowed" : "pointer", opacity: linking || !linkRepo.trim() ? 0.7 : 1 }}
            >
              {linking ? "Linking…" : "Link repo"}
            </button>
            {linkError && (
              <div style={{ fontSize: 11, color: "#ef4444" }}>{linkError}</div>
            )}
          </div>
        )}
      </div>

      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--c4-sidebar-border)", display: "flex", gap: 8 }}>
        <button
          onClick={handleSave}
          disabled={saving || !name.trim()}
          style={{ flex: 1, background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "8px 0", fontSize: 13, fontWeight: 600, cursor: saving ? "not-allowed" : "pointer", opacity: saving || !name.trim() ? 0.7 : 1 }}
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          onClick={onClose}
          style={{ background: "none", color: "var(--c4-sidebar-muted)", border: "1px solid var(--c4-sidebar-border)", borderRadius: 6, padding: "8px 12px", fontSize: 13, cursor: "pointer" }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function CopyableCommand({ cmd }: { cmd: string }) {
  const [copied, setCopied] = useState(false);
  const copy = useCallback(() => {
    navigator.clipboard.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [cmd]);
  return (
    <div style={{ display: "flex", alignItems: "center", background: "#0f172a", borderRadius: 6, padding: "8px 12px", gap: 10, border: "1px solid #1e293b" }}>
      <code style={{ flex: 1, color: "#e2e8f0", fontFamily: "monospace", fontSize: 13, overflow: "auto", whiteSpace: "nowrap" }}>{cmd}</code>
      <button
        onClick={copy}
        style={{ background: "none", border: "none", color: copied ? "#22c55e" : "#64748b", cursor: "pointer", fontSize: 11, fontWeight: 600, padding: "2px 4px", flexShrink: 0 }}
      >
        {copied ? "✓ copied" : "copy"}
      </button>
    </div>
  );
}

function SetupGuide({ onImport }: { onImport: (tab: NewProjectTab) => void }) {
  const steps: Array<{ title: string; content: React.ReactNode }> = [
    {
      title: "Install the CLI",
      content: <CopyableCommand cmd="curl -fsSL https://seeforce.io/install.sh | sh" />,
    },
    {
      title: "Log in to SeeForce",
      content: <CopyableCommand cmd="seeforce login" />,
    },
    {
      title: "Annotate your codebase",
      content: (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <p style={{ margin: 0, fontSize: 12, color: "var(--c4-sidebar-muted)" }}>
            <strong style={{ color: "var(--c4-sidebar-text)" }}>Recommended:</strong> install the MCP server — your AI assistant annotates automatically.
          </p>
          <CopyableCommand cmd="seeforce mcp install" />
          <p style={{ margin: 0, fontSize: 12, color: "var(--c4-sidebar-muted)" }}>
            Then ask your AI assistant (Claude Code, Cursor, etc.):
          </p>
          <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 6, padding: "8px 12px" }}>
            <code style={{ color: "#86efac", fontFamily: "monospace", fontSize: 13 }}>"Annotate my codebase with Seeforce"</code>
          </div>
          <p style={{ margin: 0, fontSize: 12, color: "var(--c4-sidebar-muted)" }}>
            You can refine the generated annotations manually afterwards for a more precise architecture view.
          </p>
        </div>
      ),
    },
    {
      title: "Scan your codebase",
      content: (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <CopyableCommand cmd="seeforce scan ." />
          <p style={{ margin: 0, fontSize: 12, color: "var(--c4-sidebar-muted)" }}>
            Generates <code style={{ fontFamily: "monospace" }}>workspace.json</code> in your repo root. Commit and push it to GitHub.
          </p>
        </div>
      ),
    },
    {
      title: "Import your project",
      content: (
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => onImport("github")}
            style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
          >
            + Import from GitHub
          </button>
          <button
            onClick={() => onImport("upload")}
            style={{ background: "#0f172a", color: "var(--c4-sidebar-text)", border: "1px solid #334155", borderRadius: 6, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
          >
            Upload workspace.json
          </button>
        </div>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 560, margin: "60px auto 0", color: "var(--c4-sidebar-text)" }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 6px" }}>Get started</h2>
      <p style={{ fontSize: 13, color: "var(--c4-sidebar-muted)", margin: "0 0 32px" }}>
        Set up the SeeForce CLI to annotate your codebase and import your architecture.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
        {steps.map((step, i) => (
          <div key={i} style={{ display: "flex", gap: 16, paddingBottom: 28 }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
              <div style={{
                width: 28, height: 28, borderRadius: "50%",
                background: "#1e293b", border: "1px solid #334155",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 12, fontWeight: 700, color: "#94a3b8", flexShrink: 0,
              }}>
                {i + 1}
              </div>
              {i < steps.length - 1 && (
                <div style={{ flex: 1, width: 1, background: "#1e293b", marginTop: 6 }} />
              )}
            </div>
            <div style={{ flex: 1, paddingTop: 4 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>{step.title}</div>
              {step.content}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function HomePage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [editingProject, setEditingProject] = useState<ProjectMapMeta | null>(null);
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [newProjectTab, setNewProjectTab] = useState<NewProjectTab>("github");
  const [syncError, setSyncError] = useState<string | null>(null);

  async function handleSync(id: number) {
    setSyncError(null);
    try {
      await syncFromGitHub(id);
      await mutate("/api/graph/");
    } catch (e) {
      setSyncError(e instanceof Error ? e.message : "Sync failed");
    }
  }
  const { data: projects, isLoading, error } = useSWR<ProjectMapMeta[]>("/api/graph/", fetchProjectMaps);
  const { data: sharedProjects } = useSWR<ProjectMapMeta[]>("/api/graph/shared/", fetchSharedProjects);

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column", background: "var(--c4-page-bg)", position: "relative", overflow: "hidden" }}>
      <header style={{ height: 48, background: "#0f172a", display: "flex", alignItems: "center", padding: "0 20px", gap: 12, flexShrink: 0 }}>
        <BrandMark />
        <button
          onClick={() => { setNewProjectTab("github"); setNewProjectOpen(true); }}
          style={{
            marginLeft: "auto",
            background: "#1e293b",
            color: "#94a3b8",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "4px 12px",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          + New project
        </button>
        <span style={{ fontSize: "0.875rem", color: "#94a3b8", opacity: 0.7 }}>{user?.username}</span>
        <button
          onClick={logout}
          style={{
            background: "#1e293b",
            color: "#94a3b8",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "4px 12px",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          Log out
        </button>
      </header>

      <main style={{ flex: 1, padding: 32, overflowY: "auto" }}>
        {isLoading && (
          <div style={{ color: "var(--c4-sidebar-muted)", fontSize: 14 }}>Loading…</div>
        )}
        {error && (
          <div style={{ color: "#ef4444", fontSize: 14 }}>Failed to load projects.</div>
        )}
        {syncError && (
          <div style={{ fontSize: 12, color: "#ef4444", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 6, padding: "8px 12px", marginBottom: 16 }}>
            Sync failed: {syncError}
          </div>
        )}
        {projects && projects.length === 0 && (
          <SetupGuide onImport={(tab) => { setNewProjectTab(tab); setNewProjectOpen(true); }} />
        )}
        {projects && projects.length > 0 && (
          <div style={{ maxWidth: 1200, margin: "0 auto" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 16 }}>
              {projects.map((p) => (
                <ProjectCard
                  key={p.id}
                  project={p}
                  onClick={() => navigate(`/project/${p.id}`)}
                  onDelete={() => deleteProject(p.id)}
                  onEdit={() => setEditingProject(p)}
                  onSync={p.project_id?.startsWith("github:") ? () => handleSync(p.id) : undefined}
                />
              ))}
            </div>
          </div>
        )}

        {sharedProjects && sharedProjects.length > 0 && (
          <div style={{ maxWidth: 1200, margin: "32px auto 0" }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--c4-sidebar-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>
              Shared with me
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 16 }}>
              {sharedProjects.map((p) => (
                <ProjectCard
                  key={`shared-${p.id}`}
                  project={p}
                  onClick={() => navigate(`/project/${p.id}`)}
                  onDelete={() => {}}
                  onEdit={() => {}}
                />
              ))}
            </div>
          </div>
        )}
      </main>

      <EditSidebar project={editingProject} onClose={() => setEditingProject(null)} />
      <NewProjectSidebar
        open={newProjectOpen}
        initialTab={newProjectTab}
        onClose={() => setNewProjectOpen(false)}
        onDone={(id) => navigate(`/project/${id}`)}
      />
    </div>
  );
}
