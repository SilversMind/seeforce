#!/usr/bin/env node
/**
 * Bakes the anonymous landing view into dist/index.html at build time.
 *
 * The landing copy lives in LoginPage, which App only mounts after an async
 * auth check resolves. Crawlers that don't execute JS — every LLM crawler, and
 * Googlebot before its deferred render pass — therefore see an empty mount
 * point, and JS-capable ones can snapshot the "Loading…" branch instead. This
 * puts the real markup in the served HTML; main.tsx uses createRoot, so React
 * discards this copy and re-renders on mount rather than hydrating it.
 *
 * Run by `npm run build` after `vite build`. Vite's ssrLoadModule handles the
 * TS/JSX transform, so this needs no separate build step for the component.
 */
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const target = resolve(root, "dist/index.html");
const MOUNT = '<div id="root"></div>';

const vite = await createServer({
  root,
  configFile: false,
  logLevel: "warn",
  server: { middlewareMode: true },
  appType: "custom",
});

try {
  const { default: LoginPage } = await vite.ssrLoadModule("/src/pages/LoginPage.tsx");
  if (typeof LoginPage !== "function") {
    throw new Error("src/pages/LoginPage.tsx has no default-exported component");
  }

  const markup = renderToStaticMarkup(createElement(LoginPage));
  if (!markup.includes("SeeForce")) {
    throw new Error("prerendered markup is missing the landing copy — did LoginPage change?");
  }

  const shell = await readFile(target, "utf8");
  if (!shell.includes(MOUNT)) {
    throw new Error(`mount point ${MOUNT} not found in ${target} — run vite build first`);
  }

  // Django's catch-all serves this file on every route, so drop the landing
  // markup anywhere but "/" — bots don't run this and still read the copy.
  const guard = `<script>if(location.pathname!=="/")document.getElementById("root").textContent="";</script>`;
  await writeFile(target, shell.replace(MOUNT, `<div id="root">${markup}</div>${guard}`));
  console.log(`prerender: injected ${markup.length} bytes of landing markup into dist/index.html`);
} finally {
  await vite.close();
}
