import type { DataNode, TreeProps } from "antd/es/tree";
import {
  IChapterTreeItem,
  IAnalysisCategoryTreeItem,
  ITreeNode
} from "./type.ts";
import { string } from "slate";

// 章节组件接口数据构造ITreeNode
export const sectionTreeConvertRender = (
  data: IChapterTreeItem[],
  level = 0
): ITreeNode[] => {
  return data.map((item) => {
    const newItem: ITreeNode = {
      key: item.id.toString(),
      title: item.sectionTitle,
      parentId: item.parentId.toString(),
      hasSectionPrompt: item.hasSectionPrompt,
      level
    };
    if (item.subSections) {
      newItem.children = sectionTreeConvertRender(item.subSections, level + 1);
    }
    return newItem;
  });
};

// 分析组件分类接口数据构造ITreeNode
export const analysisCategoryTreeConvertRender = (
  data: IAnalysisCategoryTreeItem[],
  level = 0
): ITreeNode[] => {
  return data.map((item) => {
    const newItem: ITreeNode = {
      key: item.id,
      title: item.categoryName,
      parentId: item.parentId,
      level
    };
    if (item.subCategories) {
      newItem.children = analysisCategoryTreeConvertRender(
        item.subCategories,
        level + 1
      );
    }
    return newItem;
  });
};

// 根据key查找节点
export const findNodeByKey = (key: string, tree: any): any => {
  for (const node of tree) {
    if (node.key === key) return node;
    if (node.children) {
      const found = findNodeByKey(key, node.children);
      if (found) return found;
    }
  }
  return null;
};

// 新增节点后更新树
export const updateTreeData = (
  list: ITreeNode[],
  parentKey: string,
  newNode: ITreeNode
): ITreeNode[] => {
  if (parentKey == "0") {
    return [...list, newNode];
  } else {
    return list.map((node) => {
      if (node.key === parentKey) {
        return {
          ...node,
          children: [...(node.children || []), newNode]
        };
      }
      if (node.children) {
        return {
          ...node,
          children: updateTreeData(node.children, parentKey, newNode)
        };
      }
      return node;
    });
  }
};

// 重命名节点后更新树
export const updateTreeDataProperty = (
  list: ITreeNode[],
  key: string,
  // title: string,
  property: string,
  value: any,
  newId?: string
): ITreeNode[] => {
  return list.map((node) => {
    if (node.key === key) {
      return {
        ...node,
        key: newId ? newId : key,
        // title: title,
        [property]: value,
        children: [...(node.children || [])]
      };
    }
    if (node.children) {
      return {
        ...node,
        children: updateTreeDataProperty(
          node.children,
          key,
          property,
          value,
          newId
        )
      };
    }
    return node;
  });
};

//删除节点
export const removeNode = (list: ITreeNode[], nodeKey: string): ITreeNode[] => {
  return list
    .filter((node) => node.key !== nodeKey)
    .map((node) => ({
      ...node,
      children: node.children ? removeNode(node.children, nodeKey) : undefined
    }));
};

// 找到树中最深的最左边的叶子节点
export const findFirstLeafKeyDFS = (nodes: ITreeNode[]): string | null => {
  for (const node of nodes) {
    // 如果是叶子节点（没有子节点或子节点数组为空）
    if (!node.children || node.children.length === 0) {
      return node.key as string;
    }

    // 递归检查子节点
    const leafKey = findFirstLeafKeyDFS(node.children);
    if (leafKey !== null) {
      return leafKey;
    }
  }

  return null;
};

// 找到某个节点的最深一层子节点
export const findFirstChildByParentKey = (
  treeData: ITreeNode[],
  parentKey: string
): string | null => {
  // 辅助函数：递归查找目标节点
  const findNode = (nodes: ITreeNode[], key: string): ITreeNode | null => {
    for (const node of nodes) {
      if (node.key === key) return node;
      if (node.children) {
        const found = findNode(node.children, key);
        if (found) return found;
      }
    }
    return null;
  };

  // 查找目标节点
  const targetNode = findNode(treeData, parentKey);
  if (!targetNode) return null;

  // 如果没有子节点，返回目标节点自己的key
  if (!targetNode.children || targetNode.children.length === 0) {
    return targetNode.key as string;
  }

  // 沿着第一个子节点一直向下查找
  let current = targetNode;
  while (current.children && current.children.length > 0) {
    current = current.children[0];
  }

  return current.key as string;
};

