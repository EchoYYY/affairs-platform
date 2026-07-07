import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api to the FastAPI backend so the SPA and API share an origin in dev.
export default defineConfig({
  plugins: [react()],
  // react-simple-maps can otherwise pull in a second React copy → "Invalid hook call"
  resolve: { dedupe: ["react", "react-dom"] },
  optimizeDeps: { include: ["react-simple-maps", "react", "react-dom"] },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
