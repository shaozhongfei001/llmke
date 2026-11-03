/**
 * T-A5（D7b）：问答 PDF 预览按引用定位画高亮。
 *
 * 方案：从 pdfjs 页面文本层按“引用片段”搜索首个命中，合并其文本框得到 PDF 坐标矩形，
 * 交给 GientechStreamReader 的 annotations 机制画高亮层。
 *
 * 契约说明（如实）：
 * - 检索侧只下发 locator（page/chunk），没有 PDF 坐标；本模块用文本搜索补齐坐标；
 * - 搜索目标是“引用片段文本”（fact/答案片段），命中首个即可——这是尽力而为的定位，
 *   不是逐字符对齐；扫面件/无文本层 PDF 无法高亮（返回 null，静默降级为页码跳转）。
 */
export interface PdfTextItem {
  str: string;
  transform: number[];
  width?: number;
  height?: number;
}

export interface HighlightAnnotation {
  id: string;
  pageNumber: number;
  x: number;
  y: number;
  width: number;
  height: number;
  content?: string;
  color?: string;
}

export const HIGHLIGHT_COLOR = "rgba(255, 213, 79, 0.45)";

/** 空白归一：PDF 文本层常把一行拆成多 item、词间带换行。 */
export function normalizeText(s: string): string {
  return String(s || "").replace(/\s+/g, "");
}

export interface PageTextItem {
  str: string;
  transform: number[];
  width?: number;
  height?: number;
}

/**
 * 在单页文本项里找 snippet 的首个连续命中，返回并集矩形（PDF 坐标系，左上原点）。
 * 找不到/片段为空返回 null。
 */
export function buildHighlightRect(
  items: PageTextItem[],
  snippet: string,
  pageNumber: number
): HighlightAnnotation | null {
  const target = normalizeText(snippet);
  if (!target || !items.length) return null;

  // 拼接整页文本，记录每个 item 在拼接串中的起止下标（归一化后）
  const spans: { item: PageTextItem; start: number; end: number }[] = [];
  let acc = "";
  for (const it of items) {
    const n = normalizeText(it.str);
    if (!n) continue;
    spans.push({ item: it, start: acc.length, end: acc.length + n.length });
    acc += n;
  }
  if (!acc) return null;

  const hit = acc.indexOf(target);
  if (hit < 0) return null;
  const hitEnd = hit + target.length;

  const matched = spans.filter(sp => sp.end > hit && sp.start < hitEnd);
  if (!matched.length) return null;

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const sp of matched) {
    const t = sp.item.transform || [];
    const e = Number(t[4]) || 0;
    const f = Number(t[5]) || 0;
    // 字号取变换矩阵的缩放（c 分量），PDF 文本常见纯平移+缩放
    const fontScale = Math.hypot(Number(t[2]) || 0, Number(t[3]) || 0) || 1;
    const w =
      (typeof sp.item.width === "number" && sp.item.width > 0
        ? sp.item.width
        : normalizeText(sp.item.str).length * fontScale * 0.5) || 1;
    const h =
      (typeof sp.item.height === "number" && sp.item.height > 0
        ? sp.item.height
        : fontScale) || 1;
    minX = Math.min(minX, e);
    minY = Math.min(minY, f);
    maxX = Math.max(maxX, e + w);
    maxY = Math.max(maxY, f + h);
  }

  return {
    id: `citation-${pageNumber}-${hit}`,
    pageNumber,
    x: minX,
    y: minY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
    content: snippet.slice(0, 120),
    color: HIGHLIGHT_COLOR
  };
}
