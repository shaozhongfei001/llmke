import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import path from "path";

export default defineConfig({
  build: {
    outDir: "rag",
    sourcemap: false
  },
  plugins: [react(), svgr()],
  resolve: {
    alias: [
      { find: "@root", replacement: path.resolve(__dirname, ".") },
      { find: "@", replacement: path.resolve(__dirname, "src") },
      { find: "@core", replacement: path.resolve(__dirname, "src/core") }
    ]
  }
});


