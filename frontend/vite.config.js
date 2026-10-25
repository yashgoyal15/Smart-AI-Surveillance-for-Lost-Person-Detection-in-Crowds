import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// simple vite config, nothing fancy
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
