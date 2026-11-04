/**
 * 库级建设概览条（Knowledge Atlas 顶栏）：
 * 知识库名 | 代次/发布版本 | 五段生命周期流水线（解析→抽取→构图→社区→发布）| 可见域 | 刷新/重建。
 * 数据来自 GraphLifecycleAdapter；后端契约未就绪时自动回落 mockAdapter（见 mockAdapter.ts）。
 */
import { useEffect, useState } from "react";
import { Button, Tooltip, message } from "antd";
import { ReloadOutlined, SyncOutlined } from "@ant-design/icons";
import type { LifecycleState, SegmentKey } from "./lifecycle";
import { SEGMENT_LABELS, SEGMENT_ORDER, STATUS_META, STATE_COPY } from "./lifecycle";
import type { GraphLifecycleAdapter } from "./mockAdapter";
import { httpAdapter, mockAdapter } from "./mockAdapter";
import "./knowledge-graph.less";

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
    <div className="kgv-overview">
      <div className="kgv-overview__head">
        <span className="kgv-overview__title">{kbName}</span>
        {state && (
          <span className="kgv-overview__meta">
            <span>代次 {state.generation}</span>
            <span className="kgv-meta-sep" />
            <span>发布 {state.publishedVersion || "—"}</span>
            {state.visibleDomain && (
              <>
                <span className="kgv-meta-sep" />
                <span>可见域 {state.visibleDomain}</span>
              </>
            )}
          </span>
        )}
        {source && (
          <span
            className={`kgv-overview__source ${source === "mock" ? "is-mock" : ""}`}
            title="数据来源；mock 表示后端生命周期接口未接线（等待后端契约）"
          >
            {source}
          </span>
        )}
        <div className="kgv-pipeline__actions">
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
        </div>
      </div>

      {state && (
        <div className="kgv-pipeline">
          {SEGMENT_ORDER.map((key: SegmentKey, i: number) => {
            const seg = state.segments?.[key];
            const meta = seg ? STATUS_META[seg.status] : null;
            const tip = seg
              ? seg.status === "FAILED"
                ? `${meta?.tip}：${seg.reason || "未知原因"}`
                : seg.status === "INVALIDATED"
                  ? `${meta?.tip}：${seg.reason || "上游已更新"}`
                  : meta?.tip
              : "";
            const statusCls = seg
              ? `kgv-state-${seg.status.toLowerCase()}`
              : "kgv-state-pending";
            return (
              <div className="kgv-pipeline__seg" key={key}>
                {i > 0 && <div className="kgv-pipeline__link" />}
                <Tooltip title={tip}>
                  <span className={`kgv-pipeline__dot ${statusCls}`}>
                    {seg?.status === "RUNNING" ? (
                      <SyncOutlined spin style={{ fontSize: 12, color: "inherit" }} />
                    ) : (
                      <span className="kgv-pipeline__core" />
                    )}
                  </span>
                </Tooltip>
                <span className="kgv-pipeline__label">
                  {SEGMENT_LABELS[key]}
                  {seg && <span className="kgv-pipeline__state">{meta?.text}</span>}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {building && (
        <div className="kgv-banner is-info">
          {STATE_COPY.buildingShowOld(
            state?.showingOldGeneration ?? state!.generation - 1
          )}
        </div>
      )}
      {emptyGraph && (
        <div className="kgv-banner is-warn">{STATE_COPY.emptyGraph}</div>
      )}
    </div>
  );
};

export default LifecycleBar;
