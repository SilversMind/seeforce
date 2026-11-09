/*
@c3:component
name: Change List
container: Frontend
technology: React
description: Lists every change the selected merge request makes to the architecture, at every C4 level rather than only the one on screen, so a reviewer reads the change set instead of hunting it on the canvas. Selecting an item opens that element on the current level when it is there, and otherwise says which level holds it.
short_desc: Lists the whole comparison's changes, grouped by level
*/
import { useState } from "react";
import type { ChangeListItem, ComparisonSummary } from "../../services/api";

const COLOUR: Record<ChangeListItem["state"], string> = {
  added: "var(--c4-delta-added)",
  modified: "var(--c4-delta-modified)",
  removed: "var(--c4-delta-removed)",
};

const MARK: Record<ChangeListItem["state"], string> = { added: "+", modified: "~", removed: "−" };

export function DeltaChangeList({
  summary,
  visibleNodeIds,
  onSelect,
}: {
  summary: ComparisonSummary;
  visibleNodeIds: Set<string>;
  onSelect: (nodeId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  if (summary.empty) return null;

  const counts: [ChangeListItem["state"], number][] = [
    ["added", summary.added], ["modified", summary.changed], ["removed", summary.removed],
  ];

  return (
    <div
      style={{
        position: "absolute",
        top: 8,
        right: 284,
        zIndex: 15,
        width: 300,
        maxHeight: open ? "70%" : undefined,
        overflowY: open ? "auto" : "visible",
        background: "var(--c4-sidebar-bg)",
        border: "1px solid var(--c4-sidebar-border)",
        borderRadius: 6,
        padding: "8px 10px",
      }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        title={open ? "Hide the change list" : "Show the change list"}
        style={{
          display: "flex", alignItems: "center", gap: 6, width: "100%",
          background: "var(--c4-sidebar-chip-bg, rgba(127,127,127,0.12))",
          border: "1px solid var(--c4-sidebar-border)", borderRadius: 4,
          padding: "4px 6px", cursor: "pointer", textAlign: "left",
          fontSize: 10, fontWeight: 600, textTransform: "uppercase",
          letterSpacing: "0.05em", color: "var(--c4-sidebar-text)",
        }}
      >
        <span style={{ fontSize: 9 }}>{open ? "▾" : "▸"}</span>
        <span>{summary.changes.length} change{summary.changes.length === 1 ? "" : "s"}</span>
        <span style={{ marginLeft: "auto", display: "flex", gap: 5 }}>
          {counts.filter(([, n]) => n > 0).map(([state, n]) => (
            <span key={state} style={{ color: COLOUR[state], fontWeight: 700 }}>
              {MARK[state]}
              {n}
            </span>
          ))}
        </span>
      </button>

      {open && summary.changes.map((change, index) => {
        const here = change.node_id != null && visibleNodeIds.has(change.node_id);
        return (
          <button
            key={`${change.path}-${index}`}
            onClick={() => here && onSelect(change.node_id!)}
            title={here ? "Show on this level" : `Visible at ${change.level}`}
            style={{
              display: "block", width: "100%", textAlign: "left", background: "none",
              border: "none", borderTop: "1px solid var(--c4-sidebar-border)",
              padding: "5px 0", cursor: here ? "pointer" : "default",
            }}
          >
            <span style={{ fontSize: 11, color: COLOUR[change.state], fontWeight: 700, marginRight: 4 }}>
              {MARK[change.state]}
            </span>
            <span style={{ fontSize: 11, color: "var(--c4-sidebar-text)" }}>{change.path}</span>
            <span style={{ fontSize: 10, color: "var(--c4-sidebar-muted)", marginLeft: 4 }}>
              {here ? "" : change.level}
            </span>
            {change.summary && (
              <div style={{ fontSize: 10, color: "var(--c4-sidebar-muted)", marginTop: 1 }}>
                {change.summary}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
