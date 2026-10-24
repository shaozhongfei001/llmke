import { Button, Empty, Tabs } from "antd";
import { useMemo, useState } from "react";
import { stageTypes, sourceTypes } from "..";
import { IconCollapseDown, IconCollapseUp } from "@/components/Icon";
import ActionTreeItem, { treeItemTypes } from "./ActionTreeItem";

interface Iprops {
  stageType: stageTypes;
  dbTreeData: any;
  dbList: any[];
  sceneDbList: any[];
  isVersion?: boolean;
  setIsRelationTablesShow: (sta: boolean) => void;
  delTreeNode: (list: any[], sourceType: sourceTypes) => void;
}

enum dbTypes {
  myDb = "myDb",
  modelDb = "modelDb"
}

const tabItems = [
  {
    key: dbTypes.myDb,
    label: "我选择的数据表"
  },
  {
    key: dbTypes.modelDb,
    label: "模版关联的数据表"
  }
];

type DbTableTreeNode = {
  id: string | number;
  name: string;
  tables?: DbTableTreeNode[];
  isLeaf: boolean;
  children?: DbTableTreeNode[];
};

export const DbTableItem = (props: Iprops) => {
  const {
    stageType,
    dbTreeData,
    dbList = [],
    sceneDbList,
    isVersion = false,
    setIsRelationTablesShow,
    delTreeNode
  } = props;
  const [curTab, setCurTab] = useState<dbTypes>(dbTypes.myDb);
  const [isAllExpand, setIsAllExpand] = useState<boolean>(false);
  const changeExpandSta = () => {
    setIsAllExpand(!isAllExpand);
  };

  const tabOnChange = (tabKey: any) => {
    setCurTab(tabKey);
  };

  const myDbNum = useMemo(() => {
    return dbList && dbList.length ? dbList.length : 0;
  }, [dbList]);

  const handlerChooseFile = () => {
    setIsRelationTablesShow(true);
  };

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

  const delNode = (node: any) => {
    const { children } = node;
    let refIds: string[] = [];
    if (children && children.length) {
      refIds = children.map((i: any) => String(i.id));
    } else {
      refIds.push(String(node.id));
    }
    const list: any[] = [];
    (dbList || []).forEach((i: any) => {
      if (!refIds.includes(String(i.refId))) {
        list.push(i);
      }
    });
    delTreeNode(list, sourceTypes.database);
  };

  const myDbTreeData = useMemo(() => {
    return generatePrunedTree(
      dbTreeData,
      dbList.map((i: any) => i.refId)
    );
  }, [dbList, dbTreeData]);

  const sceneDbTreeData = useMemo(() => {
    return generatePrunedTree(
      dbTreeData,
      sceneDbList.map((key) => key)
    );
  }, [sceneDbList, dbTreeData]);

  return (
    <>
      <div className="rounded-lg w-full">
        <div className="text-center mb-3 pr-4">
          <Button
            disabled={isVersion}
            type="link"
            className="h-11 w-full px-0"
            onClick={handlerChooseFile}
          >
            <div className="block w-full h-10 bg-white text-primary-color border-dashed border-[#d9d9d9] border-[1px] rounded leading-10 hover:opacity-75">
              选择数据表
              {/* {stageType === stageTypes.scene && myDbNum ? (
                <span>（{myDbNum}）</span>
              ) : null} */}
            </div>
          </Button>
        </div>
        {stageType === stageTypes.write ? (
          <div className="material-tab-wrap relative mb-3 mr-4">
            <i className="inline-block h-[1px] w-full absolute bottom-0 border-0 border-b border-solid border-b-[#eee]"></i>
            <Tabs items={tabItems} onChange={tabOnChange} activeKey={curTab} />
          </div>
        ) : null}
        <div className="w-full pr-2">
          <div className="mb-2 text-text-color2">
            已选择的数据表
            <Button
              title={isAllExpand ? "收起" : "展开"}
              type="link"
              onClick={changeExpandSta}
              className={`h-4 my-2 mr-0 text-[#888] hover:text-[#055aff]`}
              icon={
                isAllExpand ? (
                  <IconCollapseUp className="p-1 text-base" />
                ) : (
                  <IconCollapseDown className="p-1 text-base" />
                )
              }
            />
          </div>
          {curTab === dbTypes.myDb ? (
            myDbTreeData.length ? (
              myDbTreeData.map((rootNode: any) => {
                return (
                  <ActionTreeItem
                    key={rootNode.key}
                    node={rootNode}
                    stageType={stageType}
                    isAllExpand={isAllExpand}
                    isVersion={isVersion}
                    treeItemType={treeItemTypes.dbTable}
                    delNode={delNode}
                  />
                );
              })
            ) : (
              <Empty className="mt-10" />
            )
          ) : sceneDbList.length ? (
            sceneDbList.map((rootNode: any) => {
              return (
                <ActionTreeItem
                  key={rootNode.key}
                  node={rootNode}
                  stageType={stageType}
                  isAllExpand={isAllExpand}
                  isVersion={isVersion}
                  treeItemType={treeItemTypes.dbTable}
                />
              );
            })
          ) : (
            <Empty className="mt-10" />
          )}
        </div>
      </div>
    </>
  );
};

export default DbTableItem;
