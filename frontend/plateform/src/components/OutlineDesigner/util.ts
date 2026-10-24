import { OutlineData } from './@types';
import { ItemInfo } from './type';

// 获得当前node在tree里面的深度和所在层级的位置以及当前层级是否只有自己，用于渲染样式
export const getItemInfo = (id: string | number, tree: OutlineData[]): ItemInfo => {
  function findInfo(currentNodes, targetId, depth = 0) {
    for (const node of currentNodes) {
      if (node.id === targetId) {
        let location = 'center';
        if (targetId === currentNodes[0].id) {
          location = 'top';
        } else {
          if (targetId === currentNodes[currentNodes.length - 1].id) location = 'bottom';
        }
        // 找到目标节点，返回当前深度
        return { depth, location, onlyOne: currentNodes.length === 1 };
      }
      if (node.children && node.children.length > 0) {
        // 递归检查子节点
        const childInfo = findInfo(node.children, targetId, depth + 1);
        if (childInfo.depth !== -1) {
          // 如果在子节点中找到了目标节点，则返回其深度
          return childInfo;
        }
      }
    }
    return {
      depth: -1,
      location: 'center',
      onlyOne: true,
    };
  }
  return findInfo(tree, id);
};

export const isChildren = (tree, id) => {
  if (!tree.children) return false;
  return tree.children.some((node) => {
    if (node.id === id) return true;
    return isChildren(node, id);
  });
};
