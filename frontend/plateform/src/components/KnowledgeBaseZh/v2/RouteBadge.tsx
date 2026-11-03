/**
 * 路线徽标（P4 真实生效可见 / 交接文件 §5）：
 * GRAPH（蓝）/ 社区报告（紫）/ DENSE_FALLBACK+原因（黄）。
 * 全站统一组件：聊天页与图谱增强 Tab4 共用同一套口径。
 */
import type { RouteKind } from "./lifecycle";
import { ROUTE_META, STATE_COPY } from "./lifecycle";

export interface RouteBadgeProps {
  route: RouteKind;
  /** DENSE_FALLBACK 时展示的回落原因 */
  reason?: string;
  /** 禁用图对照（P4：提供"禁用图对照"入口时置 true，展示对照组样式） */
  graphDisabled?: boolean;
}

export const RouteBadge = ({ route, reason, graphDisabled }: RouteBadgeProps) => {
  const meta = ROUTE_META[route];
  const title =
    route === "DENSE_FALLBACK"
      ? STATE_COPY.denseFallback(reason)
      : route === "GRAPH" && graphDisabled
        ? "图检索已禁用（对照模式），当前为向量检索结果"
        : meta.label;
  return (
    <span
      title={title}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "1px 8px",
        borderRadius: 999,
        fontSize: 12,
        lineHeight: "18px",
        color: meta.color,
        background: meta.bg,
        border: `1px solid ${meta.color}33`,
        whiteSpace: "nowrap"
      }}
    >
      {route === "DENSE_FALLBACK" && "⚠ "}
      {graphDisabled && route === "GRAPH" ? "对照·" : ""}
      {meta.label}
      {route === "DENSE_FALLBACK" && reason ? `（${reason}）` : ""}
    </span>
  );
};

export default RouteBadge;
