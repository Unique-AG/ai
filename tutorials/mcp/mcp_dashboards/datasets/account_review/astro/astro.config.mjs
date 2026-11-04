import { defineConfig } from "astro/config";

// Single static page, all CSS inlined as <style>, no client islands anywhere
// in src/ → `astro build` never emits a bundled script for the live target.
// The preview and live-local targets each add exactly one <script src>, injected
// conditionally by src/components/HostScripts.astro. Those files are bundled out
// of src/host/ into public/ by scripts/build-hosts.mjs, per mode, so the live
// build's public/ is empty and its output really is zero-JS.
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
  // have zero client-side npm imports for Vite to pre-bundle anyway — the host
  // scripts are bundled separately by esbuild and served from public/ as plain
  // <script src> — so skipping the scan entirely is safe here.
  vite: {
    optimizeDeps: {
      noDiscovery: true,
    },
  },
});
