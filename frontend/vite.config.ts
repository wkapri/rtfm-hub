import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // bind 0.0.0.0 so other devices on the LAN can reach the dev server
    port: 5174, // 5173 is rtfm-rag's own frontend — different port so both can run at once
    proxy: {
      "/api": "http://localhost:8001", // hubapp backend (8000 is rtfm-rag's own)
    },
  },
});
