import useSWR from "swr";
import { buildViewUrl, type ReactFlowData } from "../services/api";
import type { ViewState } from "../store/viewStore";

const fetcher = (url: string) =>
  fetch(url).then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  });

export function useWorkspace(view: ViewState): {
  nodes: ReactFlowData["nodes"];
  edges: ReactFlowData["edges"];
  isLoading: boolean;
  error: Error | undefined;
} {
  const url =
    view.workspaceId != null
      ? buildViewUrl(view.workspaceId, view.level, view.systemId, view.containerId)
      : null;

  const { data, error, isLoading } = useSWR<ReactFlowData>(url, fetcher);

  return {
    nodes: data?.nodes ?? [],
    edges: data?.edges ?? [],
    isLoading,
    error,
  };
}
