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

const DemoEnv = ["10.15.12.13:9009", "10.15.12.13:9005"];
const Include = ["10.64.7.145", "localhost"];

// export const getDemoEnv = () => {
//   return Include.some((item) => {
//     return location.host.indexOf(item) > -1;
//   });
// };

export const getDemoEnv = () => {
  return true;
};
