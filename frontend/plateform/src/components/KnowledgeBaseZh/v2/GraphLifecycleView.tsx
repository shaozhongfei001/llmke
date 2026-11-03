/**
 * 图谱增强 V2 整页骨架演示（交接文件 §4 信息架构，5 Tab）：
 * Tab1 库级图谱 / Tab2 实体 / Tab3 社区 / Tab4 全局问答 / Tab5 构建与更新。
 *
 * 当前阶段：状态机与徽标骨架 + 可注入 mock 的适配层；
 * 画布/实体/社区的真实数据接口等待后端契约（见 mockAdapter.ts 与验收清单）。
 * 进入方式：/knowledgeBase/graphLifecycle/:id（演示路由，不影响现有图谱页）。
 */
import { useMemo, useState } from "react";
import { Button, Empty, Input, Tabs, Tag, message } from "antd";
import LifecycleBar from "./LifecycleBar";
import RouteBadge from "./RouteBadge";
import {
  MOCK_GLOBAL_ANSWERS,
  MOCK_LIFECYCLE_VARIANTS,
  mockAdapter
} from "./mockAdapter";
import type { GlobalAnswerResult, LifecycleState } from "./lifecycle";
import { STATE_COPY } from "./lifecycle";

/** 模拟"按所选状态组合返回"的适配器（演示全部状态用） */
const makeVariantAdapter = (
  variant: LifecycleState,
  answerIndex: number
) => ({
  name: "mock",
  async getLifecycle(): Promise<LifecycleState> {
    return variant;
  },
  async getGlobalAnswer(): Promise<GlobalAnswerResult> {
    return MOCK_GLOBAL_ANSWERS[answerIndex].sample;
  }
});

