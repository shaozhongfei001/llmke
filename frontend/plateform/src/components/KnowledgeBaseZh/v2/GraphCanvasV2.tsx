/**
 * 知识图谱工作台 —— 画布渲染（画布优先，业务名称 + 有向谓词 + 类型色系）。
 * 纯渲染组件：接收已筛选的 nodes/edges，负责确定性力导布局、相机、平移/缩放、点选。
 */
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState
} from "react";
import { Empty } from "antd";
import { typeColor } from "./graphData";
import type { GraphEdge, GraphNode } from "./graphData";

export interface GraphCanvasHandle {
  fit: () => void;
  centerNode: (id: string) => void;
  zoomIn: () => void;
  zoomOut: () => void;
}

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** 高亮的边 id 集合（如问答支持路径） */
  highlightEdges?: Set<string>;
  /** 跨文档高亮模式 */
  crossDocMode?: boolean;
  /** 社区着色：vid → 社区色 */
  communityColor?: Map<string, string>;
  legend?: { label: string; color: string; count: number }[];
  /** 缩放变化回调（用于父组件显示百分比） */
  onScaleChange?: (scale: number) => void;
}

/** 重点实体：概览缩小到小字号时仍保留标签（v2 主链统一"实体"；旧 Nebula 按细分类） */
const PROMINENT_TYPES = new Set(["实体", "产品", "客户", "评级"]);

interface Pos {
  x: number;
  y: number;
}

