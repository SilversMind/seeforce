import ELK from "elkjs/lib/elk.bundled.js";

const elk = new ELK();

// Estimated node sizes — ELK needs dimensions to avoid overlaps.
const NODE_WIDTH = 180;
const NODE_HEIGHT = 64;

type WithPosition = { id: string; position: { x: number; y: number } };
type WithSourceTarget = { id: string; source: string; target: string };

export async function applyElkLayout<N extends WithPosition, E extends WithSourceTarget>(
  nodes: N[],
  edges: E[],
): Promise<N[]> {
  if (nodes.length === 0) return nodes;

  // Count degree per node to weight priority (higher degree → more central in force layout).
  const degree: Record<string, number> = {};
  for (const e of edges) {
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
      layoutOptions: {
        // Priority drives centrality in force layout.
        "elk.priority": String((degree[n.id] ?? 0) + 1),
      },
    })),
    edges: edges.map((e) => ({
      id: e.id,
      sources: [e.source],
      targets: [e.target],
    })),
  };

  const layout = await elk.layout(elkGraph);

  return nodes.map((n) => {
    const elkNode = layout.children?.find((c) => c.id === n.id);
    if (elkNode?.x == null || elkNode?.y == null) return n;
    return { ...n, position: { x: elkNode.x, y: elkNode.y } };
  });
}
