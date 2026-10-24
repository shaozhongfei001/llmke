// vite.config.ts
import { defineConfig, normalizePath } from "file:///E:/workplace/Project/Rag/search_agent/node_modules/vite/dist/node/index.js";
import react from "file:///E:/workplace/Project/Rag/search_agent/node_modules/@vitejs/plugin-react/dist/index.mjs";
import path from "path";
import svgr from "file:///E:/workplace/Project/Rag/search_agent/node_modules/vite-plugin-svgr/dist/index.mjs";
import viteCompression from "file:///E:/workplace/Project/Rag/search_agent/node_modules/vite-plugin-compression/dist/index.mjs";
import resolve from "file:///E:/workplace/Project/Rag/search_agent/node_modules/@rollup/plugin-node-resolve/dist/es/index.js";
import colors from "file:///E:/workplace/Project/Rag/search_agent/node_modules/tailwindcss/colors.js";
import { createRequire } from "node:module";
import { viteStaticCopy } from "file:///E:/workplace/Project/Rag/search_agent/node_modules/vite-plugin-static-copy/dist/index.js";
import legacy from "file:///E:/workplace/Project/Rag/search_agent/node_modules/@vitejs/plugin-legacy/dist/index.mjs";
var __vite_injected_original_dirname = "E:\\workplace\\Project\\Rag\\search_agent";
var __vite_injected_original_import_meta_url = "file:///E:/workplace/Project/Rag/search_agent/vite.config.ts";
var require2 = createRequire(__vite_injected_original_import_meta_url);
var pdfjsDistPath = path.dirname(require2.resolve("pdfjs-dist/package.json"));
var cMapsDir = normalizePath(path.join(pdfjsDistPath, "cmaps"));
var SERVER_13 = `http://10.15.12.13`;
var SERVER_12 = `http://10.15.12.12`;
var SERVER_11 = `http://10.15.12.11`;
var CURRENT_SERVER = SERVER_13;
var PORT = CURRENT_SERVER === SERVER_11 || CURRENT_SERVER === SERVER_12 ? "8889" : "8888";
var vite_config_default = defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          redux: ["react-redux", "redux"],
          lodash: ["lodash"],
          axios: ["axios", "axios-mock-adapter"]
        }
      }
    }
  },
  plugins: [
    // eslint({
    //   fix: false,
    //   include: "src/**/*.+(js|ts|tsx)"
    // }),
    viteStaticCopy({
      targets: [
        {
          src: cMapsDir,
          dest: ""
        }
      ]
    }),
    resolve(),
    react(),
    svgr(),
    viteCompression({
      threshold: 512e3
    }),
    legacy({
      targets: [
        "chrome >= 60",
        "firefox >= 75",
        "safari >= 12",
        "not ie <= 11"
      ],
      modernPolyfills: true
    })
  ],
  resolve: {
    alias: [
      {
        find: "@root",
        replacement: path.resolve(__vite_injected_original_dirname, ".")
      },
      {
        find: "@",
        replacement: path.resolve(__vite_injected_original_dirname, "src")
      },
      {
        find: "@core",
        replacement: path.resolve(__vite_injected_original_dirname, "src/core")
      }
    ]
  },
  server: {
    host: "0.0.0.0",
    port: 8888,
    proxy: {
      "/minio": {
        // target: 'http://10.114.10.191:2226/',
        // target: "http://10.64.7.145:80/",
        target: `${CURRENT_SERVER}:9000/`,
        changeOrigin: true,
        rewrite: (path2) => path2.replace(/^\/minio/, "")
      },
      "/cecProxy": {
        // target: 'http://10.114.10.191:2226/',
        // target: "http://10.64.7.145:80/",
        target: `${CURRENT_SERVER}:${PORT}/`,
        changeOrigin: true,
        rewrite: (path2) => path2.replace(/^\/cecProxy/, "")
      },
      "/proxy": {
        // target: "http://10.64.17.78:9001",
        target: `${CURRENT_SERVER}:${PORT}/`,
        changeOrigin: true,
        rewrite: (path2) => path2.replace(/^\/proxy/, "")
      }
      //   "/ai": {
      //     // target: "http://10.64.13.66:8888/qa/ai",
      //     target: `${CURRENT_SERVER}/qa/ai`,
      //     changeOrigin: true,
      //     rewrite: (path) => path.replace(/^\/ai/, "")
      //   },
    }
  },
  preview: {
    port: 8090
  },
  css: {
    preprocessorOptions: {
      less: {
        //关于ant主题的所有变量都在这里修改，使用tailwindcss的颜色变量和项目中的主题同步
        modifyVars: {
          "@primary-color": colors.sky[600]
        },
        javascriptEnabled: true
      }
    }
  },
  optimizeDeps: {
    exclude: ["@mxmweb/fv"]
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJFOlxcXFx3b3JrcGxhY2VcXFxcUHJvamVjdFxcXFxSYWdcXFxcc2VhcmNoX2FnZW50XCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJFOlxcXFx3b3JrcGxhY2VcXFxcUHJvamVjdFxcXFxSYWdcXFxcc2VhcmNoX2FnZW50XFxcXHZpdGUuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9FOi93b3JrcGxhY2UvUHJvamVjdC9SYWcvc2VhcmNoX2FnZW50L3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHsgQ29uZmlnRW52LCBkZWZpbmVDb25maWcsIG5vcm1hbGl6ZVBhdGggfSBmcm9tIFwidml0ZVwiO1xyXG5pbXBvcnQgcmVhY3QgZnJvbSBcIkB2aXRlanMvcGx1Z2luLXJlYWN0XCI7XHJcbmltcG9ydCBwYXRoIGZyb20gXCJwYXRoXCI7XHJcbmltcG9ydCBzdmdyIGZyb20gXCJ2aXRlLXBsdWdpbi1zdmdyXCI7XHJcbmltcG9ydCB2aXRlQ29tcHJlc3Npb24gZnJvbSBcInZpdGUtcGx1Z2luLWNvbXByZXNzaW9uXCI7XHJcbmltcG9ydCByZXNvbHZlIGZyb20gXCJAcm9sbHVwL3BsdWdpbi1ub2RlLXJlc29sdmVcIjtcclxuaW1wb3J0IGNvbG9ycyBmcm9tIFwidGFpbHdpbmRjc3MvY29sb3JzXCI7XHJcbmltcG9ydCB7IGNyZWF0ZVJlcXVpcmUgfSBmcm9tIFwibm9kZTptb2R1bGVcIjtcclxuaW1wb3J0IHsgdml0ZVN0YXRpY0NvcHkgfSBmcm9tIFwidml0ZS1wbHVnaW4tc3RhdGljLWNvcHlcIjtcclxuLy8gaW1wb3J0IGVzbGludCBmcm9tIFwidml0ZS1wbHVnaW4tZXNsaW50XCI7XHJcbmNvbnN0IHJlcXVpcmUgPSBjcmVhdGVSZXF1aXJlKGltcG9ydC5tZXRhLnVybCk7XHJcbmltcG9ydCBsZWdhY3kgZnJvbSBcIkB2aXRlanMvcGx1Z2luLWxlZ2FjeVwiO1xyXG5cclxuY29uc3QgcGRmanNEaXN0UGF0aCA9IHBhdGguZGlybmFtZShyZXF1aXJlLnJlc29sdmUoXCJwZGZqcy1kaXN0L3BhY2thZ2UuanNvblwiKSk7XHJcbmNvbnN0IGNNYXBzRGlyID0gbm9ybWFsaXplUGF0aChwYXRoLmpvaW4ocGRmanNEaXN0UGF0aCwgXCJjbWFwc1wiKSk7XHJcbmNvbnN0IFNFUlZFUl8xMTUgPSBgaHR0cDovLzE5Mi4xNjguNS4xMTVgO1xyXG5jb25zdCBTRVJWRVJfMTE2ID0gYGh0dHA6Ly8xOTIuMTY4LjUuMTE2YDtcclxuY29uc3QgU0VSVkVSXzc4ID0gYGh0dHA6Ly8xMC42NC4xMy42NmA7XHJcbmNvbnN0IFNFUlZFUl8xNDUgPSBgaHR0cDovLzEwLjY0LjcuMTQ1YDtcclxuY29uc3QgU0VSVkVSXzE4NSA9IGBodHRwOi8vMTEyLjEyNC40Ny4xODVgO1xyXG5jb25zdCBTRVJWRVJfMTMgPSBgaHR0cDovLzEwLjE1LjEyLjEzYDtcclxuY29uc3QgU0VSVkVSXzEyID0gYGh0dHA6Ly8xMC4xNS4xMi4xMmA7XHJcbmNvbnN0IFNFUlZFUl8xMSA9IGBodHRwOi8vMTAuMTUuMTIuMTFgO1xyXG5cclxuLy8gZXNsaW50LWRpc2FibGUtbmV4dC1saW5lIHByZWZlci1jb25zdFxyXG5sZXQgQ1VSUkVOVF9TRVJWRVIgPSBTRVJWRVJfMTM7XHJcblxyXG5jb25zdCBQT1JUID1cclxuICBDVVJSRU5UX1NFUlZFUiA9PT0gU0VSVkVSXzExIHx8IENVUlJFTlRfU0VSVkVSID09PSBTRVJWRVJfMTJcclxuICAgID8gXCI4ODg5XCJcclxuICAgIDogXCI4ODg4XCI7IC8vODg4OFxyXG5cclxuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKHtcclxuICBidWlsZDoge1xyXG4gICAgcm9sbHVwT3B0aW9uczoge1xyXG4gICAgICBvdXRwdXQ6IHtcclxuICAgICAgICBtYW51YWxDaHVua3M6IHtcclxuICAgICAgICAgIHJlYWN0OiBbXCJyZWFjdFwiLCBcInJlYWN0LWRvbVwiLCBcInJlYWN0LXJvdXRlci1kb21cIl0sXHJcbiAgICAgICAgICByZWR1eDogW1wicmVhY3QtcmVkdXhcIiwgXCJyZWR1eFwiXSxcclxuICAgICAgICAgIGxvZGFzaDogW1wibG9kYXNoXCJdLFxyXG4gICAgICAgICAgYXhpb3M6IFtcImF4aW9zXCIsIFwiYXhpb3MtbW9jay1hZGFwdGVyXCJdXHJcbiAgICAgICAgfVxyXG4gICAgICB9XHJcbiAgICB9XHJcbiAgfSxcclxuICBwbHVnaW5zOiBbXHJcbiAgICAvLyBlc2xpbnQoe1xyXG4gICAgLy8gICBmaXg6IGZhbHNlLFxyXG4gICAgLy8gICBpbmNsdWRlOiBcInNyYy8qKi8qLisoanN8dHN8dHN4KVwiXHJcbiAgICAvLyB9KSxcclxuICAgIHZpdGVTdGF0aWNDb3B5KHtcclxuICAgICAgdGFyZ2V0czogW1xyXG4gICAgICAgIHtcclxuICAgICAgICAgIHNyYzogY01hcHNEaXIsXHJcbiAgICAgICAgICBkZXN0OiBcIlwiXHJcbiAgICAgICAgfVxyXG4gICAgICBdXHJcbiAgICB9KSxcclxuICAgIHJlc29sdmUoKSxcclxuICAgIHJlYWN0KCksXHJcbiAgICBzdmdyKCksXHJcbiAgICB2aXRlQ29tcHJlc3Npb24oe1xyXG4gICAgICB0aHJlc2hvbGQ6IDUxMjAwMFxyXG4gICAgfSksXHJcbiAgICBsZWdhY3koe1xyXG4gICAgICB0YXJnZXRzOiBbXHJcbiAgICAgICAgXCJjaHJvbWUgPj0gNjBcIixcclxuICAgICAgICBcImZpcmVmb3ggPj0gNzVcIixcclxuICAgICAgICBcInNhZmFyaSA+PSAxMlwiLFxyXG4gICAgICAgIFwibm90IGllIDw9IDExXCJcclxuICAgICAgXSxcclxuICAgICAgbW9kZXJuUG9seWZpbGxzOiB0cnVlXHJcbiAgICB9KVxyXG4gIF0gYXMgYW55W10sXHJcbiAgcmVzb2x2ZToge1xyXG4gICAgYWxpYXM6IFtcclxuICAgICAge1xyXG4gICAgICAgIGZpbmQ6IFwiQHJvb3RcIixcclxuICAgICAgICByZXBsYWNlbWVudDogcGF0aC5yZXNvbHZlKF9fZGlybmFtZSwgXCIuXCIpXHJcbiAgICAgIH0sXHJcbiAgICAgIHtcclxuICAgICAgICBmaW5kOiBcIkBcIixcclxuICAgICAgICByZXBsYWNlbWVudDogcGF0aC5yZXNvbHZlKF9fZGlybmFtZSwgXCJzcmNcIilcclxuICAgICAgfSxcclxuICAgICAge1xyXG4gICAgICAgIGZpbmQ6IFwiQGNvcmVcIixcclxuICAgICAgICByZXBsYWNlbWVudDogcGF0aC5yZXNvbHZlKF9fZGlybmFtZSwgXCJzcmMvY29yZVwiKVxyXG4gICAgICB9XHJcbiAgICBdXHJcbiAgfSxcclxuICBzZXJ2ZXI6IHtcclxuICAgIGhvc3Q6IFwiMC4wLjAuMFwiLFxyXG4gICAgcG9ydDogODg4OCxcclxuICAgIHByb3h5OiB7XHJcbiAgICAgIFwiL21pbmlvXCI6IHtcclxuICAgICAgICAvLyB0YXJnZXQ6ICdodHRwOi8vMTAuMTE0LjEwLjE5MToyMjI2LycsXHJcbiAgICAgICAgLy8gdGFyZ2V0OiBcImh0dHA6Ly8xMC42NC43LjE0NTo4MC9cIixcclxuICAgICAgICB0YXJnZXQ6IGAke0NVUlJFTlRfU0VSVkVSfTo5MDAwL2AsXHJcbiAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlLFxyXG4gICAgICAgIHJld3JpdGU6IChwYXRoKSA9PiBwYXRoLnJlcGxhY2UoL15cXC9taW5pby8sIFwiXCIpXHJcbiAgICAgIH0sXHJcbiAgICAgIFwiL2NlY1Byb3h5XCI6IHtcclxuICAgICAgICAvLyB0YXJnZXQ6ICdodHRwOi8vMTAuMTE0LjEwLjE5MToyMjI2LycsXHJcbiAgICAgICAgLy8gdGFyZ2V0OiBcImh0dHA6Ly8xMC42NC43LjE0NTo4MC9cIixcclxuICAgICAgICB0YXJnZXQ6IGAke0NVUlJFTlRfU0VSVkVSfToke1BPUlR9L2AsXHJcbiAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlLFxyXG4gICAgICAgIHJld3JpdGU6IChwYXRoKSA9PiBwYXRoLnJlcGxhY2UoL15cXC9jZWNQcm94eS8sIFwiXCIpXHJcbiAgICAgIH0sXHJcbiAgICAgIFwiL3Byb3h5XCI6IHtcclxuICAgICAgICAvLyB0YXJnZXQ6IFwiaHR0cDovLzEwLjY0LjE3Ljc4OjkwMDFcIixcclxuICAgICAgICB0YXJnZXQ6IGAke0NVUlJFTlRfU0VSVkVSfToke1BPUlR9L2AsXHJcbiAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlLFxyXG4gICAgICAgIHJld3JpdGU6IChwYXRoKSA9PiBwYXRoLnJlcGxhY2UoL15cXC9wcm94eS8sIFwiXCIpXHJcbiAgICAgIH1cclxuICAgICAgLy8gICBcIi9haVwiOiB7XHJcbiAgICAgIC8vICAgICAvLyB0YXJnZXQ6IFwiaHR0cDovLzEwLjY0LjEzLjY2Ojg4ODgvcWEvYWlcIixcclxuICAgICAgLy8gICAgIHRhcmdldDogYCR7Q1VSUkVOVF9TRVJWRVJ9L3FhL2FpYCxcclxuICAgICAgLy8gICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcclxuICAgICAgLy8gICAgIHJld3JpdGU6IChwYXRoKSA9PiBwYXRoLnJlcGxhY2UoL15cXC9haS8sIFwiXCIpXHJcbiAgICAgIC8vICAgfSxcclxuICAgIH1cclxuICB9LFxyXG4gIHByZXZpZXc6IHtcclxuICAgIHBvcnQ6IDgwOTBcclxuICB9LFxyXG4gIGNzczoge1xyXG4gICAgcHJlcHJvY2Vzc29yT3B0aW9uczoge1xyXG4gICAgICBsZXNzOiB7XHJcbiAgICAgICAgLy9cdTUxNzNcdTRFOEVhbnRcdTRFM0JcdTk4OThcdTc2ODRcdTYyNDBcdTY3MDlcdTUzRDhcdTkxQ0ZcdTkwRkRcdTU3MjhcdThGRDlcdTkxQ0NcdTRGRUVcdTY1MzlcdUZGMENcdTRGN0ZcdTc1Mjh0YWlsd2luZGNzc1x1NzY4NFx1OTg5Q1x1ODI3Mlx1NTNEOFx1OTFDRlx1NTQ4Q1x1OTg3OVx1NzZFRVx1NEUyRFx1NzY4NFx1NEUzQlx1OTg5OFx1NTQwQ1x1NkI2NVxyXG4gICAgICAgIG1vZGlmeVZhcnM6IHtcclxuICAgICAgICAgIFwiQHByaW1hcnktY29sb3JcIjogY29sb3JzLnNreVs2MDBdXHJcbiAgICAgICAgfSxcclxuICAgICAgICBqYXZhc2NyaXB0RW5hYmxlZDogdHJ1ZVxyXG4gICAgICB9XHJcbiAgICB9XHJcbiAgfSxcclxuICBvcHRpbWl6ZURlcHM6IHtcclxuICAgIGV4Y2x1ZGU6IFtcIkBteG13ZWIvZnZcIl1cclxuICB9XHJcbn0gYXMgY29uc3QpO1xyXG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQTJTLFNBQW9CLGNBQWMscUJBQXFCO0FBQ2xXLE9BQU8sV0FBVztBQUNsQixPQUFPLFVBQVU7QUFDakIsT0FBTyxVQUFVO0FBQ2pCLE9BQU8scUJBQXFCO0FBQzVCLE9BQU8sYUFBYTtBQUNwQixPQUFPLFlBQVk7QUFDbkIsU0FBUyxxQkFBcUI7QUFDOUIsU0FBUyxzQkFBc0I7QUFHL0IsT0FBTyxZQUFZO0FBWG5CLElBQU0sbUNBQW1DO0FBQWtKLElBQU0sMkNBQTJDO0FBVTVPLElBQU1BLFdBQVUsY0FBYyx3Q0FBZTtBQUc3QyxJQUFNLGdCQUFnQixLQUFLLFFBQVFBLFNBQVEsUUFBUSx5QkFBeUIsQ0FBQztBQUM3RSxJQUFNLFdBQVcsY0FBYyxLQUFLLEtBQUssZUFBZSxPQUFPLENBQUM7QUFNaEUsSUFBTSxZQUFZO0FBQ2xCLElBQU0sWUFBWTtBQUNsQixJQUFNLFlBQVk7QUFHbEIsSUFBSSxpQkFBaUI7QUFFckIsSUFBTSxPQUNKLG1CQUFtQixhQUFhLG1CQUFtQixZQUMvQyxTQUNBO0FBRU4sSUFBTyxzQkFBUSxhQUFhO0FBQUEsRUFDMUIsT0FBTztBQUFBLElBQ0wsZUFBZTtBQUFBLE1BQ2IsUUFBUTtBQUFBLFFBQ04sY0FBYztBQUFBLFVBQ1osT0FBTyxDQUFDLFNBQVMsYUFBYSxrQkFBa0I7QUFBQSxVQUNoRCxPQUFPLENBQUMsZUFBZSxPQUFPO0FBQUEsVUFDOUIsUUFBUSxDQUFDLFFBQVE7QUFBQSxVQUNqQixPQUFPLENBQUMsU0FBUyxvQkFBb0I7QUFBQSxRQUN2QztBQUFBLE1BQ0Y7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBLEVBQ0EsU0FBUztBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUEsSUFLUCxlQUFlO0FBQUEsTUFDYixTQUFTO0FBQUEsUUFDUDtBQUFBLFVBQ0UsS0FBSztBQUFBLFVBQ0wsTUFBTTtBQUFBLFFBQ1I7QUFBQSxNQUNGO0FBQUEsSUFDRixDQUFDO0FBQUEsSUFDRCxRQUFRO0FBQUEsSUFDUixNQUFNO0FBQUEsSUFDTixLQUFLO0FBQUEsSUFDTCxnQkFBZ0I7QUFBQSxNQUNkLFdBQVc7QUFBQSxJQUNiLENBQUM7QUFBQSxJQUNELE9BQU87QUFBQSxNQUNMLFNBQVM7QUFBQSxRQUNQO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxRQUNBO0FBQUEsTUFDRjtBQUFBLE1BQ0EsaUJBQWlCO0FBQUEsSUFDbkIsQ0FBQztBQUFBLEVBQ0g7QUFBQSxFQUNBLFNBQVM7QUFBQSxJQUNQLE9BQU87QUFBQSxNQUNMO0FBQUEsUUFDRSxNQUFNO0FBQUEsUUFDTixhQUFhLEtBQUssUUFBUSxrQ0FBVyxHQUFHO0FBQUEsTUFDMUM7QUFBQSxNQUNBO0FBQUEsUUFDRSxNQUFNO0FBQUEsUUFDTixhQUFhLEtBQUssUUFBUSxrQ0FBVyxLQUFLO0FBQUEsTUFDNUM7QUFBQSxNQUNBO0FBQUEsUUFDRSxNQUFNO0FBQUEsUUFDTixhQUFhLEtBQUssUUFBUSxrQ0FBVyxVQUFVO0FBQUEsTUFDakQ7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBLEVBQ0EsUUFBUTtBQUFBLElBQ04sTUFBTTtBQUFBLElBQ04sTUFBTTtBQUFBLElBQ04sT0FBTztBQUFBLE1BQ0wsVUFBVTtBQUFBO0FBQUE7QUFBQSxRQUdSLFFBQVEsR0FBRyxjQUFjO0FBQUEsUUFDekIsY0FBYztBQUFBLFFBQ2QsU0FBUyxDQUFDQyxVQUFTQSxNQUFLLFFBQVEsWUFBWSxFQUFFO0FBQUEsTUFDaEQ7QUFBQSxNQUNBLGFBQWE7QUFBQTtBQUFBO0FBQUEsUUFHWCxRQUFRLEdBQUcsY0FBYyxJQUFJLElBQUk7QUFBQSxRQUNqQyxjQUFjO0FBQUEsUUFDZCxTQUFTLENBQUNBLFVBQVNBLE1BQUssUUFBUSxlQUFlLEVBQUU7QUFBQSxNQUNuRDtBQUFBLE1BQ0EsVUFBVTtBQUFBO0FBQUEsUUFFUixRQUFRLEdBQUcsY0FBYyxJQUFJLElBQUk7QUFBQSxRQUNqQyxjQUFjO0FBQUEsUUFDZCxTQUFTLENBQUNBLFVBQVNBLE1BQUssUUFBUSxZQUFZLEVBQUU7QUFBQSxNQUNoRDtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBLElBT0Y7QUFBQSxFQUNGO0FBQUEsRUFDQSxTQUFTO0FBQUEsSUFDUCxNQUFNO0FBQUEsRUFDUjtBQUFBLEVBQ0EsS0FBSztBQUFBLElBQ0gscUJBQXFCO0FBQUEsTUFDbkIsTUFBTTtBQUFBO0FBQUEsUUFFSixZQUFZO0FBQUEsVUFDVixrQkFBa0IsT0FBTyxJQUFJLEdBQUc7QUFBQSxRQUNsQztBQUFBLFFBQ0EsbUJBQW1CO0FBQUEsTUFDckI7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBLEVBQ0EsY0FBYztBQUFBLElBQ1osU0FBUyxDQUFDLFlBQVk7QUFBQSxFQUN4QjtBQUNGLENBQVU7IiwKICAibmFtZXMiOiBbInJlcXVpcmUiLCAicGF0aCJdCn0K
