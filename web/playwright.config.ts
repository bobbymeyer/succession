import { defineConfig } from "@playwright/test";

// Runs against the production build, served the way GitHub Pages will serve
// it. `npm run build` first.
export default defineConfig({
  testDir: "tests",
  timeout: 180_000,
  use: { baseURL: "http://127.0.0.1:4173/", browserName: "chromium" },
  webServer: [
    {
      command: "npx vite preview --port 4173 --strictPort --host 127.0.0.1",
      url: "http://127.0.0.1:4173/",
      reuseExistingServer: !process.env.CI,
    },
    {
      // Somebody else's site, for tests/embed.spec.ts: another origin
      // (localhost, not 127.0.0.1) serving whatever page the test writes.
      command: "node -e \"require('fs').mkdirSync('.embed-parent',{recursive:true})\" && python3 -m http.server 4174 --bind 127.0.0.1 --directory .embed-parent",
      url: "http://127.0.0.1:4174/",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
