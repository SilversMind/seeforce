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

export async function applyElkLayout<N extends WithPosition, E extends WithSourceTarget>(
  nodes: N[],
  edges: E[],
): Promise<{ nodes: N[]; edges: E[] }> {
  const validEdges = edges.filter((e) => e.source !== e.target);

  if (nodes.length === 0) return { nodes, edges: validEdges };

  const degree: Record<string, number> = {};
  for (const e of validEdges) {
    degree[e.source] = (degree[e.source] ?? 0) + 1;
    degree[e.target] = (degree[e.target] ?? 0) + 1;
  }

  const elkGraph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "DOWN",
      "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "elk.layered.cycleBreaking.strategy": "GREEDY",
      "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
      "elk.spacing.nodeNode": String(80 + MIN_GAP),
      "elk.layered.spacing.nodeNodeBetweenLayers": String(120 + MIN_GAP),
    },
    children: nodes.map((n) => ({
      id: n.id,
      // Real measured size when available; ELK sizes its own spacing options
      // relative to these, so an under-reported box is what let neighbors
      // sit close enough to visually touch or overlap.
      width: n.measured?.width ?? NODE_WIDTH,
      height: n.measured?.height ?? NODE_HEIGHT,
      layoutOptions: { "elk.priority": String((degree[n.id] ?? 0) + 1) },
    })),
    edges: validEdges.map((e) => ({ id: e.id, sources: [e.source], targets: [e.target] })),
  };

  const layout = await elk.layout(elkGraph);

  const laidOut = nodes.map((n) => {
    const elkNode = layout.children?.find((c) => c.id === n.id);
    if (elkNode?.x == null || elkNode?.y == null) return n;
    return { ...n, position: { x: elkNode.x, y: elkNode.y } };
  });

  return { nodes: laidOut, edges: validEdges };
}
