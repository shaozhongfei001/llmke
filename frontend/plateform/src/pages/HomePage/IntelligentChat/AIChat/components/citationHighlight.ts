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

/** 归一化串上的 token 区间（用于降级匹配）。 */
function tokenizeRanges(
  text: string
): { token: string; start: number; end: number }[] {
  const out: { token: string; start: number; end: number }[] = [];
  const re = /[\u4e00-\u9fff]+|[A-Za-z0-9]+/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    out.push({ token: m[0], start: m.index, end: m.index + m[0].length });
  }
  return out;
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

  let hit = acc.indexOf(target);
  let hitEnd = hit >= 0 ? hit + target.length : -1;

  if (hit < 0) {
    // 降级匹配：全文未命中时（如引用片段是"主语+谓语+宾语"而文档是表格单元格），
    // 改用"最长公共 token 连续串"（中文串/字母数字串切词），≥2 个 token 才画，
    // 单个 token 不画（太泛，容易画错行）。
    const accTokens = tokenizeRanges(acc);
    const tgtTokens: string[] =
      normalizeText(snippet).match(/[\u4e00-\u9fff]+|[A-Za-z0-9]+/g) || [];
    let bestStart = -1;
    let bestEnd = -1;
    for (let i = 0; i < accTokens.length; i++) {
      for (let j = 0; j < tgtTokens.length && i + j < accTokens.length; j++) {
        if (accTokens[i + j].token !== tgtTokens[j]) break;
        if (j + 1 >= 2 && j + 1 > bestEnd - bestStart) {
          bestStart = i;
          bestEnd = i + j + 1;
        }
      }
    }
    if (bestEnd - bestStart < 2) {
      // 单 token 降级：表格型文档（事实散在单元格）找不到连续 ≥2 token 时，
      // 退到"最长目标 token（≥4 字符）"的首个命中，给用户一个确定的视觉锚点；
      // 找不到足够长的 token 才放弃（返回 null 静默降级跳页）。
      let bestTok: { token: string; start: number; end: number } | null = null;
      for (const t of accTokens) {
        if (t.token.length < 4) continue;
        if (tgtTokens.includes(t.token) &&
            (!bestTok || t.token.length > bestTok.token.length)) {
          bestTok = t;
        }
      }
      if (!bestTok) return null;
      hit = bestTok.start;
      hitEnd = bestTok.end;
    } else {
      hit = accTokens[bestStart].start;
      hitEnd = accTokens[bestEnd - 1].end;
    }
  }

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
