import { Text } from 'slate';
import { Children } from 'react';
import { deserializeHtml, deserializeMd } from '@udecode/plate';

const traverseTree = (tree: any[], editor) => {
  function traverseTreeNode(node) {
    if (node.children && node.children.length > 0 && node.type === 'p' && !node.isPass) {
      let deleteA: number[] = [];
      node.children.forEach((child, index) => {
        if (child.text) {
          const res = deserializeMd(editor, child.text);
          node.children[index] = res[0];
          delete child.text;
          child.isPass = true;
        }
        traverseTreeNode(child); // 递归遍历子节点
      });
      node.children = node.children.filter((item, index) => {
        return !deleteA.includes(index);
      });
    }
  }

  // 从根节点开始遍历整个树
  tree.forEach((node) => {
    traverseTreeNode(node);
  });
};

export const insertInfo = (text: string = '', editor) => {
  if (!text) return;
  let parsed: any = deserializeHtml(editor, { collapseWhiteSpace: false, element: text });

  editor.insertNode({
    type: 'p',
    children: parsed,
  });
};
