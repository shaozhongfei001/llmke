export const traversalTree = (
  tree: any[],
  cb: (node: any) => any,
  key: string = "children"
) => {
  tree.forEach((node: any) => {
    cb(node);
    if (node[key]) {
      traversalTree(node[key], cb, key);
    }
  });
};

// 定义树节点的类型
interface TreeNode {
  customId: string;
  children?: TreeNode[];
}

// 定义函数：遍历树并添加children
export const addChildrenToNode = (
  tree: TreeNode[],
  targetId: string,
  newChildren: TreeNode[]
): any[] => {
  // 递归函数：深度优先遍历树
  function traverse(node: TreeNode): TreeNode {
    // 如果当前节点的id匹配目标id，为其添加children

    if (node.customId === targetId) {
      node.children = newChildren;
      return node;
    }

    // 如果当前节点有子节点，递归处理每个子节点
    if (node.children) {
      node.children = node.children.map((child) => traverse(child));
    }

    return node;
  }

  // 遍历树的根节点数组
  return tree.map((node) => traverse(node));
};
