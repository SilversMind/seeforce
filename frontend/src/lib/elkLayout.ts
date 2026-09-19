import ELK from "elkjs/lib/elk.bundled.js";

const elk = new ELK();

/**
 * Fallback size for an unmeasured node. Real layout should always pass
 * measured dimensions — node boxes are content-sized (minWidth/maxWidth +
 * wrapping text) and can run past this estimate, which is what let nodes
 * overlap before.
 */
const NODE_WIDTH = 180;
const NODE_HEIGHT = 64;
/** Minimum visual gap enforced between any two node boxes after layout. */
const MIN_GAP = 24;

type WithPosition = {
  id: string;
  position: { x: number; y: number };
  measured?: { width?: number; height?: number };
};
type WithSourceTarget = { id: string; source: string; target: string };

/**
 * ELK's "layered" algorithm assigns every zero-incoming-edge node to the
 * same leftmost column by construction — no crossing-minimization or
 * layering-strategy tuning can move a source-only component closer to its
 * targets. "stress" optimizes by edge-length tension instead of fixed
 * layers, verified against layered on a real fan-in view (0 crossings vs
 * 6). Trade-off: stress has no built-in box-overlap guarantee like layered
 * does, hence enforceMinSpacing() below.
 */
const STRESS_DESIRED_EDGE_LENGTH = 260;

type Rect = { id: string; x: number; y: number; w: number; h: number };

/**
 * Iterative separating-axis push-apart: while two boxes overlap or sit
 * closer than `gap`, shove them apart along the axis with the smaller (or
 * more negative) overlap. Converges fast for graphs this size.
 */
function enforceMinSpacing(rects: Rect[], gap = MIN_GAP, iterations = 50): Rect[] {
  const out = rects.map((r) => ({ ...r }));
  for (let iter = 0; iter < iterations; iter++) {
    let moved = false;
    for (let i = 0; i < out.length; i++) {
      for (let j = i + 1; j < out.length; j++) {
        const a = out[i];
        const b = out[j];
        const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
        const oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
        // Negative ox/oy = a real gap that big; below -gap already clears the minimum.
        if (ox <= -gap || oy <= -gap) continue;
        moved = true;
        const acx = a.x + a.w / 2;
        const bcx = b.x + b.w / 2;
        const acy = a.y + a.h / 2;
        const bcy = b.y + b.h / 2;
        if (ox < oy) {
          const push = (ox + gap) / 2;
          if (acx < bcx) {
            a.x -= push;
            b.x += push;
          } else {
            a.x += push;
            b.x -= push;
          }
        } else {
          const push = (oy + gap) / 2;
          if (acy < bcy) {
            a.y -= push;
            b.y += push;
          } else {
            a.y += push;
            b.y -= push;
          }
        }
      }
    }
    if (!moved) break;
  }
  return out;
}

export async function applyElkLayout<N extends WithPosition, E extends WithSourceTarget>(
  nodes: N[],
  edges: E[],
): Promise<{ nodes: N[]; edges: E[] }> {
  const validEdges = edges.filter((e) => e.source !== e.target);

  if (nodes.length === 0) return { nodes, edges: validEdges };

  const elkGraph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "stress",
      "elk.stress.desiredEdgeLength": String(STRESS_DESIRED_EDGE_LENGTH),
    },
    children: nodes.map((n) => ({
      id: n.id,
      // Real measured size when available — an under-reported box is what let neighbors touch.
      width: n.measured?.width ?? NODE_WIDTH,
      height: n.measured?.height ?? NODE_HEIGHT,
    })),
    edges: validEdges.map((e) => ({ id: e.id, sources: [e.source], targets: [e.target] })),
  };

  const layout = await elk.layout(elkGraph);

  const rects: Rect[] = nodes.map((n) => {
    const elkNode = layout.children?.find((c) => c.id === n.id);
    const width = n.measured?.width ?? NODE_WIDTH;
    const height = n.measured?.height ?? NODE_HEIGHT;
    return { id: n.id, x: elkNode?.x ?? 0, y: elkNode?.y ?? 0, w: width, h: height };
  });
  const resolved = enforceMinSpacing(rects);

  const laidOut = nodes.map((n) => {
    const r = resolved.find((rect) => rect.id === n.id);
    if (!r) return n;
    return { ...n, position: { x: r.x, y: r.y } };
  });

  return { nodes: laidOut, edges: validEdges };
}
