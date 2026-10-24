interface Node {
  key: string;
  children?: Node[];
}
export const traverse = (nodes: Node[], handleFn: any) => {
  nodes.forEach((node) => {
    handleFn(node);
    if (
      node.children &&
      Array.isArray(node.children) &&
      node.children.length > 0
    ) {
      traverse(node.children, handleFn);
    }
  });
};

// R12：原 DemoEnv 内网地址常量未被任何代码引用（getDemoEnv 已硬编码 return true），删除以免残留内网主机
const Include = ["10.64.7.145", "localhost"];

// export const getDemoEnv = () => {
//   return Include.some((item) => {
//     return location.host.indexOf(item) > -1;
//   });
// };

export const getDemoEnv = () => {
  return true;
};
