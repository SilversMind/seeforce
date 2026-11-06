import { useMemo } from "react";
import useSWR from "swr";
import {
  buildViewUrl,
  buildShareViewUrl,
  buildDeltaViewUrl,
  type ComparisonSummary,
  type DeltaElementState,
  type PullRequestOption,
  type ReactFlowData,
} from "../services/api";
import type { ViewState } from "../store/viewStore";

const fetcher = (url: string) =>
  fetch(url).then(async (r) => {
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      throw Object.assign(new Error(body.error ?? `HTTP ${r.status}`), {
        status: r.status,
        missing: body.missing ?? null,
      });
    }
    return r.json();
  });

const EMPTY_NODES: ReactFlowData["nodes"] = [];
const EMPTY_EDGES: ReactFlowData["edges"] = [];

/** The class that paints one comparison state; amber says which kind it is. */
export function deltaClassName(delta: DeltaElementState | undefined): string | undefined {
  if (!delta) return undefined;
  if (delta.state === "modified") {
    return delta.self_changed ? "c4-delta c4-delta-modified" : "c4-delta c4-delta-contains";
  }
  return `c4-delta c4-delta-${delta.state}`;
}

export function useWorkspace(view: ViewState): {
  nodes: ReactFlowData["nodes"];
  edges: ReactFlowData["edges"];
  comparison: PullRequestOption | undefined;
  summary: ComparisonSummary | undefined;
  isLoading: boolean;
  error: Error | undefined;
  refetch: () => void;
} {
  const url =
    view.projectMapId == null
      ? null
      : view.pullRequest != null && !view.shareToken
        ? buildDeltaViewUrl(view.projectMapId, view.level, view.systemId, view.containerId, view.pullRequest)
        : view.shareToken
          ? buildShareViewUrl(view.shareToken, view.level, view.systemId, view.containerId)
          : buildViewUrl(view.projectMapId, view.level, view.systemId, view.containerId);

  const { data, error, isLoading, mutate } = useSWR<ReactFlowData>(url, fetcher);

  const rawNodes = data?.nodes ?? EMPTY_NODES;
  const rawEdges = data?.edges ?? EMPTY_EDGES;

  const nodes = useMemo(
    () => rawNodes.map((n) => {
      const className = deltaClassName(n.data.delta);
      return className ? { ...n, className } : n;
    }),
    [rawNodes],
  );

  const edges = useMemo(() => {
    const nodeLabel = Object.fromEntries(nodes.map((n) => [n.id, n.data.label]));
    return rawEdges.map((e) => ({
      ...e,
      data: {
        ...e.data,
        source_node: { id: e.source, label: nodeLabel[e.source] ?? e.source },
        target_node: { id: e.target, label: nodeLabel[e.target] ?? e.target },
      },
    }));
  }, [nodes, rawEdges]);

  return {
    nodes,
    edges,
    comparison: data?.comparison,
    summary: data?.summary,
    isLoading,
    error,
    refetch: () => mutate(),
  };
}
