/**
 * 知识图谱工作台 —— 数据适配层。
 * 主链使用 wholeGraphSearch（业务图：真实名称/类型/有向谓词/来源文件）。
 * v2WholeGraph 为 GraphRAG 原始图（name=哈希、edgeType=related），不作为主展示。
 */
import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";

/* ---------------- 类型与色系 ---------------- */

export interface GraphNode {
  vid: string;
  name: string;
  nodeType: string;
  fileIds: string[];
  titles: string[];
}

export interface GraphEdge {
  id: string;
  predicate: string;
  source: string;
  target: string;
  srcName: string;
  dstName: string;
  fileId: string;
  title: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

/** 类型色系：真实 nodeType → 颜色（相近语义同色，配合类型文字区分） */
const TYPE_COLOR: Record<string, string> = {
  实体: "#5275e1",
  数值: "#489d96",
  value: "#489d96",
  entity: "#5275e1",
  产品: "#5275e1",
  客户: "#9471c4",
  担保: "#d97b5e",
  担保主体: "#d97b5e",
  评级: "#c89748",
  "利率/点数": "#d68a2e",
  金额: "#489d96",
  口径: "#5ba876",
  指标: "#5ba876",
  期限: "#5b8fc9",
  日期: "#5b8fc9",
  时间: "#5b8fc9",
  流程节点: "#7c6bd6",
  业务动作: "#7c6bd6",
  机构: "#b06ab3",
  角色: "#b06ab3",
  地点: "#b06ab3",
  单证: "#8898b2",
  编号: "#8898b2",
  频次: "#8898b2",
  unclassified: "#9aa4b5"
};

const FALLBACK_COLORS = [
  "#5275e1",
  "#9471c4",
  "#c89748",
  "#489d96",
  "#d68a2e",
  "#7c6bd6",
  "#d97b5e",
  "#5b8fc9",
  "#5ba876",
  "#8898b2"
];

/** 返回节点类型的颜色；未知类型按稳定顺序回退到色板 */
export function typeColor(nodeType: string): string {
  if (TYPE_COLOR[nodeType]) return TYPE_COLOR[nodeType];
  // 稳定哈希 → 色板，避免每次刷新变色
  let h = 0;
  for (let i = 0; i < nodeType.length; i++) h = (h * 31 + nodeType.charCodeAt(i)) >>> 0;
  return FALLBACK_COLORS[h % FALLBACK_COLORS.length];
}

/** 颜色 → 浅底填充色（用于节点圆点底） */
export function typeFill(color: string): string {
  return color + "1f";
}

/* ---------------- 接口适配 ---------------- */

const graphPrefix = `${getUrlPrefix()}/graph`;

/** 拉取全库业务图谱：按库路由（kb=spaceName），V2 优先，旧 Nebula 仅在 V2 网络不可达时兜底 */
export async function fetchWholeGraph(spaceName: string): Promise<GraphData> {
  // 主链：V2 图服务 /v2/graph/view?kb=<spaceName>（dev 走 /graphapi 代理到 18094）。
  // 用原生 fetch 而非 axios$：v2 接口返回 {status,...} 无 success 字段，
  // axios$ 响应拦截器会把无 success 的响应判成 false。
  // 关键：必须带 kb 参数 —— 否则 18094 返回单快照，所有库都会看到同一套图（串库假数据）。
  let v2Responded = false;
  try {
    const res = await fetch(`/graphapi/v2/graph/view?kb=${encodeURIComponent(spaceName)}`);
    v2Responded = true;
    if (res.ok) {
      const d = await res.json();
      if (d?.status === "ok" && Array.isArray(d.nodes)) {
        return adaptGraphV2(d.nodes, d.edges || []);
      }
      // NOT_BUILT / GRAPH_UNAVAILABLE：该库未建图，如实报错，不落到旧 Nebula 冒充
      throw new Error(d?.reason || "该知识库尚未构建图谱");
    }
  } catch (e: any) {
    if (v2Responded) throw e; // V2 明确响应了但无数据，以 V2 为准
    /* 网络错误：fallthrough 到旧 Nebula */
  }
  // 兜底：旧 Nebula 业务图（仅 V2 网络不可达时；同样按 spaceName 区分）
  const res: any = await axios$.post(
    `${graphPrefix}/search/wholeGraphSearch`,
    { spaceName },
    { headers: { "X-Platform": "rag-qa" } }
  );
  const d = res?.data || res || {};
  return adaptGraph(d.nodeList || [], d.edgeList || []);
}

/** V2 /v2/graph/view 结构 → 前端图模型（节点来源从断言 sources 聚合） */
function adaptGraphV2(rawNodes: any[], rawEdges: any[]): GraphData {
  const nodes: GraphNode[] = (rawNodes || []).map((n: any) => ({
    vid: String(n?.id ?? n?.name ?? ""),
    name: String(n?.name || n?.id || ""),
    nodeType: String(n?.type || n?.kind || "实体"),
    fileIds: [],
    titles: []
  }));
  const idx = new Map(nodes.map(n => [n.vid, n]));
  const edges: GraphEdge[] = (rawEdges || []).map((e: any) => {
    const srcs = Array.isArray(e?.sources) ? e.sources : [];
    const fileId = String(srcs[0]?.file_id || "");
    const title = String(srcs[0]?.title || "");
    const src = String(e?.source || "");
    const dst = String(e?.target || "");
    // 把边来源聚合到两端节点的来源列表（供"原文依据"用）
    for (const vid of [src, dst]) {
      const nd = idx.get(vid);
      if (nd && fileId && !nd.fileIds.includes(fileId)) {
        nd.fileIds.push(fileId);
        nd.titles.push(title);
      }
    }
    return {
      id: String(e?.id || ""),
      predicate: String(e?.predicate || "关联"),
      source: src,
      target: dst,
      srcName: idx.get(src)?.name || src,
      dstName: idx.get(dst)?.name || dst,
      fileId,
      title
    };
  });
  return { nodes, edges };
}

/** 拉取文件子图（subGraph） */
export async function fetchSubGraph(
  spaceName: string,
  fileId: string
): Promise<GraphData> {
  const res: any = await axios$.get(
    `${graphPrefix}/search/subGraph`,
    { params: { spaceName, fileId }, headers: { "X-Platform": "rag-qa" } }
  );
  const d = res?.data || res || {};
  return adaptGraph(d.nodeList || [], d.edgeList || []);
}

/** 后端返回结构 → 前端图模型 */
function adaptGraph(rawNodes: any[], rawEdges: any[]): GraphData {
  const nodes: GraphNode[] = (rawNodes || []).map((n: any) => {
    const fileId = String(n?.properties?.file_id || "");
    const title = String(n?.properties?.title || "");
    return {
      vid: String(n?.vid ?? n?.name ?? ""),
      name: String(n?.name || n?.vid || ""),
      nodeType: String(n?.nodeType || "unclassified"),
      fileIds: fileId ? fileId.split(",").filter(Boolean) : [],
      titles: title ? title.split(",").filter(Boolean) : []
    };
  });
  const edges: GraphEdge[] = (rawEdges || []).map((e: any) => ({
    id: String(e?.id || ""),
    predicate: String(e?.edgeType || e?.name || "关联"),
    source: String(e?.src?.vid || ""),
    target: String(e?.dst?.vid || ""),
    srcName: String(e?.src?.name || e?.src?.vid || ""),
    dstName: String(e?.dst?.name || e?.dst?.vid || ""),
    fileId: String(e?.src?.properties?.file_id || e?.properties?.file_id || ""),
    title: String(e?.src?.properties?.title || e?.properties?.title || "")
  }));
  return { nodes, edges };
}

/* ---------------- 社区 / 问答 ---------------- */

export interface CommunitySection {
  community: string;
  entities: string[];
  factCount: number;
  facts: { text: string; sources: string[] }[];
  isolated: boolean;
  size: number;
  sources: string[];
}

export interface GlobalCommunityResult {
  status: string;
  communities: number;
  sections: CommunitySection[];
  sourceMeta: Record<string, { file_id: string; locator: string; title: string }>;
  answer: string;
  citations: { community: string; text: string; sources: string[] }[];
  citationCheck: any;
}

/** 拉取社区（/v2/graph/global，dev 走 /graphapi 代理到 18094，生产走 VITE_V2_GRAPH_API）。
 *  kb 为知识库 spaceName（primitiveName，如 kb_9），按库路由快照。 */
export async function fetchCommunities(kb: string): Promise<GlobalCommunityResult | null> {
  try {
    const base =
      (import.meta as any).env?.VITE_V2_GRAPH_API || "/graphapi";
    const token = (window as any).__gientechToken || "";
    const res = await fetch(`${base}/v2/graph/global`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: token } : {})
      },
      body: JSON.stringify({ query: "", max_communities: 20, kb })
    });
    if (!res.ok) return null;
    const d = await res.json();
    if (!d?.sections) return null;
    if (d?.status === "NOT_BUILT") return null; // 该库未建图：如实空态，不显示"共 0 个"
    return {
      status: d.status,
      communities: d.communities,
      sections: (d.sections || []).map((s: any) => ({
        community: s.community,
        entities: s.entities || [],
        factCount: s.fact_count ?? s.factCount ?? 0,
        facts: s.facts || [],
        isolated: s.isolated,
        size: s.size,
        sources: s.sources || []
      })),
      sourceMeta: d.source_meta || {},
      answer: d.answer || "",
      citations: d.citations || [],
      citationCheck: d.citation_check
    };
  } catch {
    return null;
  }
}

/** 文件详情（原文预览用） */
export async function fetchFileById(fileId: string): Promise<any | null> {
  try {
    const res: any = await axios$.get(
      `${getUrlPrefix()}/index/knowledgeBase/file/getById`,
      { params: { id: fileId }, headers: { "X-Platform": "rag-qa" } }
    );
    return res?.data || null;
  } catch {
    return null;
  }
}
