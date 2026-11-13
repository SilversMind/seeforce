/*
@c3:component
name: Lexicon
container: Frontend
description: Provides per-project glossary to the graph — distributes the loaded terms through React context, highlights matching terms in blue within node descriptions and edge relationship labels, and shows the definition in a slide-up bottom panel on click.
short_desc: Per-project glossary — highlights and defines terms in the graph
uses:
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
