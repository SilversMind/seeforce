/*
@c3:component
name: Feature List
container: Frontend
technology: React
description: Reads the feature catalogue off the project payload and lists what the repo lets you do, grouped by category, with the prerequisites a reader must satisfy shown apart from the capabilities the repo offers. Shows each feature's one-sentence intent, the model elements it names, and whether a human has reviewed it or an agent generated it. Carries no drift indicator of any kind, because no verdict is stored and a stale badge would be worse than none.
short_desc: Lists the catalogue of intentions a repo serves, grouped by category
uses:
- Backend: "reads the feature catalogue from the project payload it already fetches to draw the map"
  technology: REST
*/
import useSWR from "swr";
import { Link, useParams } from "react-router-dom";
import { fetchProjectMap, type CatalogueFeature } from "../services/api";

const MUTED = "var(--c4-sidebar-muted)";
const BORDER = "1px solid var(--c4-sidebar-border)";

function ReviewMark({ reviewed }: { reviewed: boolean }) {
  return (
    <span
      title={reviewed ? "Reviewed by a human" : "Generated, not yet reviewed"}
      style={{
        fontSize: 10,
        textTransform: "uppercase",
        letterSpacing: 0.5,
        padding: "2px 6px",
        borderRadius: 3,
        border: BORDER,
        color: reviewed ? "var(--c4-sidebar-text)" : MUTED,
        opacity: reviewed ? 1 : 0.75,
        whiteSpace: "nowrap",
      }}
    >
      {reviewed ? "reviewed" : "generated"}
    </span>
  );
}

function FeatureRow({ feature }: { feature: CatalogueFeature }) {
  return (
    <li style={{ padding: "10px 0", borderBottom: BORDER, listStyle: "none" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ fontWeight: 600, fontSize: 14, color: "var(--c4-sidebar-text)" }}>{feature.name}</span>
        <ReviewMark reviewed={feature.reviewed} />
      </div>
      <div style={{ fontSize: 13, color: MUTED, marginTop: 2 }}>{feature.intent}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
        {feature.components.map((component) => (
          <span
            key={component}
            style={{ fontSize: 11, color: MUTED, border: BORDER, borderRadius: 3, padding: "1px 5px" }}
          >
            {component}
          </span>
        ))}
      </div>
    </li>
  );
}

function Block({ title, features }: { title: string; features: CatalogueFeature[] }) {
  if (features.length === 0) return null;
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.6, color: MUTED, marginBottom: 2 }}>
        {title}
      </div>
      <ul style={{ margin: 0, padding: 0 }}>
        {features.map((f) => (
          <FeatureRow key={f.id} feature={f} />
        ))}
      </ul>
    </div>
  );
}

export function FeaturesPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);
  const { data, error } = useSWR(["project", projectId], () => fetchProjectMap(projectId));

  const categories = data?.features?.categories ?? [];
  const total = categories.reduce((n, c) => n + c.features.length, 0);

  return (
    <div style={{ maxWidth: 820, margin: "0 auto", padding: "24px 16px", color: "var(--c4-sidebar-text)" }}>
      <Link to={`/project/${projectId}`} style={{ fontSize: 13, color: MUTED, textDecoration: "none" }}>
        ← Back to the map
      </Link>
      <h1 style={{ fontSize: 20, margin: "12px 0 0" }}>What this repo lets you do</h1>
      <div style={{ fontSize: 13, color: MUTED, marginTop: 4 }}>
        {data?.name}
        {total > 0 ? ` · ${total} features` : ""}
      </div>

      {error && <div style={{ marginTop: 24, fontSize: 13 }}>Could not load this project.</div>}
      {!error && !data && <div style={{ marginTop: 24, fontSize: 13, color: MUTED }}>Loading…</div>}

      {data && total === 0 && (
        <div style={{ marginTop: 24, fontSize: 13, color: MUTED }}>
          This project has no feature catalogue. Commit a <code>.seeforce/features.json</code> and import it again.
        </div>
      )}

      {categories.map((category) => (
        <section key={category.name} style={{ marginTop: 28 }}>
          <h2 style={{ fontSize: 15, margin: 0, paddingBottom: 4, borderBottom: BORDER }}>{category.name}</h2>
          <Block title="Capabilities" features={category.features.filter((f) => f.kind === "capability")} />
          <Block title="Prerequisites" features={category.features.filter((f) => f.kind === "prerequisite")} />
        </section>
      ))}
    </div>
  );
}
