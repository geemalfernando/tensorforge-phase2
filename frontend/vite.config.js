import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
export default defineConfig({
  plugins: [react()],
  base: "/static/ui/",
  build: {
    outDir: "../app/static/ui",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/dashboard": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/docs": "http://127.0.0.1:8000",
      "/openapi.json": "http://127.0.0.1:8000",
    },
  },
});
