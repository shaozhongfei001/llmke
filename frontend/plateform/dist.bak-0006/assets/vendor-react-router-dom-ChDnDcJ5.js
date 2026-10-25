import{r as s,u as w}from"./vendor-react-Bfz093Ih.js";import"./vendor-react-dom-CjqO5MCD.js";import{u as T,a as v,l as U,R as g}from"./vendor-react-router-DZj_5xeJ.js";import{c as y}from"./vendor-@remix-run/router-G1b6SE1w.js";/**
 * React Router DOM v6.30.2
 *
 * Copyright (c) Remix Software Inc.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE.md file in the root directory of this source tree.
 *
 * @license MIT
 */function f(e){return e===void 0&&(e=""),new URLSearchParams(typeof e=="string"||Array.isArray(e)||e instanceof URLSearchParams?e:Object.keys(e).reduce((c,r)=>{let t=e[r];return c.concat(Array.isArray(t)?t.map(a=>[r,a]):[[r,t]])},[]))}function E(e,c){let r=f(e);return c&&c.forEach((t,a)=>{r.has(a)||c.getAll(a).forEach(o=>{r.append(a,o)})}),r}const F="6";try{window.__reactRouterVersion=F}catch(e){}const P="startTransition",S=w[P];function L(e){let{basename:c,children:r,future:t,window:a}=e,o=s.useRef();o.current==null&&(o.current=y({window:a,v5Compat:!0}));let n=o.current,[u,i]=s.useState({action:n.action,location:n.location}),{v7_startTransition:l}=t||{},h=s.useCallback(m=>{l&&S?S(()=>i(m)):i(m)},[i,l]);return s.useLayoutEffect(()=>n.listen(h),[n,h]),s.useEffect(()=>U(t),[t]),s.createElement(g,{basename:c,children:r,location:u.location,navigationType:u.action,navigator:n,future:t})}var R;(function(e){e.UseScrollRestoration="useScrollRestoration",e.UseSubmit="useSubmit",e.UseSubmitFetcher="useSubmitFetcher",e.UseFetcher="useFetcher",e.useViewTransitionState="useViewTransitionState"})(R||(R={}));var p;(function(e){e.UseFetcher="useFetcher",e.UseFetchers="useFetchers",e.UseScrollRestoration="useScrollRestoration"})(p||(p={}));function V(e){let c=s.useRef(f(e)),r=s.useRef(!1),t=T(),a=s.useMemo(()=>E(t.search,r.current?null:c.current),[t.search]),o=v(),n=s.useCallback((u,i)=>{const l=f(typeof u=="function"?u(a):u);r.current=!0,o("?"+l,i)},[o,a]);return[a,n]}export{L as B,V as u};
