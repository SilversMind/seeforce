import { create } from "zustand";

export type Level = "C1" | "C2" | "C3";

export interface ViewState {
  workspaceId: number | null;
  level: Level;
  systemId: string | null;
  containerId: string | null;
}

interface ViewStore extends ViewState {
  setWorkspace: (id: number) => void;
  drillToC2: (systemId: string) => void;
  drillToC3: (containerId: string) => void;
  back: () => void;
}

export const useViewStore = create<ViewStore>((set, get) => ({
  workspaceId: null,
  level: "C1",
  systemId: null,
  containerId: null,

  setWorkspace: (id) => set({ workspaceId: id, level: "C1", systemId: null, containerId: null }),

  drillToC2: (systemId) => set({ level: "C2", systemId, containerId: null }),

  drillToC3: (containerId) => set({ level: "C3", containerId }),

  back: () => {
    const { level } = get();
    if (level === "C3") set({ level: "C2", containerId: null });
    else if (level === "C2") set({ level: "C1", systemId: null });
  },
}));
