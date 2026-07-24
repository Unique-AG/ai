import { defineConfig } from "astro/config";

// Single static page, all CSS inlined as <style>, no client islands anywhere
// in src/ → `astro build` never emits a bundled script for the live target.
// (The preview target adds exactly one plain <script src="/mock-host.js">,
// injected conditionally in src/pages/index.astro — see that file and
// public/mock-host.js.)
export default defineConfig({
  output: "static",
  build: {
    inlineStylesheets: "always",
  },
  // `astro dev`'s Vite dependency-scanner (esbuild) chokes on this page —
  // a known Vite/Astro limitation where its scan phase mis-parses raw HTML
  // as JS ("Failed to scan for dependencies... Unexpected \"!\"" at
  // `<!doctype html>`) — unrelated to `astro build`, which fully compiles
  // through the real Astro compiler and is unaffected (see README). We
  // have zero client-side npm imports to pre-bundle anyway (mock-host.js
  // is plain vanilla JS loaded via <script src>), so skipping the scan
  // entirely is safe here.
  vite: {
    optimizeDeps: {
      noDiscovery: true,
    },
  },
});