// 移动节点时，找父节点及兄弟节点
export const findNodeParentAndSibling = (
  tree: ITreeNode[],
  targetKey: string
): {
  preKey: string | null;
  nextKey: string | null;
  parentId: string | null;
} => {
  // 1. 构建三个映射表
  const nodeMap = new Map<string, ITreeNode>(); // key -> node
  const parentMap = new Map<string, string>(); // key -> parentId
  const childrenMap = new Map<string, ITreeNode[]>(); // parentId -> children

  // 特殊处理虚拟根节点
  childrenMap.set("0", []);

  // 递归遍历填充映射表
  function traverse(nodes: ITreeNode[], parentId: string = "0") {
    nodes.forEach((node) => {
      // 填充节点映射
      nodeMap.set(node.key.toString(), node);
      parentMap.set(node.key.toString(), parentId);

      // 填充子节点映射
      if (!childrenMap.has(parentId)) {
        childrenMap.set(parentId, []);
      }
      childrenMap.get(parentId)!.push(node);

      // 递归处理子节点
      if (node.children) {
        traverse(node.children, node.key.toString());
      }
    });
  }

  traverse(tree);

  // 2. 检查目标节点是否存在
  if (!nodeMap.has(targetKey)) {
    return { preKey: null, nextKey: null, parentId: null };
  }

  // 3. 获取parentId
  const parentId = parentMap.get(targetKey)!;

  // 4. 获取兄弟节点列表（包括自己）
  const siblings = childrenMap.get(parentId) || [];

  // 5. 查找目标节点在兄弟列表中的位置
  const index = siblings.findIndex((node) => node.key.toString() === targetKey);
  if (index === -1) {
    return { preKey: null, nextKey: null, parentId };
  }

  // 6. 根据规则返回相邻节点
  let preKey: string | null = null;
  let nextKey: string | null = null;
  if (index === 0) {
    // 是第一个节点，返回下一个
    nextKey = siblings.length > 1 ? siblings[1].key.toString() : null;
  } else {
    // 不是第一个，返回上一个
    preKey = siblings[index - 1].key.toString();
  }

  return { preKey, nextKey, parentId };
};

// 使用正则表达式匹配所有 {{...}} 的内容
export const extractTemplateVariables = (input: string): any[] => {
  const regex = /\{\{(.*?)\}\}/g;
  const matches: string[] = [];

  let match;
  while ((match = regex.exec(input)) !== null) {
    // 添加匹配到的内容（去掉前后空格）
    matches.push(match[1].trim());
  }
  return matches.map((i) => {
    return {
      dataIndex: i,
      title: i,
      fieldProps: {
        autoFocus: false
      }
    };
  });
};

// 找到所有第一级子节点
export const findFristKeys = (tree: ITreeNode[], key: string): boolean => {
  const keys = tree.map((t) => t.key as string);
  return keys.includes(key);
};

// 判断是否是叶子节点
export const isLeafByKey = (key: React.Key, data: ITreeNode[]): boolean => {
  let result = false;

  const traverse = (nodes: ITreeNode[]) => {
    for (const node of nodes) {
      if (node.key === key) {
        result = !node.children || node.children.length === 0;
        return true;
      }
      if (node.children) {
        traverse(node.children);
      }
    }
  };

  traverse(data);
  return result;
};

// 递归获取所有节点 key
export const getAllNodeKeys = (treeData: ITreeNode[]): React.Key[] => {
  return treeData.reduce<React.Key[]>((acc, node) => {
    acc.push(node.key);
    if (node.children) {
      acc.push(...getAllNodeKeys(node.children));
    }
    return acc;
  }, []);
};

export const checkEntireTreeTitleAndPrompt = (node: ITreeNode): boolean => {
  // 检查当前节点
  if (node.title == "未命名章节" || !node?.hasSectionPrompt) {
    return false;
  }

  // 检查子节点
  if (node.children && node.children.length > 0) {
    return node.children.every((child) => checkEntireTreeTitleAndPrompt(child));
  }

  return true;
};

// 展开指定节点及其父节点
export const expandNodeAndParents = (
  expandKeys: string[],
  key: string,
  data: ITreeNode[]
) => {
  const keys = new Set<React.Key>();

  const findParents = (nodes: ITreeNode[], targetKey: string): boolean => {
    return nodes.some((node) => {
      if (node.key === targetKey) {
        keys.add(node.key);
        return true;
      }
      if (node.children) {
        const found = findParents(node.children, targetKey);
        if (found) {
          keys.add(node.key);
          return true;
        }
      }
      return false;
    });
  };

  findParents(data, key);
  return Array.from(new Set([...keys]));
  // return Array.from(new Set([...expandKeys, ...keys]));
};

// 展开指定节点及其下一级子节点
export const handleSmartExpand = (expandedKeys: string[], node: ITreeNode) => {
  const nodeKey = node.key;
  const isExpanded = expandedKeys.includes(nodeKey as string);

  // 获取直接子节点keys
  const childKeys = node.children
    ? node.children.map((child) => child.key)
    : [];

  if (isExpanded) {
    // 已展开 -> 展开所有子节点
    const newExpandedKeys = [...expandedKeys, ...childKeys];
    return newExpandedKeys;
  } else {
    // 未展开 -> 展开当前节点及直接子节点
    const newExpandedKeys = [...expandedKeys, nodeKey, ...childKeys];
    return newExpandedKeys;
  }
};
// 找到某个节点及其所有子节点ID
export const findNodeAndChildrenKeys = (
  tree: ITreeNode[],
  targetKey: string
): string[] => {
  const result: string[] = [];

  const findNode = (nodes: ITreeNode[]) => {
    for (const node of nodes) {
      if (node.key === targetKey) {
        result.push(node.key);
        // 递归收集所有子节点
        if (node.children) {
          collectChildrenKeys(node.children);
        }
        return true;
      }
      if (node.children && findNode(node.children)) {
        return true;
      }
    }
    return false;
  };

  const collectChildrenKeys = (children) => {
    for (const child of children) {
      result.push(child.key);
      if (child.children) {
        collectChildrenKeys(child.children);
      }
    }
  };

  findNode(tree);
  return result;
};
