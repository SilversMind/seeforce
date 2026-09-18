import ELK from "elkjs/lib/elk.bundled.js";

const elk = new ELK();

// Fallback only — used when a node hasn't been measured yet (e.g. no DOM
// mount pass happened). Real layout should always pass measured dimensions,
// since node boxes are content-sized (minWidth/maxWidth + wrapping text) and
// can run well past this estimate, which is what let nodes overlap before.
const NODE_WIDTH = 180;
const NODE_HEIGHT = 64;
// Minimum visual gap enforced on top of ELK's own spacing so two node
// boxes can never touch, even at the edges of ELK's spacing tolerance.
const MIN_GAP = 24;

type WithPosition = {
  id: string;
  position: { x: number; y: number };
  measured?: { width?: number; height?: number };
};
type WithSourceTarget = { id: string; source: string; target: string };

// The "stress" algorithm minimizes edge-length tension instead of assigning
// nodes to strict layers — it can pull a source-only node (no incoming edges,
// e.g. an API component that only calls out to a shared DB) toward its
// targets instead of stranding it in a fixed leftmost column with every
// other source node, which is what "layered" always does by construction
// and no amount of crossing-minimization/layering-strategy tuning changes:
// verified by reproducing the Backend C3 view's fan-in pattern standalone
// with elkjs (stress: 0 crossings vs layered: 6). Trade-off: stress has no
// built-in box-overlap guarantee (layered reserves per-node slot space,
// stress only optimizes point positions), so enforceMinSpacing() below is
// required, not optional.
const STRESS_DESIRED_EDGE_LENGTH = 260;

type Rect = { id: string; x: number; y: number; w: number; h: number };

// Simple iterative separating-axis push-apart: while any two boxes overlap
// OR sit closer than `gap`, shove them apart along whichever axis has the
// smaller (or more negative) overlap. Converges fast for graphs this size
// (tens of nodes, not hundreds).
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
        // ox/oy are the signed overlap on each axis — negative means a real
        // gap of that many px on that axis alone. Below -gap on either axis
        // means the boxes already clear the minimum, so skip them.
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
      // Real measured size when available; an under-reported box is what
      // let neighbors sit close enough to visually touch before.
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
