import { useLexicon } from "../../../contexts/LexiconContext";
import { highlightTerms } from "../../../lib/lexicon";

interface Props {
  text: string;
  style?: React.CSSProperties;
}

export function DescriptionWithHighlights({ text, style }: Props) {
  const { lexicon, setActiveTerm } = useLexicon();
  if (!text) return null;
  const segments = highlightTerms(text, lexicon);

  return (
    <div style={style}>
      {segments.map((seg, i) =>
        seg.type === "text" ? (
          <span key={i}>{seg.content}</span>
        ) : (
          <span
            key={i}
            onClick={(e) => {
              e.stopPropagation();
              setActiveTerm(seg.entry);
            }}
            style={{
              color: "var(--c4-system-border)",
              textDecoration: "underline",
              cursor: "pointer",
            }}
          >
            {seg.content}
          </span>
        ),
      )}
    </div>
  );
}
