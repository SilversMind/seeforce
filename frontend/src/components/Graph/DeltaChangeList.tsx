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
  const [open, setOpen] = useState(true);
  if (summary.empty) return null;

  return (
    <div
      style={{
        position: "absolute",
        top: 8,
        right: 284,
        zIndex: 15,
        width: 300,
        maxHeight: "70%",
        overflowY: "auto",
        background: "var(--c4-sidebar-bg)",
        border: "1px solid var(--c4-sidebar-border)",
        borderRadius: 6,
        padding: "8px 10px",
      }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          background: "none", border: "none", padding: 0, cursor: "pointer", width: "100%",
          textAlign: "left", fontSize: 10, fontWeight: 600, textTransform: "uppercase",
          letterSpacing: "0.05em", color: "var(--c4-sidebar-muted)",
        }}
      >
        {open ? "▾" : "▸"} {summary.changes.length} change{summary.changes.length === 1 ? "" : "s"}
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
