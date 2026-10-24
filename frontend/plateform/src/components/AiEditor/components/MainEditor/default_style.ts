import { text } from "mermaid/dist/rendering-util/rendering-elements/shapes/text.js";

const commonStyle = {
  fontSize: "16pt", // 字体大小
  lineHeight: "24pt", // 行间距
  letterSpacing: "0.96px", // 字间距
  color: "#222", // 字色
  fontFamily: "仿宋",
  textIndent: "32pt"
};

export const defaultStyle = {
  /*=========默认样式=========*/
  heading: {
    h1: {
      fontSize: "35pt", // 字体大小
      fontFamily: "华文楷体",
      textAlign: "center",
      textIndent: "0pt",
      fontWeight: "bold"
    },
    h2: {
      fontSize: "16pt",
      fontFamily: "华文楷体",
      fontWeight: "bold"
    },
    h3: {
      fontSize: "16pt",
      fontFamily: "华文楷体",
      fontWeight: "bold"
    },
    h4: {
      fontSize: "16pt",
      fontFamily: "华文楷体",
      fontWeight: "bold"
    },
    h5: commonStyle,
    h6: {
      ...commonStyle,
      fontSize: "14pt"
    },
    h7: {
      ...commonStyle,
      fontSize: "14pt"
    }
    // 可以继续为 h4, h5 设置样式
  },
  p: commonStyle,
  list: {
    fontSize: "21.3px", // 字体大小
    lineHeight: "28px", // 行间距
    letterSpacing: "0.96px", // 字间距
    color: "#222", // 字色
    fontFamily: "仿宋",
    listStyle: "none"
  },
  table: { fontSize: "10.5pt", textIndent: "0pt" },
  /**=========自定义样式======== */
  customStyle: {
    "custom-h1": {
      fontFamily: "黑体",
      fontSize: "21.3px",
      lineHeight: "28px"
    },
    "custom-h2": {
      fontFamily: "楷体",
      fontSize: "21.3px",
      lineHeight: "28px"
    },
    "custom-h3": {
      fontFamily: "仿宋",
      fontSize: "21.3px",
      lineHeight: "28px"
    },
    "custom-h4": {
      fontFamily: "仿宋",
      fontSize: "21.3px",
      lineHeight: "28px"
    }
  }
};

// 内蒙古银行
// export const defaultStyle = {
//   /*=========默认样式=========*/
//   heading: {
//     h1: {
//       fontSize: "22pt", // 字体大小
//       lineHeight: "30pt", // 行间距
//       fontFamily: "方正小标宋简体",
//       textAlign: "center",
//       textIndent: "0pt"
//     },
//     h2: {
//       fontSize: "16pt",
//       lineHeight: "2",
//       fontFamily: "黑体",
//       fontWeight: "bold"
//     },
//     h3: {
//       fontSize: "16pt",
//       lineHeight: "2",
//       fontFamily: "华文楷体",
//       fontWeight: "normal"
//     },
//     h4: {
//       fontSize: "16pt",
//       lineHeight: "2",
//       fontFamily: "华文楷体",
//       fontWeight: "normal"
//     },
//     h5: {
//       fontSize: "16pt", // 字体大小
//       lineHeight: "24pt", // 行间距
//       fontFamily: "仿宋",
//       textIndent: "32pt",
//       fontWeight: "normal"
//     },
//     h6: {
//       fontSize: "16pt", // 字体大小
//       lineHeight: "24pt", // 行间距
//       fontFamily: "仿宋",
//       textIndent: "32pt",
//       fontWeight: "normal"
//     }
//     // 可以继续为 h4, h5, h6 设置样式
//   },
//   p: {
//     fontSize: "16pt", // 字体大小
//     lineHeight: "24pt", // 行间距
//     fontFamily: "仿宋",
//     textIndent: "32pt"
//   },
//   list: {
//     fontSize: "16pt", // 字体大小
//     lineHeight: "24pt", // 行间距
//     fontFamily: "仿宋",
//     textIndent: "32pt",
//     listStyle: "none"
//   },
//   table: { fontSize: "10.5pt", textIndent: "0pt", fontFamily: "仿宋" },
//   /**=========自定义样式======== */
//   customStyle: {
//     "form-item": {
//       marginLeft: "40pt",
//       fontFamily: "方正小标宋简体",
//       fontSize: "18pt"
//     }
//   }
// };

export const redTitleStyle = {
  heading: {
    // 红色的标题
    h1: {
      width: "144%",
      transform: "scaleX(0.7)",
      position: "relative",
      left: "-21.5%",
      fontSize: "45pt", // 字体大小
      lineHeight: "1.1", // 行间距
      letterSpacing: "-3px", // 字间距
      color: "red", // 字色
      fontFamily: "方正小标宋简体",
      fontWeight: "normal",
      textAlign: "center"
    },
    // 黑色的标题
    h2: {
      fontSize: "29px", // 字体大小
      fontFamily: "宋体",
      textAlign: "center",
      lineHeight: "21pt", // 行间距
      margin: "16pt 0 0 0"
    },
    // 发文字号，居中
    h3: {
      fontSize: "16pt", // 字体大小
      letterSpacing: "0.64px", // 字间距
      fontFamily: "仿宋",
      textAlign: "center",
      fontWeight: "normal",
      lineHeight: "16pt" // 行间距
    },
    // 发文机关，发文时间，右对齐
    h4: {
      fontSize: "16pt", // 字体大小
      letterSpacing: "0.64px", // 字间距
      fontFamily: "仿宋",
      textAlign: "right",
      fontWeight: "normal",
      lineHeight: "32px", // 行间距
      marginTop: "14px",
      marginBottom: "14px"
    },
    // 主送机关左对齐
    h5: {
      fontSize: "16pt", // 字体大小
      letterSpacing: "0.64px", // 字间距
      fontFamily: "仿宋",
      textAlign: "left",
      fontWeight: "normal",
      lineHeight: "32px", // 行间距
      marginTop: "20px",
      marginBottom: "20px"
    }
  },
  p: {
    fontSize: "16pt", // 字体大小
    lineHeight: "24pt", // 行间距
    letterSpacing: "0.96px", // 字间距
    color: "#222", // 字色
    fontFamily: "仿宋",
    textIndent: "32pt"
  },
  list: {
    fontSize: "21.3px", // 字体大小
    lineHeight: "28px", // 行间距
    letterSpacing: "0.96px", // 字间距
    color: "#222", // 字色
    fontFamily: "仿宋",
    textIndent: "32pt",
    listStyle: "none"
  },
  /**=========自定义样式======== */
  customStyle: {
    "custom-h1": {
      fontFamily: "黑体",
      fontSize: "16pt",
      lineHeight: "30pt"
    },
    "custom-h2": {
      fontFamily: "楷体",
      fontSize: "16pt",
      lineHeight: "30pt"
    },
    "custom-h3": {
      fontFamily: "仿宋",
      fontSize: "16pt",
      lineHeight: "30pt"
    },
    "custom-h4": {
      fontFamily: "仿宋",
      fontSize: "16pt",
      lineHeight: "30pt"
    }
  }
};
