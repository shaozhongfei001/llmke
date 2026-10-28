import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Empty, Spin, Tag } from "antd";
import { useAppPassport } from "@root/src/core/helps";

/**
 * R14-LIVE-06：自研图谱渲染，替换 vendored `@mxmweb/somelib` 的 <AiGraph />。
 *
 * 为什么换掉（有据可查，不是"想重写"）：
 *   - 该组件在本地容器里停在 `app_init -> app_wait`，画布 1524×676 正常、
 *     数据接口 200（87 节点 / 61 关系），但一个节点都不画，且不报错（静默失败）；
 *   - 它读的初始化数据是 `initData`（上层传 null），走 local 分支后用空对象初始化；
 *     服务端模式分支又依赖一套我们拿不到的 config 契约（控制台 `当前版本: undefined`、
 *     `Cannot read properties of undefined (reading 'config')`）；
 *   - 源码已 minify，反推契约成本高于自己渲染，且每次升级都可能再静默坏一次。
 *
 * 数据来源（实测可用，均返回实例，不是 schema）：
 *   POST /proxy/graph/search/wholeGraphSearch {spaceName}  -> {nodeList, edgeList}
 *   GET  /proxy/graph/search/subGraph?spaceName=&fileId=   -> {nodeList, edgeList}
 *   node: {vid, name, nodeType, properties:{file_id,title}}
 *   edge: {id, edgeType, src:{vid}, dst:{vid}}
 *
 * 布局用一次性 O(n²) 斥力 + 边弹簧的确定性迭代（87 节点约 2e6 次运算，主线程几十毫秒），
 * 不引入新依赖，也不做持续动画——验收时"看得到、点得动、数得清"比"炫"重要。
 */

type GNode = { vid: string; name?: string; nodeType?: string; properties?: Record<string, any> };
type GEdge = { id?: string; edgeType?: string; src?: { vid?: string }; dst?: { vid?: string } };

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#EC4899", "#84CC16"];

