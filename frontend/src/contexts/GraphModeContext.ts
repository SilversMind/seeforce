import { createContext, useContext } from "react";

export type GraphMode = "enriched" | "original";

export const GraphModeContext = createContext<GraphMode>("enriched");

export function useGraphMode() {
  return useContext(GraphModeContext);
}
