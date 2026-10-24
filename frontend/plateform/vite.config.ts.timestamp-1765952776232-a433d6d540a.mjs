// vite.config.ts
import { defineConfig, normalizePath } from "file:///E:/workplace/ai-plateform/node_modules/vite/dist/node/index.js";
import react from "file:///E:/workplace/ai-plateform/node_modules/@vitejs/plugin-react/dist/index.js";
import path from "path";
import svgr from "file:///E:/workplace/ai-plateform/node_modules/vite-plugin-svgr/dist/index.mjs";
import viteCompression from "file:///E:/workplace/ai-plateform/node_modules/vite-plugin-compression/dist/index.mjs";
import resolve from "file:///E:/workplace/ai-plateform/node_modules/@rollup/plugin-node-resolve/dist/es/index.js";
import colors from "file:///E:/workplace/ai-plateform/node_modules/tailwindcss/colors.js";
import { createRequire } from "node:module";
import { viteStaticCopy } from "file:///E:/workplace/ai-plateform/node_modules/vite-plugin-static-copy/dist/index.js";
import legacy from "file:///E:/workplace/ai-plateform/node_modules/@vitejs/plugin-legacy/dist/index.mjs";
var __vite_injected_original_dirname = "E:\\workplace\\ai-plateform";
var __vite_injected_original_import_meta_url = "file:///E:/workplace/ai-plateform/vite.config.ts";
var require2 = createRequire(__vite_injected_original_import_meta_url);
var pdfjsDistPath = path.dirname(require2.resolve("pdfjs-dist/package.json"));
var cMapsDir = normalizePath(path.join(pdfjsDistPath, "cmaps"));
var SERVER_12 = `http://10.15.12.12`;
var SERVER_11 = `http://10.15.12.11`;
var SERVER_20 = `http://10.2.22.20`;
var CURRENT_SERVER = SERVER_20;
var PORT = CURRENT_SERVER === SERVER_20 ? "8889" : CURRENT_SERVER === SERVER_11 || CURRENT_SERVER === SERVER_12 ? "8889" : "8888";
var vite_config_default = defineConfig(({ mode }) => {
  const isDebugBuild = process.env.DEBUG_BUILD === "1";
  return {
    build: {
      outDir: "rag",
      sourcemap: false,
      minify: isDebugBuild ? false : "esbuild",
      reportCompressedSize: isDebugBuild ? false : true,
      rollupOptions: {
        external: isDebugBuild ? [
          /assets\/worker-.*\.js$/,
          "@mxmweb/fviewer",
          "@mxmweb/xviewer",
          "@mxmweb/veoviewer"
        ] : [],
        output: {
          manualChunks(id) {
            if (!id) return;
            if (id.includes("node_modules")) {
              const parts = id.split("node_modules/").pop()?.split("/") || [];
              const pkg = parts[0]?.startsWith("@") ? `${parts[0]}/${parts[1]}` : parts[0];
              if (pkg) return `vendor-${pkg}`;
            }
            if (id.includes("src/assets/")) return "assets";
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
      ...isDebugBuild ? [] : [
        viteCompression({ threshold: 512e3 }),
        legacy({
          targets: [
            "chrome >= 60",
            "firefox >= 75",
            "safari >= 12",
            "not ie <= 11"
          ],
          modernPolyfills: true
        })
      ]
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
      exclude: ["@mxmweb/fv", "@gientech/modual", "@mxmweb/veoviewer"]
    }
  };
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJFOlxcXFx3b3JrcGxhY2VcXFxcYWktcGxhdGVmb3JtXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJFOlxcXFx3b3JrcGxhY2VcXFxcYWktcGxhdGVmb3JtXFxcXHZpdGUuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9FOi93b3JrcGxhY2UvYWktcGxhdGVmb3JtL3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHsgQ29uZmlnRW52LCBkZWZpbmVDb25maWcsIG5vcm1hbGl6ZVBhdGggfSBmcm9tIFwidml0ZVwiO1xyXG5pbXBvcnQgcmVhY3QgZnJvbSBcIkB2aXRlanMvcGx1Z2luLXJlYWN0XCI7XHJcbmltcG9ydCBwYXRoIGZyb20gXCJwYXRoXCI7XHJcbmltcG9ydCBzdmdyIGZyb20gXCJ2aXRlLXBsdWdpbi1zdmdyXCI7XHJcbmltcG9ydCB2aXRlQ29tcHJlc3Npb24gZnJvbSBcInZpdGUtcGx1Z2luLWNvbXByZXNzaW9uXCI7XHJcbmltcG9ydCByZXNvbHZlIGZyb20gXCJAcm9sbHVwL3BsdWdpbi1ub2RlLXJlc29sdmVcIjtcclxuaW1wb3J0IGNvbG9ycyBmcm9tIFwidGFpbHdpbmRjc3MvY29sb3JzXCI7XHJcbmltcG9ydCB7IGNyZWF0ZVJlcXVpcmUgfSBmcm9tIFwibm9kZTptb2R1bGVcIjtcclxuaW1wb3J0IHsgdml0ZVN0YXRpY0NvcHkgfSBmcm9tIFwidml0ZS1wbHVnaW4tc3RhdGljLWNvcHlcIjtcclxuLy8gaW1wb3J0IGVzbGludCBmcm9tIFwidml0ZS1wbHVnaW4tZXNsaW50XCI7XHJcbmNvbnN0IHJlcXVpcmUgPSBjcmVhdGVSZXF1aXJlKGltcG9ydC5tZXRhLnVybCk7XHJcbmltcG9ydCBsZWdhY3kgZnJvbSBcIkB2aXRlanMvcGx1Z2luLWxlZ2FjeVwiO1xyXG5cclxuY29uc3QgcGRmanNEaXN0UGF0aCA9IHBhdGguZGlybmFtZShyZXF1aXJlLnJlc29sdmUoXCJwZGZqcy1kaXN0L3BhY2thZ2UuanNvblwiKSk7XHJcbmNvbnN0IGNNYXBzRGlyID0gbm9ybWFsaXplUGF0aChwYXRoLmpvaW4ocGRmanNEaXN0UGF0aCwgXCJjbWFwc1wiKSk7XHJcbmNvbnN0IFNFUlZFUl8xMTUgPSBgaHR0cDovLzE5Mi4xNjguNS4xMTVgO1xyXG5jb25zdCBTRVJWRVJfMTE2ID0gYGh0dHA6Ly8xOTIuMTY4LjUuMTE2YDtcclxuY29uc3QgU0VSVkVSXzc4ID0gYGh0dHA6Ly8xMC42NC4xMy42NmA7XHJcbmNvbnN0IFNFUlZFUl8xNDUgPSBgaHR0cDovLzEwLjY0LjcuMTQ1YDtcclxuY29uc3QgU0VSVkVSXzE4NSA9IGBodHRwOi8vMTEyLjEyNC40Ny4xODVgO1xyXG5jb25zdCBTRVJWRVJfMTMgPSBgaHR0cDovLzEwLjE1LjEyLjEzYDtcclxuY29uc3QgU0VSVkVSXzEyID0gYGh0dHA6Ly8xMC4xNS4xMi4xMmA7XHJcbmNvbnN0IFNFUlZFUl8xMSA9IGBodHRwOi8vMTAuMTUuMTIuMTFgO1xyXG5jb25zdCBTRVJWRVJfMjAgPSBgaHR0cDovLzEwLjIuMjIuMjBgO1xyXG5cclxuLy8gZXNsaW50LWRpc2FibGUtbmV4dC1saW5lIHByZWZlci1jb25zdFxyXG5sZXQgQ1VSUkVOVF9TRVJWRVIgPSBTRVJWRVJfMjA7XHJcblxyXG5jb25zdCBQT1JUID1cclxuICBDVVJSRU5UX1NFUlZFUiA9PT0gU0VSVkVSXzIwXHJcbiAgICA/IFwiODg4OVwiXHJcbiAgICA6IENVUlJFTlRfU0VSVkVSID09PSBTRVJWRVJfMTEgfHwgQ1VSUkVOVF9TRVJWRVIgPT09IFNFUlZFUl8xMlxyXG4gICAgPyBcIjg4ODlcIlxyXG4gICAgOiBcIjg4ODhcIjsgLy84ODg4XHJcblxyXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoKHsgbW9kZSB9KSA9PiB7XHJcbiAgY29uc3QgaXNEZWJ1Z0J1aWxkID0gcHJvY2Vzcy5lbnYuREVCVUdfQlVJTEQgPT09IFwiMVwiO1xyXG4gIHJldHVybiB7XHJcbiAgICBidWlsZDoge1xyXG4gICAgICBvdXREaXI6IFwicmFnXCIsXHJcbiAgICAgIHNvdXJjZW1hcDogZmFsc2UsXHJcbiAgICAgIG1pbmlmeTogaXNEZWJ1Z0J1aWxkID8gZmFsc2UgOiBcImVzYnVpbGRcIixcclxuICAgICAgcmVwb3J0Q29tcHJlc3NlZFNpemU6IGlzRGVidWdCdWlsZCA/IGZhbHNlIDogdHJ1ZSxcclxuICAgICAgcm9sbHVwT3B0aW9uczoge1xyXG4gICAgICAgIGV4dGVybmFsOiBpc0RlYnVnQnVpbGRcclxuICAgICAgICAgID8gW1xyXG4gICAgICAgICAgICAgIC9hc3NldHNcXC93b3JrZXItLipcXC5qcyQvLFxyXG4gICAgICAgICAgICAgIFwiQG14bXdlYi9mdmlld2VyXCIsXHJcbiAgICAgICAgICAgICAgXCJAbXhtd2ViL3h2aWV3ZXJcIixcclxuICAgICAgICAgICAgICBcIkBteG13ZWIvdmVvdmlld2VyXCJcclxuICAgICAgICAgICAgXVxyXG4gICAgICAgICAgOiBbXSxcclxuICAgICAgICBvdXRwdXQ6IHtcclxuICAgICAgICAgIG1hbnVhbENodW5rcyhpZCkge1xyXG4gICAgICAgICAgICBpZiAoIWlkKSByZXR1cm47XHJcbiAgICAgICAgICAgIGlmIChpZC5pbmNsdWRlcyhcIm5vZGVfbW9kdWxlc1wiKSkge1xyXG4gICAgICAgICAgICAgIGNvbnN0IHBhcnRzID0gaWQuc3BsaXQoXCJub2RlX21vZHVsZXMvXCIpLnBvcCgpPy5zcGxpdChcIi9cIikgfHwgW107XHJcbiAgICAgICAgICAgICAgY29uc3QgcGtnID0gcGFydHNbMF0/LnN0YXJ0c1dpdGgoXCJAXCIpXHJcbiAgICAgICAgICAgICAgICA/IGAke3BhcnRzWzBdfS8ke3BhcnRzWzFdfWBcclxuICAgICAgICAgICAgICAgIDogcGFydHNbMF07XHJcbiAgICAgICAgICAgICAgaWYgKHBrZykgcmV0dXJuIGB2ZW5kb3ItJHtwa2d9YDtcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICAvLyBpZiAoaWQuaW5jbHVkZXMoXCJzcmMvY29tcG9uZW50cy9Lbm93bGVkZ2VCYXNlWmgvXCIpKSB7XHJcbiAgICAgICAgICAgIC8vICAgY29uc3QgcmVsID0gaWQuc3BsaXQoXCJzcmMvY29tcG9uZW50cy9Lbm93bGVkZ2VCYXNlWmgvXCIpLnBvcCgpIHx8IFwia2JcIjtcclxuICAgICAgICAgICAgLy8gICBjb25zdCB0b3AgPSByZWwuc3BsaXQoXCIvXCIpWzBdIHx8IFwia2JcIjtcclxuICAgICAgICAgICAgLy8gICByZXR1cm4gYGtiLSR7dG9wfWA7XHJcbiAgICAgICAgICAgIC8vIH1cclxuICAgICAgICAgICAgaWYgKGlkLmluY2x1ZGVzKFwic3JjL2Fzc2V0cy9cIikpIHJldHVybiBcImFzc2V0c1wiO1xyXG4gICAgICAgICAgfVxyXG4gICAgICAgIH1cclxuICAgICAgfVxyXG4gICAgfSxcclxuICAgIHBsdWdpbnM6IFtcclxuICAgICAgLy8gZXNsaW50KHtcclxuICAgICAgLy8gICBmaXg6IGZhbHNlLFxyXG4gICAgICAvLyAgIGluY2x1ZGU6IFwic3JjLyoqLyouKyhqc3x0c3x0c3gpXCJcclxuICAgICAgLy8gfSksXHJcbiAgICAgIHZpdGVTdGF0aWNDb3B5KHtcclxuICAgICAgICB0YXJnZXRzOiBbXHJcbiAgICAgICAgICB7XHJcbiAgICAgICAgICAgIHNyYzogY01hcHNEaXIsXHJcbiAgICAgICAgICAgIGRlc3Q6IFwiXCJcclxuICAgICAgICAgIH1cclxuICAgICAgICBdXHJcbiAgICAgIH0pLFxyXG4gICAgICByZXNvbHZlKCksXHJcbiAgICAgIHJlYWN0KCksXHJcbiAgICAgIHN2Z3IoKSxcclxuICAgICAgLi4uKGlzRGVidWdCdWlsZFxyXG4gICAgICAgID8gW11cclxuICAgICAgICA6IFtcclxuICAgICAgICAgICAgdml0ZUNvbXByZXNzaW9uKHsgdGhyZXNob2xkOiA1MTIwMDAgfSksXHJcbiAgICAgICAgICAgIGxlZ2FjeSh7XHJcbiAgICAgICAgICAgICAgdGFyZ2V0czogW1xyXG4gICAgICAgICAgICAgICAgXCJjaHJvbWUgPj0gNjBcIixcclxuICAgICAgICAgICAgICAgIFwiZmlyZWZveCA+PSA3NVwiLFxyXG4gICAgICAgICAgICAgICAgXCJzYWZhcmkgPj0gMTJcIixcclxuICAgICAgICAgICAgICAgIFwibm90IGllIDw9IDExXCJcclxuICAgICAgICAgICAgICBdLFxyXG4gICAgICAgICAgICAgIG1vZGVyblBvbHlmaWxsczogdHJ1ZVxyXG4gICAgICAgICAgICB9KVxyXG4gICAgICAgICAgXSlcclxuICAgIF0gYXMgYW55W10sXHJcbiAgICByZXNvbHZlOiB7XHJcbiAgICAgIGFsaWFzOiBbXHJcbiAgICAgICAge1xyXG4gICAgICAgICAgZmluZDogXCJAcm9vdFwiLFxyXG4gICAgICAgICAgcmVwbGFjZW1lbnQ6IHBhdGgucmVzb2x2ZShfX2Rpcm5hbWUsIFwiLlwiKVxyXG4gICAgICAgIH0sXHJcbiAgICAgICAge1xyXG4gICAgICAgICAgZmluZDogXCJAXCIsXHJcbiAgICAgICAgICByZXBsYWNlbWVudDogcGF0aC5yZXNvbHZlKF9fZGlybmFtZSwgXCJzcmNcIilcclxuICAgICAgICB9LFxyXG4gICAgICAgIHtcclxuICAgICAgICAgIGZpbmQ6IFwiQGNvcmVcIixcclxuICAgICAgICAgIHJlcGxhY2VtZW50OiBwYXRoLnJlc29sdmUoX19kaXJuYW1lLCBcInNyYy9jb3JlXCIpXHJcbiAgICAgICAgfVxyXG4gICAgICBdXHJcbiAgICB9LFxyXG4gICAgc2VydmVyOiB7XHJcbiAgICAgIGhvc3Q6IFwiMC4wLjAuMFwiLFxyXG4gICAgICBwb3J0OiA4ODg4LFxyXG4gICAgICBwcm94eToge1xyXG4gICAgICAgIFwiL21pbmlvXCI6IHtcclxuICAgICAgICAgIC8vIHRhcmdldDogJ2h0dHA6Ly8xMC4xMTQuMTAuMTkxOjIyMjYvJyxcclxuICAgICAgICAgIC8vIHRhcmdldDogXCJodHRwOi8vMTAuNjQuNy4xNDU6ODAvXCIsXHJcbiAgICAgICAgICB0YXJnZXQ6IGAke0NVUlJFTlRfU0VSVkVSfTo5MDAwL2AsXHJcbiAgICAgICAgICBjaGFuZ2VPcmlnaW46IHRydWUsXHJcbiAgICAgICAgICByZXdyaXRlOiAocGF0aCkgPT4gcGF0aC5yZXBsYWNlKC9eXFwvbWluaW8vLCBcIlwiKVxyXG4gICAgICAgIH0sXHJcbiAgICAgICAgXCIvY2VjUHJveHlcIjoge1xyXG4gICAgICAgICAgLy8gdGFyZ2V0OiAnaHR0cDovLzEwLjExNC4xMC4xOTE6MjIyNi8nLFxyXG4gICAgICAgICAgLy8gdGFyZ2V0OiBcImh0dHA6Ly8xMC42NC43LjE0NTo4MC9cIixcclxuICAgICAgICAgIHRhcmdldDogYCR7Q1VSUkVOVF9TRVJWRVJ9OiR7UE9SVH0vYCxcclxuICAgICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcclxuICAgICAgICAgIHJld3JpdGU6IChwYXRoKSA9PiBwYXRoLnJlcGxhY2UoL15cXC9jZWNQcm94eS8sIFwiXCIpXHJcbiAgICAgICAgfSxcclxuICAgICAgICBcIi9wcm94eVwiOiB7XHJcbiAgICAgICAgICAvLyB0YXJnZXQ6IFwiaHR0cDovLzEwLjY0LjE3Ljc4OjkwMDFcIixcclxuICAgICAgICAgIHRhcmdldDogYCR7Q1VSUkVOVF9TRVJWRVJ9OiR7UE9SVH0vYCxcclxuICAgICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcclxuICAgICAgICAgIHJld3JpdGU6IChwYXRoKSA9PiBwYXRoLnJlcGxhY2UoL15cXC9wcm94eS8sIFwiXCIpXHJcbiAgICAgICAgfVxyXG4gICAgICAgIC8vICAgXCIvYWlcIjoge1xyXG4gICAgICAgIC8vICAgICAvLyB0YXJnZXQ6IFwiaHR0cDovLzEwLjY0LjEzLjY2Ojg4ODgvcWEvYWlcIixcclxuICAgICAgICAvLyAgICAgdGFyZ2V0OiBgJHtDVVJSRU5UX1NFUlZFUn0vcWEvYWlgLFxyXG4gICAgICAgIC8vICAgICBjaGFuZ2VPcmlnaW46IHRydWUsXHJcbiAgICAgICAgLy8gICAgIHJld3JpdGU6IChwYXRoKSA9PiBwYXRoLnJlcGxhY2UoL15cXC9haS8sIFwiXCIpXHJcbiAgICAgICAgLy8gICB9LFxyXG4gICAgICB9XHJcbiAgICB9LFxyXG4gICAgcHJldmlldzoge1xyXG4gICAgICBwb3J0OiA4MDkwXHJcbiAgICB9LFxyXG4gICAgY3NzOiB7XHJcbiAgICAgIHByZXByb2Nlc3Nvck9wdGlvbnM6IHtcclxuICAgICAgICBsZXNzOiB7XHJcbiAgICAgICAgICAvL1x1NTE3M1x1NEU4RWFudFx1NEUzQlx1OTg5OFx1NzY4NFx1NjI0MFx1NjcwOVx1NTNEOFx1OTFDRlx1OTBGRFx1NTcyOFx1OEZEOVx1OTFDQ1x1NEZFRVx1NjUzOVx1RkYwQ1x1NEY3Rlx1NzUyOHRhaWx3aW5kY3NzXHU3Njg0XHU5ODlDXHU4MjcyXHU1M0Q4XHU5MUNGXHU1NDhDXHU5ODc5XHU3NkVFXHU0RTJEXHU3Njg0XHU0RTNCXHU5ODk4XHU1NDBDXHU2QjY1XHJcbiAgICAgICAgICBtb2RpZnlWYXJzOiB7XHJcbiAgICAgICAgICAgIFwiQHByaW1hcnktY29sb3JcIjogY29sb3JzLnNreVs2MDBdXHJcbiAgICAgICAgICB9LFxyXG4gICAgICAgICAgamF2YXNjcmlwdEVuYWJsZWQ6IHRydWVcclxuICAgICAgICB9XHJcbiAgICAgIH1cclxuICAgIH0sXHJcbiAgICBvcHRpbWl6ZURlcHM6IHtcclxuICAgICAgZXhjbHVkZTogW1wiQG14bXdlYi9mdlwiLCBcIkBnaWVudGVjaC9tb2R1YWxcIiwgXCJAbXhtd2ViL3Zlb3ZpZXdlclwiXVxyXG4gICAgfVxyXG4gIH0gYXMgY29uc3Q7XHJcbn0pO1xyXG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQW1RLFNBQW9CLGNBQWMscUJBQXFCO0FBQzFULE9BQU8sV0FBVztBQUNsQixPQUFPLFVBQVU7QUFDakIsT0FBTyxVQUFV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
