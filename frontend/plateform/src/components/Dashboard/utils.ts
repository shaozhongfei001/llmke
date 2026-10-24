export const traverse = (nodes, handleFn) => {
  nodes.forEach((node) => {
    handleFn(node);
    if (node.children && Array.isArray(node.children) && node.children.length > 0) {
      traverse(node.children, handleFn);
    }
  });
};
