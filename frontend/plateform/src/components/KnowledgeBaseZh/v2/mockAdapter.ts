/**
 * 图谱增强 V2 数据适配层（可注入 mock）。
 *
 * 交接文件第 8 节：后端若未就绪（五段状态、route trace、社区报告接口没有），
 * 先做前端状态机与徽标骨架 + 可注入 mock 的适配层，并明确标注"等待后端契约"。
 *
 * - GraphLifecycleAdapter 是唯一数据契约：视图只依赖它；
 * - mockAdapter 演示全部状态（交接文件 §9.1：无后端时演示所有状态）；
 * - httpAdapter 预留真实接口落点，当前抛"等待后端契约"，调用方自动回落 mock。
 */
import type {
  GlobalAnswerResult,
  LifecycleState,
  RouteKind,
  SegmentStatus
} from "./lifecycle";

export interface GraphLifecycleAdapter {
  readonly name: string;
  /** 拉取库级生命周期（五段状态 + 代次/发布版本 + global 就绪） */
  getLifecycle(kbId: string): Promise<LifecycleState>;
  /** global 问答（Tab4）；返回 undefined 表示能力未接线 */
  getGlobalAnswer?(
    kbId: string,
    question: string
  ): Promise<GlobalAnswerResult | undefined>;
}

/** 演示用的状态组合（覆盖状态机全部取值） */
export const MOCK_LIFECYCLE_VARIANTS: {
  key: string;
  label: string;
  state: LifecycleState;
}[] = [
  {
    key: "all-ready",
    label: "全部就绪（正常态）",
    state: {
      generation: 7,
      publishedVersion: "v3.2.0",
      visibleDomain: "本库全部成员",
      global: "READY",
      segments: {
        parse: { status: "READY" },
        extract: { status: "READY" },
        graph: { status: "READY" },
        community: { status: "READY" },
        publish: { status: "READY" }
      }
    }
  },
  {
    key: "building",
    label: "构建中（展示旧版本）",
    state: {
      generation: 8,
      publishedVersion: "v3.2.0",
      visibleDomain: "本库全部成员",
      global: "PARTIAL",
      globalReason: "新版社区报告尚未生成",
      showingOldGeneration: 7,
      segments: {
        parse: { status: "READY" },
        extract: { status: "READY" },
        graph: { status: "RUNNING" },
        community: { status: "PENDING" },
        publish: { status: "PENDING" }
      }
    }
  },
  {
    key: "empty",
    label: "图空（READY_EMPTY）",
    state: {
      generation: 3,
      publishedVersion: "v1.1.0",
      visibleDomain: "本库全部成员",
      global: "NOT_READY",
      globalReason: "社区报告未就绪（NOT_READY）",
      segments: {
        parse: { status: "READY_EMPTY" },
        extract: { status: "READY_EMPTY" },
        graph: { status: "READY_EMPTY" },
        community: { status: "READY_EMPTY" },
        publish: { status: "INVALIDATED", reason: "事实集为空，发布被撤回" }
      }
    }
  },
  {
    key: "failed",
    label: "失败/失效混合态",
    state: {
      generation: 5,
      publishedVersion: "v2.0.0",
      visibleDomain: "本库全部成员",
      global: "NOT_READY",
      globalReason: "社区报告未就绪（NOT_READY）",
      segments: {
        parse: { status: "READY" },
        extract: { status: "FAILED", reason: "抽取任务超时（60s 无响应）" },
        graph: { status: "INVALIDATED", reason: "抽取产物已更新，需重构图" },
        community: { status: "INVALIDATED", reason: "图已更新，需重算社区" },
        publish: { status: "PENDING" }
      }
    }
  }
];

/** mock global 回答（三种路线各一例，P4 真实生效可见） */
export const MOCK_GLOBAL_ANSWERS: {
  route: RouteKind;
  reason?: string;
  sample: GlobalAnswerResult;
}[] = [
  {
    route: "GRAPH",
    sample: {
      route: "GRAPH",
      citationCheckPassed: true,
      answer:
        "星航贷单户最高授信额度为 8000.0 万元（依据：授信审批权限管理办法 第 3.1 条）。",
      citations: [
        {
          fileId: "333",
          title: "授信审批权限管理办法.docx",
          locator: "page=1;chunk=0",
          snippet: "单户最高授信额度为 8000.0 万元"
        }
      ]
    }
  },
  {
    route: "COMMUNITY_REPORT",
    sample: {
      route: "COMMUNITY_REPORT",
      citationCheckPassed: true,
      answer:
        "授信审批流程共 3 步：支行初审 → 分行复核 → 总行终审。",
      citations: [
        {
          fileId: "333",
          title: "授信审批权限管理办法.docx",
          locator: "page=2;chunk=1",
          snippet: "支行初审 → 分行复核 → 总行终审"
        }
      ]
    }
  },
  {
    route: "DENSE_FALLBACK",
    reason: "图服务 18094 不可用（连接拒绝）",
    sample: {
      route: "DENSE_FALLBACK",
      routeReason: "图服务 18094 不可用（连接拒绝）",
      citationCheckPassed: false,
      answer:
        "（以下为向量检索结果，未经图检索增强）授信额度相关条款见各管理办法。",
      citations: [
        {
          fileId: "333",
          title: "授信审批权限管理办法.docx",
          locator: "page=1;chunk=0",
          snippet: "授信额度"
        }
      ]
    }
  }
];

