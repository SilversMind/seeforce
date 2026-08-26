/*
@c3:component
name: Lexicon
container: Frontend
description: Provides per-project glossary to the graph — loads terms via SWR, distributes them through React context, highlights matching terms in blue within node descriptions and edge relationship labels, and shows the definition in a slide-up bottom panel on click.
uses:
- Edit API: "fetches and mutates lexicon entries"
  technology: REST
- Architecture Visualizer: "injects lexicon context into the ReactFlow node tree"
*/

import { createContext, useContext } from "react";
import type { LexiconEntry } from "../lib/lexicon";

export interface LexiconContextValue {
  lexicon: LexiconEntry[];
  setActiveTerm: (entry: LexiconEntry | null) => void;
}

export const LexiconContext = createContext<LexiconContextValue>({
  lexicon: [],
  setActiveTerm: () => {},
});

export function useLexicon(): LexiconContextValue {
  return useContext(LexiconContext);
}
