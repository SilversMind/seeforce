import { create } from "zustand";

export type Level = "C1" | "C2" | "C3";

export interface ViewState {
  projectMapId: number | null;
  level: Level;
  systemId: string | null;
  systemName: string | null;
  containerId: string | null;
  containerName: string | null;
}

interface ViewStore extends ViewState {
  setProjectMap: (id: number) => void;
  drillToC2: (systemId: string, systemName: string) => void;
  drillToC3: (containerId: string, containerName: string) => void;
  goToC1: () => void;
  goToC2: () => void;
}

export const useViewStore = create<ViewStore>((set) => ({
  projectMapId: null,
  level: "C1",
  systemId: null,
  systemName: null,
  containerId: null,
  containerName: null,

  setProjectMap: (id) =>
    set({ projectMapId: id, level: "C1", systemId: null, systemName: null, containerId: null, containerName: null }),

  drillToC2: (systemId, systemName) =>
    set({ level: "C2", systemId, systemName, containerId: null, containerName: null }),

  drillToC3: (containerId, containerName) =>
    set({ level: "C3", containerId, containerName }),

  goToC1: () =>
    set({ level: "C1", systemId: null, systemName: null, containerId: null, containerName: null }),

  goToC2: () =>
    set({ level: "C2", containerId: null, containerName: null }),
}));
