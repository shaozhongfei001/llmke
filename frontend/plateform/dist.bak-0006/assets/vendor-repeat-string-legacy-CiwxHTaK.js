System.register([],function(r,e){"use strict";return{execute:function(){
/*!
       * repeat-string <https://github.com/jonschlinkert/repeat-string>
       *
       * Copyright (c) 2014-2015, Jon Schlinkert.
       * Licensed under the MIT License.
       */
var e,t="";r("r",function(r,n){if("string"!=typeof r)throw new TypeError("expected a string");if(1===n)return r;if(2===n)return r+r;var i=r.length*n;if(e!==r||void 0===e)e=r,t="";else if(t.length>=i)return t.substr(0,i);for(;i>t.length&&n>1;)1&n&&(t+=r),n>>=1,r+=r;return t=(t+=r).substr(0,i)})}}});
