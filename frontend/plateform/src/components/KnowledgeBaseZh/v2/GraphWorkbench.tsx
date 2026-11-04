/**
 * 知识图谱工作台 —— 画布优先的知识探索视图（替换原 KnowledgeGraphView）。
 * 布局：工具栏（探索/社区/问答 + 搜索 + 筛选 + 跨文档 + 全屏 + 构建菜单）+ 画布 + 按需面板。
 * 数据主链：wholeGraphSearch（业务图）；社区 /v2/graph/global；问答 question_re。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button, Empty, Input, Spin, message, Modal, Tag, Dropdown, Tooltip } from "antd";
import {
  ApartmentOutlined,
  MessageOutlined,
  TeamOutlined,
  SearchOutlined,
  FilterOutlined,
  LinkOutlined,
  ExpandOutlined,
  ReloadOutlined,
  PlusOutlined,
  MinusOutlined,
  AimOutlined,
  CloseOutlined,
  FileTextOutlined,
  QuestionCircleOutlined
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import GraphCanvasV2, { GraphCanvasHandle } from "./GraphCanvasV2";
import {
  fetchWholeGraph,
  fetchCommunities,
  fetchFileById,
  typeColor,
  typeFill,
  type GraphData,
  type GraphEdge,
  type GraphNode,
  type GlobalCommunityResult
} from "./graphData";
import "./workbench.less";

type Mode = "graph" | "community" | "qa";

const GraphWorkbench = ({ kbInfo }: { kbInfo: any }) => {
  const navigate = useNavigate();
  const graphSpace = kbInfo?.primitiveName || kbInfo?.kbName || "";
  const canvasRef = useRef<GraphCanvasHandle>(null);

  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<Mode>("graph");
  const [selected, setSelected] = useState<string | null>(null);
  const [panel, setPanel] = useState<null | "entity" | "community" | "qa">(null);

  // 筛选
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [crossMode, setCrossMode] = useState(false);
  const [typeFilter, setTypeFilter] = useState<Set<string> | null>(null);
  const [docFilter, setDocFilter] = useState("all");
  const [communityFilter, setCommunityFilter] = useState("all");
  const [hopFilter, setHopFilter] = useState("all");

  // 搜索
  const [searchQ, setSearchQ] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  // 社区
  const [community, setCommunity] = useState<GlobalCommunityResult | null>(null);
  const [communityLoading, setCommunityLoading] = useState(false);

  // 全屏
  const [focused, setFocused] = useState(false);
  // 缩放百分比
  const [zoomScale, setZoomScale] = useState(1);

  const loadGraph = useCallback(async () => {
    if (!graphSpace) return;
    setLoading(true);
    setError("");
    try {
      const g = await fetchWholeGraph(graphSpace);
      setGraph(g);
    } catch (e: any) {
      setError(e?.message || "图谱加载失败");
    } finally {
      setLoading(false);
    }
  }, [graphSpace]);

  useEffect(() => {
    loadGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphSpace]);

  const loadCommunity = useCallback(async () => {
    setCommunityLoading(true);
    const c = await fetchCommunities(kbInfo?.id);
    setCommunity(c);
    setCommunityLoading(false);
  }, [kbInfo?.id]);

  useEffect(() => {
    if (mode === "community" && !community) loadCommunity();
  }, [mode, community, loadCommunity]);

  /* ---------- 派生：类型图例 / 文档列表 ---------- */
  const legend = useMemo(() => {
    const m = new Map<string, number>();
    for (const n of graph.nodes) m.set(n.nodeType, (m.get(n.nodeType) || 0) + 1);
    return Array.from(m.entries())
      .map(([label, count]) => ({ label, color: typeColor(label), count }))
      .sort((a, b) => b.count - a.count);
  }, [graph.nodes]);

  const docList = useMemo(() => {
    const m = new Map<string, string>();
    graph.nodes.forEach(n => n.fileIds.forEach((f, i) => m.set(f, n.titles[i] || f)));
    return Array.from(m.entries()).map(([id, name]) => ({ id, name }));
  }, [graph.nodes]);

  const nodeMap = useMemo(() => new Map(graph.nodes.map(n => [n.vid, n])), [graph.nodes]);

  /* ---------- 邻居 ---------- */
  const neighbors = useMemo(() => {
    const set = new Set<string>();
    if (!selected) return set;
    set.add(selected);
    for (const e of graph.edges) {
      if (e.source === selected) set.add(e.target);
      if (e.target === selected) set.add(e.source);
    }
    return set;
  }, [selected, graph.edges]);

  /* ---------- 可见数据（筛选） ---------- */
  const visible = useMemo(() => {
    let nodes = graph.nodes.filter(n => {
      if (typeFilter && !typeFilter.has(n.nodeType)) return false;
      if (docFilter !== "all" && !n.fileIds.includes(docFilter)) return false;
      return true;
    });
    if (hopFilter !== "all" && selected) {
      nodes = nodes.filter(n => neighbors.has(n.vid));
    }
    const ids = new Set(nodes.map(n => n.vid));
    const edges = graph.edges.filter(e => ids.has(e.source) && ids.has(e.target));
    return { nodes, edges };
  }, [graph, typeFilter, docFilter, hopFilter, selected, neighbors]);

  /* ---------- 搜索 ---------- */
  const searchResults = useMemo(() => {
    const q = searchQ.trim().toLowerCase();
    if (!q) return [];
    return graph.nodes.filter(n => n.name.toLowerCase().includes(q)).slice(0, 8);
  }, [searchQ, graph.nodes]);

  const selectNode = (id: string, locate = false) => {
    setSelected(id);
    setPanel("entity");
    setMode("graph");
    setSearchOpen(false);
    setSearchQ("");
    if (locate) setTimeout(() => canvasRef.current?.centerNode(id), 60);
  };

  const closePanel = () => {
    setPanel(null);
    setSelected(null);
  };

  const switchMode = (m: Mode) => {
    setMode(m);
    if (m === "graph") {
      setPanel(null);
      setSelected(null);
    } else if (m === "community") {
      setPanel("community");
      setSelected(null);
    } else {
      setPanel("qa");
    }
  };

  /* ---------- 选中节点的关联边 ---------- */
  const selectedNode = selected ? nodeMap.get(selected) : null;
  const selectedEdges = useMemo(() => {
    if (!selected) return [];
    return graph.edges.filter(e => e.source === selected || e.target === selected);
  }, [selected, graph.edges]);

  const [rebuildOpen, setRebuildOpen] = useState(false);
  const [rebuildConfirm, setRebuildConfirm] = useState("");
  const [diagOpen, setDiagOpen] = useState(false);
  const searchRef = useRef<any>(null);

  // U14 键盘入口：/ 聚焦搜索；Esc 退出专注 / 关闭面板 / 关闭筛选
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (document.activeElement as any)?.tagName;
      if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(tag)) {
        e.preventDefault();
        searchRef.current?.focus?.();
        return;
      }
      if (e.key === "Escape") {
        if (focused) setFocused(false);
        else if (diagOpen) setDiagOpen(false);
        else if (rebuildOpen) setRebuildOpen(false);
        else if (filtersOpen) setFiltersOpen(false);
        else if (panel) closePanel();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [focused, panel, filtersOpen, diagOpen, rebuildOpen]);

  return (
    <div className={`kgw ${focused ? "is-focused" : ""}`}>
      {/* 工具栏 */}
      <div className="kgw-toolbar">
        <div className="kgw-view-switch">
          <button className={mode === "graph" ? "active" : ""} onClick={() => switchMode("graph")}>
            <ApartmentOutlined /> <span className="kgw-btn-text">图谱探索</span>
          </button>
          <button className={mode === "community" ? "active" : ""} onClick={() => switchMode("community")}>
            <TeamOutlined /> <span className="kgw-btn-text">主题社区</span>
          </button>
          <button className={mode === "qa" ? "active" : ""} onClick={() => switchMode("qa")}>
            <MessageOutlined /> <span className="kgw-btn-text">图谱问答</span>
          </button>
        </div>

        <div className="kgw-search">
          <SearchOutlined className="kgw-search-icon" />
          <Input
            ref={searchRef}
            className="kgw-search-input"
            placeholder="查找实体、业务名称"
            value={searchQ}
            onChange={e => {
              setSearchQ(e.target.value);
              setSearchOpen(true);
            }}
            onFocus={() => setSearchOpen(true)}
            onBlur={() => setTimeout(() => setSearchOpen(false), 200)}
            onPressEnter={() => searchResults[0] && selectNode(searchResults[0].vid, true)}
          />
          {searchOpen && searchQ.trim() && (
            <div className="kgw-search-results">
              {searchResults.length ? (
                searchResults.map(n => (
                  <div key={n.vid} className="kgw-search-result" onMouseDown={() => selectNode(n.vid, true)}>
                    <span className="kgw-search-dot" style={{ background: typeColor(n.nodeType) }} />
                    <span className="kgw-search-name">{n.name}</span>
                    <span className="kgw-search-type">{n.nodeType}</span>
                  </div>
                ))
              ) : (
                <div className="kgw-search-empty">未找到该实体，请尝试业务名称</div>
              )}
            </div>
          )}
        </div>

        <div className="kgw-toolbar-spacer" />

        <Button
          className={`kgw-toolbtn ${filtersOpen ? "active" : ""}`}
          icon={<FilterOutlined />}
          onClick={() => setFiltersOpen(v => !v)}
        >
          <span className="kgw-btn-text">筛选</span>
        </Button>
        <Tooltip title="高亮由多份资料支撑的关联路径">
          <Button
            className={`kgw-toolbtn ${crossMode ? "active" : ""}`}
            icon={<LinkOutlined />}
            onClick={() => setCrossMode(v => !v)}
          >
            <span className="kgw-btn-text">跨文档</span>
          </Button>
        </Tooltip>
        <Tooltip title="画布全屏，Esc 退出">
          <Button className="kgw-toolbtn" icon={<ExpandOutlined />} onClick={() => setFocused(v => !v)} />
        </Tooltip>
        <Dropdown
          trigger={["click"]}
          menu={{
            items: [
              { key: "history", label: "构建记录" },
              { key: "incremental", label: "增量更新" },
              { type: "divider" as const },
              { key: "rebuild", label: "全量重建", danger: true },
              { key: "diag", label: "技术诊断" }
            ],
            onClick: ({ key }) => {
              if (key === "rebuild") setRebuildOpen(true);
              else if (key === "diag") setDiagOpen(true);
              else message.info("构建记录/增量更新接口待接入（/v2/build 契约）");
            }
          }}
        >
          <Button className="kgw-toolbtn" icon={<ReloadOutlined />}>
            <span className="kgw-btn-text">更新与构建</span>
          </Button>
        </Dropdown>
      </div>

      {/* 工作区 */}
      <div className="kgw-stage">
        {/* 筛选抽屉 */}
        {filtersOpen && (
          <div className="kgw-filter">
            <div className="kgw-pane-head">
              筛选实体与来源
              <Button type="text" size="small" icon={<CloseOutlined />} onClick={() => setFiltersOpen(false)} />
            </div>
            <div className="kgw-pane-body">
              <div className="kgw-filter-section">
                <div className="kgw-section-label">实体类型</div>
                {legend.map(l => (
                  <label key={l.label} className="kgw-filter-option">
                    <input
                      type="checkbox"
                      checked={!typeFilter || typeFilter.has(l.label)}
                      onChange={e => {
                        const next = new Set(typeFilter || legend.map(x => x.label));
                        if (e.target.checked) next.add(l.label);
                        else next.delete(l.label);
                        setTypeFilter(next);
                      }}
                    />
                    <span className="kgw-filter-dot" style={{ background: l.color }} />
                    {l.label}
                    <small>{l.count}</small>
                  </label>
                ))}
              </div>
              <div className="kgw-filter-section">
                <div className="kgw-section-label">来源文档</div>
                <select className="kgw-filter-select" value={docFilter} onChange={e => setDocFilter(e.target.value)}>
                  <option value="all">全部文档</option>
                  {docList.map(d => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </div>
              <div className="kgw-filter-section">
                <div className="kgw-section-label">围绕所选实体</div>
                <select className="kgw-filter-select" value={hopFilter} disabled={!selected} onChange={e => setHopFilter(e.target.value)}>
                  <option value="all">全库关联</option>
                  <option value="1">只看 1 跳关联</option>
                  <option value="2">只看 2 跳关联</option>
                </select>
                <div className="kgw-filter-note">筛选改变当前视图，不改变知识库内容。</div>
              </div>
              <div className="kgw-filter-footer">
                <Button onClick={() => { setTypeFilter(null); setDocFilter("all"); setHopFilter("all"); }}>重置筛选</Button>
                <Button type="primary" onClick={() => canvasRef.current?.fit()}>适配视图</Button>
              </div>
            </div>
          </div>
        )}

        {/* 画布 */}
        <div className="kgw-graph-col">
          {loading ? (
            <div className="kgw-loading"><Spin tip="加载图谱…" /></div>
          ) : error ? (
            <div className="kgw-empty">
              <Empty description={error}>
                <Button type="primary" onClick={loadGraph}>重试</Button>
              </Empty>
            </div>
          ) : (
            <>
              <GraphCanvasV2
                ref={canvasRef}
                nodes={visible.nodes}
                edges={visible.edges}
                selectedId={selected}
                onSelect={id => selectNode(id)}
                crossDocMode={crossMode}
                legend={legend}
                onScaleChange={setZoomScale}
              />
              {/* 计数 */}
              <div className="kgw-count">
                <span>显示实体 <b>{visible.nodes.length}</b><span className="kgw-count-total"> / {graph.nodes.length}</span></span>
                <span className="kgw-count-rule" />
                <span>关系 <b>{visible.edges.length}</b><span className="kgw-count-total"> / {graph.edges.length}</span></span>
                {crossMode && (
                  <>
                    <span className="kgw-count-rule" />
                    <span>跨文档路径已高亮</span>
                  </>
                )}
              </div>
              {/* 缩放工具 */}
              <div className="kgw-zoom">
                <Button size="small" icon={<MinusOutlined />} onClick={() => canvasRef.current?.zoomOut()} />
                <span className="kgw-zoom-value">{Math.round(zoomScale * 100)}%</span>
                <Button size="small" icon={<PlusOutlined />} onClick={() => canvasRef.current?.zoomIn()} />
                <Button size="small" icon={<AimOutlined />} onClick={() => canvasRef.current?.fit()} title="适配当前图谱" />
              </div>
            </>
          )}
        </div>

        {/* 详情面板 */}
        {panel === "entity" && selectedNode && (
          <EntityInspector
            node={selectedNode}
            edges={selectedEdges}
            nodeMap={nodeMap}
            onSelect={id => selectNode(id, true)}
            onClose={closePanel}
            onLocate={() => canvasRef.current?.centerNode(selectedNode.vid)}
            onAsk={() => switchMode("qa")}
            kbId={kbInfo?.id}
            navigate={navigate}
          />
        )}

        {/* 社区面板 */}
        {panel === "community" && (
          <CommunityPanel community={community} loading={communityLoading} onClose={() => switchMode("graph")} />
        )}

        {/* 问答面板 */}
        {panel === "qa" && (
          <QaPanel kbId={kbInfo?.id} onClose={() => switchMode("graph")} />
        )}
      </div>

      {/* 全量重建确认 */}
      <Modal
        open={rebuildOpen}
        title="全量重建"
        okText="确认重建"
        okButtonProps={{ disabled: rebuildConfirm !== (kbInfo?.kbName || ""), danger: true }}
        onOk={() => { message.info("重建任务接口待接入（/v2/build 契约）"); setRebuildOpen(false); setRebuildConfirm(""); }}
        onCancel={() => setRebuildOpen(false)}
      >
        <p>全量重建用于解析或抽取策略变化等情形，计算成本较高。</p>
        <p>目标知识库：<b>{kbInfo?.kbName}</b></p>
        <Input
          placeholder="请输入知识库名称确认"
          value={rebuildConfirm}
          onChange={e => setRebuildConfirm(e.target.value)}
          style={{ marginTop: 12 }}
        />
      </Modal>

      {/* 技术诊断 */}
      <Modal open={diagOpen} title="技术诊断" footer={null} onCancel={() => setDiagOpen(false)}>
        <p>图谱空间：{graphSpace}</p>
        <p>节点总数：{graph.nodes.length} · 关系总数：{graph.edges.length}</p>
        <p>数据源：/graph/search/wholeGraphSearch（Nebula 业务图）</p>
      </Modal>
    </div>
  );
};

/* ================= 实体详情 ================= */
const EntityInspector = ({
  node,
  edges,
  nodeMap,
  onSelect,
  onClose,
  onLocate,
  onAsk,
  kbId,
  navigate
}: {
  node: GraphNode;
  edges: GraphEdge[];
  nodeMap: Map<string, GraphNode>;
  onSelect: (id: string) => void;
  onClose: () => void;
  onLocate: () => void;
  onAsk: () => void;
  kbId: string;
  navigate: any;
}) => {
  const [tab, setTab] = useState<"relations" | "sources" | "props">("relations");
  const color = typeColor(node.nodeType);

  const related = edges.map(e => {
    const isOut = e.source === node.vid;
    const other = isOut ? e.target : e.source;
    return {
      predicate: e.predicate,
      direction: isOut ? "→" : "←",
      otherId: other,
      other: nodeMap.get(other)
    };
  });

  return (
    <div className="kgw-inspector">
      <div className="kgw-pane-head">
        实体详情
        <Button type="text" size="small" icon={<CloseOutlined />} onClick={onClose} />
      </div>
      <div className="kgw-inspector-body">
        <div className="kgw-detail-top">
          <span className="kgw-entity-tag" style={{ color, background: typeFill(color) }}>
            <span className="kgw-entity-dot" style={{ background: color }} />
            {node.nodeType}
          </span>
          <div className="kgw-detail-title">{node.name}</div>
          <div className="kgw-detail-meta">
            <span><b>{new Set(node.fileIds).size}</b> 份来源</span>
            <span><b>{edges.length}</b> 条关联</span>
          </div>
        </div>
        <div className="kgw-detail-tabs">
          <button className={tab === "relations" ? "active" : ""} onClick={() => setTab("relations")}>关联</button>
          <button className={tab === "sources" ? "active" : ""} onClick={() => setTab("sources")}>原文依据</button>
          <button className={tab === "props" ? "active" : ""} onClick={() => setTab("props")}>属性</button>
        </div>

        {tab === "relations" && (
          <div className="kgw-detail-section">
            <div className="kgw-section-label">关联实体 · {related.length}</div>
            {related.map((r, i) => (
              <div className="kgw-detail-row" key={i}>
                <span className="kgw-mini-dot" style={{ background: r.other ? typeColor(r.other.nodeType) : "#ccc" }} />
                <span className="kgw-relation">{r.predicate} {r.direction}</span>
                <button className="kgw-jump" onClick={() => onSelect(r.otherId)}>{r.other?.name || r.otherId}</button>
              </div>
            ))}
            {related.length === 0 && <div className="kgw-none">暂无关联实体</div>}
          </div>
        )}

        {tab === "sources" && (
          <div className="kgw-detail-section">
            <div className="kgw-section-label">原文依据 · {new Set(node.fileIds).size} 份资料</div>
            {node.fileIds.map((fid, i) => (
              <div
                className="kgw-source-card"
                key={fid}
                onClick={async () => {
                  const f = await fetchFileById(fid);
                  navigate(`/chats/knowledgeBase/KnowledgeAnalyBlock/${kbId}/${fid}`, {
                    state: {
                      docId: fid,
                      fileId: fid,
                      parsedFilePath: f?.convertedFilePath || f?.filePath || "",
                      filePath: f?.filePath || ""
                    }
                  });
                }}
              >
                <div className="kgw-source-head">
                  <FileTextOutlined />
                  <span>{node.titles[i] || fid}</span>
                </div>
                <div className="kgw-source-foot">来源文件 · file_id={fid}</div>
              </div>
            ))}
            {node.fileIds.length === 0 && <div className="kgw-none">无来源信息</div>}
          </div>
        )}

        {tab === "props" && (
          <div className="kgw-detail-section">
            <dl className="kgw-props">
              <dt>业务名称</dt><dd>{node.name}</dd>
              <dt>实体类型</dt><dd>{node.nodeType}</dd>
              <dt>技术标识</dt><dd>{node.vid}</dd>
              <dt>来源覆盖</dt><dd>{new Set(node.fileIds).size} 份文档</dd>
            </dl>
            <details className="kgw-tech">
              <summary>技术标识</summary>
              <code>vid={node.vid}</code>
            </details>
          </div>
        )}
      </div>
      <div className="kgw-detail-actions">
        <Button icon={<AimOutlined />} onClick={onLocate}>定位实体</Button>
        <Button type="primary" onClick={onAsk}>围绕它提问</Button>
      </div>
    </div>
  );
};

/* ================= 社区面板 ================= */
const CommunityPanel = ({
  community,
  loading,
  onClose
}: {
  community: GlobalCommunityResult | null;
  loading: boolean;
  onClose: () => void;
}) => {
  return (
    <div className="kgw-inspector">
      <div className="kgw-pane-head">
        主题社区
        <Button type="text" size="small" icon={<CloseOutlined />} onClick={onClose} />
      </div>
      <div className="kgw-inspector-body">
        {loading ? (
          <div className="kgw-loading"><Spin /></div>
        ) : !community ? (
          <div className="kgw-none" style={{ padding: 24 }}>
            社区报告接口不可用（/v2/graph/global）。这是后端真实缺口，未用演示数据冒充。
          </div>
        ) : (
          <div className="kgw-detail-section">
            <div className="kgw-section-label">真实算法社区 · 共 {community.communities} 个</div>
            {community.sections.slice(0, 20).map((s, i) => (
              <div className="kgw-community-card" key={s.community}>
                <div className="kgw-community-head">
                  <span className="kgw-community-name">社区 {s.community}</span>
                  <span className="kgw-community-meta">{s.size} 实体 · {s.factCount} 事实</span>
                </div>
                <div className="kgw-community-facts">
                  {s.facts.slice(0, 4).map((f, j) => (
                    <div className="kgw-fact" key={j}>
                      <span className="kgw-fact-text">{f.text}</span>
                      <span className="kgw-fact-src">
                        {f.sources.map(sid => community.sourceMeta[sid]?.title || sid).join("、")}
                      </span>
                    </div>
                  ))}
                  {s.facts.length > 4 && <div className="kgw-fact-more">… 共 {s.factCount} 条事实</div>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

/* ================= 问答面板 ================= */
const QaPanel = ({ kbId, onClose }: { kbId: string; onClose: () => void }) => {
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState("");
  const [refs, setRefs] = useState<any[]>([]);

  const ask = async () => {
    if (!question.trim()) return;
    setAsking(true);
    setAnswer("");
    setRefs([]);
    try {
      const ls = localStorage.getItem("gitech_ril:rag_ai");
      const token = ls ? JSON.parse(ls).userInfo?.token || "" : "";
      const res = await fetch(`/proxy/qa/ai/question_re`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: token, "X-Platform": "rag-qa" },
        body: JSON.stringify({
          sessionId: `kg-${Date.now()}`,
          queryId: `kgq-${Date.now()}`,
          content: question.trim(),
          type: "text",
          sysType: "KNO_INDEX",
          configId: 1
        })
      });
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      const refsArr: any[] = [];
      let done = false;
      while (!done) {
        const { value, done: d } = await reader!.read();
        done = d;
        if (value) {
          buf += decoder.decode(value, { stream: !done });
          const lines = buf.split("\n");
          buf = lines.pop() || "";
          for (const line of lines) {
            if (!line.startsWith("data:")) continue;
            const obj = JSON.parse(line.slice(5).trim());
            const content = obj?.reply?.content;
            if (content) setAnswer(a => a + content);
            if (obj?.reference) {
              try {
                const r = JSON.parse(obj.reference);
                if (Array.isArray(r)) refsArr.push(...r);
              } catch {
                /* ignore */
              }
            }
          }
        }
      }
      if (refsArr.length) setRefs(refsArr);
    } catch (e: any) {
      setAnswer("问答失败：" + (e?.message || "服务不可用"));
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="kgw-inspector">
      <div className="kgw-pane-head">
        图谱问答
        <Button type="text" size="small" icon={<CloseOutlined />} onClick={onClose} />
      </div>
      <div className="kgw-inspector-body">
        <div className="kgw-qa">
          <p className="kgw-qa-desc">沿真实检索入口提问，回答与引用来自当前知识库的授权代次。</p>
          <Input.TextArea
            className="kgw-qa-input"
            placeholder="例如：星航贷AAA档加点幅度是多少？"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            autoSize={{ minRows: 3, maxRows: 5 }}
          />
          <Button type="primary" block loading={asking} onClick={ask} icon={<MessageOutlined />}>
            提问
          </Button>
          {answer && (
            <div className="kgw-qa-answer">
              <div className="kgw-qa-answer-text">{answer}</div>
              {refs.length > 0 && (
                <div className="kgw-qa-refs">
                  {refs.slice(0, 6).map((r, i) => (
                    <span className="kgw-qa-ref" key={i}>
                      {typeof r === "string" ? r : r.title || r.fileName || r.name || "引用"}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default GraphWorkbench;
