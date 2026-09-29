#!/usr/bin/env node
/**
 * Bakes LoginPage into dist/index.html so crawlers that don't run JS read the landing copy.
 * NOTE: main.tsx uses createRoot, so React discards this markup and re-renders instead of hydrating.
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

  // Django's catch-all serves this file on every route, so drop the markup anywhere but "/".
  const guard = `<script>if(location.pathname!=="/")document.getElementById("root").textContent="";</script>`;
  await writeFile(target, shell.replace(MOUNT, `<div id="root">${markup}</div>${guard}`));
  console.log(`prerender: injected ${markup.length} bytes of landing markup into dist/index.html`);
} finally {
  await vite.close();
}
