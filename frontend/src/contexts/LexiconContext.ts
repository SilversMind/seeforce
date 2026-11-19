/*
@c3:component
name: Lexicon
container: Frontend
description: |
  - Shares the project's glossary with every node, edge and sidebar of the graph
  - Lets any of them open a term's definition in the bottom panel
short_desc: Shares the project's glossary and the open term across the graph
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
