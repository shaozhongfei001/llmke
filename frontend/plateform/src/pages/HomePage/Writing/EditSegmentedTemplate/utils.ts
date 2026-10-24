interface SectionType {
  id: number;
  articleTypeID?: number;
  articleID?: number; // 文章配置时使用
  sectionPrompt?: string;
  sectionContentExample?: string;
  materialType?: number[];
  content?: string;
}

interface OutlineType {
  id: string;
  title?: string;
  sectionId?: number;
  section?: SectionType;
  contentSources?: any[];
  children?: OutlineType[];
  subParagraphs?: OutlineType[];
  placeholder?: string;
  extraInfo?: any;
}
// 新增section事，没有section id ,大纲绑定的section id默认为0
export const outlinesTransformSection = (data: any[], pId: any) => {
  return data.map((item: OutlineType) => {
    const { id, title, section, sectionId } = item;
    const newItem: OutlineType = {
      title,
      sectionId,
      section
    };
    if (pId == id) {
      if (sectionId) {
        newItem.sectionId = sectionId;
      } else {
        newItem.sectionId = 0; // 新增时，sectionId传0
      }
    }

    if (item.extraInfo) {
      newItem.extraInfo = item.extraInfo;
    }
    if (item.children) {
      newItem.subParagraphs = outlinesTransformSection(item.children, pId);
    }
    return newItem;
  });
};

interface TreeNode {
  id: number;
  name: string;
  daName?: string;
  tables?: TreeNode[];
}
export const filterTreeByIds = (
  tree: TreeNode[],
  ids: number[]
): TreeNode[] => {
  return tree
    .map((node) => {
      const filteredChildren = node.tables
        ? filterTreeByIds(node.tables, ids)
        : [];

      // 只保留当前节点以及它的过滤后的子节点
      if (ids.includes(node.id) || filteredChildren.length > 0) {
        return {
          ...node,
          tables: filteredChildren
        };
      }
      return null; // 不包括没有选中的节点
    })
    .filter((node) => node !== null) as TreeNode[]; // 移除 null
};

export const findTableList = (tree: TreeNode[], ids: number[]): TreeNode[] => {
  const result: TreeNode[] = [];

  function traverse(node: TreeNode) {
    if (node.tables) {
      node.tables.forEach((child) => {
        if (ids.includes(child.id)) {
          result.push(child); // 添加子节点信息
          traverse(child); // 递归遍历子节点
        }
      });
    }
  }

  tree.forEach((rootNode) => {
    traverse(rootNode);
  });

  return result;
};
