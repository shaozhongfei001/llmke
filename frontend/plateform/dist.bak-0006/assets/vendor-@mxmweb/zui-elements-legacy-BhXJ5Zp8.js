!function(){let e,t,o,r,n=e=>e;System.register(["../vendor-react-legacy-Co-T2RJM.js","../vendor-styled-components-legacy-DULKPiI_.js","./zui-theme-legacy-m3iNS6o2.js","../vendor-react-dom-legacy-D3hIQ6uY.js"],function(i,s){"use strict";var l,a,d,c,u,p,m,h;return{setters:[e=>{l=e.j,a=e.r,d=e.t},e=>{c=e.d},e=>{u=e.c,p=e.h,m=e.i},e=>{h=e.r}],execute:function(){const s=c.button.attrs({className:"zui-button"})(e||(e=n`
  height: 36px;
  min-height: 36px;
  max-height: 36px;
  line-height: 34px;
  padding: 0 12px;
  border-radius: ${0};
  font-size: ${0};
  border: none;
  cursor: ${0};
  transition: all 0.2s;
  opacity: ${0};
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  position: relative;
  background: ${0};
  color: ${0};
  border: ${0};
  box-shadow: none;

  /* Loading 状态样式 */
  ${0}

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`),e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.space)?void 0:o.radius)||"4px"},e=>{var t,o,r,n,i,s;return e.$fontSize||(null==(r=null==(o=null==(t=e.$theme)?void 0:t.fonts)?void 0:o.sm)?void 0:r.size)||(null==(s=null==(i=null==(n=e.$theme)?void 0:n.fonts)?void 0:i.body)?void 0:s.size)||"12px"},e=>e.$disabled||e.$loading?"not-allowed":"pointer",e=>e.$disabled?.5:1,({$btnType:e,$theme:t})=>{var o,r,n;return"text"===e?"none":"primary"===e?(null==(o=null==t?void 0:t.colors)?void 0:o.primary)||"#007bff":"error"===e?(null==(r=null==t?void 0:t.colors)?void 0:r.error)||"#FF0000":"default"===e?(null==(n=null==t?void 0:t.colors)?void 0:n.background)||"#f8f9fa":"none"},({$btnType:e,$theme:t})=>{var o,r;return"text"===e?(null==(o=null==t?void 0:t.colors)?void 0:o.primary)||"#007bff":"primary"===e||"error"===e?"#ffffff":(null==(r=null==t?void 0:t.colors)?void 0:r.text)||"#343a40"},({$btnType:e,$theme:t})=>{var o;return"default"===e?`1px solid ${(null==(o=null==t?void 0:t.colors)?void 0:o.border)||"#dee2e6"}`:"none"},e=>e.$loading&&"\n    pointer-events: none;\n    opacity: 0.8;\n\n    .button-loading {\n      width: 14px;\n      height: 14px;\n      border: 2px solid transparent;\n      border-top: 2px solid currentColor;\n      border-radius: 50%;\n      animation: spin 1s linear infinite;\n      margin-right: 6px;\n    }\n  "),f=i("J",({mode:e="default",size:t="md",label:o,icon:r,disabled:n=!1,loading:i=!1,onClick:a,styles:d,style:c,className:h,children:f,...b})=>{var g,x,v,y,$,w;const k=u(),j=p(p({theme:m,mode:"light"},k),d).theme||m,z=t&&null!=(x=null==(g=null==j?void 0:j.fonts)?void 0:g[t])&&x.size?j.fonts[t].size:(null==(y=null==(v=null==j?void 0:j.fonts)?void 0:v.sm)?void 0:y.size)||(null==(w=null==($=null==j?void 0:j.fonts)?void 0:$.body)?void 0:w.size)||"12px";return l.jsxs(s,{$btnType:e,$disabled:n,$loading:i,$theme:j,$fontSize:z,onClick:()=>{!n&&!i&&a&&a()},disabled:n||i,style:c,className:h,...b,children:[i&&l.jsx("span",{className:"button-loading"}),r&&l.jsx("span",{className:"button-icon",style:{marginRight:4},children:r}),o&&l.jsx("span",{className:"button-label",children:o}),f]})}),b=e=>e.replace(/([a-z0-9])([A-Z])/g,"$1-$2").toLowerCase(),g=(...e)=>e.filter((e,t,o)=>!!e&&""!==e.trim()&&o.indexOf(e)===t).join(" ").trim();
/**
       * @license lucide-react v0.456.0 - ISC
       *
       * This source code is licensed under the ISC license.
       * See the LICENSE file in the root directory of this source tree.
       */
/**
       * @license lucide-react v0.456.0 - ISC
       *
       * This source code is licensed under the ISC license.
       * See the LICENSE file in the root directory of this source tree.
       */
var x={xmlns:"http://www.w3.org/2000/svg",width:24,height:24,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor",strokeWidth:2,strokeLinecap:"round",strokeLinejoin:"round"};
/**
       * @license lucide-react v0.456.0 - ISC
       *
       * This source code is licensed under the ISC license.
       * See the LICENSE file in the root directory of this source tree.
       */const v=a.forwardRef(({color:e="currentColor",size:t=24,strokeWidth:o=2,absoluteStrokeWidth:r,className:n="",children:i,iconNode:s,...l},d)=>a.createElement("svg",{ref:d,...x,width:t,height:t,stroke:e,strokeWidth:r?24*Number(o)/Number(t):o,className:g("lucide",n),...l},[...s.map(([e,t])=>a.createElement(e,t)),...Array.isArray(i)?i:[i]])),y=(e,t)=>{const o=a.forwardRef(({className:o,...r},n)=>a.createElement(v,{ref:n,iconNode:t,className:g(`lucide-${b(e)}`,o),...r}));return o.displayName=`${e}`,o},$=y("ChevronDown",[["path",{d:"m6 9 6 6 6-6",key:"qrunsl"}]]),w=y("Ellipsis",[["circle",{cx:"12",cy:"12",r:"1",key:"41hilf"}],["circle",{cx:"19",cy:"12",r:"1",key:"1wjl8i"}],["circle",{cx:"5",cy:"12",r:"1",key:"1pcz8c"}]]),k=c.div(t||(t=n`
  position: fixed;
  background: ${0};
  border: 1px solid ${0};
  border-radius: ${0};
  box-shadow: ${0};
  z-index: 9999;
  min-width: ${0};
  max-width: 300px;
  overflow: hidden;
  padding: 4px 0;
`),e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.colors)?void 0:o.background)||"#f8f9fa"},e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.colors)?void 0:o.border)||"#dee2e6"},e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.space)?void 0:o.radius)||"4px"},e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.colors)?void 0:o.shadow)||"0 1px 3px rgba(0, 0, 0, 0.12)"},e=>e.$buttonRect?`${e.$buttonRect.width}px`:"auto"),j=c.div(o||(o=n`
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: ${0};
  background: transparent;
  transition: background-color 0.2s;

  &:hover {
    background: ${0};
  }

  &:first-child {
    border-top-left-radius: ${0};
    border-top-right-radius: ${0};
  }

  &:last-child {
    border-bottom-left-radius: ${0};
    border-bottom-right-radius: ${0};
  }
`),e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.colors)?void 0:o.text)||"#343a40"},e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.colors)?void 0:o.disabledBackground)||"#F5F5F5"},e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.space)?void 0:o.radius)||"4px"},e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.space)?void 0:o.radius)||"4px"},e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.space)?void 0:o.radius)||"4px"},e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.space)?void 0:o.radius)||"4px"}),z=c.div(r||(r=n`
  height: 1px;
  background: ${0};
  margin: 4px 0;
`),e=>{var t,o;return(null==(o=null==(t=e.$theme)?void 0:t.colors)?void 0:o.border)||"#dee2e6"});
/**
       * @license lucide-react v0.456.0 - ISC
       *
       * This source code is licensed under the ISC license.
       * See the LICENSE file in the root directory of this source tree.
       */if(i({s:({mode:e="default",label:t="选择选项",actions:o,styles:r,icon:n,disabled:i=!1,style:s,className:d,children:c,eventEmit:b,...g})=>{const[x,v]=a.useState(!1),y=a.useRef(null),[w,S]=a.useState(null),[N,C]=a.useState({top:0,left:0}),E=u(),L=p(p({theme:m,mode:"light"},E),r);a.useEffect(()=>{console.log("[DropDownButton] 组件挂载，eventEmit:",b),console.log("[DropDownButton] actions:",o)},[b,o]);a.useEffect(()=>{if(!x)return;const e=e=>{y.current&&!y.current.contains(e.target)&&v(!1)},t=()=>v(!1),o=()=>v(!1);return document.addEventListener("mousedown",e),window.addEventListener("scroll",t,!0),window.addEventListener("resize",o),()=>{document.removeEventListener("mousedown",e),window.removeEventListener("scroll",t,!0),window.removeEventListener("resize",o)}},[x]);return l.jsxs("div",{ref:y,style:{position:"relative",display:"inline-block"},className:d,children:[l.jsxs(f,{mode:e,label:t,icon:n,disabled:i,onClick:()=>{i||(x||(()=>{if(!y.current)return;const e=y.current.getBoundingClientRect();S(e);const t=e.bottom+4,o=e.left;C({top:t,left:o})})(),v(!x))},styles:r,style:s,...g,children:[c,l.jsx($,{size:14,style:{marginLeft:4,transition:"transform 0.2s",transform:x?"rotate(180deg)":"rotate(0deg)"}})]}),x&&h.createPortal(x&&w?l.jsx(k,{$theme:L.theme||m,$buttonRect:w,style:{top:N.top,left:N.left},children:o.map((e,t)=>"divider"===e.type?l.jsx(z,{$theme:L.theme||m},e.key||`divider-${t}`):l.jsxs(j,{$theme:L.theme||m,onMouseDown:t=>{t.preventDefault(),t.stopPropagation(),(e=>{b&&b("dropdown_action",{key:e}),v(!1)})(e.key),e.onClick&&e.onClick()},children:[e.icon&&l.jsx("span",{className:"mr-2",children:e.icon}),e.component||e.label]},e.key||`action-${t}`))}):null,document.body)]})},i:({actions:e,onAction:t,direction:o="top",styles:r})=>{const[n,i]=a.useState(!1),s=a.useRef(null),[d,c]=a.useState({}),f=a.useRef(null);a.useEffect(()=>{if(!n)return;const t=s.current;if(!t)return;const r=t.getBoundingClientRect(),i=window.scrollX||window.pageXOffset,l=window.scrollY||window.pageYOffset;let a={position:"absolute",left:r.right-128+i,width:128,zIndex:9999};if("bottom"===o)a.top=r.bottom+8-12+l;else{const t=30*e.length+1;a.top=r.top-8+10-t+l}c(a)},[n,o,e]),a.useEffect(()=>{if(!n)return;const e=e=>{s.current&&s.current.contains(e.target)||f.current&&f.current.contains(e.target)||i(!1)},t=()=>i(!1);return document.addEventListener("mousedown",e),window.addEventListener("scroll",t,!0),()=>{document.removeEventListener("mousedown",e),window.removeEventListener("scroll",t,!0)}},[n]);const b=u(),g=p(p({theme:m,mode:"light"},b),r),x=l.jsx("div",{ref:f,className:`origin-bottom-right absolute right-0 w-32 rounded-md shadow-lg focus:outline-none border transition-all duration-200 ease-in-out\n        ${n?"opacity-100 translate-y-0 pointer-events-auto scale-100":"opacity-0 pointer-events-none scale-95"}\n      `,style:{...d,background:g.theme.colors.background,color:g.theme.colors.text,border:`1px solid ${g.theme.colors.border}`,borderRadius:g.theme.space.radius,boxShadow:g.theme.colors.shadow,minWidth:128,zIndex:9999},children:l.jsx("div",{className:"py-1 px-2",children:e.map((e,o)=>"divider"===e.type?l.jsx("div",{className:"my-2 bg-gray-100",style:{height:1}},e.key||`divider-${o}`):l.jsxs("button",{className:"w-full rounded flex cursor-pointer items-center px-4 py-2 text-sm transition whitespace-nowrap",style:{color:g.theme.colors.text,background:"transparent",border:"none",fontSize:12},onClick:o=>{o.stopPropagation(),i(!1),t(e.key),e.onClick&&e.onClick()},type:"button",onMouseOver:e=>e.currentTarget.style.background=g.theme.colors.disabledBackground,onMouseOut:e=>e.currentTarget.style.background="transparent",children:[e.icon&&l.jsx("span",{className:"mr-2",children:e.icon}),e.label]},e.key||`action-${o}`))})});return l.jsxs(l.Fragment,{children:[l.jsx("button",{ref:s,className:"card-action-more-btn cursor-pointer! flex items-center justify-center w-9 h-9 rounded-sm transition border-none outline-none",style:{background:"transparent",color:g.theme.colors.primary,borderRadius:g.theme.space.radius},onClick:e=>{e.stopPropagation(),i(e=>!e)},tabIndex:0,"aria-label":"更多操作",type:"button",children:l.jsx(w,{size:18,className:"text-blue-500"})}),n&&h.createPortal(x,document.body)]})}}),typeof window<"u"&&!document.getElementById("card-action-more-btn-style")){const e=document.createElement("style");e.id="card-action-more-btn-style",e.innerHTML="\n    .card-action-more-btn:hover {\n      background: #f5f6fa !important;\n      color: #222 !important;\n      box-shadow: 0 2px 8px 0 rgba(51,112,255,0.06);\n    }\n  ",document.head.appendChild(e)}i("l",({current:e,pageSize:t,total:o,onChange:r,showSizeChanger:n=!0,pageSizeOptions:i=[6,12,24,48],onPageSizeChange:s,theme:a,size:c="md",showPageNumbers:u=!0})=>{const p=Math.ceil(o/t);if(p<=1&&!n)return null;const m={colors:{background:"#ffffff",text:"#1f2937",border:"#d9d9d9",disabledBackground:"#f5f5f5",primary:"#1677ff"},space:{radius:"6px"},...a},h=(()=>{const t=[],o=[];for(let r=Math.max(2,e-2);r<=Math.min(p-1,e+2);r++)t.push(r);return e-2>2?o.push(1,"..."):o.push(1),o.push(...t),e+2<p-1?o.push("...",p):p>1&&o.push(p),o})(),f="sm"===c?{height:24,minWidth:24,fontSize:12,paddingX:8}:{height:28,minWidth:28,fontSize:12,paddingX:8},[b,g]=d.useState(""),x=()=>{if(!b||""===b.trim())return;const t=parseInt(b,10);if(Number.isNaN(t))return;const o=Math.max(1,Math.min(p,t));o!==e&&r(o),g(String(o))},v={background:m.colors.background,color:m.colors.text,border:"1px solid transparent",borderRadius:m.space.radius,height:f.height,minWidth:f.minWidth,padding:`0 ${f.paddingX}px`,fontSize:f.fontSize,lineHeight:`${f.height}px`},y={...v,border:`1px solid ${m.colors.primary}`,color:m.colors.primary},$={background:"transparent",color:m.colors.text,border:"none",height:f.height,minWidth:f.minWidth,padding:`0 ${f.paddingX}px`,fontSize:f.fontSize,lineHeight:`${f.height}px`,borderRadius:m.space.radius};return l.jsxs("div",{style:{gap:"10px"},className:"flex items-center justify-center select-none",children:[n&&l.jsxs("div",{style:{gap:"6px"},className:"flex items-center ] mr-3",children:[l.jsx("span",{style:{fontSize:f.fontSize,color:m.colors.text},children:"每页"}),l.jsx("select",{value:t,onChange:e=>s&&s(parseInt(e.target.value,10)),style:{height:f.height,border:`1px solid ${m.colors.border}`,borderRadius:m.space.radius,padding:`0 ${f.paddingX}px`,background:m.colors.background,color:m.colors.text,fontSize:f.fontSize},"aria-label":"每页条数",children:i.map(e=>l.jsx("option",{value:e,children:e},e))}),l.jsx("span",{style:{fontSize:f.fontSize,color:m.colors.text},children:"条"})]}),l.jsx("button",{disabled:1===e,onClick:()=>r(e-1),className:"flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-200",style:$,onMouseEnter:t=>{1!==e&&(t.currentTarget.style.color=m.colors.primary)},onMouseLeave:t=>{t.currentTarget.style.color=1===e?"#bfbfbf":m.colors.text},"aria-label":"上一页",children:l.jsx("svg",{width:f.fontSize+4,height:f.fontSize+4,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor",strokeWidth:"2",strokeLinecap:"round",strokeLinejoin:"round",style:{color:1===e?"#bfbfbf":void 0},children:l.jsx("polyline",{points:"15,18 9,12 15,6"})})}),u&&h.map((t,o)=>{if("..."===t)return l.jsx("span",{style:{...v,color:"#bfbfbf"},children:"..."},`ellipsis-${o}`);const n=t===e;return l.jsx("button",{onClick:()=>r(t),className:"flex items-center justify-center transition-all duration-150",style:n?y:v,onMouseEnter:e=>{n||(e.currentTarget.style.borderColor=m.colors.primary,e.currentTarget.style.color=m.colors.primary)},onMouseLeave:e=>{n||(e.currentTarget.style.borderColor="transparent",e.currentTarget.style.color=m.colors.text)},"aria-label":`第 ${t} 页`,"aria-current":n?"page":void 0,children:t},t)}),l.jsx("button",{disabled:e===p,onClick:()=>r(e+1),className:"flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-200",style:$,onMouseEnter:t=>{e!==p&&(t.currentTarget.style.color=m.colors.primary)},onMouseLeave:t=>{t.currentTarget.style.color=e===p?"#bfbfbf":m.colors.text},"aria-label":"下一页",children:l.jsx("svg",{width:f.fontSize+4,height:f.fontSize+4,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor",strokeWidth:"2",strokeLinecap:"round",strokeLinejoin:"round",style:{color:e===p?"#bfbfbf":void 0},children:l.jsx("polyline",{points:"9,18 15,12 9,6"})})}),l.jsxs("div",{style:{gap:"6px"},className:"flex items-center  ml-4",children:[l.jsx("span",{style:{fontSize:f.fontSize,color:m.colors.text},children:"前往"}),l.jsx("input",{type:"number",inputMode:"numeric",min:1,max:p,value:b,onChange:e=>g(e.target.value),onKeyDown:e=>{"Enter"===e.key&&(e.preventDefault(),x())},onBlur:()=>x(),style:{height:f.height,width:"sm"===c?48:64,border:`1px solid ${m.colors.border}`,borderRadius:m.space.radius,padding:`0 ${f.paddingX}px`,background:m.colors.background,color:m.colors.text,fontSize:f.fontSize},"aria-label":"跳转页码输入"}),l.jsx("span",{style:{fontSize:f.fontSize,color:m.colors.text},children:"页"})]})]})})}}})}();
