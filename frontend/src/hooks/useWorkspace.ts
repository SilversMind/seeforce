import { useMemo } from "react";
import useSWR from "swr";
import { buildViewUrl, buildShareViewUrl, previewWorkspace, type ReactFlowData } from "../services/api";
import type { ViewState } from "../store/viewStore";

const fetcher = (url: string) =>
  fetch(url).then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  });

const EMPTY_NODES: ReactFlowData["nodes"] = [];
const EMPTY_EDGES: ReactFlowData["edges"] = [];

export function useWorkspace(view: ViewState): {
  nodes: ReactFlowData["nodes"];
  edges: ReactFlowData["edges"];
  isLoading: boolean;
  error: Error | undefined;
  refetch: () => void;
} {
  const isEphemeral = view.ephemeralWorkspace != null;

  const url = isEphemeral
    ? null
    : view.projectMapId != null
      ? view.shareToken
        ? buildShareViewUrl(view.shareToken, view.level, view.systemId, view.containerId)
        : buildViewUrl(view.projectMapId, view.level, view.systemId, view.containerId)
      : null;

  const ephemeralKey = isEphemeral
    ? ["preview", view.level, view.systemId, view.containerId]
    : null;

  const { data: normalData, error: normalError, isLoading: normalLoading, mutate } = useSWR<ReactFlowData>(url, fetcher);

  const { data: ephemeralData, error: ephemeralError, isLoading: ephemeralLoading } = useSWR<ReactFlowData>(
    ephemeralKey,
    () => previewWorkspace(view.ephemeralWorkspace, view.level, view.systemId ?? undefined, view.containerId ?? undefined),
  );

  const data = isEphemeral ? ephemeralData : normalData;
  const error = isEphemeral ? ephemeralError : normalError;
  const isLoading = isEphemeral ? ephemeralLoading : normalLoading;

  const nodes = data?.nodes ?? EMPTY_NODES;
  const rawEdges = data?.edges ?? EMPTY_EDGES;

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
    isLoading,
    error,
    refetch: () => mutate(),
  };
}
