import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Listen on all network addresses (0.0.0.0)
    allowedHosts: true, // Allow Cloudflare tunnel hosts
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
