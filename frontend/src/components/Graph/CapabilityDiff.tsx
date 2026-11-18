import type { CapabilityChange } from "../../services/api";

const COLOR: Record<CapabilityChange["status"], string> = {
  unchanged: "inherit",
  added: "var(--c4-delta-added)",
  removed: "var(--c4-delta-removed)",
  reworded: "var(--c4-delta-modified)",
};

const MARK: Record<CapabilityChange["status"], string> = { unchanged: "", added: "+", removed: "−", reworded: "~" };

/** Renders a merged capability tree, colouring each bullet by whether it was added, removed or reworded. */
export function CapabilityDiff({ items, depth = 0 }: { items: CapabilityChange[]; depth?: number }) {
  return (
    <ul style={{ margin: depth ? "2px 0 0" : 0, paddingLeft: 16, display: "flex", flexDirection: "column", gap: 2, listStyleType: depth ? "circle" : "disc" }}>
      {items.map((c, i) => (
        <li
          key={i}
          title={c.status === "unchanged" ? undefined : c.status}
          style={{ lineHeight: 1.45, color: COLOR[c.status], opacity: c.status === "unchanged" ? 0.75 : 1 }}
        >
          {MARK[c.status] && <strong style={{ marginRight: 4 }}>{MARK[c.status]}</strong>}
          <span style={{ textDecoration: c.status === "removed" ? "line-through" : undefined }}>{c.text}</span>
          {c.before && (
            <div style={{ textDecoration: "line-through", color: "var(--c4-sidebar-muted)", fontSize: 11 }}>{c.before}</div>
          )}
          {c.children.length > 0 && <CapabilityDiff items={c.children} depth={depth + 1} />}
        </li>
      ))}
    </ul>
  );
}