/** mock 适配器：确定性演示数据，覆盖状态机全部取值 */
export const mockAdapter: GraphLifecycleAdapter = {
  name: "mock",
  async getLifecycle(kbId: string): Promise<LifecycleState> {
    return MOCK_LIFECYCLE_VARIANTS[0].state;
  },
  async getGlobalAnswer(kbId: string, question: string) {
    return MOCK_GLOBAL_ANSWERS[0].sample;
  }
};

/**
 * 真实接口适配器（D4 后端契约已收口：/v2/status、/v2/entities、/v2/graph/global）。
 *
 * baseUrl 取值：VITE_V2_GRAPH_API（dev 直连 18094，需后端 CORS 放行）；
 * 生产经网关映射（待网关配置）后改为 /graphapi。失败时抛错 → 调用方回落 mock 并标注。
 */
export const httpAdapter: GraphLifecycleAdapter = {
  name: "http",
  async getLifecycle(kbId: string): Promise<LifecycleState> {
    const base =
      (import.meta as any).env?.VITE_V2_GRAPH_API || "http://127.0.0.1:18094";
    const token = (window as any).__gientechToken || "";
    const res = await fetch(`${base}/v2/status`, {
      headers: token ? { Authorization: token } : {}
    });
    if (!res.ok) throw new Error(`/v2/status HTTP ${res.status}`);
    const d = await res.json();
    const seg = (status: string, reason?: string): SegmentStatus =>
      (["READY", "READY_EMPTY", "PENDING", "RUNNING", "FAILED", "INVALIDATED"].includes(
        status
      )
        ? status
        : "READY") as SegmentStatus;
    const st = (status: string, reason?: string) => ({
      status: seg(status),
      ...(reason ? { reason } : {})
    });
    // 后端尚未给五段细粒度状态：全部映射自 pointer/fence（构图为 READY，
    // 社区按 citation_check_ok 判 READY/FAILED/PENDING，发布按 pointer 有无判 READY/PENDING）
    const pointer = d?.pointer || {};
    const comm = d?.community || {};
    const hasSnapshot = Boolean(d?.snapshot);
    const segments: Record<string, { status: SegmentStatus; reason?: string }> = {
      parse: st(hasSnapshot ? "READY" : "PENDING"),
      extract: st(hasSnapshot ? "READY" : "PENDING"),
      graph: st(hasSnapshot ? "READY" : "PENDING"),
      community: hasSnapshot
        ? comm.citation_check_ok === true
          ? st("READY")
          : comm.citation_check_ok === false
            ? st("FAILED", "引用校验未通过")
            : st("PENDING")
        : st("PENDING"),
      publish: st(pointer.fencing ? "READY" : "PENDING")
    };
    return {
      generation: Number(pointer.generation || 0),
      publishedVersion: pointer.built_at ? `release-${pointer.built_at}` : "",
      segments: segments as LifecycleState["segments"],
      global: hasSnapshot
        ? comm.citation_check_ok === true
          ? "READY"
          : comm.citation_check_ok === false
            ? "PARTIAL"
            : "NOT_READY"
        : "NOT_READY",
      globalReason: comm.citation_check_ok === false ? "引用校验未通过" : undefined,
      visibleDomain: undefined,
      showingOldGeneration: pointer.generation
        ? Number(pointer.generation) - 1
        : undefined
    };
  },
  async getGlobalAnswer(kbId: string, question: string) {
    const base =
      (import.meta as any).env?.VITE_V2_GRAPH_API || "http://127.0.0.1:18094";
    const token = (window as any).__gientechToken || "";
    const res = await fetch(`${base}/v2/graph/global`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: token } : {})
      },
      body: JSON.stringify({ query: question, max_communities: 3 })
    });
    if (!res.ok) return undefined;
    const d = await res.json();
    if (!d?.answer) return undefined; // NOT_READY / NO_RELEVANT_FACTS → 不冒充
    const route: RouteKind =
      d.reason === "NO_RELEVANT_FACTS" || d.citation_check?.ok === false
        ? "DENSE_FALLBACK"
        : "COMMUNITY_REPORT";
    return {
      answer: String(d.answer),
      route,
      routeReason: d.reason === "NO_RELEVANT_FACTS" ? String(d.reason) : undefined,
      citationCheckPassed: d.citation_check?.ok !== false,
      citations: (d.citations || []).map((c: any) => ({
        fileId: String((c.sources || [])[0] || ""),
        title:
          (d.source_meta || {})[String((c.sources || [])[0])]?.title ||
          "",
        locator:
          (d.source_meta || {})[String((c.sources || [])[0])]?.locator || "",
        snippet: String(c.text || "")
      }))
    };
  }
};
