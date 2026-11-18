/** How much bigger the largest node of a view is than the smallest. */
const MAX_NODE_GROWTH = 0.6;

/** The node's scale factor, from 1 to 1.6, given the data.size the backend sets from its lines of code. */
export function nodeScale(data: Record<string, unknown>): number {
  const size = typeof data.size === "number" ? data.size : 0;
  return 1 + Math.min(Math.max(size, 0), 1) * MAX_NODE_GROWTH;
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
