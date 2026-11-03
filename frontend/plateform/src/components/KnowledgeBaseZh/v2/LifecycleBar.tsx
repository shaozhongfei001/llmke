/**
 * 顶栏五段生命周期状态条（P2 生命周期可见 / 交接文件 §4 顶栏）：
 * KB 名 | 代次/发布版本 | 五段状态条(解析/抽取/构图/社区/发布) | 可见域 | 刷新/重建。
 * 数据来自 GraphLifecycleAdapter；后端契约未就绪时自动回落 mockAdapter（见 mockAdapter.ts）。
 */
import { useEffect, useState } from "react";
import { Button, Tooltip, message } from "antd";
import { ReloadOutlined, SyncOutlined } from "@ant-design/icons";
import type { LifecycleState, SegmentKey } from "./lifecycle";
import { SEGMENT_LABELS, SEGMENT_ORDER, STATUS_META, STATE_COPY } from "./lifecycle";
import type { GraphLifecycleAdapter } from "./mockAdapter";
import { httpAdapter, mockAdapter } from "./mockAdapter";

export interface LifecycleBarProps {
  kbInfo: any; // { id, kbName, primitiveName, ... }
  adapter?: GraphLifecycleAdapter;
  onRefresh?: () => void;
  onRebuild?: (mode: "full" | "incremental") => void;
}

export const LifecycleBar = ({
  kbInfo,
  adapter,
  onRefresh,
  onRebuild
}: LifecycleBarProps) => {
  const kbId = kbInfo?.id ?? kbInfo?.kbId ?? "";
  const kbName = kbInfo?.kbName || kbInfo?.primitiveName || "知识库";
  const [state, setState] = useState<LifecycleState | null>(null);
  const [source, setSource] = useState<string>("");
  const [refreshing, setRefreshing] = useState(false);

  const load = async (silent = false) => {
    setRefreshing(true);
    try {
      const used = adapter ?? httpAdapter;
      let next: LifecycleState;
      try {
        next = await used.getLifecycle(String(kbId));
      } catch {
        // 后端契约未就绪 → 回落 mock（演示全部状态），并明确标注来源
        next = await mockAdapter.getLifecycle(String(kbId));
        setSource("mock");
      }
      if (source === "") setSource(used.name);
      setState(next);
    } catch (e: any) {
      if (!silent) message.error(e?.message || "获取生命周期状态失败");
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kbId, adapter]);

  const building = state?.segments.graph?.status === "RUNNING";
  const emptyGraph = state?.segments.graph?.status === "READY_EMPTY";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        flexWrap: "wrap",
        padding: "8px 12px",
        marginBottom: 8,
        border: "1px solid #f0f0f0",
        borderRadius: 8,
        background: "#fff"
      }}
    >
      <span style={{ fontSize: 14, fontWeight: 600, color: "#1d2129" }}>
        {kbName}
      </span>
      {state && (
        <span style={{ fontSize: 12, color: "#86909c" }}>
          代次 {state.generation} · 发布 {state.publishedVersion}
        </span>
      )}
      <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
        {SEGMENT_ORDER.map(key => {
          const seg = state?.segments?.[key];
          const meta = seg ? STATUS_META[seg.status] : null;
          const tip = seg
            ? seg.status === "FAILED"
              ? `${meta?.tip}：${seg.reason || "未知原因"}`
              : seg.status === "INVALIDATED"
                ? `${meta?.tip}：${seg.reason || "上游已更新"}`
                : meta?.tip
            : "";
          return (
            <Tooltip key={key} title={tip}>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  padding: "0 8px",
                  height: 22,
                  borderRadius: 4,
                  fontSize: 12,
                  lineHeight: "22px",
                  color: meta?.color || "#8c8c8c",
                  background: `${meta?.color || "#8c8c8c"}14`,
                  border: `1px solid ${meta?.color || "#8c8c8c"}33`,
                  cursor: tip ? "help" : "default"
                }}
              >
                {seg?.status === "RUNNING" && <SyncOutlined spin style={{ fontSize: 11 }} />}
                {SEGMENT_LABELS[key]}
                {seg && `·${meta?.text}`}
              </span>
            </Tooltip>
          );
        })}
      </span>
      {state?.visibleDomain && (
        <span style={{ fontSize: 12, color: "#86909c" }}>
          可见域：{state.visibleDomain}
        </span>
      )}
      {source && (
        <span
          title="数据来源；mock 表示后端生命周期接口未接线（等待后端契约）"
          style={{
            fontSize: 11,
            color: source === "mock" ? "#faad14" : "#86909c",
            border: "1px dashed currentColor",
            borderRadius: 4,
            padding: "0 4px"
          }}
        >
          {source}
        </span>
      )}
      <span style={{ marginLeft: "auto", display: "inline-flex", gap: 8 }}>
        {onRebuild && (
          <>
            <Button size="small" onClick={() => onRebuild("incremental")}>
              增量更新
            </Button>
            <Button size="small" type="primary" onClick={() => onRebuild("full")}>
              全量重建
            </Button>
          </>
        )}
        <Button
          size="small"
          icon={<ReloadOutlined spin={refreshing} />}
          onClick={() => {
            load(false);
            onRefresh?.();
          }}
        >
          刷新
        </Button>
      </span>
      {building && (
        <div
          style={{
            width: "100%",
            padding: "6px 10px",
            borderRadius: 6,
            background: "#e6f4ff",
            color: "#1677ff",
            fontSize: 12
          }}
        >
          {STATE_COPY.buildingShowOld(state?.showingOldGeneration ?? state!.generation - 1)}
        </div>
      )}
      {emptyGraph && (
        <div
          style={{
            width: "100%",
            padding: "6px 10px",
            borderRadius: 6,
            background: "#fff7e6",
            color: "#ad6800",
            fontSize: 12
          }}
        >
          {STATE_COPY.emptyGraph}
        </div>
      )}
    </div>
  );
};

export default LifecycleBar;
