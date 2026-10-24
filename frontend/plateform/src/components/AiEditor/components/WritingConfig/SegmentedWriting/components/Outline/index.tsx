import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { Button, Tooltip, Empty, Spin } from "antd";
import { useEffect, useState, useRef, useMemo, ReactNode } from "react";
import { v4 as uid } from "uuid";

import { IconCollapseDown, IconCollapseUp } from "@/components/Icon";
import outlinesFill from "@/assets/svg/outlines-fill.svg";
import "./style.less";

import { OutlineType } from "@/components/AiEditor/components/WritingConfig/SegmentedWriting/type";

import TreeItem, { DropPosition } from "./TreeItem";
import SourceMaterial from "./SourceMaterial";
import Chapter from "./Chapter";
import UploadModelDoc from "./UploadModelDoc";
import SelectMaterialModal, {
  writingTypes
} from "@/components/AiEditor/components/WritingConfig/components/SelectMaterialModal";

export const isShowRelation = true;

export enum dropItemtypes {
  chapter = "chapter"
}
export interface TreeNode extends OutlineType {
  depth?: number;
  parentId?: string | undefined;
  isLeaf?: boolean;
  isExpand?: boolean | undefined;
  isExternal?: boolean;
}
interface Iprops {
  outlines: TreeNode[];
  treeList: any[];
  stageType?: stageTypes;
  applyLoading?: boolean;
  children?: ReactNode;
  sceneContentSources?: any[];
  relationsRef?: any;
  isVersion?: boolean;
  setOutlines: (outlines: TreeNode[]) => void;
  applyOutlines?: (extractRes: any) => void;
  deleteSection?: (record: OutlineType) => any | boolean;
  loopDataSourceDelete?: (
    data: OutlineType[],
    id: React.Key | undefined
  ) => TreeNode[];
  setSectionData?: (params: any) => void;
  materialConfiem: (list: any[], sourceType: sourceTypes) => void;
  dropSection?: (sceneId: string | number) => any;
  saveDropResult?: (newOutlines?: any, isSlience?: any) => any;
  getMaterialTree?: (originData: any) => void;
}

enum chooseTypes {
  material = "material",
  chapter = "chapter",
  none = "none"
}

export enum stageTypes {
  scene = "scene",
  write = "write"
}

export enum outlineChangeTypes {
  addSubTitle = "addSubTitle",
  delNode = "delNode",
  configSection = "configSection",
  editTitle = "editTitle"
}

export type outlineChangeData = {
  node: any;
  title?: string;
};

export enum nodeTypes {
  selfNode = "selfNode",
  externalNode = "externalNode"
}

export enum sourceTypes {
  knowledge_base = "knowledge_base",
  database = "database"
}

const RelationType = "section";

const initOriginData = {
  kbs: [],
  folders: [],
  files: []
};

export const fixRelationsObj = (originOutlines: any[], relationsObj?: any) => {
  const _relationsObj = relationsObj || {};
  originOutlines.forEach((i: any) => {
    const { dependency, sectionId, subParagraphs } = i;
    if (dependency && dependency.length) {
      const relations = dependency.filter(
        (j: any) => j.sourceType === RelationType
      );
      if (relations.length) {
        _relationsObj[String(sectionId)] = Array.from(
          new Set(relations.map((j: any) => j.refIds).flat(Infinity))
        );
      }
    }
    if (subParagraphs && subParagraphs.length) {
      fixRelationsObj(subParagraphs, _relationsObj);
    }
  });

  return _relationsObj;
};

export const findNodesByIds = (
  tree: any[],
  ids: any[],
  key: string = "children"
) => {
  const result: any[] = [];
  const idSet = new Set(ids.map((i) => String(i)));

  const traverse = (node: any) => {
    if (idSet.has(String(node.sectionId))) {
      result.push(node);
    }
    if (node[key] && node[key].length) {
      node[key].forEach((child: any) => traverse(child));
    }
  };

  tree.forEach((root: any) => traverse(root));
  return result;
};

