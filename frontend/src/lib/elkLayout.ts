import ELK from "elkjs/lib/elk.bundled.js";

const HANDLE_ORDER = ["left-t", "top-t", "right-t", "bottom-t"] as const;

function deduplicateTargetHandles<E extends { target: string; targetHandle: string }>(
  edges: E[],
): E[] {
  const byTarget: Record<string, E[]> = {};
  for (const edge of edges) {
    (byTarget[edge.target] ??= []).push(edge);
  }
  for (const group of Object.values(byTarget)) {
    if (group.length <= 1) continue;
    const handleCounts: Record<string, number> = {};
    for (const e of group) handleCounts[e.targetHandle] = (handleCounts[e.targetHandle] ?? 0) + 1;
    if (!Object.values(handleCounts).some((c) => c > 1)) continue;
    const used = new Set<string>();
    for (const edge of group) {
      if (!used.has(edge.targetHandle)) {
        used.add(edge.targetHandle);
        continue;
      }
      const alt = HANDLE_ORDER.find((h) => !used.has(h));
      if (alt) {
        (edge as { targetHandle: string }).targetHandle = alt;
        used.add(alt);
      }
    }
  }
  return edges;
}

const elk = new ELK();

const NODE_WIDTH = 180;
const NODE_HEIGHT = 64;

type WithPosition = { id: string; position: { x: number; y: number } };
type WithSourceTarget = { id: string; source: string; target: string };
type HandlePair = { sourceHandle: string; targetHandle: string };

function getHandlePair(
  src: { x: number; y: number },
  tgt: { x: number; y: number },
): HandlePair {
  const dx = tgt.x - src.x;
  const dy = tgt.y - src.y;
  if (Math.abs(dy) >= Math.abs(dx)) {
    return dy > 0
      ? { sourceHandle: "bottom-s", targetHandle: "top-t" }
      : { sourceHandle: "top-s", targetHandle: "bottom-t" };
  }
  return dx > 0
    ? { sourceHandle: "right-s", targetHandle: "left-t" }
    : { sourceHandle: "left-s", targetHandle: "right-t" };
}

/** Attach source/target handle positions to edges based on node layout. */
export function computeEdgeHandles<N extends WithPosition, E extends WithSourceTarget>(
  nodes: N[],
  edges: E[],
): (E & HandlePair)[] {
  const posMap: Record<string, { x: number; y: number }> = {};
  nodes.forEach((n) => { posMap[n.id] = n.position; });
  const routed = edges
    .filter((e) => e.source !== e.target)
    .map((e) => ({
      ...e,
      ...getHandlePair(posMap[e.source] ?? { x: 0, y: 0 }, posMap[e.target] ?? { x: 0, y: 0 }),
    }));
  return deduplicateTargetHandles(routed);
}

export async function applyElkLayout<N extends WithPosition, E extends WithSourceTarget>(
  nodes: N[],
  edges: E[],
): Promise<{ nodes: N[]; edges: (E & HandlePair)[] }> {
  const validEdges = edges.filter((e) => e.source !== e.target);
  const fallback = (e: E): E & HandlePair => ({ ...e, sourceHandle: "bottom-s", targetHandle: "top-t" });

  if (nodes.length === 0) {
    return { nodes, edges: validEdges.map(fallback) };
  }

  const degree: Record<string, number> = {};
  for (const e of validEdges) {
    degree[e.source] = (degree[e.source] ?? 0) + 1;
    degree[e.target] = (degree[e.target] ?? 0) + 1;
  }

  const elkGraph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "force",
      "elk.force.iterations": "300",
      "elk.spacing.nodeNode": "80",
      "elk.force.repulsivePower": "2",
    },
    children: nodes.map((n) => ({
      id: n.id,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      layoutOptions: { "elk.priority": String((degree[n.id] ?? 0) + 1) },
    })),
    edges: validEdges.map((e) => ({ id: e.id, sources: [e.source], targets: [e.target] })),
  };

  const layout = await elk.layout(elkGraph);

  const posMap: Record<string, { x: number; y: number }> = {};
  nodes.forEach((n) => { posMap[n.id] = n.position; });

  const laidOut = nodes.map((n) => {
    const elkNode = layout.children?.find((c) => c.id === n.id);
    if (elkNode?.x == null || elkNode?.y == null) return n;
    posMap[n.id] = { x: elkNode.x, y: elkNode.y };
    return { ...n, position: { x: elkNode.x, y: elkNode.y } };
  });

  const routedEdges = deduplicateTargetHandles(validEdges.map((e) => ({
    ...e,
    ...getHandlePair(posMap[e.source] ?? { x: 0, y: 0 }, posMap[e.target] ?? { x: 0, y: 0 }),
  })));

  return { nodes: laidOut, edges: routedEdges };
}
