import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Relative URLs throughout, so the built site works at any path: GitHub
  // Pages under /succession/, or copied into another site and iframed.
  base: "./",
  worker: { format: "es" },
});