export const OulineCmp = (props: Iprops) => {
  const {
    outlines,
    stageType = stageTypes.scene,
    applyLoading = false,
    treeList = [],
    sceneContentSources = [],
    relationsRef = {
      current: {}
    },
    isVersion = false,
    setOutlines,
    applyOutlines = () => {},
    deleteSection = () => {},
    loopDataSourceDelete,
    setSectionData,
    materialConfiem,
    dropSection,
    saveDropResult,
    getMaterialTree
  } = props;
  const [outlinesCopy, setOutlinesCopy] = useState<TreeNode[]>([]);
  const outlinesCopyRef = useRef<any[]>([]);
  const [curChooseType, setCurChooseType] = useState<chooseTypes>(
    chooseTypes.none
  );
  const [isAllExpand, setIsAllExpand] = useState<boolean>(false);
  const [editNodeId, setEditNodeId] = useState<string | undefined>(undefined);
  const [isDropNode, setIsDropNode] = useState<boolean>(false);
  const [highLightNodeId, setHighLightNodeId] = useState<string | undefined>(
    undefined
  );
  const treeBodyRef = useRef(null);
  const [relationsObj, setRelationsObj] = useState<any>({});

  /* material cfg begin */
  const [openSelectModal, setOpenSelectModal] = useState(false);
  const [isMaterialApisFetching, setIsMaterialApisFetching] =
    useState<boolean>(false);
  const [materialTreeData, setMaterialTreeData] = useState<any>({
    ...initOriginData
  });
  /* material cfg end */

  const changeExpandSta = () => {
    setIsAllExpand(!isAllExpand);
  };

  const chooseTypeChange = (type: chooseTypes) => () => {
    type !== curChooseType && setCurChooseType(type);
  };

  const addFieldImmutable = (
    treeData: any,
    depth: number,
    pardenId?: string | number
  ) => {
    return (treeData || []).map((node: any) => ({
      ...node,
      pardenId: pardenId ? pardenId : undefined,
      depth: depth + 1,
      isLeaf: !node.children || node.children.length === 0,
      isExternal: false,
      // isExpand: node.children?.length
      //   ? Object.prototype.toString.call(node.isExpand) === "[object Boolean]"
      //     ? node.isExpand
      //     : true
      //   : undefined,
      children: node.children
        ? addFieldImmutable(node.children, depth + 1, node.id)
        : []
    }));
  };

  const relationOutlinesConvert: any = (list: any) => {
    return list
      .filter(
        (i: any) =>
          (i.isLeaf && i.sectionId) ||
          (!i.isLeaf && i.children && i.children.length)
      )
      .map((i: any) => ({
        ...i,
        key: i.sectionId || i.id,
        children: i.children ? relationOutlinesConvert(i.children || []) : []
      }));
  };

  const outlinesOnChange = (treeData: any[]) => {
    const _outlinesCopy = addFieldImmutable(treeData, 0);
    // const _relationTree = relationOutlinesConvert(_outlinesCopy) || [];
    setOutlinesCopy([..._outlinesCopy]);
    outlinesCopyRef.current = [..._outlinesCopy];
  };

  const onOutlinesChangeHandler = (
    type: outlineChangeTypes,
    cfg: outlineChangeData
  ) => {
    const { node, title } = cfg;
    const { sectionId, id, contentSources } = node;
    switch (type) {
      case outlineChangeTypes.addSubTitle:
        addSubTitleHandler(id);
        break;
      case outlineChangeTypes.delNode:
        delNodeHandler(node);
        break;
      case outlineChangeTypes.configSection:
        console.log("edit node:", node);
        setSectionData &&
          setSectionData({
            visible: true,
            node: {
              ...node,
              useCustomKb: !!node.useCustomKb,
              useCustomDB: !!node.useCustomDB
            }
          });
        break;
      case outlineChangeTypes.editTitle:
        if (title) {
          editTitleHandler(id, title);
        }
        break;
    }
  };

  const addSubTitleHandler = (nodeId: string | number) => {
    console.log(nodeId, outlinesCopy);
    const _outlinesCopy = addSubNodeById(outlinesCopy, nodeId);
    // setOutlinesCopy([..._outlinesCopy]);
    // outlinesCopyRef.current = [..._outlinesCopy];
    setOutlines([..._outlinesCopy]);
  };

  // 根据节点获取当前节点下的叶子节点sectionId数组
  const getLeafIds = (node: any, list: any[]) => {
    const { isLeaf, children, sectionId } = node;
    if (isLeaf && sectionId) {
      list.push(sectionId);
    }
    if (children && children.length) {
      children.forEach((i: any) => {
        getLeafIds(i, list);
      });
    }

    return list;
  };

  const delNodeHandler = async (node: any) => {
    if (loopDataSourceDelete) {
      const sectionIds = getLeafIds(node, []);
      const res = await deleteSection(node);
      if (res) {
        const _outlinesCopy = loopDataSourceDelete(outlinesCopy, node.id);
        setOutlines([..._outlinesCopy]);
        console.log(relationsRef.current, relationsObj);

        if (stageType === stageTypes.scene) {
          // 场景管理，删除大纲节点时需要同步设置已选择依赖关系的数据
          const _relationsObj: any = {};
          Object.keys({ ...relationsObj }).forEach((key) => {
            const _item = relationsObj[key] || [];
            const newIds: any[] = [];
            if (_item && _item.length) {
              _item.forEach((sectionId: string | number) => {
                if (!sectionIds.includes(sectionId)) {
                  newIds.push(sectionId);
                }
              });
              _relationsObj[key] = [...newIds];
            }
          });
          relationChangeHandler({ ..._relationsObj });
        }
      }
    } else {
      console.log("缺少loopDataSourceDelete");
    }
  };

  const addSubNodeById = (treeData: any[], targetId: string | number) => {
    const traverse = (nodes: any[]) => {
      for (const node of nodes) {
        if (node.id === targetId) {
          const _children = node.children || [];
          _children.push({
            id: uid()
          });
          node.children = [..._children];
          return true;
        }
        if (node.children?.length) {
          const found = traverse(node.children);
          if (found) {
            return true;
          }
        }
      }
      return false;
    };
    traverse(treeData);
    return treeData;
  };

  const editTitleHandler = (nodeId: string, title: string) => {
    const _outlinesCopy = editTitleById(outlinesCopy, nodeId, title);
    setOutlines([..._outlinesCopy]);
  };

  const editTitleById = (
    treeData: any[],
    targetId: string | number,
    title: string
  ) => {
    const traverse = (nodes: any[]) => {
      for (const node of nodes) {
        if (node.id === targetId) {
          node.title = title;
          return true;
        }
        if (node.children?.length) {
          const found = traverse(node.children);
          if (found) {
            return true;
          }
        }
      }
      return false;
    };
    traverse(treeData);
    return treeData;
  };

  const handleDrop = async (
    dragNode: any,
    targetId: string,
    position: DropPosition
  ) => {
    const { id, isExternal, dropItemtype } = dragNode;
    const dragId = id;
    console.log("drop:", dragId, targetId, position);
    const newData = [...outlinesCopyRef.current];
    // const dragNode = findNode(newData, dragId);
    // const targetNode = findNode(newData, targetId);

    let _outlinesCopy: any[] = [];
    // 处理外部节点添加
    if (isExternal) {
      if (dropItemtype === dropItemtypes.chapter) {
        setIsDropNode(true);
        const _dragNode = dropSection ? await dropSection(id) : null;
        if (!_dragNode) {
          setIsDropNode(false);
          console.log("drop error:", _dragNode);
          return;
        } else {
          setHighLightNodeId(_dragNode.id);
        }

        _outlinesCopy = insertNode(newData, _dragNode, targetId, position);
      }
    } else {
      if (dragId === targetId) {
        return;
      }
      setHighLightNodeId(dragId);
      // 处理内部节点移动
      _outlinesCopy = moveNode(newData, dragId, targetId, position);
    }

    console.log("new outline:", _outlinesCopy);
    setOutlinesCopy([..._outlinesCopy]);
    setOutlines([..._outlinesCopy]);
    outlinesCopyRef.current = [..._outlinesCopy];
    if (saveDropResult) {
      await saveDropResult(_outlinesCopy, true);
    }
    setIsDropNode(false);
  };

  // 递归查找节点
  const findNode = (nodes: TreeNode[], id: string): TreeNode | undefined => {
    for (const node of nodes) {
      if (node.id === id) {
        return node;
      }
      if (node.children && node.children.length > 0) {
        const found = findNode(node.children, id);
        if (found) {
          return found;
        }
      }
    }
  };

  // 给树数据增加parent对象
  const nodeAddParent = (
    nodes: TreeNode[],
    id: string
  ): { node: TreeNode; parent: TreeNode[] } | null => {
    for (const node of nodes) {
      if (node.id === id) {
        return { node, parent: nodes };
      }
      const _children = node.children || [];
      if (_children.length > 0) {
        const result = nodeAddParent(_children, id);
        if (result) {
          return result;
        }
      }
    }
    return null;
  };

  // 外部节点添加插入大纲
  const insertNode = (
    nodes: TreeNode[],
    newNode: TreeNode,
    targetId: string,
    position: DropPosition
  ): any => {
    const cloneTree = JSON.parse(JSON.stringify(nodes)) as TreeNode[];

    const targetInfo = nodeAddParent(cloneTree, targetId);

    if (!newNode || !targetInfo || newNode.id === targetId) {
      return nodes;
    }

    // 计算新位置
    let newParent: TreeNode[] | undefined;
    let newDepth: number;
    let insertIndex: number;

    const { node, parent } = targetInfo;
    const { children, depth } = node;
    if (position === DropPosition.child) {
      newParent = children || [];
      newDepth = depth ? depth + 1 : 1;
      insertIndex = newParent.length;
    } else {
      newParent = parent || [];
      newDepth = depth || 0;
      insertIndex =
        newParent.indexOf(targetInfo.node) +
        (position === DropPosition.after ? 1 : 0);
    }

    newNode.parentId =
      position === DropPosition.child ? targetId : targetInfo.node.parentId;
    newNode.depth = newDepth;
    newParent.splice(insertIndex, 0, newNode);

    // 递归更新子节点
    const updateChildren = (node: TreeNode) => {
      const _children = node.children || [];
      _children.forEach((child: TreeNode) => {
        child.parentId = node.id;
        child.depth = node.depth ? node.depth + 1 : 1;
        updateChildren(child);
      });
    };
    updateChildren(newNode);

    return cloneTree;
  };

  const moveNode = (
    nodes: TreeNode[],
    dragId: string,
    targetId: string,
    position: DropPosition
  ): TreeNode[] => {
    // 深拷贝保证数据不可变
    const cloneTree = JSON.parse(JSON.stringify(nodes)) as TreeNode[];
    // 查找节点辅助方法

    // 查找拖拽节点和目标节点
    const dragInfo = nodeAddParent(cloneTree, dragId);
    const targetInfo = nodeAddParent(cloneTree, targetId);

    // 边界检查
    if (!dragInfo || !targetInfo || dragId === targetId) {
      return nodes;
    }

    // 从原父节点移除
    dragInfo.parent.splice(dragInfo.parent.indexOf(dragInfo.node), 1);

    // 计算新位置
    let newParent: TreeNode[] | undefined;
    let newDepth: number;
    let insertIndex: number;

    const { node, parent } = targetInfo;
    const { children, depth } = node;
    if (position === DropPosition.child) {
      newParent = children || [];
      newDepth = depth ? depth + 1 : 1;
      insertIndex = newParent.length;
    } else {
      newParent = parent || [];
      newDepth = depth || 0;
      insertIndex =
        newParent.indexOf(targetInfo.node) +
        (position === DropPosition.after ? 1 : 0);
    }

    // 插入到新位置
    dragInfo.node.parentId =
      position === DropPosition.child ? targetId : targetInfo.node.parentId;
    dragInfo.node.depth = newDepth;
    newParent.splice(insertIndex, 0, dragInfo.node);

    // 递归更新子节点
    const updateChildren = (node: TreeNode) => {
      const _children = node.children || [];
      _children.forEach((child: TreeNode) => {
        child.parentId = node.id;
        child.depth = node.depth ? node.depth + 1 : 1;
        updateChildren(child);
      });
    };
    updateChildren(dragInfo.node);

    return cloneTree;
  };

  const editNodeIdChangeHandler = (nodeId: string | undefined) => {
    setEditNodeId(nodeId);
  };

  const closeIptHandler = (e: MouseEvent) => {
    const _target: any = e.target;

    const findElIsIpt = (el: any) => {
      const { nodeName, parentNode } = el;
      if (nodeName !== "BODY") {
        if (["SPAN", "INPUT"].includes(nodeName)) {
          if (
            el.className.includes("node-title-ipt") ||
            el.className.includes("rename-btn")
          ) {
            return true;
          }
        }
        if (parentNode) {
          return findElIsIpt(parentNode);
        }
      }
      return false;
    };

    if (!findElIsIpt(_target)) {
      editNodeIdChangeHandler(undefined);
    }
  };

  const relationChangeHandler = (newRelations: any) => {
    setRelationsObj({ ...newRelations });
    relationsRef.current = { ...newRelations };
  };

  /* material fn begin */
  const getAllFilesCb = (originData: any) => {
    console.log("originData:", originData, treeList);
    setMaterialTreeData({ ...originData });
    getMaterialTree && getMaterialTree({ ...originData });
  };

  const materialList = useMemo(() => {
    return (treeList || []).filter(
      (i) => i.sourceType == sourceTypes.knowledge_base
    );
  }, [treeList]);
  /* material fn begin */

  const dbList = useMemo(() => {
    return (treeList || []).filter((i) => i.sourceType == sourceTypes.database);
  }, [treeList]);

  useEffect(() => {
    if (
      relationsRef.current &&
      JSON.stringify(relationsRef.current) !== JSON.stringify(relationsObj)
    ) {
      setRelationsObj({ ...relationsRef.current });
    }
  }, [relationsRef.current]);

  useEffect(() => {
    if (highLightNodeId) {
      setTimeout(() => {
        setHighLightNodeId(undefined);
      }, 2000);
    }
  }, [highLightNodeId]);

  useEffect(() => {
    outlines && outlinesOnChange(outlines);
  }, [outlines]);

  useEffect(() => {
    window.addEventListener("click", closeIptHandler);
    return () => {
      window.removeEventListener("click", closeIptHandler);
    };
  }, []);

  return (
    <>
      <Spin spinning={isDropNode} tip="保存数据...">
        {/* <div className="a">{JSON.stringify(relationsRef.current)}</div> */}
        <div className="flex h-full overflow-hidden">
          <DndProvider backend={HTML5Backend}>
            <div className="flex-1 overflow-hidden h-full pt-2">
              <div className="flex justify-between h-8 mb-2 select-none">
                <div className="mt-1">
                  <b className="text-base">大纲</b>
                  <Tooltip
                    placement="top"
                    color="white"
                    title={
                      <span className="text-gray-2a my-1 inline-block">
                        一键{`${!isAllExpand ? "展开" : "收起"}`}大纲
                      </span>
                    }
                  >
                    <span
                      className="text-[#888] cursor-pointer ml-1 hover:text-[#055aff]"
                      onClick={changeExpandSta}
                    >
                      {isAllExpand ? (
                        <IconCollapseUp className="p-1 text-base" />
                      ) : (
                        <IconCollapseDown className="p-1 text-base" />
                      )}
                    </span>
                  </Tooltip>
                </div>
                <div className="flex gap-2 pr-5">
                  <Button
                    className={`border-[#eee] px-3 ${
                      curChooseType === chooseTypes.material
                        ? "!text-primary-color !bg-[#f1f5ff] !cursor-default !border-[#eee]"
                        : "text-gray-2a"
                    }`}
                    disabled={curChooseType === chooseTypes.material}
                    onClick={chooseTypeChange(chooseTypes.material)}
                  >
                    选择素材
                  </Button>
                  {stageType === stageTypes.scene ? (
                    <Button
                      className={`border-[#eee] px-3 ${
                        curChooseType === chooseTypes.chapter
                          ? "!text-primary-color !bg-[#f1f5ff] !cursor-default"
                          : "text-gray-2a"
                      }`}
                      disabled={curChooseType === chooseTypes.chapter}
                      onClick={chooseTypeChange(chooseTypes.chapter)}
                    >
                      选择章节组件
                    </Button>
                  ) : null}
                  {stageType === stageTypes.scene ? (
                    <UploadModelDoc
                      disabled={isVersion}
                      applyOutlines={applyOutlines}
                      materialTreeData={materialTreeData}
                    />
                  ) : null}
                  {props.children && props.children}
                </div>
              </div>
              {applyLoading ? (
                <div className="w-full flex flex-col justify-center items-center">
                  <img src={outlinesFill} className="w-32 h-32 auto-rotating" />
                  <span className="text-text-color2 mt-2">大纲自动填充中</span>
                </div>
              ) : null}
              <div className="outline-table-wrap mr-1">
                <div className="header-wrap flex bg-[#fafafa] border-0 border-b border-solid border-b-[#eee] h-[46px] leading-[46px] text-sm text-gray-2a mr-4">
                  <div className="subject-cell pl-14 flex-1 leading-[46px]">
                    标题
                  </div>
                  {stageType === stageTypes.scene && isShowRelation ? (
                    <div className="relation-cell w-[100px] pl-4 box-border leading-[46px]">
                      依赖关系
                    </div>
                  ) : null}
                  <div className="w-32 pl-4 box-border leading-[46px]">
                    操作
                  </div>
                </div>
                <div
                  ref={treeBodyRef}
                  className="w-full pr-4 overflow-x-hidden overflow-y-auto h-[calc(100vh-295px)] pt-0 scrollbar-thin"
                >
                  {outlinesCopy.length ? (
                    outlinesCopy.map((rootNode: any) => {
                      return (
                        <TreeItem
                          key={rootNode.id}
                          node={rootNode}
                          outlines={outlinesCopy}
                          stageType={stageType}
                          isAllExpand={isAllExpand}
                          editNodeId={editNodeId}
                          highLightNodeId={highLightNodeId}
                          relationsObj={relationsObj}
                          isVersion={isVersion}
                          onOutlinesChangeHandler={onOutlinesChangeHandler}
                          onDrop={handleDrop}
                          editNodeIdChangeHandler={editNodeIdChangeHandler}
                          relationOnChange={relationChangeHandler}
                        />
                      );
                    })
                  ) : (
                    <Empty className="mt-10" />
                  )}
                </div>
              </div>
            </div>
            <div
              className={`transition-[width] duration-[750ms] ease-in-out border-solid border-0 border-[#eee] ${
                curChooseType === chooseTypes.none
                  ? "w-0"
                  : "w-[530px] border-l"
              } overflow-hidden bg-[#f1f5fc]`}
            >
              {/* [linear-gradient(137.59deg,#E5EDFF,#DCEDFF,#EEF7FF)] */}
              <div className="pl-5 pr-1 text-gray-2a">
                {curChooseType === chooseTypes.material ? (
                  <div className="overflow-hidden h-[calc(100vh-205px)">
                    <SourceMaterial
                      isVersion={isVersion}
                      stageType={stageType}
                      materialList={materialList}
                      dbList={dbList}
                      materialTreeData={materialTreeData}
                      sceneContentSources={sceneContentSources}
                      isLoading={isMaterialApisFetching}
                      setOpenSelectModal={setOpenSelectModal}
                      materialConfiem={materialConfiem}
                      closeDrawerHandler={chooseTypeChange(chooseTypes.none)}
                    />
                  </div>
                ) : curChooseType === chooseTypes.chapter ? (
                  <div className="relative py-2 overflow-x-hidden overflow-y-auto scrollbar-thin h-[calc(100vh-205px)]">
                    <Chapter
                      isVersion={isVersion}
                      closeDrawerHandler={chooseTypeChange(chooseTypes.none)}
                    />
                  </div>
                ) : null}
              </div>
            </div>
          </DndProvider>
        </div>
      </Spin>
      <SelectMaterialModal
        writingType={writingTypes.Segmented}
        openSelectModal={openSelectModal}
        setOpenSelectModal={setOpenSelectModal}
        initSelectedArr={materialList}
        isMaterialApisFetching={isMaterialApisFetching}
        setIsMaterialApisFetching={setIsMaterialApisFetching}
        getAllMertail={materialConfiem}
        getAllFilesCb={getAllFilesCb}
      />
    </>
  );
};

export default OulineCmp;
