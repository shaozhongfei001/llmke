export const classifyMaterialToApi = (data: any[]) => {
  const newData: any[] = [];

  (data || []).forEach((item) => {
    if (item.usage === "both") {
      // 拆分成两个对象，分别为 template 和 content
      newData.push({
        ...item,
        usage: "template"
      });
      newData.push({
        ...item,
        usage: "content"
      });
    } else {
      newData.push(item);
    }
  });

  // 创建一个 Map 来存储分类结果
  const resultMap = new Map();

  // 遍历输入数据
  newData.forEach((item) => {
    const { refEntityType, usage, refId, refName } = item;
    const key = `${usage}_${refEntityType}`; // 使用 usage 和 refEntityType 作为唯一键

    // 如果 Map 中不存在该键，则初始化
    if (!resultMap.has(key)) {
      resultMap.set(key, {
        sourceType: "knowledge_base", // 固定值
        refEntityType: refEntityType,
        usage: usage,
        refIds: [],
        refNames: []
      });
    }

    // 获取当前分类的对象
    const category = resultMap.get(key);

    // 添加 refId 和 refName
    category.refIds.push(refId);
    category.refNames.push(refName);
  });
  console.log("-----re", resultMap, data);

  // 将 Map 转换为数组并返回
  return Array.from(resultMap.values());
};

export const classifyMaterialToRender = (data: any[]) => {
  const refMap = {};

  const mSource = (data || []).filter((s) => s.sourceType == "knowledge_base");

  mSource.forEach((item) => {
    (item.refIds || []).forEach((id, index) => {
      const name = item.refNames[index];
      if (!refMap[id]) {
        refMap[id] = {
          sourceType: item.sourceType,
          refEntityType: item.refEntityType,
          usage: item.usage,
          refId: id,
          refName: name
        };
      } else {
        // Merge usage to 'both' if it exists and is different
        if (refMap[id].usage !== item.usage) {
          refMap[id].usage = "both";
        }
      }
    });
  });
  console.log("map-----", refMap, data, mSource);

  return Object.values(refMap);
};

enum sourceTypes {
  knowledge_base = "knowledge_base",
  database = "database"
}

export const classifyMaterialToRenderNew = (data: any[]) => {
  const kbMap = {} as any;
  const dbMap = {} as any;

  const mSource = (data || []).filter((s) =>
    Object.keys(sourceTypes).includes(s.sourceType)
  );

  mSource.forEach((item) => {
    (item.refIds || []).forEach((id: string | number, index: number) => {
      const name = item.refNames[index];
      if (item.sourceType === sourceTypes.knowledge_base) {
        if (!kbMap[id]) {
          kbMap[id] = {
            sourceType: item.sourceType,
            refEntityType: item.refEntityType,
            usage: item.usage,
            refId: id,
            refName: name
          };
        } else {
          // Merge usage to 'both' if it exists and is different
          if (kbMap[id].usage !== item.usage) {
            kbMap[id].usage = "both";
          }
        }
      }
      if (item.sourceType === sourceTypes.database) {
        if (!dbMap[id]) {
          dbMap[id] = {
            sourceType: item.sourceType,
            refEntityType: item.refEntityType,
            dbName: item.dbNames[index],
            refId: id,
            refName: name
          };
        }
      }
    });
  });
  console.log("map-----", kbMap, dbMap, data, mSource);
  return [...Object.values(kbMap), ...Object.values(dbMap)];
};

export const mergeAndDeduplicate = (A, B) => {
  // 合并两个数组
  const combined = [...A, ...B];

  // 使用 Set 来追踪已见过的 refId
  const seen = new Set();

  return combined.filter((item) => {
    if (!seen.has(item.refId.toString())) {
      seen.add(item.refId.toString()); // 标记为已见
      return true; // 保留该项
    }
    return false; // 过滤掉重复项
  });
};

// 新增section事，没有section id ,大纲绑定的section id默认为0
export const outlinesTransformSection = (
  data: any[],
  pId: any,
  sectionData: any,
  selectedM: any
) => {
  return data.map((item: any) => {
    const { id, title, section, sectionId, contentSources, contentOperation } =
      item;
    const newItem: any = {
      title,
      sectionId,
      section,
      contentOperation,
      contentSources
    };
    if (pId == id) {
      if (sectionId) {
        newItem.sectionId = sectionId;
      } else {
        newItem.sectionId = 0; // 新增时，sectionId传0
      }
      newItem.section = {
        materialType: sectionData.materialType,
        hasSectionPrompt: sectionData.sectionPrompt?.length > 0 ? true : false,
        hasContent: newItem?.section?.hasContent
          ? newItem?.section?.hasContent
          : false
      };

      if (selectedM && selectedM?.length > 0) {
        newItem.contentSources = classifyMaterialToApi(selectedM);
      } else {
        newItem.contentSources = selectedM || null;
      }
    } else {
      if (!item.children || item.children?.length == 0) {
        if (contentSources && contentSources?.length > 0) {
          newItem.contentSources = classifyMaterialToApi(contentSources);
        } else {
          newItem.contentSources = contentSources || null;
        }
      }
    }

    if (item.extraInfo) {
      newItem.extraInfo = item.extraInfo;
    }

    if (item.children) {
      newItem.subParagraphs = outlinesTransformSection(
        item.children,
        pId,
        sectionData,
        selectedM
      );
    }
    return newItem;
  });
};

/**
 * 获取 filterCb 的叶子节点及其父节点快照
 * @param tree 源数据树
 * @param childrenKey 子节点的键名
 * @param filterCb 过滤条件
 * @returns 只包含目标叶子及其父节点的新树
 */
export function getTreeSnapshot(
  tree: any[],
  childrenKey: string,
  filterCb: (node: any) => boolean
): any[] {
  function filterTree(nodes: any[]): any[] {
    return nodes
      .map((node) => {
        // 递归处理子节点
        const _children = node[childrenKey]
          ? filterTree(node[childrenKey])
          : undefined;

        const isLeaf = !node[childrenKey] || node[childrenKey].length === 0;
        const isTargetLeaf = isLeaf && filterCb(node);

        // 如果是目标叶子，或有目标子节点，则保留
        if (isTargetLeaf || (_children && _children.length > 0)) {
          // 返回新对象，避免污染原数据
          const newNode = { ...node };
          if (_children) newNode[childrenKey] = _children;
          else delete newNode[childrenKey];
          return newNode;
        }
        return null;
      })
      .filter(Boolean);
  }
  return filterTree(tree);
}

/**
 * 获取树的所有叶子节点
 * @param tree 树结构数组
 * @param childKey 子节点字段名，默认 'subParagraphs'，可传 'children'
 * @returns 叶子节点数组
 */
export function getAllLeafNodeSectionIds(
  tree: any[],
  childKey: string = "subParagraphs"
): any[] {
  const result: any[] = [];
  function traverse(nodes: any[]) {
    nodes.forEach((node) => {
      const children = node[childKey];
      if (children && children.length > 0) {
        traverse(children);
      } else {
        result.push(node.sectionId);
      }
    });
  }
  traverse(tree);
  return result;
}

export const traversalTree = (
  tree: any,
  childrenKey = "subParagraphs",
  cb: (node: any) => any
) => {
  return tree.map((node: any) => {
    const newNode = cb(node);
    if (node[childrenKey]) {
      newNode["children"] = traversalTree(node[childrenKey], childrenKey, cb);
    }
    return newNode;
  });
};
