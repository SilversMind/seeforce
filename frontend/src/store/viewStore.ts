import { create } from "zustand";

export type Level = "C1" | "C2" | "C3";

export type PositionMap = Record<string, { x: number; y: number }>;

export interface ViewState {
  workspaceId: number | null;
  level: Level;
  systemId: string | null;
  containerId: string | null;
}

interface ViewStore extends ViewState {
  layoutCache: Record<string, PositionMap>;
  setWorkspace: (id: number) => void;
  drillToC2: (systemId: string) => void;
  drillToC3: (containerId: string) => void;
  back: () => void;
  saveLayout: (viewKey: string, positions: PositionMap) => void;
}

export function buildViewKey(level: Level, systemId: string | null, containerId: string | null): string {
  return `${level}:${systemId ?? ""}:${containerId ?? ""}`;
}

export const useViewStore = create<ViewStore>((set, get) => ({
  workspaceId: null,
  level: "C1",
  systemId: null,
  containerId: null,
  layoutCache: {},

  setWorkspace: (id) => set({ workspaceId: id, level: "C1", systemId: null, containerId: null }),

  drillToC2: (systemId) => set({ level: "C2", systemId, containerId: null }),

  drillToC3: (containerId) => set({ level: "C3", containerId }),

  back: () => {
    const { level } = get();
    if (level === "C3") set({ level: "C2", containerId: null });
    else if (level === "C2") set({ level: "C1", systemId: null });
  },

  saveLayout: (viewKey, positions) =>
    set((s) => ({ layoutCache: { ...s.layoutCache, [viewKey]: positions } })),
}));
