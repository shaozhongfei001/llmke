import { Empty } from "antd";
import { useMemo, useEffect } from "react";
import ActionTreeItem, {
  treeItemTypes
} from "@/components/AiEditor/components/WritingConfig/SegmentedWriting/components/Outline/SourceMaterial/ActionTreeItem";

interface Iprops {
  dbTreeData: any;
  dbList: any[];
  clsoeExceptCls?: string;
  panelCls?: string;
  closeTreeHandler: () => void;
}

type DbTableTreeNode = {
  id: string | number;
  name: string;
  tables?: DbTableTreeNode[];
  isLeaf: boolean;
  children?: DbTableTreeNode[];
};

export const DbTree = (props: Iprops) => {
  const {
    dbTreeData,
    dbList = [],
    clsoeExceptCls = "",
    panelCls = "",
    closeTreeHandler
  } = props;

  const generatePrunedTree = (
    originalTree: DbTableTreeNode[],
    leafIds: string[]
  ): DbTableTreeNode[] => {
    // 1. 收集所有需要保留的节点ID（叶子节点+父节点）
    const retainedIds = new Set<string>();
    leafIds.forEach((leafId) =>
      collectAncestorIds(originalTree, leafId, retainedIds)
    );

    // 2. 根据保留的ID构建新树
    return buildPrunedTree(originalTree, retainedIds);
  };

  // 递归收集叶子节点及其所有父节点ID
  const collectAncestorIds = (
    nodes: DbTableTreeNode[],
    targetId: string,
    retainedIds: Set<string>
  ): boolean => {
    for (const node of nodes) {
      if (String(node.id) === String(targetId)) {
        retainedIds.add(String(node.id));
        return true;
      }
      if (node.children) {
        const found = collectAncestorIds(node.children, targetId, retainedIds);
        if (found) {
          retainedIds.add(String(node.id)); // 添加父节点ID
          return true;
        }
      }
    }
    return false;
  };

  // 构建精简后的树结构
  const buildPrunedTree = (
    nodes: DbTableTreeNode[],
    retainedIds: Set<string>
  ): DbTableTreeNode[] => {
    return nodes
      .filter((node) => retainedIds.has(String(node.id)))
      .map((node) => ({
        ...node,
        children: node.children
          ? buildPrunedTree(node.children, retainedIds)
          : undefined
      }));
  };

  const myDbTreeData = useMemo(() => {
    return generatePrunedTree(
      dbTreeData,
      dbList.map((i: any) => i.refId)
    );
  }, [dbList, dbTreeData]);

  const clickListener = (e: any) => {
    const { target } = e;
    isCloseTree(target);
  };

  const isCloseTree = (el: any) => {
    const { tagName, nodeType, className, parentNode } = el;
    if (tagName === "BODY") {
      closeTreeHandler();
      return;
    }
    if (
      (nodeType === 1 &&
        className &&
        className.toString().includes(panelCls)) ||
      className.toString().includes(clsoeExceptCls)
    ) {
      return;
    }
    // console.log(parentNode);
    isCloseTree(parentNode);
  };

  useEffect(() => {
    window.addEventListener("click", clickListener);
    return () => {
      window.removeEventListener("click", clickListener);
    };
  }, []);

  return (
    <>
      {myDbTreeData.length ? (
        myDbTreeData.map((rootNode: any) => {
          return (
            <ActionTreeItem
              key={rootNode.key}
              node={rootNode}
              isAllExpand={true}
              showAction={false}
              treeItemType={treeItemTypes.dbTable}
            />
          );
        })
      ) : (
        <div className="w-full h-[60vh] min-h-52 flex items-center justify-center">
          <Empty />
        </div>
      )}
    </>
  );
};

export default DbTree;
