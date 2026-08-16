import type { LexiconEntry } from "../services/api";

export type { LexiconEntry };

export type Segment =
  | { type: "text"; content: string }
  | { type: "term"; content: string; entry: LexiconEntry };

export function highlightTerms(text: string, lexicon: LexiconEntry[]): Segment[] {
  if (!text || lexicon.length === 0) return [{ type: "text", content: text }];

  // Sort longest first so "Memory Bus" matches before "Memory"
  const sorted = [...lexicon].sort((a, b) => b.term.length - a.term.length);

  const escaped = sorted.map((e) => e.term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const regex = new RegExp(`\\b(${escaped.join("|")})\\b`, "gi");

  const segments: Segment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "text", content: text.slice(lastIndex, match.index) });
    }
    const matchedText = match[0];
    const entry = sorted.find((e) => e.term.toLowerCase() === matchedText.toLowerCase())!;
    segments.push({ type: "term", content: matchedText, entry });
    lastIndex = match.index + matchedText.length;
  }

  if (lastIndex < text.length) {
    segments.push({ type: "text", content: text.slice(lastIndex) });
  }

  return segments.length > 0 ? segments : [{ type: "text", content: text }];
}
