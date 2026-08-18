import { create } from "zustand";

export type Level = "C1" | "C2" | "C3";

export interface ViewState {
  projectMapId: number | null;
  shareToken: string | null;
  level: Level;
  systemId: string | null;
  systemName: string | null;
  containerId: string | null;
  containerName: string | null;
}

interface ViewStore extends ViewState {
  setProjectMap: (id: number) => void;
  setShareView: (id: number, token: string) => void;
  clearProjectMap: () => void;
  drillToC2: (systemId: string, systemName: string) => void;
  drillToC3: (containerId: string, containerName: string) => void;
  goToC1: () => void;
  goToC2: () => void;
}

export const useViewStore = create<ViewStore>((set) => ({
  projectMapId: null,
  shareToken: null,
  level: "C1",
  systemId: null,
  systemName: null,
  containerId: null,
  containerName: null,

  setProjectMap: (id) =>
    set({ projectMapId: id, shareToken: null, level: "C1", systemId: null, systemName: null, containerId: null, containerName: null }),

  setShareView: (id, token) =>
    set({ projectMapId: id, shareToken: token, level: "C1", systemId: null, systemName: null, containerId: null, containerName: null }),

  clearProjectMap: () =>
    set({ projectMapId: null, shareToken: null, level: "C1", systemId: null, systemName: null, containerId: null, containerName: null }),

  drillToC2: (systemId, systemName) =>
    set({ level: "C2", systemId, systemName, containerId: null, containerName: null }),

  drillToC3: (containerId, containerName) =>
    set({ level: "C3", containerId, containerName }),

  goToC1: () =>
    set({ level: "C1", systemId: null, systemName: null, containerId: null, containerName: null }),

  goToC2: () =>
    set({ level: "C2", containerId: null, containerName: null }),
}));