export const GraphLifecycleView = () => {
  const [variantKey, setVariantKey] = useState(MOCK_LIFECYCLE_VARIANTS[0].key);
  const [answerKey, setAnswerKey] = useState(0);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<GlobalAnswerResult | null>(null);
  const [asking, setAsking] = useState(false);
  const [backpressureLeft, setBackpressureLeft] = useState(0);

  const variant = useMemo(
    () =>
      MOCK_LIFECYCLE_VARIANTS.find(v => v.key === variantKey) ??
      MOCK_LIFECYCLE_VARIANTS[0],
    [variantKey]
  );
  const adapter = useMemo(
    () => makeVariantAdapter(variant.state, answerKey),
    [variant, answerKey]
  );

  const ask = async () => {
    if (!question.trim()) return;
    setAsking(true);
    setAnswer(null);
    // 模拟 BACKPRESSURE：排队已满时先提示约 N 秒后可重试
    if (answerKey === 2) {
      setBackpressureLeft(3);
      for (let n = 3; n > 0; n--) {
        await new Promise(r => setTimeout(r, 1000));
        setBackpressureLeft(n - 1);
      }
    }
    const res = await adapter.getGlobalAnswer();
    setAnswer(res);
    setAsking(false);
  };

  const globalBlocked =
    variant.state.global === "NOT_READY" || variant.state.global === "PARTIAL";

  return (
    <div style={{ padding: 16, background: "#f7f8fa", minHeight: "100vh" }}>
      {/* 顶栏：KB 名 | 代次/发布 | 五段状态条 | 可见域 | 刷新/重建（数据走适配层） */}
      <LifecycleBar
        kbInfo={{ id: "demo-kb", kbName: "授信审批知识库（demo）" }}
        adapter={adapter}
        onRefresh={() => message.info("已刷新（mock）")}
        onRebuild={mode => message.info(`已提交${mode === "full" ? "全量" : "增量"}重建（mock，等待后端契约）`)}
      />

      <div
        style={{
          background: "#fff",
          border: "1px solid #f0f0f0",
          borderRadius: 8,
          padding: 12
        }}
      >
        <div style={{ marginBottom: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, color: "#86909c", lineHeight: "24px" }}>
            状态组合（演示状态机全部取值）：
          </span>
          {MOCK_LIFECYCLE_VARIANTS.map(v => (
            <Button
              key={v.key}
              size="small"
              type={variantKey === v.key ? "primary" : "default"}
              onClick={() => setVariantKey(v.key)}
            >
              {v.label}
            </Button>
          ))}
        </div>

        <Tabs
          items={[
            {
              key: "graph",
              label: "Tab1 库级图谱",
              children: (
                <div>
                  <div style={{ marginBottom: 8, color: "#86909c", fontSize: 12 }}>
                    画布骨架：实体按类型着色 + 有向边箭头 + 社区光晕 + 孤点开关 + 来源高亮。
                    （真实节点/边数据等待后端契约，当前展示占位）
                  </div>
                  {variant.state.segments.graph.status === "READY_EMPTY" ? (
                    <Empty description={STATE_COPY.emptyGraph} />
                  ) : (
                    <div
                      style={{
                        height: 320,
                        border: "1px dashed #d9d9d9",
                        borderRadius: 8,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#86909c",
                        flexDirection: "column",
                        gap: 8
                      }}
                    >
                      <div>[画布占位：库级统一图]</div>
                      <div style={{ fontSize: 12 }}>
                        {variant.state.segments.graph.status === "RUNNING"
                          ? STATE_COPY.buildingShowOld(
                              variant.state.showingOldGeneration ??
                                variant.state.generation - 1
                            )
                          : "点实体 → 事实表[主体·谓词·对象·方向·单位·生效期·适用条件] + 多来源定位高亮（等待后端契约）"}
                      </div>
                    </div>
                  )}
                </div>
              )
            },
            {
              key: "entity",
              label: "Tab2 实体",
              children: (
                <Empty
                  description="实体搜索/列表、别名与同名异体标识、跨文档来源与路径（等待后端契约）"
                />
              )
            },
            {
              key: "community",
              label: "Tab3 社区",
              children: (
                <div>
                  <div style={{ marginBottom: 8, fontSize: 12, color: "#86909c" }}>
                    层级列表 / 成员 / 代表性事实 / findings 逐条带支持组 / 孤点保留
                    （等待后端契约）。
                  </div>
                  <Tag color={variant.state.global === "READY" ? "green" : "orange"}>
                    global {variant.state.global}
                  </Tag>
                </div>
              )
            },
            {
              key: "global",
              label: "Tab4 全局问答",
              children: (
                <div>
                  <div style={{ marginBottom: 8, display: "flex", gap: 8 }}>
                    <Input
                      placeholder="对库级知识提问（全局问答，消费社区报告）"
                      value={question}
                      onChange={e => setQuestion(e.target.value)}
                      onPressEnter={ask}
                      style={{ maxWidth: 480 }}
                      disabled={globalBlocked}
                    />
                    <Button
                      type="primary"
                      onClick={ask}
                      loading={asking}
                      disabled={globalBlocked}
                    >
                      提问
                    </Button>
                    <select
                      value={answerKey}
                      onChange={e => setAnswerKey(Number(e.target.value))}
                      style={{ borderRadius: 6, border: "1px solid #d9d9d9" }}
                    >
                      <option value={0}>路线：GRAPH</option>
                      <option value={1}>路线：社区报告</option>
                      <option value={2}>路线：DENSE_FALLBACK + 积压演示</option>
                    </select>
                  </div>
                  {globalBlocked && (
                    <div
                      style={{
                        padding: "6px 10px",
                        borderRadius: 6,
                        background: "#fff7e6",
                        color: "#ad6800",
                        fontSize: 12,
                        marginBottom: 8
                      }}
                    >
                      {variant.state.global === "NOT_READY"
                        ? STATE_COPY.globalNotReady
                        : STATE_COPY.globalPartial}
                    </div>
                  )}
                  {backpressureLeft > 0 && (
                    <div
                      style={{
                        padding: "6px 10px",
                        borderRadius: 6,
                        background: "#fff1f0",
                        color: "#cf1322",
                        fontSize: 12,
                        marginBottom: 8
                      }}
                    >
                      {STATE_COPY.backpressure(backpressureLeft)}
                    </div>
                  )}
                  {answer && (
                    <div
                      style={{
                        border: "1px solid #f0f0f0",
                        borderRadius: 8,
                        padding: 12,
                        marginTop: 8
                      }}
                    >
                      <div style={{ marginBottom: 6 }}>
                        <RouteBadge
                          route={answer.route}
                          reason={answer.routeReason}
                        />
                      </div>
                      {!answer.citationCheckPassed ? (
                        <div
                          style={{
                            color: "#86909c",
                            fontSize: 12,
                            marginBottom: 6
                          }}
                        >
                          ⚠ {STATE_COPY.citationCheckFailed}（答案已折叠）
                          <details style={{ display: "inline", marginLeft: 8 }}>
                            <summary style={{ cursor: "pointer", color: "#1677ff" }}>
                              展开查看
                            </summary>
                            <div style={{ marginTop: 4 }}>{answer.answer}</div>
                          </details>
                        </div>
                      ) : (
                        <div style={{ marginBottom: 8 }}>{answer.answer}</div>
                      )}
                      <div style={{ fontSize: 12, color: "#86909c" }}>
                        引用（类型化，含 locator，可点开原文并高亮——真实点击闭环见
                        AIChat 知识溯源链路）：
                      </div>
                      {answer.citations.map((c, i) => (
                        <div
                          key={i}
                          style={{
                            fontSize: 12,
                            padding: "4px 8px",
                            borderLeft: "2px solid #1677ff",
                            marginTop: 4,
                            background: "#f7f8fa"
                          }}
                        >
                          {c.title}（file_id={c.fileId}，locator={c.locator}）
                          {c.snippet ? `：${c.snippet}` : ""}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
            },
            {
              key: "build",
              label: "Tab5 构建与更新",
              children: (
                <div style={{ fontSize: 12, color: "#86909c" }}>
                  <div>全量/增量选择、进度与代次、撤权记录（fence）、失败重试、版本历史与回退（等待后端契约）。</div>
                  <div style={{ marginTop: 8 }}>
                    演示状态：{STATE_COPY.permissionDenied}（权限拒绝统一话术，不透露资源是否存在）
                  </div>
                </div>
              )
            }
          ]}
        />
      </div>
    </div>
  );
};

export default GraphLifecycleView;