export default function GraphCanvas({
  spaceName,
  fileId,
  type,
  onBack
}: {
  spaceName: string;
  fileId?: string;
  type: "allGraph" | "subGraph";
  onBack: () => void;
}) {
  const { getToken } = useAppPassport();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [nodes, setNodes] = useState<GNode[]>([]);
  const [edges, setEdges] = useState<GEdge[]>([]);
  const [active, setActive] = useState<GNode | null>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    const token: any = getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Authorization: token || "",
      "X-Platform": "rag-qa"
    };
    setLoading(true);
    setError("");
    const req =
      type === "subGraph"
        ? fetch(
            `/proxy/graph/search/subGraph?spaceName=${encodeURIComponent(spaceName)}${
              fileId ? `&fileId=${encodeURIComponent(fileId)}` : ""
            }`,
            { headers }
          )
        : fetch(`/proxy/graph/search/wholeGraphSearch`, {
            method: "POST",
            headers,
            body: JSON.stringify({ spaceName })
          });
    req
      .then(r => {
        // 网关 404 会回落成 index.html，JSON.parse 会抛 "Unexpected token '<'"，
        // 这里显式区分"没拿到 JSON"和"没图数据"，避免又变成一条静默失败。
        const ct = r.headers.get("content-type") || "";
        if (!ct.includes("json")) throw new Error(`图数据接口返回的不是 JSON（HTTP ${r.status}）`);
        return r.json();
      })
      .then(d => {
        if (cancelled) return;
        if (d && d.success === false) throw new Error(d.errorMsg || "图数据接口返回失败");
        const data = (d && d.data) || {};
        setNodes(data.nodeList || []);
        setEdges(data.edgeList || []);
      })
      .catch(e => {
        if (!cancelled) setError(e?.message || "图数据加载失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [spaceName, fileId, type]);

  const colorOf = useMemo(() => {
    const types = Array.from(new Set(nodes.map(n => n.nodeType || "unclassified")));
    const map: Record<string, string> = {};
    types.forEach((t, i) => (map[t] = COLORS[i % COLORS.length]));
    return map;
  }, [nodes]);

  const layout = useMemo(() => {
    const n = nodes.length;
    if (!n) return { pos: [] as { x: number; y: number }[], w: 900, h: 620 };
    const w = 900;
    const h = 620;
    const cx = w / 2;
    const cy = h / 2;
    const pos = nodes.map((_, i) => {
      const a = (i / n) * Math.PI * 2;
      const r = Math.min(w, h) * 0.28 + (i % 7) * 6;
      return { x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r };
    });
    const index = new Map(nodes.map((nd, i) => [nd.vid, i]));
    const links = edges
      .map(e => ({ s: index.get(e.src?.vid || ""), t: index.get(e.dst?.vid || "") }))
      .filter(l => l.s !== undefined && l.t !== undefined) as { s: number; t: number }[];

    // 确定性力导：斥力 + 弹簧 + 向心，迭代次数固定，结果与时间无关（可复现）
    const ITER = 220;
    const K = 90;
    for (let it = 0; it < ITER; it++) {
      const disp = pos.map(() => ({ x: 0, y: 0 }));
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          let dx = pos[i].x - pos[j].x;
          let dy = pos[i].y - pos[j].y;
          let d2 = dx * dx + dy * dy;
          if (d2 < 1) {
            dx = (Math.random() - 0.5) * 0.4;
            dy = (Math.random() - 0.5) * 0.4;
            d2 = 1;
          }
          const f = (K * K) / d2;
          const d = Math.sqrt(d2);
          disp[i].x += (dx / d) * f;
          disp[i].y += (dy / d) * f;
          disp[j].x -= (dx / d) * f;
          disp[j].y -= (dy / d) * f;
        }
      }
      for (const l of links) {
        const dx = pos[l.s].x - pos[l.t].x;
        const dy = pos[l.s].y - pos[l.t].y;
        const d = Math.max(Math.sqrt(dx * dx + dy * dy), 0.01);
        const f = (d * d) / K;
        disp[l.s].x -= (dx / d) * f;
        disp[l.s].y -= (dy / d) * f;
        disp[l.t].x += (dx / d) * f;
        disp[l.t].y += (dy / d) * f;
      }
      const cooling = 1 - it / ITER;
      for (let i = 0; i < n; i++) {
        // 向心，保证不飘出视口
        disp[i].x += (cx - pos[i].x) * 0.02;
        disp[i].y += (cy - pos[i].y) * 0.02;
        const len = Math.max(Math.sqrt(disp[i].x ** 2 + disp[i].y ** 2), 0.01);
        const step = Math.min(len, 12) * cooling;
        pos[i].x = Math.min(w - 60, Math.max(60, pos[i].x + (disp[i].x / len) * step));
        pos[i].y = Math.min(h - 40, Math.max(40, pos[i].y + (disp[i].y / len) * step));
      }
    }
    return { pos, w, h };
  }, [nodes, edges]);

  const indexOf = useMemo(() => new Map(nodes.map((n, i) => [n.vid, i])), [nodes]);

  return (
    <div className="w-full h-full flex flex-col bg-white rounded-[8px] border border-[#EEEEEE]">
      <div className="h-[48px] flex items-center justify-between px-[16px] border-b border-[#F0F0F0]">
        <div className="flex items-center gap-[12px]">
          <Button size="small" onClick={onBack}>
            返回
          </Button>
          <span className="text-[14px] font-bold">力导布局</span>
          <span className="text-[13px] text-[#666]">
            节点数: {nodes.length} / {nodes.length}　关系数: {edges.length} / {edges.length}
          </span>
        </div>
        <div className="flex items-center gap-[8px]">
          <span className="text-[12px] text-[#999]">缩放 {Math.round(scale * 100)}%</span>
          <Button size="small" onClick={() => setScale(s => Math.min(2.5, +(s + 0.2).toFixed(2)))}>
            +
          </Button>
          <Button size="small" onClick={() => setScale(s => Math.max(0.4, +(s - 0.2).toFixed(2)))}>
            −
          </Button>
          <Button
            size="small"
            onClick={() => {
              setScale(1);
              setOffset({ x: 0, y: 0 });
            }}
          >
            复位
          </Button>
        </div>
      </div>

      <div className="flex-1 flex min-h-0">
        <div
          className="flex-1 relative overflow-hidden"
          onMouseDown={e => {
            dragRef.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y };
          }}
          onMouseMove={e => {
            const d = dragRef.current;
            if (!d) return;
            setOffset({ x: d.ox + (e.clientX - d.x), y: d.oy + (e.clientY - d.y) });
          }}
          onMouseUp={() => (dragRef.current = null)}
          onMouseLeave={() => (dragRef.current = null)}
        >
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Spin tip="加载图数据…" />
            </div>
          )}
          {!loading && error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-[13px] text-[#666]">
              <div>图数据加载失败：{error}</div>
              <div className="text-[12px] text-[#999]">
                空间 {spaceName}
                {fileId ? ` / 文件 ${fileId}` : ""}
              </div>
            </div>
          )}
          {!loading && !error && nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Empty description="该范围没有图谱数据（可先在“文件管理”里做图谱解析）" />
            </div>
          )}
          {!loading && !error && nodes.length > 0 && (
            <svg width="100%" height="100%" viewBox={`0 0 ${layout.w} ${layout.h}`} style={{ cursor: "grab" }}>
              <g transform={`translate(${offset.x} ${offset.y}) scale(${scale})`}>
                {edges.map((e, i) => {
                  const s = indexOf.get(e.src?.vid || "");
                  const t = indexOf.get(e.dst?.vid || "");
                  if (s === undefined || t === undefined) return null;
                  const a = layout.pos[s];
                  const b = layout.pos[t];
                  return (
                    <line
                      key={e.id || i}
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke="#CBD5E1"
                      strokeWidth={1}
                    />
                  );
                })}
                {nodes.map((n, i) => {
                  const p = layout.pos[i];
                  const color = colorOf[n.nodeType || "unclassified"] || "#3B82F6";
                  const isActive = active?.vid === n.vid;
                  return (
                    <g key={n.vid || i} transform={`translate(${p.x} ${p.y})`} onClick={() => setActive(n)}>
                      <circle r={isActive ? 9 : 6} fill={color} stroke="#fff" strokeWidth={1.5} cursor="pointer" />
                      <text y={18} textAnchor="middle" fontSize={11} fill="#334155" cursor="pointer">
                        {(n.name || n.vid || "").slice(0, 12)}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          )}
        </div>

        <div className="w-[300px] border-l border-[#F0F0F0] px-[14px] py-[12px] overflow-y-auto">
          <div className="text-[14px] font-bold mb-[10px]">节点信息</div>
          {!active && <div className="text-[13px] text-[#999]">点击左侧节点查看属性</div>}
          {active && (
            <div className="text-[13px] text-[#333] flex flex-col gap-[6px]">
              <div>
                <Tag color={colorOf[active.nodeType || "unclassified"]}>{active.nodeType || "unclassified"}</Tag>
              </div>
              <div>名称：{active.name || active.vid}</div>
              <div>来源文件：{active.properties?.title || "-"}</div>
              <div>file_id：{active.properties?.file_id || "-"}</div>
            </div>
          )}
          <div className="mt-[16px] text-[12px] text-[#999]">
            数据源：{type === "subGraph" ? "/graph/search/subGraph" : "/graph/search/wholeGraphSearch"}
            <br />
            空间：{spaceName}
          </div>
        </div>
      </div>
    </div>
  );
}