const GraphCanvasV2 = forwardRef<GraphCanvasHandle, Props>(function GraphCanvasV2(
  { nodes, edges, selectedId, onSelect, highlightEdges, crossDocMode, communityColor, legend, onScaleChange },
  ref
) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);
  const [vp, setVp] = useState({ w: 900, h: 620 });

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setVp({ w: el.clientWidth || 900, h: el.clientHeight || 620 });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const nodeIndex = useMemo(() => new Map(nodes.map((n, i) => [n.vid, i])), [nodes]);

  /** 确定性力导布局（结果只依赖 nodes/edges，与时间无关） */
  const layout = useMemo<{ pos: Pos[] }>(() => {
    const n = nodes.length;
    if (!n) return { pos: [] };
    const w = 1000;
    const h = 760;
    const cx = w / 2;
    const cy = h / 2;
    const pos: Pos[] = nodes.map((_, i) => {
      const a = (i / n) * Math.PI * 2;
      const r = Math.min(w, h) * 0.28 + (i % 9) * 5;
      return { x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r };
    });
    const links = edges
      .map(e => ({ s: nodeIndex.get(e.source), t: nodeIndex.get(e.target) }))
      .filter(l => l.s !== undefined && l.t !== undefined) as { s: number; t: number }[];

    const ITER = Math.max(120, Math.min(260, Math.round(n * 1.6)));
    const K = 95;
    for (let it = 0; it < ITER; it++) {
      const disp = pos.map(() => ({ x: 0, y: 0 }));
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          let dx = pos[i].x - pos[j].x;
          let dy = pos[i].y - pos[j].y;
          let d2 = dx * dx + dy * dy;
          if (d2 < 1) {
            dx = (Math.sin(i * 7 + j) - 0.5) * 0.6;
            dy = (Math.cos(i * 3 + j) - 0.5) * 0.6;
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
        disp[i].x += (cx - pos[i].x) * 0.02;
        disp[i].y += (cy - pos[i].y) * 0.02;
        const len = Math.max(Math.sqrt(disp[i].x ** 2 + disp[i].y ** 2), 0.01);
        const step = Math.min(len, 12) * cooling;
        pos[i].x = Math.min(w - 50, Math.max(50, pos[i].x + (disp[i].x / len) * step));
        pos[i].y = Math.min(h - 40, Math.max(40, pos[i].y + (disp[i].y / len) * step));
      }
    }
    return { pos };
  }, [nodes, edges, nodeIndex]);

  /** 邻域（选中节点 1 跳） */
  const neighbors = useMemo(() => {
    const set = new Set<string>();
    if (!selectedId) return set;
    set.add(selectedId);
    for (const e of edges) {
      if (e.source === selectedId) set.add(e.target);
      if (e.target === selectedId) set.add(e.source);
    }
    return set;
  }, [selectedId, edges]);

  const fit = () => {
    if (!nodes.length) return;
    const xs = nodes.map(n => layout.pos[nodeIndex.get(n.vid)!].x);
    const ys = nodes.map(n => layout.pos[nodeIndex.get(n.vid)!].y);
    const x0 = Math.min(...xs) - 90;
    const x1 = Math.max(...xs) + 90;
    const y0 = Math.min(...ys) - 70;
    const y1 = Math.max(...ys) + 90;
    const s = Math.min((vp.w - 30) / (x1 - x0), (vp.h - 40) / (y1 - y0), 1.2);
    setScale(Math.max(0.25, s));
    setOffset({
      x: (vp.w - (x1 - x0) * s) / 2 - x0 * s,
      y: (vp.h - (y1 - y0) * s) / 2 - y0 * s
    });
  };

  const centerNode = (id: string) => {
    const idx = nodeIndex.get(id);
    if (idx === undefined) return;
    const p = layout.pos[idx];
    const s = Math.max(scale, 0.9);
    setScale(s);
    setOffset({ x: vp.w * 0.5 - p.x * s, y: vp.h * 0.46 - p.y * s });
  };

  useImperativeHandle(ref, () => ({
    fit,
    centerNode,
    zoomIn: () => setScale(s => Math.min(2.6, +(s * 1.2).toFixed(2))),
    zoomOut: () => setScale(s => Math.max(0.25, +(s / 1.2).toFixed(2)))
  }));

  // 首次数据就绪时适配
  const fitted = useRef(false);
  useEffect(() => {
    if (nodes.length && !fitted.current) {
      fitted.current = true;
      setTimeout(fit, 60);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes.length]);

  useEffect(() => {
    onScaleChange?.(scale);
  }, [scale, onScaleChange]);

  const showEdgeLabel = selectedId !== null;

  return (
    <div className="kgw-viewport" ref={viewportRef}>
      {nodes.length === 0 ? (
        <div className="kgw-empty">
          <Empty description="当前筛选下没有实体，可放宽类型、文档或社区范围" />
        </div>
      ) : (
        <svg
          className="kgw-svg"
          width="100%"
          height="100%"
          viewBox={`0 0 ${vp.w} ${vp.h}`}
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
          onWheel={e => {
            e.preventDefault();
            const factor = e.deltaY > 0 ? 1 / 1.1 : 1.1;
            const s = Math.min(2.6, Math.max(0.25, scale * factor));
            const f = s / scale;
            const px = e.clientX - (viewportRef.current?.getBoundingClientRect().left || 0);
            const py = e.clientY - (viewportRef.current?.getBoundingClientRect().top || 0);
            setOffset(o => ({ x: px - (px - o.x) * f, y: py - (py - o.y) * f }));
            setScale(s);
          }}
          style={{ cursor: dragRef.current ? "grabbing" : "grab" }}
        >
          <defs>
            <marker
              id="kgw-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto"
            >
              <path d="M0 1 L9 5 L0 9" fill="none" stroke="#b6c5dc" strokeWidth="1.5" />
            </marker>
            <marker
              id="kgw-arrow-active"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto"
            >
              <path d="M0 1 L9 5 L0 9" fill="none" stroke="#4872e9" strokeWidth="1.5" />
            </marker>
          </defs>
          <g transform={`translate(${offset.x} ${offset.y}) scale(${scale})`}>
            {edges.map(e => {
              const s = nodeIndex.get(e.source);
              const t = nodeIndex.get(e.target);
              if (s === undefined || t === undefined) return null;
              const a = layout.pos[s];
              const b = layout.pos[t];
              const isSel =
                selectedId !== null && (e.source === selectedId || e.target === selectedId);
              const isHighlight = highlightEdges?.has(e.id);
              const isDim =
                (crossDocMode && !e.title?.includes(",")) ||
                (isHighlight !== undefined && !isHighlight && selectedId === null && highlightEdges?.size);
              const mx = (a.x + b.x) / 2;
              const my = (a.y + b.y) / 2;
              return (
                <g key={e.id || `${e.source}-${e.predicate}-${e.target}`}>
                  <line
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    className={
                      isHighlight || isSel
                        ? "kgw-edge kgw-edge--active"
                        : isDim
                          ? "kgw-edge kgw-edge--dim"
                          : "kgw-edge"
                    }
                    markerEnd={isHighlight || isSel ? "url(#kgw-arrow-active)" : "url(#kgw-arrow)"}
                  />
                  {(showEdgeLabel && (isSel || isHighlight)) && (
                    <text className="kgw-edge-label" x={mx} y={my - 6} textAnchor="middle">
                      {e.predicate}
                    </text>
                  )}
                </g>
              );
            })}
            {nodes.map((n, i) => {
              const p = layout.pos[i];
              const color = typeColor(n.nodeType);
              const isSel = selectedId === n.vid;
              const isNeighbor = selectedId !== null && neighbors.has(n.vid);
              const isDim = selectedId !== null && !isNeighbor;
              const prominent = PROMINENT_TYPES.has(n.nodeType) || isSel;
              const r = n.nodeType === "产品" ? 22 : n.nodeType === "客户" ? 18 : 13;
              // 概览级（默认 fit 约 69%）隐藏次要标签，避免 137 节点文字堆叠
              const hideLabel = scale < 0.8 && !prominent;
              const labelSize = Math.max(
                prominent ? 14 : 12,
                (prominent ? 14 : 12) / scale
              );
              return (
                <g
                  key={n.vid}
                  className={`kgw-node ${isSel ? "is-sel" : ""} ${isDim ? "is-dim" : ""}`}
                  transform={`translate(${p.x} ${p.y})`}
                  onClick={e => {
                    e.stopPropagation();
                    onSelect(n.vid);
                  }}
                  style={{ cursor: "pointer" }}
                >
                  {isSel && (
                    <circle className="kgw-ring" r={r + 7} fill="none" stroke="#d4e0ff" strokeWidth="4" />
                  )}
                  <circle r={r} fill={color + "22"} stroke={color} strokeWidth="1.8" />
                  {n.nodeType === "产品" && (
                    <path
                      d="M-7-6h14v12H-7Zm4 4h8m-8 4h8"
                      fill="none"
                      stroke={color}
                      strokeWidth="1.2"
                    />
                  )}
                  {n.nodeType === "客户" && (
                    <>
                      <circle cy="-4" r="4" fill="none" stroke={color} strokeWidth="1.2" />
                      <path d="M-6 7c0-7 12-7 12 0" fill="none" stroke={color} strokeWidth="1.2" />
                    </>
                  )}
                  {communityColor?.has(n.vid) && (
                    <circle r={r + 12} fill="none" stroke={communityColor.get(n.vid)} strokeOpacity="0.25" strokeWidth="10" />
                  )}
                  {!hideLabel && (
                    <text
                      className="kgw-node-label"
                      y={r + 22}
                      textAnchor="middle"
                      style={{ fontSize: labelSize }}
                    >
                      {n.name.length > 14 ? n.name.slice(0, 13) + "…" : n.name}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      )}

      {/* 图例 */}
      {legend && legend.length > 0 && (
        <div className="kgw-legend">
          {legend.map(l => (
            <span key={l.label} className="kgw-legend-item">
              <span className="kgw-legend-dot" style={{ background: l.color }} />
              {l.label}
              <span className="kgw-legend-count">{l.count}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
});

export default GraphCanvasV2;
