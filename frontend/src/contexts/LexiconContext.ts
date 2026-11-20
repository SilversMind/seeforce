/*
@c3:component
name: Lexicon
container: Frontend
description: |
  - Shares the project's loaded glossary through React context
  - Highlights glossary terms in node descriptions and edge labels
  - Shows a term's definition in a bottom panel on click
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
