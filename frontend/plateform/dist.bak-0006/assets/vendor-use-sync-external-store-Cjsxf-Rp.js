import{c as j}from"./vendor-@ant-design/colors-CwZCmT9p.js";import{r as V}from"./vendor-react-Bfz093Ih.js";var w={exports:{}},p={};/**
 * @license React
 * use-sync-external-store-shim.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var v=V;function z(e,r){return e===r&&(e!==0||1/e===1/r)||e!==e&&r!==r}var M=typeof Object.is=="function"?Object.is:z,O=v.useState,I=v.useEffect,_=v.useLayoutEffect,G=v.useDebugValue;function W(e,r){var o=r(),c=O({inst:{value:o,getSnapshot:r}}),u=c[0].inst,n=c[1];return _(function(){u.value=o,u.getSnapshot=r,b(u)&&n({inst:u})},[e,o,r]),I(function(){return b(u)&&n({inst:u}),e(function(){b(u)&&n({inst:u})})},[e]),G(o),o}function b(e){var r=e.getSnapshot;e=e.value;try{var o=r();return!M(e,o)}catch(c){return!0}}function g(e,r){return r()}var x=typeof window>"u"||typeof window.document>"u"||typeof window.document.createElement>"u"?g:W;p.useSyncExternalStore=v.useSyncExternalStore!==void 0?v.useSyncExternalStore:x;w.exports=p;var R=w.exports;const re=j(R);var D={exports:{}},h={};/**
 * @license React
 * use-sync-external-store-shim/with-selector.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var y=V,C=R;function L(e,r){return e===r&&(e!==0||1/e===1/r)||e!==e&&r!==r}var k=typeof Object.is=="function"?Object.is:L,F=C.useSyncExternalStore,U=y.useRef,A=y.useEffect,B=y.useMemo,H=y.useDebugValue;h.useSyncExternalStoreWithSelector=function(e,r,o,c,u){var n=U(null);if(n.current===null){var a={hasValue:!1,value:null};n.current=a}else a=n.current;n=B(function(){function m(t){if(!d){if(d=!0,l=t,t=c(t),u!==void 0&&a.hasValue){var f=a.value;if(u(f,t))return s=f}return s=t}if(f=s,k(l,t))return f;var $=c(t);return u!==void 0&&u(f,$)?(l=t,f):(l=t,s=$)}var d=!1,l,s,E=o===void 0?null:o;return[function(){return m(r())},E===null?void 0:function(){return m(E())}]},[r,o,c,u]);var i=F(e,n[0],n[1]);return A(function(){a.hasValue=!0,a.value=i},[i]),H(i),i};D.exports=h;var J=D.exports;const ue=j(J);var K={};/**
 * @license React
 * use-sync-external-store-with-selector.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var S=V;function N(e,r){return e===r&&(e!==0||1/e===1/r)||e!==e&&r!==r}var P=typeof Object.is=="function"?Object.is:N,Q=S.useSyncExternalStore,T=S.useRef,X=S.useEffect,Y=S.useMemo,Z=S.useDebugValue;K.useSyncExternalStoreWithSelector=function(e,r,o,c,u){var n=T(null);if(n.current===null){var a={hasValue:!1,value:null};n.current=a}else a=n.current;n=Y(function(){function m(t){if(!d){if(d=!0,l=t,t=c(t),u!==void 0&&a.hasValue){var f=a.value;if(u(f,t))return s=f}return s=t}if(f=s,P(l,t))return f;var $=c(t);return u!==void 0&&u(f,$)?(l=t,f):(l=t,s=$)}var d=!1,l,s,E=o===void 0?null:o;return[function(){return m(r())},E===null?void 0:function(){return m(E())}]},[r,o,c,u]);var i=Q(e,n[0],n[1]);return X(function(){a.hasValue=!0,a.value=i},[i]),Z(i),i};export{ue as a,R as s,re as u,J as w};
