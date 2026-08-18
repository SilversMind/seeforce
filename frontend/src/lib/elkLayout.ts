import ELK from "elkjs/lib/elk.bundled.js";

const elk = new ELK();

const NODE_WIDTH = 180;
const NODE_HEIGHT = 64;

type WithPosition = { id: string; position: { x: number; y: number } };
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

  const laidOut = nodes.map((n) => {
    const elkNode = layout.children?.find((c) => c.id === n.id);
    if (elkNode?.x == null || elkNode?.y == null) return n;
    return { ...n, position: { x: elkNode.x, y: elkNode.y } };
  });

  return { nodes: laidOut, edges: validEdges };
}
