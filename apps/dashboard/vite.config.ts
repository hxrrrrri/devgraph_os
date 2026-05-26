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
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom"],
          "graph-vendor": ["@xyflow/react"],
          "layout-vendor": ["@dagrejs/dagre", "elkjs"],
          "community-vendor": ["graphology", "graphology-communities-louvain"],
          "store-vendor": ["zustand"],
          "motion-vendor": ["framer-motion"],
          "markdown-vendor": ["prism-react-renderer", "react-markdown"],
          "icons-vendor": ["lucide-react"]
        }
      }
    }
  }
});
