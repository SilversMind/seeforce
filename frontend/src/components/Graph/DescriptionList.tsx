import { parseBullets, type Bullet } from "../../lib/description";

/** Renders a description as nested bullets, or as plain prose when it is not a `- ` list. */
export function DescriptionList({ text }: { text: string }) {
  const bullets = parseBullets(text);
  if (!bullets) return <div style={{ whiteSpace: "pre-wrap" }}>{text}</div>;
  return <BulletList items={bullets} depth={0} />;
}

function BulletList({ items, depth }: { items: Bullet[]; depth: number }) {
  return (
    <ul style={{ margin: depth ? "2px 0 0" : 0, paddingLeft: 16, display: "flex", flexDirection: "column", gap: 2, listStyleType: depth ? "circle" : "disc" }}>
      {items.map((b, i) => (
        <li key={i} style={{ lineHeight: 1.45 }}>
          {b.text}
          {b.children.length > 0 && <BulletList items={b.children} depth={depth + 1} />}
        </li>
      ))}
    </ul>
  );
}
