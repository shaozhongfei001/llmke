/**
 * 图谱实体类型色 —— SPECTRA 视觉层映射
 *
 * 为什么单独一层而不是改 graphData.ts：
 * graphData.ts 属于共享区的数据/类型逻辑（接口适配、稳定哈希、typeColor 规则），
 * 按《前端设计边界》不得改造。因此保持 typeColor 作为**未知类型的兜底与稳定排序依据**，
 * 只在本视觉层把已知类型换成 SPECTRA 调色板；未命中类型的兜底哈希算法与 graphData 完全一致
 * （同一 hash 函数 + 同一索引取模），保证刷新后颜色稳定、不出现“每次变色”。
 *
 * 用色口径：冷青 = 知识链路/实体，暖金 = 产品与当前焦点，薄荷 = 客户与成功，
 * 其余辅助色保持低饱和，避免画布被高饱和色块占据。
 */

export const SPECTRA_TYPE_COLOR: Record<string, string> = {
  // 业务实体
  产品: "#D8BD89",
  客户: "#A9D8BA",
  评级: "#C8B3E0",
  担保: "#C9A08C",
  担保主体: "#C9A08C",
  机构: "#B29CC8",
  角色: "#B29CC8",
  地点: "#B29CC8",
  // 数值与口径
  数值: "#8FC8C8",
  value: "#8FC8C8",
  金额: "#8FC8C8",
  "利率/点数": "#CBB07A",
  口径: "#9CC9AE",
  指标: "#9CC9AE",
  期限: "#8FB6D8",
  日期: "#8FB6D8",
  时间: "#8FB6D8",
  // 流程与动作
  流程节点: "#9FAAD8",
  业务动作: "#9FAAD8",
  // 通用
  entity: "#94CED2",
  实体: "#94CED2",
  单证: "#9DB0B4",
  编号: "#9DB0B4",
  频次: "#9DB0B4",
  unclassified: "#85959A"
};

/** 与 graphData.TYPE_COLOR / FALLBACK_COLORS 同构的兜底色板（SPECTRA 低饱和） */
const SPECTRA_FALLBACK = [
  "#94CED2",
  "#A9D8BA",
  "#D8BD89",
  "#C8B3E0",
  "#8FB6D8",
  "#9CC9AE",
  "#C9A08C",
  "#8FC8C8",
  "#CBB07A",
  "#9DB0B4"
];

/**
 * 已知类型 → SPECTRA 色；未命中 → 与 graphData.typeColor 相同的稳定哈希取模。
 * @param nodeType 实体类型
 * @param fallbackColor graphData.typeColor(nodeType) 的结果，仅用于保证「同一类型恒同一色」
 */
export function spectraTypeColor(nodeType: string, fallbackColor?: string): string {
  const key = nodeType ?? "";
  if (SPECTRA_TYPE_COLOR[key]) return SPECTRA_TYPE_COLOR[key];
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  const picked = SPECTRA_FALLBACK[h % SPECTRA_FALLBACK.length];
  return picked || fallbackColor || SPECTRA_FALLBACK[0];
}

/** 颜色 → 低透明底（用于节点圆填充），与 graphData.typeFill 语义一致 */
export function spectraTypeFill(color: string): string {
  return `${color}22`;
}
