/*
@c3:component
name: Comparison Selector
container: Frontend
technology: React
description: Lets a reviewer pick which open pull request to see on the map and leave the comparison again, lists the repository's open pull requests with the branch each one targets, names both commits actually compared so "compared against what?" is answered on screen, and explains the four state badges in a legend. Shows plainly why no comparison is available — no repository link, no open pull request, or no repository access for this account — instead of an empty control.
short_desc: Picks the pull request to compare and explains the states
uses:
- API Client: "lists the linked repository's open pull requests"
  technology: REST
*/
import useSWR from "swr";
import { fetchOpenPullRequests, type ComparisonSummary, type PullRequestOption } from "../../services/api";
import { useViewStore } from "../../store/viewStore";

const PANEL: React.CSSProperties = {
  position: "absolute",
  top: 8,
  right: 12,
  zIndex: 15,
  width: 260,
  background: "var(--c4-sidebar-bg)",
  border: "1px solid var(--c4-sidebar-border)",
  borderRadius: 6,
  padding: "8px 10px",
  display: "flex",
  flexDirection: "column",
  gap: 6,
};

const LABEL: React.CSSProperties = {
  fontSize: 10,
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  color: "var(--c4-sidebar-muted)",
};

const STATES: [string, string][] = [
  ["added", "var(--c4-delta-added)"],
  ["modified", "var(--c4-delta-modified)"],
  ["contains changes", "var(--c4-delta-modified)"],
  ["removed", "var(--c4-delta-removed)"],
];

function Legend() {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {STATES.map(([name, colour]) => (
        <span key={name} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, color: "var(--c4-sidebar-muted)" }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: colour, flexShrink: 0 }} />
          {name}
        </span>
      ))}
    </div>
  );
}

export function DeltaSelector({
  projectMapId,
  comparison,
  summary,
  error,
}: {
  projectMapId: number;
  comparison: PullRequestOption | undefined;
  summary: ComparisonSummary | undefined;
  error: (Error & { status?: number; missing?: string | null }) | undefined;
}) {
  const pullRequest = useViewStore((s) => s.pullRequest);
  const setPullRequest = useViewStore((s) => s.setPullRequest);

  const { data: options, error: listError } = useSWR(
    [`/api/graph/${projectMapId}/pulls/`],
    () => fetchOpenPullRequests(projectMapId),
  );

  if (listError) {
    return (
      <div style={PANEL}>
        <span style={LABEL}>Compare a merge request</span>
        <span style={{ fontSize: 11, color: "var(--c4-sidebar-muted)" }}>{listError.message}</span>
      </div>
    );
  }

  return (
    <div style={PANEL}>
      <span style={LABEL}>Compare a merge request</span>

      {options !== undefined && options.length === 0 && (
        <span style={{ fontSize: 11, color: "var(--c4-sidebar-muted)" }}>
          No open pull request on this repository.
        </span>
      )}

      {options !== undefined && options.length > 0 && (
        <select
          value={pullRequest ?? ""}
          onChange={(e) => setPullRequest(e.target.value ? Number(e.target.value) : null)}
          style={{
            background: "var(--c4-sidebar-input-bg)",
            border: "1px solid var(--c4-sidebar-border)",
            borderRadius: 6,
            padding: "5px 8px",
            fontSize: 12,
            color: "var(--c4-sidebar-text)",
            outline: "none",
          }}
        >
          <option value="">None — show the current map</option>
          {options.map((o) => (
            <option key={o.number} value={o.number}>
              #{o.number} {o.title} → {o.base_ref}
            </option>
          ))}
        </select>
      )}

      {pullRequest != null && error && (
        <span style={{ fontSize: 11, color: "var(--c4-delta-removed)" }}>
          {error.message}
          {error.missing ? ` (${error.missing} side)` : ""}
        </span>
      )}

      {comparison && (
        <>
          <span style={{ fontSize: 10, color: "var(--c4-sidebar-muted)", fontFamily: "monospace" }}>
            {comparison.base_sha.slice(0, 7)} → {comparison.head_sha.slice(0, 7)} ({comparison.base_ref})
          </span>
          {summary?.empty ? (
            <span style={{ fontSize: 11, color: "var(--c4-sidebar-text)" }}>
              This merge request changes no architecture.
            </span>
          ) : (
            <span style={{ fontSize: 11, color: "var(--c4-sidebar-text)" }}>
              {summary?.added} added, {summary?.removed} removed, {summary?.changed} changed
            </span>
          )}
          {!summary?.empty && <Legend />}
        </>
      )}

      {pullRequest != null && (
        <button
          onClick={() => setPullRequest(null)}
          style={{
            background: "none",
            border: "1px solid var(--c4-sidebar-border)",
            borderRadius: 6,
            padding: "4px 0",
            fontSize: 11,
            color: "var(--c4-sidebar-muted)",
            cursor: "pointer",
          }}
        >
          Leave comparison
        </button>
      )}
    </div>
  );
}
