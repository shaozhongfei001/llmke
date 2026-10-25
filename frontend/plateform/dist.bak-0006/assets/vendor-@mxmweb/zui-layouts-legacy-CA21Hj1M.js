!function(){let e,t,i,o,l,n,r,s,a,d,c,h,p,x,u,g,f,v,m,b,k,w,y,j,C,$,I,z,B,S,A,M,T,D,E,W=e=>e;System.register(["../vendor-react-legacy-Co-T2RJM.js","../vendor-styled-components-legacy-DULKPiI_.js","./zui-theme-legacy-m3iNS6o2.js","./zui-components-legacy-Bfcp5TGZ.js"],function(L,F){"use strict";var R,N,H,O,P,Y,K,q,Z,G;return{setters:[e=>{R=e.t,N=e.j,H=e.r},e=>{O=e.d},e=>{P=e.c,Y=e.h,K=e.i,q=e.E},e=>{Z=e.F,G=e.D}],execute:function(){const F=H.createContext({outlet:null,matches:[],isDataRoute:!1}),X=H.createContext(null);function V(e){return function(e){let t=H.useContext(F).outlet;return t&&H.createElement(X.Provider,{value:e},t)}(e.context)}new Promise(()=>{});
/**
       * @license lucide-react v0.456.0 - ISC
       *
       * This source code is licensed under the ISC license.
       * See the LICENSE file in the root directory of this source tree.
       */
const _=e=>e.replace(/([a-z0-9])([A-Z])/g,"$1-$2").toLowerCase(),J=(...e)=>e.filter((e,t,i)=>!!e&&""!==e.trim()&&i.indexOf(e)===t).join(" ").trim();
/**
       * @license lucide-react v0.456.0 - ISC
       *
       * This source code is licensed under the ISC license.
       * See the LICENSE file in the root directory of this source tree.
       */var Q={xmlns:"http://www.w3.org/2000/svg",width:24,height:24,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor",strokeWidth:2,strokeLinecap:"round",strokeLinejoin:"round"};
/**
       * @license lucide-react v0.456.0 - ISC
       *
       * This source code is licensed under the ISC license.
       * See the LICENSE file in the root directory of this source tree.
       */const U=H.forwardRef(({color:e="currentColor",size:t=24,strokeWidth:i=2,absoluteStrokeWidth:o,className:l="",children:n,iconNode:r,...s},a)=>H.createElement("svg",{ref:a,...Q,width:t,height:t,stroke:e,strokeWidth:o?24*Number(i)/Number(t):i,className:J("lucide",l),...s},[...r.map(([e,t])=>H.createElement(e,t)),...Array.isArray(n)?n:[n]])),ee=(e,t)=>{const i=H.forwardRef(({className:i,...o},l)=>H.createElement(U,{ref:l,iconNode:t,className:J(`lucide-${_(e)}`,i),...o}));return i.displayName=`${e}`,i},te=ee("ArrowLeft",[["path",{d:"m12 19-7-7 7-7",key:"1l729n"}],["path",{d:"M19 12H5",key:"x3x0zl"}]]),ie=ee("ChevronRight",[["path",{d:"m9 18 6-6-6-6",key:"mthhwq"}]]),oe=O.div(e||(e=W`
  display: flex;
  justify-content: flex-start;
  align-items: flex-start;
  margin-left: 20px;
  flex-direction: column;
  height: 100%;
  width: 100%;
  max-width: 98%;
  position: relative;
`)),le=O.div(t||(t=W`
  display: flex;
  height: 38px;
  z-index: 10;
  background: transparent;
  gap: 8px;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  width: 100%;
  min-width: 0; /* 确保 flex 子元素可以收缩 */
`)),ne=O.button(i||(i=W`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  cursor: pointer;

  /* 仅让图标在 hover 时上浮，按钮背景保持透明 */
  svg {
    transition: transform 0.2s ease;
  }

  &:hover {
    background: transparent;
  }

  &:hover svg {
    transform: translateY(-1px);
  }

  &:active svg {
    transform: translateY(0);
  }
`)),re=O.div(o||(o=W`
  line-height: 1.4;
  cursor: pointer;
  transition: color 0.2s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
  min-width: 0;

  &:hover {
    color: #007bff;
  }
`)),se=O.div(l||(l=W`
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
`)),ae=O.div(n||(n=W`
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;
  max-width: 50%;
  min-width: 0;
  overflow: hidden;
`)),de=O.div(r||(r=W`
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: ${0};
  font-weight: ${0};
  cursor: ${0};
  transition: color 0.2s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;

  &:hover {
    color: ${0};
  }
`),e=>e.$isLast?"#343a40":"#6c757d",e=>e.$isLast?"600":"normal",e=>e.$isClickable?"pointer":"default",e=>e.$isLast?"#007bff":"inherit"),ce=O.div(s||(s=W`
  display: flex;
  align-items: center;
  color: #6c757d;
  margin: 0 2px;
`)),he=O.div(a||(a=W`
  display: flex;
  flex-direction: column;
  width: 100%;
  height: calc(100% - 45px);
  min-height: 650px;
  overflow: auto;
`));
/**
       * @license lucide-react v0.456.0 - ISC
       *
       * This source code is licensed under the ISC license.
       * See the LICENSE file in the root directory of this source tree.
       */O.div(d||(d=W`
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
`));const pe=O.div.withConfig({shouldForwardProp:e=>!["backgroundImage","backgroundColor"].includes(e)})(c||(c=W`
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: ${0};
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 1;
`),e=>e.backgroundImage?`url(${e.backgroundImage}) center/cover no-repeat`:e.backgroundColor||"#1a1a1a"),xe=O.div(h||(h=W`
  height: 48px;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  z-index: 10;
  flex-shrink: 0;
`)),ue=O.div(p||(p=W`
  flex: 1;
  width: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  z-index: 2;
  background: transparent;

  /* 自定义滚动条样式 */
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.3);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.5);
  }
`)),ge=O.div(x||(x=W`
  height: 80px;
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 12px 0;
  background: transparent;
  z-index: 10;
  flex-shrink: 0;
`)),fe=O.div(u||(u=W`
  --header-height: 56px;
  --page-gutter: 16px;
  --sidebar-width: 264px;
  --toc-width: 268px;
  --content-max: 960px;

  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 100vh;
  height: 100vh; /* 以视口高度为基准，便于内部独立滚动布局 */
  position: relative;
`)),ve=O.div(g||(g=W`
  position: sticky;
  top: 0;
  z-index: 30;
  width: 100%;
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  backdrop-filter: blur(8px);
`)),me=O.div(f||(f=W`
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
`)),be=O.div(v||(v=W`
  display: flex;
  align-items: center;
  gap: 8px;
`)),ke=O.button(m||(m=W`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid rgba(0,0,0,0.08);
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease, transform .1s ease;

  &:hover { background: rgba(0,0,0,0.04); }
  &:active { transform: translateY(1px); }
`)),we=O.div(b||(b=W`
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr var(--toc-width);
  gap: 16px;
  width: 100%;
  padding: 12px 0;
  box-sizing: border-box;
  transition: grid-template-columns .25s ease;
  height: calc(100vh - var(--header-height));
  min-height: calc(100vh - var(--header-height));
  overflow: hidden; /* 内部区域各自滚动 */

  @media (max-width: 1280px) {
    grid-template-columns: var(--sidebar-width) 1fr 0px;
  }

  @media (max-width: 960px) {
    grid-template-columns: 0px 1fr 0px;
    gap: 12px;
    padding: 12px 12px 20px 12px;
  }
`)),ye=O.aside(k||(k=W`
  position: relative;
`)),je=O.div(w||(w=W`
  height: 100%;
  overflow: hidden;
  padding-right: 8px;
  border-right: 1px solid rgba(0,0,0,0.06);
  transition: opacity .2s ease, transform .2s ease;
  opacity: ${0};
  transform: translateX(${0});
  pointer-events: ${0};
`),e=>e.$collapsed?0:1,e=>e.$collapsed?"-6px":"0px",e=>e.$collapsed?"none":"auto"),Ce=O.button(y||(y=W`
  position: absolute;
  top: 6px;
  right: -10px;
  width: 10px;
  height: 72px;
  border: none;
  background: rgba(0,0,0,0.06);
  border-radius: 0 8px 8px 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background .15s ease;
  &:hover { background: rgba(0,0,0,0.12); }
`)),$e=O.div(j||(j=W`
  height: 100%;
  overflow: auto;
  padding-right: 8px;
`)),Ie=O.main(C||(C=W`
  position: relative;
  min-width: 0;
  height: 100%;
  overflow: auto; /* 文档渲染区独立滚动 */
`)),ze=O.div($||($=W`
  width: 100%;
  max-width: var(--content-max);
  margin: 0 auto;
  background-clip: padding-box;
  border-radius: 8px;
  padding: 0px 12px;
  padding-bottom: 120px; /* 底部留出足够的 margin，确保可以滚动到最底部 */
`)),Be=O.div(I||(I=W`
  height: 100%;
  transition: opacity .5s ease;
  opacity: ${0};
`),e=>e.$opacity),Se=O.aside(z||(z=W`
  position: relative;
  z-index: 1;
  height: 100%;
  overflow: hidden;
`)),Ae=O.div(B||(B=W`
  /* 右侧目录独立滚动 */
  position: relative;
  height: 100%;
  width: 100%;
  max-width: var(--toc-width);
  overflow-x: hidden; /* 禁止横向滚动 */
  overflow-y: auto; /* 只允许垂直滚动 */
  padding-left: 8px;
  border-left: 1px solid rgba(0,0,0,0.06);
  background: transparent;
  z-index: 1;
`)),Me=O.div(S||(S=W`
  transition: opacity .2s ease, transform .2s ease;
  opacity: ${0};
  transform: translateX(${0});
  pointer-events: ${0};
  width: 100%;
  max-width: 100%;
  /* 不设置高度限制，让内容自然流动，由父容器 TocFloat 控制滚动 */
`),e=>e.$collapsed?0:1,e=>e.$collapsed?"6px":"0px",e=>e.$collapsed?"none":"auto");L({$:({children:e,goBack:t,title:i,description:o,breadcrumbs:l,dockItems:n,dockActiveMode:r="single",defaultDockActiveId:s,defaultDockActiveIds:a,styles:d,eventsEmit:c})=>{var h,p,x,u,g,f,v,m;const b=P(),k=Y(Y({theme:K,mode:"light"},b),d),w=(null==k?void 0:k.theme)||K,y=R.useRef(null),j=(e,t)=>{null!=c&&c.onBreadcrumbClick?c.onBreadcrumbClick(e,t):e.onClick&&e.onClick()},[C,$]=R.useState(!0);return N.jsx(oe,{style:{background:w.colors.appBackground,color:w.colors.text,fontFamily:(null==(p=null==(h=w.fonts)?void 0:h.body)?void 0:p.family)||"PingFang SC, Microsoft YaHei, Arial, sans-serif"},children:N.jsxs("div",{style:{height:"100%",display:"flex",width:"100%",gap:12},children:[n&&n.length>0&&N.jsx("div",{style:{flex:`0 0 ${C?72:28}px`,transition:"flex-basis .2s ease"},children:N.jsx(Z,{items:n,open:C,onOpenChange:$,onItemClick:e=>((e,t)=>{null!=c&&c.onDockItemClick&&c.onDockItemClick(e,t)})({id:String(e.key),label:e.name},0),defaultOpen:!0})}),N.jsxs("div",{style:{display:"flex",flexDirection:"column",flex:1,minWidth:0},children:[(i||o||t||l)&&N.jsxs(le,{ref:y,children:[t&&N.jsx(ne,{onClick:()=>{null!=c&&c.onGoBack?c.onGoBack():t&&t()},style:{color:w.colors.primary,borderRadius:w.space.radius||"6px"},title:"返回",children:N.jsx(te,{size:18})}),(()=>{if(!l||0===l.length)return null;const e=R.useRef(null),[t,i]=R.useState({start:0,end:l.length,showEllipsis:!1}),o=R.useCallback(()=>{if(!e.current||l.length<=3)return void i({start:0,end:l.length,showEllipsis:!1});const t=.5*e.current.offsetWidth;let o=Math.floor((t-30)/140);if(o<2&&(o=2),o>=l.length)return void i({start:0,end:l.length,showEllipsis:!1});const n=Math.min(o-1,l.length);i({start:0,end:n,showEllipsis:n<l.length-1})},[l.length]);if(R.useEffect(()=>{o();const t=new ResizeObserver(()=>{o()});return e.current&&t.observe(e.current),()=>{t.disconnect()}},[o]),l.length<=3)return N.jsx(ae,{children:l.map((e,t)=>N.jsxs(R.Fragment,{children:[N.jsx(de,{$isLast:t===l.length-1,$isClickable:!!(t<l.length-1||e.onClick),onClick:()=>j(e,t),style:{color:t===l.length-1?w.colors.text:w.colors.textSecondary||w.colors.disabledText},title:e.label,children:e.label}),t<l.length-1&&N.jsx(ce,{children:N.jsx(ie,{size:14})})]},e.id))});const{start:n,end:r,showEllipsis:s}=t;return N.jsxs(ae,{children:[l.slice(n,r).map((e,t)=>N.jsxs(R.Fragment,{children:[N.jsx(de,{$isLast:t===r-n-1&&!s,$isClickable:!!(t<r-n-1||e.onClick),onClick:()=>j(e,n+t),style:{color:t!==r-n-1||s?w.colors.textSecondary||w.colors.disabledText:w.colors.text},title:e.label,children:e.label}),t<r-n-1&&N.jsx(ce,{children:N.jsx(ie,{size:14})})]},e.id)),s&&N.jsxs(N.Fragment,{children:[N.jsx(ce,{children:N.jsx(ie,{size:14})}),N.jsx(de,{$isLast:!1,$isClickable:!1,style:{color:w.colors.textSecondary||w.colors.disabledText,cursor:"default",maxWidth:"auto"},title:`${l.slice(r,-1).map(e=>e.label).join(" > ")}`,children:"..."}),N.jsx(ce,{children:N.jsx(ie,{size:14})}),N.jsx(de,{$isLast:!0,$isClickable:!!l[l.length-1].onClick,onClick:()=>j(l[l.length-1],l.length-1),style:{color:w.colors.text},title:l[l.length-1].label,children:l[l.length-1].label})]})]})})(),i&&N.jsx(re,{onClick:()=>{null!=c&&c.onTitleClick&&c.onTitleClick()},style:{color:w.colors.text,fontSize:(null==(u=null==(x=w.fonts)?void 0:x.heading)?void 0:u.size)||"16px",fontWeight:(null==(f=null==(g=w.fonts)?void 0:g.heading)?void 0:f.weight)||"600"},title:i,children:i}),o&&N.jsx(se,{style:{color:w.colors.textSecondary||w.colors.disabledText,opacity:.7,fontSize:(null==(m=null==(v=w.fonts)?void 0:v.body)?void 0:m.size)||"12px"},title:o,children:o})]}),N.jsx(he,{style:{background:w.colors.dashboardBackground||"transparent",border:`1px solid ${w.colors.border}`||void 0,borderRadius:w.space.radius||void 0,boxShadow:w.colors.shadow||void 0},children:e||N.jsx(V,{})})]})]})})},B:({children:e,backgroundImage:t,backgroundColor:i,header:o,dockItems:l,dockActiveMode:n="single",defaultDockActiveId:r,defaultDockActiveIds:s,styles:a,eventsEmit:d})=>{var c,h;const p=P(),x=Y(Y({theme:K,mode:"light"},p),a),u=(null==x?void 0:x.theme)||K;return N.jsxs(pe,{backgroundImage:t,backgroundColor:i,children:[o&&N.jsx(xe,{children:o}),N.jsx(ue,{style:{color:u.colors.text,fontFamily:(null==(h=null==(c=u.fonts)?void 0:c.body)?void 0:h.family)||"PingFang SC, Microsoft YaHei, Arial, sans-serif"},children:e}),l&&l.length>0&&N.jsx(ge,{children:N.jsx(G,{items:l,itemWidth:48,itemHeight:48,magnification:1.5,itemGap:8,activeMode:n,defaultActiveId:r,defaultActiveIds:s,onItemClick:(e,t)=>{null!=d&&d.onDockItemClick?d.onDockItemClick(e,t):e.onClick&&e.onClick()},onActiveChange:(e,t)=>{null!=d&&d.onDockActiveChange&&d.onDockActiveChange(e,t)},onActiveChangeMultiple:(e,t)=>{null!=d&&d.onDockActiveChangeMultiple&&d.onDockActiveChangeMultiple(e,t)}})})]})}}),O.button(A||(A=W`
  position: absolute;
  top: 6px;
  left: -10px;
  width: 10px;
  height: 72px;
  border: none;
  background: rgba(0,0,0,0.06);
  border-radius: 8px 0 0 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background .15s ease;
  &:hover { background: rgba(0,0,0,0.12); }
`));const Te=O.div(M||(M=W`
  font-size: 12px;
  opacity: .7;
  padding: 8px 8px;
`)),De=O.button(T||(T=W`
  width: 100%;
  padding: 8px 10px;
  background: transparent;
  border: none;
  text-align: left;
  cursor: pointer;
  border-radius: 6px;
  color: inherit;
  transition: background .15s ease, color .15s ease;
  font-size: 13px;
  line-height: 1.5;
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  /* 限制为最多两行，超出显示省略号 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0; /* 允许内容收缩 */

  &:hover {
    background: rgba(0,0,0,0.04);
  }

  ${0}
`),e=>e.$active?"background: rgba(0,0,0,0.08); font-weight: 600;":""),Ee=O.div(D||(D=W`
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  white-space: nowrap;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  &::-webkit-scrollbar { display: none; }
`)),We=O.div(E||(E=W`
  width: 1px;
  height: 16px;
  background: currentColor;
  opacity: .2;
`)),Le={theme:{...K,colors:{...K.colors,appBackground:"#ffffff",panelBackground:"#ffffff",dashboardBackground:"#ffffff",text:"#24292f",textSecondary:"#6b7280",border:"#e5e7eb",shadow:"0 1px 2px rgba(0,0,0,0.06)"}}},Fe={theme:{...K,colors:{...K.colors,appBackground:"#0f172a",panelBackground:"#111827",dashboardBackground:"#0b1220",text:"#e5e7eb",textSecondary:"#9ca3af",border:"#1f2937",shadow:"none"}},mode:"dark"};L("D",e=>{var t,i,o,l;const{children:n,headerLogo:r,contentKey:s,modules:a,activeModuleKey:d,onModuleChange:c,languages:h,activeLanguageKey:p,onLanguageChange:x,themes:u,activeThemeKey:g,onThemeChange:f,sidebarItems:v,activeSidebarId:m,onSidebarItemClick:b,activeTocId:k,onTocItemClick:w,collapsibleSidebar:y=!0,styles:j}=e,C=P(),$="dark"===e.activeThemeKey?Fe:Le,I=Y(Y(Y({theme:K,mode:"light"},C),$),j),z=(null==I?void 0:I.theme)||K,[B,S]=R.useState(!1),[A,M]=R.useState(!1),[T,D]=R.useState(!1),E="string"==typeof k,[W,L]=R.useState(k),F=R.useRef(null),[H,O]=R.useState(void 0),[Z,G]=R.useState(n),[X,V]=R.useState(1);R.useEffect(()=>{if(void 0===s)return void G(n);V(0);const e=setTimeout(()=>{G(n),requestAnimationFrame(()=>V(1))},120);return()=>clearTimeout(e)},[s,n]),R.useMemo(()=>{var e,t,i,o,l,n,r,s,a,d,c,h,p;return{primaryColor:null==(e=null==z?void 0:z.colors)?void 0:e.primary,secondaryColor:null==(t=null==z?void 0:z.colors)?void 0:t.secondary,backgroundColor:null==(i=null==z?void 0:z.colors)?void 0:i.appBackground,textColor:null==(o=null==z?void 0:z.colors)?void 0:o.text,borderColor:null==(l=null==z?void 0:z.colors)?void 0:l.border,disabledBackground:null==(n=null==z?void 0:z.colors)?void 0:n.disabledBackground,borderRadius:null==(r=null==z?void 0:z.space)?void 0:r.radius,padding:null==(s=null==z?void 0:z.space)?void 0:s.padding,margin:null==(a=null==z?void 0:z.space)?void 0:a.margin,baseFontSize:null!=(c=null==(d=null==z?void 0:z.fonts)?void 0:d.body)&&c.size?parseInt(null==(p=null==(h=null==z?void 0:z.fonts)?void 0:h.body)?void 0:p.size,10):void 0}},[z]),R.useEffect(()=>{if(!e.tocItems){void 0!==s&&O(void 0);let e=0;const t=10;let i=null,o=null;const l=()=>{const o=F.current;if(!o)return void(e<t?(e++,i=setTimeout(l,200)):O([]));const n=Array.from(o.querySelectorAll("h1, h2, h3"));if(0===n.length)return void(e<t?(e++,i=setTimeout(l,200)):O([]));const r=new Map,s=n.map(e=>{var t;const i=e.id||(null==(t=e.textContent)?void 0:t.trim().replace(/\s+/g,"-").toLowerCase())||"",o=r.get(i)||0;r.set(i,o+1);const l=o>0?`${i}-${o}`:i;e.id||(e.id=l);const n="H1"===e.tagName?1:"H2"===e.tagName?2:3;return{id:l,label:e.textContent||"",level:n}});O(s)};return o=requestAnimationFrame(()=>{i=setTimeout(l,100)}),()=>{null!==o&&cancelAnimationFrame(o),null!==i&&clearTimeout(i)}}O(void 0)},[n,e.tocItems,s]),R.useEffect(()=>{var t;if(E)return;const i=((null!==(t=e.tocItems)&&void 0!==t?t:H)||[]).map(e=>e.id).filter(Boolean);if(0===i.length)return;L(void 0);const o=new IntersectionObserver(e=>{var t,i;const o=e.filter(e=>e.isIntersecting).sort((e,t)=>e.boundingClientRect.top-t.boundingClientRect.top);null!=(i=null==(t=o[0])?void 0:t.target)&&i.id&&L(o[0].target.id)},{root:null,rootMargin:"0px 0px -70% 0px",threshold:0});return i.forEach(e=>{const t=document.getElementById(e);t&&o.observe(t)}),()=>o.disconnect()},[H,E,e.tocItems,s]);const _=(e,t)=>{if(!e||0===e.length)return;const i=Math.max(0,e.findIndex(e=>e.key===t)),o=e[(i+1)%e.length];return null==o?void 0:o.key},J=e=>{const t=document.getElementById(e);t&&t.scrollIntoView({behavior:"smooth",block:"start",inline:"nearest"})};return N.jsx(q,{theme:z,mode:I.mode,children:N.jsxs(fe,{style:{background:z.colors.appBackground,color:z.colors.text,fontFamily:(null==(i=null==(t=z.fonts)?void 0:t.body)?void 0:i.family)||"PingFang SC, Microsoft YaHei, Arial, sans-serif"},children:[N.jsxs(ve,{style:{background:z.colors.panelBackground||z.colors.dashboardBackground||"rgba(255,255,255,0.6)",color:z.colors.text},children:[N.jsxs(me,{children:[r,a&&a.length>0&&N.jsx(Ee,{children:a.map(e=>N.jsx(De,{$active:e.key===d,onClick:()=>null==c?void 0:c(e.key),title:e.label,children:e.label},e.key))})]}),N.jsxs(be,{children:[N.jsx("div",{className:"hide-on-desktop",style:{display:"none"}}),h&&h.length>0&&N.jsx(ke,{onClick:()=>{const e=_(h,p);e&&(null==x||x(e))},title:(null==(o=h.find(e=>e.key===p))?void 0:o.label)||"Language","aria-label":"language",style:{color:z.colors.text},children:N.jsxs("svg",{width:"16",height:"16",viewBox:"0 0 24 24",fill:"none",xmlns:"http://www.w3.org/2000/svg",children:[N.jsx("path",{d:"M12 21c4.97 0 9-4.03 9-9s-4.03-9-9-9-9 4.03-9 9 4.03 9 9 9Z",stroke:"currentColor",strokeWidth:"1.6"}),N.jsx("path",{d:"M3 12h18M12 3c-2.5 2.5-3.75 5.167-3.75 9S9.5 19.5 12 21c2.5-1.5 3.75-4.167 3.75-8S14.5 5.5 12 3Z",stroke:"currentColor",strokeWidth:"1.6"})]})}),N.jsx(We,{}),u&&u.length>0&&N.jsx(ke,{onClick:()=>{const e=_(u,g);e&&(null==f||f(e))},title:(null==(l=u.find(e=>e.key===g))?void 0:l.label)||"Theme","aria-label":"theme",style:{color:z.colors.text},children:N.jsx("svg",{width:"16",height:"16",viewBox:"0 0 24 24",fill:"none",xmlns:"http://www.w3.org/2000/svg",children:N.jsx("path",{d:"M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z",stroke:"currentColor",strokeWidth:"1.6"})})}),N.jsx("div",{className:"mobile-only",style:{display:"none"},children:N.jsx(De,{onClick:()=>D(!0),title:"打开目录",children:"目录"})})]})]}),(t=>{const i=(Array.isArray(v)?v.length:0)>1,o=A?"10px":"var(--toc-width)",l=i?`${i?B?"10px":"var(--sidebar-width)":"0px"} 1fr ${o}`:`1fr ${o}`;return N.jsxs(we,{style:{gridTemplateColumns:l},children:[i&&N.jsxs(ye,{children:[N.jsx(je,{$collapsed:B,children:N.jsx($e,{children:v&&v.length>0&&N.jsx("div",{children:Object.entries(v.reduce((e,t)=>{const i=t.group||"文档";return e[i]=e[i]||[],e[i].push(t),e},{})).map(([e,t])=>N.jsxs("div",{children:[N.jsx(Te,{children:e}),N.jsx("div",{style:{display:"flex",flexDirection:"column",gap:4,padding:"0 8px 8px 8px"},children:t.map(e=>N.jsx(De,{$active:e.id===m,onClick:()=>{e.href&&(e.href.startsWith("#")?J(e.href.slice(1)):window.location.href=e.href),null==b||b(e),D(!1)},title:e.label,children:e.label},e.id))})]},e))})})}),y&&i&&N.jsx(Ce,{onClick:()=>S(e=>!e),title:B?"展开左侧栏":"收起左侧栏","aria-label":"toggle-left",children:B?N.jsx("svg",{width:"10",height:"10",viewBox:"0 0 24 24",fill:"none",xmlns:"http://www.w3.org/2000/svg",children:N.jsx("path",{d:"M9 6l6 6-6 6",stroke:"currentColor",strokeWidth:"1.6"})}):N.jsx("svg",{width:"10",height:"10",viewBox:"0 0 24 24",fill:"none",xmlns:"http://www.w3.org/2000/svg",children:N.jsx("path",{d:"M15 6l-6 6 6 6",stroke:"currentColor",strokeWidth:"1.6"})})})]}),N.jsx(Ie,{children:N.jsx(ze,{ref:F,children:N.jsx(Be,{$opacity:X,children:Z})})}),N.jsx(Se,{children:N.jsx(Ae,{children:N.jsxs(Me,{$collapsed:A,children:[N.jsx(Te,{children:"本页目录"}),N.jsx("div",{style:{display:"flex",flexDirection:"column",gap:4,padding:"0 8px 8px 8px"},children:((null!==(t=e.tocItems)&&void 0!==t?t:H)||[]).map(e=>N.jsx(De,{$active:(E?k:W)===e.id,onClick:()=>{J(e.id),null==w||w(e)},title:e.label,style:{paddingLeft:12*Math.max(0,(e.level||1)-1)+10},children:e.label},e.id))})]})})})]})})(),T&&N.jsx("div",{role:"dialog","aria-modal":"true",style:{position:"fixed",inset:0,zIndex:40,background:"rgba(0,0,0,0.45)",display:"flex"},onClick:()=>D(!1),children:N.jsxs("div",{style:{width:"82%",maxWidth:320,height:"100%",background:z.colors.panelBackground||z.colors.dashboardBackground||"#fff",color:z.colors.text,borderRight:`1px solid ${z.colors.border}`,padding:12},onClick:e=>e.stopPropagation(),children:[N.jsxs("div",{style:{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8},children:[N.jsx("div",{style:{fontWeight:600},children:"目录"}),N.jsx(De,{onClick:()=>D(!1),children:"关闭"})]}),v&&v.length>0&&N.jsx("div",{style:{overflow:"auto",height:"calc(100% - 40px)"},children:Object.entries(v.reduce((e,t)=>{const i=t.group||"文档";return e[i]=e[i]||[],e[i].push(t),e},{})).map(([e,t])=>N.jsxs("div",{children:[N.jsx(Te,{children:e}),N.jsx("div",{style:{display:"flex",flexDirection:"column",gap:4,padding:"0 8px 8px 8px"},children:t.map(e=>N.jsx(De,{$active:e.id===m,onClick:()=>{e.href&&(e.href.startsWith("#")?J(e.href.slice(1)):window.location.href=e.href),null==b||b(e),D(!1)},children:e.label},e.id))})]},e))})]})})]})})})}}})}();
