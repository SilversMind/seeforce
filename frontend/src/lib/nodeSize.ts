import type { CSSProperties } from "react";

/** How much wider the largest node of a view is than the smallest: 1x to 2.4x. */
const MAX_NODE_GROWTH = 1.4;

/** The node's scale factor, from 1 to 2.4, given the data.size the backend sets from its lines of code. */
export function nodeScale(data: Record<string, unknown>): number {
  const size = typeof data.size === "number" ? data.size : 0;
  return 1 + Math.min(Math.max(size, 0), 1) * MAX_NODE_GROWTH;
}

/** Box size of a node: fixed by its lines of code when it has some, else sized by its text; fonts and padding scale with it. */
export function nodeBox(data: Record<string, unknown>, base: { width: number; height: number; maxWidth: number }): CSSProperties {
  if (typeof data.size !== "number") return { minWidth: base.width, maxWidth: base.maxWidth };
  // NOTE: a fixed width, not a min width, or a long short_desc stretches a small node past a big one.
  const scale = nodeScale(data);
  return { width: base.width * scale, minHeight: base.height * scale, boxSizing: "border-box", overflowWrap: "anywhere" };
}

/** Tooltip text for a node's weight, or undefined when it has no lines of code. */
export function locTitle(data: Record<string, unknown>): string | undefined {
  const loc = data.loc as number | undefined;
  return loc ? `${loc.toLocaleString()} lines of code` : undefined;
}

/** Stroke width of an edge: thicker for each doubling of its actions, capped at 8. */
export function edgeStrokeWidth(actionCount: number): number {
  return 1.5 + Math.min(Math.log2(Math.max(actionCount, 1)), 3) * 0.75;
}
