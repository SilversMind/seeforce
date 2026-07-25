import useSWR from "swr";
import { buildViewUrl, type ReactFlowData } from "../services/api";
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
  const url =
    view.workspaceId != null
      ? buildViewUrl(view.workspaceId, view.level, view.systemId, view.containerId)
      : null;

  const { data, error, isLoading, mutate } = useSWR<ReactFlowData>(url, fetcher);

  return {
    nodes: data?.nodes ?? EMPTY_NODES,
    edges: data?.edges ?? EMPTY_EDGES,
    isLoading,
    error,
    refetch: () => mutate(),
  };
}
