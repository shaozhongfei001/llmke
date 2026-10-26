/**
 * R13 前端：GraphRAG 全局模式（社区摘要 map-reduce）
 *
 * 为什么在 fetch 层注入：
 * 聊天界面来自外部依赖 @gientech/modual/chat，请求体字段
 * （enableThinking / enableWebsearch / qaChannel）在依赖内部硬编码，
 * 没有透传自定义字段的入口，而前端只允许改 src/**、不允许改 node_modules。
 * 因此在聊天页挂载期间包一层 window.fetch：只对
 * `POST /qa/ai/question`（含 `question_re`）补一个 `globalMode: true`，
 * 其它请求、以及开关关闭时的请求，一律原样放行。
 *
 * 后端契约：AiRequest.globalMode（Boolean，默认 false）。
 */

const STORAGE_KEY = "r13_global_mode";
/** /proxy/qa/ai/question、/proxy/qa/ai/question_re */
const QUESTION_PATH = /\/qa\/ai\/question(?:_re)?(?:\?|$)/;

let globalModeCache: boolean | null = null;

/** 读取当前是否全局模式（localStorage 持久化，刷新保持） */
export const readGlobalMode = (): boolean => {
  if (globalModeCache !== null) return globalModeCache;
  try {
    globalModeCache = localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    // 隐私模式/禁用存储时降级为内存态
    globalModeCache = false;
  }
  return globalModeCache;
};

/** 写入全局模式开关 */
export const setGlobalMode = (enabled: boolean): void => {
  globalModeCache = enabled;
  try {
    localStorage.setItem(STORAGE_KEY, enabled ? "1" : "0");
  } catch {
    // 忽略存储异常，仅保留内存态
  }
};

const isQuestionRequest = (url: string, method: string): boolean =>
  method.toUpperCase() === "POST" && QUESTION_PATH.test(url);

const withGlobalMode = (body: RequestInit["body"]): RequestInit["body"] => {
  if (typeof body !== "string") return body;
  try {
    const payload = JSON.parse(body);
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      return body;
    }
    return JSON.stringify({ ...payload, globalMode: true });
  } catch {
    return body;
  }
};

let installCount = 0;
let nativeFetch: typeof window.fetch | null = null;

/**
 * 安装 fetch 补丁，返回卸载函数（组件卸载时调用；计数守卫支持多实例）。
 */
export const installGlobalModeFetchPatch = (): (() => void) => {
  if (installCount === 0) {
    nativeFetch = window.fetch;
    const base = nativeFetch;
    const patched: typeof window.fetch = (input, init) => {
      try {
        if (readGlobalMode()) {
          const url =
            typeof input === "string"
              ? input
              : input instanceof URL
              ? input.toString()
              : (input as Request).url;
          const method =
            init?.method ??
            (typeof Request !== "undefined" && input instanceof Request
              ? input.method
              : "GET");
          if (isQuestionRequest(url || "", method)) {
            const nextInit: RequestInit = { ...(init || {}) };
            nextInit.body = withGlobalMode(nextInit.body);
            return base.call(window, input, nextInit);
          }
        }
      } catch {
        // 任何异常都不阻断聊天，退回原始请求
      }
      return base.call(window, input, init);
    };
    window.fetch = patched;
  }
  installCount += 1;

  let released = false;
  return () => {
    if (released) return;
    released = true;
    installCount -= 1;
    if (installCount <= 0) {
      installCount = 0;
      if (nativeFetch) window.fetch = nativeFetch;
      nativeFetch = null;
    }
  };
};
