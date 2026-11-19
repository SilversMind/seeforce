/** One `- ` line of a description, with the lines indented under it. */
export interface Bullet {
  text: string;
  children: Bullet[];
}

const BULLET_RE = /^(\s*)- (.*)$/;

/** Parses a `- ` bullet description into a tree, or returns null when it is prose. */
export function parseBullets(text: string): Bullet[] | null {
  const lines = text.split("\n").filter((l) => l.trim());
  if (lines.length === 0) return null;
  const root: Bullet[] = [];
  const stack: { indent: number; children: Bullet[] }[] = [{ indent: -1, children: root }];
  for (const line of lines) {
    const m = BULLET_RE.exec(line);
    if (!m) return null;
    const indent = m[1].length;
    while (stack[stack.length - 1].indent >= indent) stack.pop();
    const bullet: Bullet = { text: m[2].trim(), children: [] };
    stack[stack.length - 1].children.push(bullet);
    stack.push({ indent, children: bullet.children });
  }
  return root;
}

/** Counts the capabilities of a description: its leaf bullets, or 1 for a non-empty phrase. */
export function countCapabilities(text: string): number {
  const bullets = parseBullets(text);
  if (!bullets) return text.trim() ? 1 : 0;
  const leaves = (items: Bullet[]): number => items.reduce((n, b) => n + (b.children.length ? leaves(b.children) : 1), 0);
  return leaves(bullets);
}

/** Flattens a description to one line for a node card: top-level bullets joined, sub-bullets dropped. */
export function oneLine(text: string): string {
  const bullets = parseBullets(text);
  return bullets ? bullets.map((b) => b.text.replace(/:$/, "")).join(" · ") : text;
}

/** The text a node card shows: its short_desc, else its description squeezed to one line. */
export function cardText(data: Record<string, unknown>, mode: string): string {
  const overlay = mode === "enriched" ? (data.overlay_description as string) : "";
  const text = overlay || (data.short_desc as string) || (data.description as string) || "";
  return oneLine(text);
}
