import { defineConfig } from "@playwright/test";

// Runs against the production build, served the way GitHub Pages will serve
// it. `npm run build` first.
export default defineConfig({
  testDir: "tests",
  timeout: 180_000,
  use: { baseURL: "http://127.0.0.1:4173/", browserName: "chromium" },
  webServer: {
    command: "npx vite preview --port 4173 --strictPort --host 127.0.0.1",
    url: "http://127.0.0.1:4173/",
    reuseExistingServer: !process.env.CI,
  },
});
