import { ConfigEnv, defineConfig, normalizePath } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import svgr from "vite-plugin-svgr";
import viteCompression from "vite-plugin-compression";
import resolve from "@rollup/plugin-node-resolve";
import colors from "tailwindcss/colors";
import { createRequire } from "node:module";
import { viteStaticCopy } from "vite-plugin-static-copy";
// import eslint from "vite-plugin-eslint";
const require = createRequire(import.meta.url);
import legacy from "@vitejs/plugin-legacy";

const pdfjsDistPath = path.dirname(require.resolve("pdfjs-dist/package.json"));
const cMapsDir = normalizePath(path.join(pdfjsDistPath, "cmaps"));
const SERVER_115 = `http://192.168.5.115`;
const SERVER_116 = `http://192.168.5.116`;
const SERVER_78 = `http://10.64.13.66`;
const SERVER_145 = `http://10.64.7.145`;
const SERVER_185 = `http://112.124.47.185`;
const SERVER_13 = `http://10.15.12.13`;
const SERVER_12 = `http://10.15.12.12`;
const SERVER_11 = `http://10.15.12.11`;
const SERVER_20 = `http://10.2.22.20`;

// R12：前端只连本机 Java 网关（platform/r12 环境契约 §1），不再指向内网 IP
// eslint-disable-next-line prefer-const
let CURRENT_SERVER = `http://127.0.0.1`;
// 网关端口（网关根路径即 /auth /index /qa /graph /sensitive）
const PORT = "8088";
// MinIO 端口（R12 与既有 9000 实例隔离）
const MINIO_PORT = "19000";

export default defineConfig(({ mode }) => {
  const isDebugBuild = process.env.DEBUG_BUILD === "1";
  return {
    build: {
      outDir: "dist",
      sourcemap: false,
      minify: isDebugBuild ? false : "esbuild",
      reportCompressedSize: isDebugBuild ? false : true,
      rollupOptions: {
        external: isDebugBuild
          ? [
              /assets\/worker-.*\.js$/,
              "@mxmweb/fviewer",
              "@mxmweb/xviewer",
              "@mxmweb/veoviewer"
            ]
          : [],
        output: {
          manualChunks(id) {
            if (!id) return;
            if (id.includes("node_modules")) {
              const parts = id.split("node_modules/").pop()?.split("/") || [];
              const pkg = parts[0]?.startsWith("@")
                ? `${parts[0]}/${parts[1]}`
                : parts[0];
              if (pkg) return `vendor-${pkg}`;
            }
            // if (id.includes("src/components/KnowledgeBaseZh/")) {
            //   const rel = id.split("src/components/KnowledgeBaseZh/").pop() || "kb";
            //   const top = rel.split("/")[0] || "kb";
            //   return `kb-${top}`;
            // }
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
      ...(isDebugBuild
        ? []
        : [
            viteCompression({ threshold: 512000 }),
            legacy({
              targets: [
                "chrome >= 60",
                "firefox >= 75",
                "safari >= 12",
                "not ie <= 11"
              ],
              modernPolyfills: true
            })
          ])
    ] as any[],
    resolve: {
      alias: [
        {
          find: "@root",
          replacement: path.resolve(__dirname, ".")
        },
        {
          find: "@",
          replacement: path.resolve(__dirname, "src")
        },
        {
          find: "@core",
          replacement: path.resolve(__dirname, "src/core")
        }
      ]
    },
    server: {
      host: "0.0.0.0",
      port: 15174,
      proxy: {
        "/minio": {
          // R12：MinIO 127.0.0.1:19000（bucket r12-rag）
          target: `${CURRENT_SERVER}:${MINIO_PORT}/`,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/minio/, "")
        },
        "/cecProxy": {
          // 后端根（与 /proxy 等价，保留历史前缀）
          target: `${CURRENT_SERVER}:${PORT}/`,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/cecProxy/, "")
        },
        "/proxy": {
          // 后端根：/index /qa /auth /sensitive 均在网关根下
          target: `${CURRENT_SERVER}:${PORT}/`,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/proxy/, "")
        },
        // 以下为网关根路径前缀，直连时无需 rewrite
        "/auth": {
          target: `${CURRENT_SERVER}:${PORT}`,
          changeOrigin: true
        },
        "/index": {
          target: `${CURRENT_SERVER}:${PORT}`,
          changeOrigin: true
        },
        "/qa": {
          target: `${CURRENT_SERVER}:${PORT}`,
          changeOrigin: true
        },
        "/graph": {
          target: `${CURRENT_SERVER}:${PORT}`,
          changeOrigin: true
        },
        "/sensitive": {
          target: `${CURRENT_SERVER}:${PORT}`,
          changeOrigin: true
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
  } as const;
});
