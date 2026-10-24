// vite-env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  VITE_SOME_ENV_VAR: string;
  MODE: string; // 如果你有其他环境变量，也可以在这里添加
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
