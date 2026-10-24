import { createPlatePlugin } from "@udecode/plate/react";

const detectLinkEle = createPlatePlugin({
  key: "p",
  extendEditor: ({ editor }) => {
    const { normalizeNode } = editor;
    // const d = string(editor as any, [0], {})
    // console.log(d)
    return editor;
  }
});

export { detectLinkEle };
