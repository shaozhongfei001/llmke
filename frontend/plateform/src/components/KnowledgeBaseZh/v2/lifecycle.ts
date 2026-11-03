/**
 * 图谱增强 V2 生命周期状态机（前端骨架，交接文件第 5 节文案口径）。
 *
 * 五段：解析 → 抽取 → 构图 → 社区 → 发布；
 * 每段状态：READY / READY_EMPTY / PENDING / RUNNING / FAILED / INVALIDATED。
 * 该模块只有类型与文案，不包含任何网络请求（数据由 GraphLifecycleAdapter 注入）。
 * 状态机文案必须与交接文件 §5 保持一致，后端契约未就绪前由 mockAdapter 演示。
 */

export type SegmentKey = "parse" | "extract" | "graph" | "community" | "publish";

export type SegmentStatus =
  | "READY"
  | "READY_EMPTY"
  | "PENDING"
  | "RUNNING"
  | "FAILED"
  | "INVALIDATED";

export interface SegmentState {
  status: SegmentStatus;
  /** FAILED 时的原因（tooltip 展示）；INVALIDATED 时写被什么触发 */
  reason?: string;
}

export interface LifecycleState {
  /** 代次（图谱构建代次） */
  generation: number;
  /** 发布版本（知识库发布版本） */
  publishedVersion: string;
  segments: Record<SegmentKey, SegmentState>;
  /** global 问答就绪状态（社区报告） */
  global: "READY" | "NOT_READY" | "PARTIAL";
  globalReason?: string;
  /** 可见域（当前知识库可见范围） */
  visibleDomain?: string;
  /** 正在构建新版本时，旧版本代次 */
  showingOldGeneration?: number;
}

/** 引用条目（Tab4 答案的类型化引用） */
export interface CitationItem {
  fileId: string;
  title: string;
  locator: string; // 形如 page=1;chunk=0
  snippet?: string;
}

export type RouteKind = "GRAPH" | "COMMUNITY_REPORT" | "DENSE_FALLBACK";

export interface GlobalAnswerResult {
  answer: string;
  route: RouteKind;
  /** DENSE_FALLBACK 时必填：为什么图检索不可用 */
  routeReason?: string;
  /** 引用校验通过为 true；未通过时答案按"未通过引用校验"折叠 */
  citationCheckPassed: boolean;
  citations: CitationItem[];
}

/** 五段顺序与中文名（顶栏渲染顺序即此顺序） */
export const SEGMENT_ORDER: SegmentKey[] = [
  "parse",
  "extract",
  "graph",
  "community",
  "publish"
];

export const SEGMENT_LABELS: Record<SegmentKey, string> = {
  parse: "解析",
  extract: "抽取",
  graph: "构图",
  community: "社区",
  publish: "发布"
};

/** 状态徽标：颜色 + tooltip 文案口径（交接文件 §5） */
export const STATUS_META: Record<
  SegmentStatus,
  { color: string; text: string; tip: string }
> = {
  READY: {
    color: "#52c41a",
    text: "就绪",
    tip: "该阶段已完成且产物有效"
  },
  READY_EMPTY: {
    color: "#faad14",
    text: "就绪·空",
    tip: "本库暂无有效事实（READY_EMPTY），建议重解析/检查文档"
  },
  PENDING: {
    color: "#8c8c8c",
    text: "待处理",
    tip: "排队等待处理"
  },
  RUNNING: {
    color: "#1677ff",
    text: "进行中",
    tip: "处理中…"
  },
  FAILED: {
    color: "#ff4d4f",
    text: "失败",
    tip: "处理失败"
  },
  INVALIDATED: {
    color: "#fa541c",
    text: "已失效",
    tip: "上游产物已更新，本阶段需重跑"
  }
};

/** 路线徽标元数据（P4 真实生效可见） */
export const ROUTE_META: Record<
  RouteKind,
  { color: string; bg: string; label: string }
> = {
  GRAPH: { color: "#1677ff", bg: "#e6f4ff", label: "GRAPH 图检索" },
  COMMUNITY_REPORT: {
    color: "#531dab",
    bg: "#f9f0ff",
    label: "社区报告"
  },
  DENSE_FALLBACK: {
    color: "#ad6800",
    bg: "#fff7e6",
    label: "DENSE_FALLBACK 向量兜底"
  }
};

/** 状态机文案（交接文件 §5，逐条对齐） */
export const STATE_COPY = {
  buildingShowOld: (gen: number) =>
    `新版本构建中，当前展示旧版本（代次 ${gen}）`,
  emptyGraph:
    "本库暂无有效事实。请重新解析文档或检查文档内容后重试。",
  globalNotReady: "社区报告未就绪（NOT_READY），全局问答已禁用。",
  globalPartial: "社区报告仅部分就绪（PARTIAL），全局问答结果可能不完整。",
  denseFallback: (reason?: string) =>
    `图检索不可用，当前为向量检索结果${reason ? `：${reason}` : ""}`,
  citationCheckFailed: "未通过引用校验",
  permissionDenied: "您没有权限执行此操作。",
  backpressure: (sec: number) => `排队已满，约 ${sec} 秒后可重试`
};
