import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:38987"
    }
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom"],
          "graph-vendor": ["@xyflow/react"],
          "motion-vendor": ["framer-motion"],
          "icons-vendor": ["lucide-react"]
        }
      }
    }
  }
});
