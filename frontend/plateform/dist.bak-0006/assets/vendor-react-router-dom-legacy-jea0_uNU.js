System.register(["./vendor-react-legacy-Co-T2RJM.js","./vendor-react-dom-legacy-D3hIQ6uY.js","./vendor-react-router-legacy-Wt_wYA-G.js","./vendor-@remix-run/router-legacy-5HGmIVf4.js"],function(e,t){"use strict";var r,n,a,c,s,o,u;return{setters:[e=>{r=e.r,n=e.u},null,e=>{a=e.u,c=e.a,s=e.l,o=e.R},e=>{u=e.c}],execute:function(){
/**
       * React Router DOM v6.30.2
       *
       * Copyright (c) Remix Software Inc.
       *
       * This source code is licensed under the MIT license found in the
       * LICENSE.md file in the root directory of this source tree.
       *
       * @license MIT
       */
function t(e){return void 0===e&&(e=""),new URLSearchParams("string"==typeof e||Array.isArray(e)||e instanceof URLSearchParams?e:Object.keys(e).reduce((t,r)=>{let n=e[r];return t.concat(Array.isArray(n)?n.map(e=>[r,e]):[[r,n]])},[]))}e({B:function(e){let{basename:t,children:n,future:a,window:c}=e,l=r.useRef();null==l.current&&(l.current=u({window:c,v5Compat:!0}));let f=l.current,[h,m]=r.useState({action:f.action,location:f.location}),{v7_startTransition:y}=a||{},S=r.useCallback(e=>{y&&i?i(()=>m(e)):m(e)},[m,y]);return r.useLayoutEffect(()=>f.listen(S),[f,S]),r.useEffect(()=>s(a),[a]),r.createElement(o,{basename:t,children:n,location:h.location,navigationType:h.action,navigator:f,future:a})},u:function(e){let n=r.useRef(t(e)),s=r.useRef(!1),o=a(),u=r.useMemo(()=>function(e,r){let n=t(e);return r&&r.forEach((e,t)=>{n.has(t)||r.getAll(t).forEach(e=>{n.append(t,e)})}),n}(o.search,s.current?null:n.current),[o.search]),i=c(),l=r.useCallback((e,r)=>{const n=t("function"==typeof e?e(u):e);s.current=!0,i("?"+n,r)},[i,u]);return[u,l]}});try{window.__reactRouterVersion="6"}catch(y){}const i=n.startTransition;var l,f,h,m;(f=l||(l={})).UseScrollRestoration="useScrollRestoration",f.UseSubmit="useSubmit",f.UseSubmitFetcher="useSubmitFetcher",f.UseFetcher="useFetcher",f.useViewTransitionState="useViewTransitionState",(m=h||(h={})).UseFetcher="useFetcher",m.UseFetchers="useFetchers",m.UseScrollRestoration="useScrollRestoration"}}});
