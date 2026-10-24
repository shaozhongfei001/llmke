import { useMemo } from "react";
import { Tree, Empty } from "antd";
import type { TreeProps } from "antd";

import "./style.less";

interface Iprops {
  node: any;
  outlines: any[];
  treeHeight?: number;
  checkedKeys: Array<string | number>;
  relationsObj: any;
  isVersion?: boolean;
  checkedKeysChangeHandler: (keys: Array<string | number>) => void;
}

export const filterTreeDataBySectionId = (nodes: any[]) => {
  if (!nodes || !nodes.length) {
    return [];
  }
  return nodes.reduce((acc, node) => {
    const newNode = { ...node };

    // 处理子节点（后序遍历）
    if (newNode.children) {
      const filteredChildren = filterTreeDataBySectionId(newNode.children);
      newNode.children =
        filteredChildren.length > 0 ? filteredChildren : undefined;
    }

    // 叶子节点必须包含sectionId
    if (newNode.isLeaf) {
      return newNode.sectionId ? [...acc, newNode] : acc;
    }

    // 非叶子节点根据子节点决定保留
    return newNode.children ? [...acc, newNode] : acc;
  }, []);
};

export const LinkTree = (props: Iprops) => {
  const {
    node,
    treeHeight = 330,
    outlines,
    checkedKeys = [],
    relationsObj = {},
    isVersion = false,
    checkedKeysChangeHandler
  } = props;

  const onCheckHandler: TreeProps["onCheck"] = (keys: any) => {
    checkedKeysChangeHandler(keys);
  };

  const judgeDisabled = (
    selfId: string | number,
    sectionId: string | number
  ) => {
    const item = relationsObj[String(sectionId)];
    if (String(sectionId) !== String(selfId) && item && item.length) {
      return item
        .map((i: string | number) => String(i))
        .includes(String(selfId));
    }
    return String(sectionId) === String(selfId);
  };

  const relationDisabledConvert: any = (list: any, selfId: string | number) => {
    return filterTreeDataBySectionId(list).map((i: any) => ({
      ...i,
      key: i.sectionId || i.id,
      title: i.title, // + "---" + i.sectionId,
      disabled: judgeDisabled(selfId, i.sectionId),
      children: i.children ? relationDisabledConvert(i.children, selfId) : []
    }));
  };

  const buildMaps = (tree: any[]) => {
    const idMap = new Map(); // id → node
    const sectionMap = new Map(); // sectionId → id

    const traverse = (node: any, parentId = null) => {
      const nodeWithParent = { ...node, parentId };
      idMap.set(node.id, nodeWithParent);
      if (node.sectionId) {
        sectionMap.set(String(node.sectionId), node.id);
      }
      if (node.children) {
        node.children.forEach((child: any) => traverse(child, node.id));
      }
    };
    tree.forEach((root) => traverse(root));

    return { idMap, sectionMap };
  };

  const collectRelatedNodes = (
    sectionIds: any[],
    sectionMap: any,
    idMap: any
  ) => {
    const collectedIds = new Set();

    // 将 sectionId 转换为 id 并收集
    sectionIds.forEach((sectionId: number | string) => {
      const id = sectionMap.get(String(sectionId));
      if (id) {
        let currentId = id;
        // 向上追溯父链直到根节点
        while (currentId) {
          if (collectedIds.has(currentId)) {
            break; // 防止循环
          }
          collectedIds.add(currentId);
          const node = idMap.get(currentId);
          currentId = node?.parentId;
        }
      }
    });

    // 转换为节点数组
    return Array.from(collectedIds).map((id) => {
      const node = idMap.get(id);
      return { ...node, children: [] }; // 初始化 children
    });
  };
  function buildSubTree(nodes: any[]) {
    const nodeMap = new Map();
    const roots: any[] = [];

    // 第一次遍历：创建所有节点的副本
    nodes.forEach((node) => {
      const newNode = { ...node };
      nodeMap.set(newNode.id, newNode);
      if (!newNode.parentId) {
        roots.push(newNode);
      }
    });

    // 第二次遍历：建立父子关系
    nodes.forEach((node) => {
      if (node.parentId) {
        const parent = nodeMap.get(node.parentId);
        if (parent) {
          parent.children.push(nodeMap.get(node.id));
        }
      }
    });

    return roots;
  }

  const getFilteredTree = (originalTree: any[], sectionIds: any[]) => {
    const { idMap, sectionMap } = buildMaps(originalTree);
    const relatedNodes = collectRelatedNodes(sectionIds, sectionMap, idMap);

    return buildSubTree(relatedNodes);
  };

  const treeData = useMemo(() => {
    console.log(node, outlines, relationsObj);
    const { sectionId } = node;

    return sectionId
      ? isVersion
        ? getFilteredTree(outlines, relationsObj[String(sectionId)])
        : relationDisabledConvert(outlines, sectionId)
      : [];
  }, [node, outlines, relationsObj]);

  return (
    <>
      {outlines && outlines.length ? (
        <div className="link-tree-wrap">
          {/* <div>{JSON.stringify(checkedKeys)}</div> */}
          <Tree
            checkedKeys={checkedKeys}
            height={treeHeight}
            checkable={!isVersion}
            selectable={false}
            treeData={treeData}
            showIcon={false}
            defaultExpandAll={isVersion}
            onCheck={onCheckHandler}
          />
        </div>
      ) : (
        <Empty className="mt-20" />
      )}
    </>
  );
};

export default LinkTree;
