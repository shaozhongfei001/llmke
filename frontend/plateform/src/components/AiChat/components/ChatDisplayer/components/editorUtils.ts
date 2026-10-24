import { deserializeHtml, deserializeMd } from "@udecode/plate";

const traverseTree = (tree: any[], editor: any) => {
  function traverseTreeNode(node: any) {
    if (
      node.children &&
      node.children.length > 0 &&
      node.type === "p" &&
      !node.isPass
    ) {
      const deleteA: number[] = [];
      node.children.forEach((child: any, index: any) => {
        if (child.text) {
          const res = deserializeMd(editor, child.text);
          node.children[index] = res[0];
          delete child.text;
          child.isPass = true;
        }
        traverseTreeNode(child); // 递归遍历子节点
      });
      node.children = node.children.filter((item: any, index: any) => {
        return !deleteA.includes(index);
      });
    }
  }

  // 从根节点开始遍历整个树
  tree.forEach((node) => {
    traverseTreeNode(node);
  });
};

export const insertInfo = (text: string = "", editor: any) => {
  if (!text) return;
  const parsed: any = deserializeHtml(editor, {
    collapseWhiteSpace: false,
    element: text
  });

  editor.insertNode({
    type: "p",
    children: parsed
  });
};
