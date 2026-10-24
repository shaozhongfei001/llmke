import { Tooltip, Popover, Input, Button } from "antd";
import { useEffect, useMemo, useState, useRef } from "react";
import "./style.less";
import { DragIcon } from "@/components/Icon";
import {
  CaretRightOutlined,
  CaretDownOutlined,
  LinkOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined
} from "@ant-design/icons";
import {
  outlineChangeTypes,
  stageTypes,
  TreeNode,
  nodeTypes,
  findNodesByIds,
  isShowRelation
} from "./";
import { useDrag, useDrop } from "react-dnd";

import LinkTree from "./LinkTree";

interface Iprops {
  node: TreeNode;
  depth?: number;
  outlines: TreeNode[];
  stageType: stageTypes;
  isAllExpand?: boolean;
  editNodeId: string | undefined;
  highLightNodeId?: string | undefined;
  relationsObj?: any;
  onOutlinesChangeHandler: (type: outlineChangeTypes, node: any) => void;
  onDrop: (dragNode: any, targetId: string, position: DropPosition) => void;
  editNodeIdChangeHandler: (id: string | undefined) => void;
  relationOnChange?: (rObj: any) => void;
  isVersion?: boolean;
}

export enum DropPosition {
  before = "before",
  after = "after",
  child = "child"
}

const offsetPadding = 48;

const cls = {
  [DropPosition.before]: "tip-before",
  [DropPosition.after]: "tip-after",
  [DropPosition.child]: "tip-child"
};
const subPadding = 24;

export const TreeItem = (props: Iprops) => {
  const {
    node,
    depth = 0,
    outlines,
    stageType = stageTypes.scene,
    isAllExpand = true,
    editNodeId,
    highLightNodeId,
    relationsObj = {},
    isVersion = false,
    onOutlinesChangeHandler,
    onDrop,
    editNodeIdChangeHandler,
    relationOnChange
  } = props;
  const [isExpand, setIsExpand] = useState<boolean>(false);
  const [position, setPosition] = useState<DropPosition | null>(null);
  const [title, setTitle] = useState<string | undefined>(undefined);
  const positionRef = useRef<DropPosition | null>(null);
  const nodeRef = useRef(null);
  const nodeParentRef = useRef(null);
  const iptRef = useRef<any>(null);
  const [dragNodeId, setDragNodeId] = useState<string | null>(null);
  const [checkedKeys, setCheckedKeys] = useState<Array<string | number>>([]);

  const [{ isDragging }, drag, preview] = useDrag({
    type: nodeTypes.selfNode,
    item: () => {
      if (node.children && node.children?.length > 0 && isExpand) {
        setIsExpand(false);
      }
      return { ...node };
    },
    canDrag: () => !node.isExternal && !isVersion,
    collect: (monitor) => ({
      isDragging: monitor.isDragging()
    })
  });

  const [{ isOver }, drop] = useDrop(() => ({
    accept: Object.keys(nodeTypes),
    hover: (draggedItem: TreeNode, monitor) => {
      if (!monitor.isOver({ shallow: true })) {
        return;
      }
      setDragNodeId(draggedItem.id);
      const _ref: any = nodeParentRef.current;
      // const _ref: any = nodeRef.current;
      // console.log("_ref:", _ref);
      if (_ref && _ref.getBoundingClientRect) {
        const rect = _ref.getBoundingClientRect();
        const clientOffset = monitor.getClientOffset();
        const clientY = clientOffset!.y;
        const clientX = clientOffset!.x;
        const _position =
          clientX > (rect.left + rect.width + offsetPadding) / 4
            ? DropPosition.child
            : clientY < rect!.top + rect!.height / 2
              ? DropPosition.before
              : DropPosition.after;
        // console.log(clientX, rect.left, rect.width);
        if (_position !== positionRef.current) {
          // console.log("position:", _position, positionRef.current);
          positionRef.current = _position;
          setPosition(_position);
        }
      }
    },
    drop: (item: TreeNode) => {
      onDrop(item, node.id, positionRef.current || DropPosition.before);
      positionRef.current = null;
      setPosition(null);
      setDragNodeId(null);
    },
    collect: (monitor) => ({ isOver: monitor.isOver() })
  }));

  drag(nodeRef);
  drop(nodeParentRef);
  // drag(drop(nodeRef));

  const onToggle = () => {
    setIsExpand(!isExpand);
  };

  const addSubTitle = (node: any) => () => {
    onOutlinesChangeHandler(outlineChangeTypes.addSubTitle, { node });
    setTimeout(() => {
      setIsExpand(true);
    });
  };

  const delNode = (node: any) => () => {
    onOutlinesChangeHandler(outlineChangeTypes.delNode, { node });
  };

  const configSection = (node: any) => () => {
    onOutlinesChangeHandler(outlineChangeTypes.configSection, { node });
  };

  const addLinkRelation = (nodeId: string | number) => () => {
    console.log("create link!", nodeId);
  };

  const editNodeTitle = (nodeId: string) => (e: any) => {
    e.stopPropagation();
    if (editNodeId !== nodeId) {
      editNodeIdChangeHandler(nodeId);
    }
    setTimeout(() => {
      if (iptRef.current && iptRef.current.focus) {
        iptRef.current.focus();
      }
    }, 200);
  };

  const tipCls = useMemo(() => {
    return position && isOver && dragNodeId !== node.id ? cls[position] : "";
  }, [position, isOver, dragNodeId]);

  const nodeTitleChange = (e: any) => {
    const target = e.target;
    if (target) {
      const _title = target.value.trim();
      setTitle(_title);
      onOutlinesChangeHandler(outlineChangeTypes.editTitle, {
        node,
        title: _title
      });
    }
  };

  const fixSyncTitle = () => {
    if (editNodeId === node.id && title !== node.title) {
      setTitle(node.title || "");
    }
    if (editNodeId !== node.id && title !== node.title && title !== undefined) {
      onOutlinesChangeHandler(outlineChangeTypes.editTitle, { node, title });
    }
  };

  const onPopoverOpenChange = (open: boolean) => {
    if (!open) {
      console.log(node.sectionId, checkedKeys);
      const obj = {
        [String(node.sectionId)]: checkedKeys
      };
      relationOnChange && relationOnChange({ ...relationsObj, ...obj });
    }
  };

  const getTotalLeafCount = (tree: any[], targetIds: any[]) => {
    const matchedNodes = findNodesByIds(tree, targetIds);
    return matchedNodes.length
      ? matchedNodes.filter((i: any) => i.isLeaf).length
      : 0;
  };

  const checkedKeysChangeHandler = (keys: any[]) => {
    const matchedNodes = findNodesByIds(outlines, keys) || [];
    setCheckedKeys([
      ...matchedNodes.filter((i: any) => i.isLeaf).map((i: any) => i.sectionId)
    ]);
  };

  const relation = useMemo(() => {
    return relationsObj[String(node.sectionId)] || [];
  }, [relationsObj, node]);

  const relationNum = useMemo(() => {
    return relation.length ? getTotalLeafCount(outlines, relation) : 0;
  }, [relation, outlines]);

  useEffect(() => {
    if (isAllExpand !== isExpand) {
      setIsExpand(isAllExpand);
    }
  }, [isAllExpand]);

  useEffect(() => {
    if (!editNodeId || (editNodeId && editNodeId === node.id)) {
      fixSyncTitle();
    }
  }, [editNodeId, node]);

  useEffect(() => {
    if (!isOver && dragNodeId) {
      setDragNodeId(null);
    }
  }, [isOver, dragNodeId]);

  useEffect(() => {
    if (dragNodeId && isOver && dragNodeId !== node.id && !isExpand) {
      setIsExpand(true);
    } else if (dragNodeId && dragNodeId === node.id && isExpand) {
      setIsExpand(false);
    }
  }, [dragNodeId, node, isExpand, isOver]);

  useEffect(() => {
    if (relation) {
      setCheckedKeys([...relation.map((i: string | number) => Number(i))]);
    }
  }, [relation]);

  return (
    <>
      {/* <div className="a">{JSON.stringify(node)}</div> */}
      <div
        className={`tree-row relative w-full h-[52px] py-1 leading-[44px] box-border border-0 border-b border-t border-solid border-b-[#eee] border-t-white ${highLightNodeId && highLightNodeId === node.id ? "bg-[#f1f5ff] hover:border-t-[#f1f5ff] hover:bg-[#f1f5ff] " : "hover:border-t-[#f5f5f5] hover:bg-[#f5f5f5]"}`}
        style={{
          paddingLeft: `${depth * subPadding}px`
        }}
      >
        <span
          ref={nodeRef}
          className={`drag-icon absolute left-0 z-50 ${editNodeId === node.id ? "!hidden" : "hidden"} ${isDragging ? "cursor-move" : "cursor-pointer"}`}
        >
          <DragIcon className="p-1 rounded hover:bg-white" />
        </span>
        <div className={`flex relative ${tipCls}`}>
          <i className="inset-tip hidden absolute h-[1px] left-12 right-0 border-0 border-b-2 border-solid border-b-primary-color">
            <b className="inline-block relative z-50 w-[10px] h-[10px] rounded-full bg-white -left-[10px] bottom-[21px] box-border border-2 border-solid border-primary-color"></b>
          </i>
          <div
            className="subject-cell pl-12 flex-1 min-w-0 overflow-hidden"
            ref={nodeParentRef}
          >
            {editNodeId === node.id ? (
              <Input
                className="node-title-ipt w-[400px]"
                value={title}
                placeholder="请输入标题"
                ref={iptRef}
                onChange={nodeTitleChange}
                allowClear
              />
            ) : (
              <div className={`relative h-11`}>
                {/* <div ref={nodeRef}> */}
                <div className="icon-wrap absolute h-5 w-16 -left-16 top-1/2 -mt-3 inline-block box-border">
                  {node.children && node.children.length ? (
                    isExpand ? (
                      <CaretDownOutlined
                        className="float-right p-1 text-base text-[#888] hover:opacity-80"
                        title="关闭"
                        onClick={onToggle}
                      />
                    ) : (
                      <CaretRightOutlined
                        className="float-right p-1 text-base text-[#888] hover:opacity-80"
                        title="展开"
                        onClick={onToggle}
                      />
                    )
                  ) : null}
                </div>
                {!node.title ? (
                  <span
                    className="text-[#FF4D4F] px-2 py-[6px] select-none cursor-pointer rounded h-6 border-[#d9d9d9] hover:border-solid hover:border hover:px-[7px] hover:py-[5px]"
                    onClick={isVersion ? undefined : editNodeTitle(node.id)}
                  >
                    未填写标题
                  </span>
                ) : (
                  <div
                    className="w-full ml-1 h-11 overflow-hidden"
                    ref={preview}
                  >
                    <span className="w-full inline-block overflow-hidden whitespace-nowrap text-ellipsis">
                      <span
                        className="select-none px-2 py-[6px] cursor-pointer rounded h-6 border-[#d9d9d9] hover:border-solid hover:border hover:px-[7px] hover:py-[5px]"
                        title={title || node.title}
                        onClick={isVersion ? undefined : editNodeTitle(node.id)}
                      >
                        {depth === 0 ? (
                          <b>{title || node.title}</b>
                        ) : (
                          node.title
                        )}
                      </span>
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
          {stageType === stageTypes.scene &&
          node.sectionId &&
          isShowRelation ? (
            <div className="relation-cell w-[100px] pl-4 box-border select-none">
              {node.title && node.title.trim().length > 0 ? (
                <Popover
                  placement="left"
                  trigger="click"
                  arrow={false}
                  onOpenChange={isVersion ? () => {} : onPopoverOpenChange}
                  content={
                    <div className="w-[413px] h-80 pb-3">
                      <LinkTree
                        isVersion={isVersion}
                        node={node}
                        outlines={outlines}
                        checkedKeys={checkedKeys}
                        relationsObj={relationsObj}
                        checkedKeysChangeHandler={checkedKeysChangeHandler}
                      />
                    </div>
                  }
                >
                  {/* dependency */}
                  {node.isLeaf ? (
                    relationNum ? (
                      <>
                        <LinkOutlined className="mr-1 p-1 text-base cursor-pointer" />
                        {relationNum}
                      </>
                    ) : isVersion ? null : (
                      <LinkOutlined
                        className="link-icon hidden p-1 text-base"
                        onClick={addLinkRelation(node.id)}
                      />
                    )
                  ) : null}
                </Popover>
              ) : null}
            </div>
          ) : null}

          <div className="w-32 pl-4 box-border">
            <div className="action-cell hidden">
              <Tooltip
                title={<span className="text-gray-2a">添加子标题</span>}
                color="#fff"
              >
                <Button
                  disabled={isVersion}
                  className="mr-1"
                  onClick={addSubTitle(node)}
                  type="link"
                  icon={
                    <PlusOutlined className="text-[#555] p-1 text-base cursor-pointer rounded hover:text-primary-color hover:bg-white" />
                  }
                />
              </Tooltip>
              {node.title && node.title.trim().length > 0 && (
                <Tooltip
                  title={<span className="text-gray-2a">配置</span>}
                  color="#fff"
                >
                  <Button
                    className="mr-1"
                    onClick={configSection(node)}
                    type="link"
                    icon={
                      <EditOutlined className="text-[#555] p-1 text-base cursor-pointer rounded hover:text-primary-color hover:bg-white" />
                    }
                  />
                </Tooltip>
              )}
              {/* <Tooltip
              title={<span className="text-gray-2a">重命名</span>}
              color="#fff"
            >
              <Button
                disabled={isVersion}
                onClick={editNodeTitle(node.id)}
                type="link"
                icon={
                  <ControlOutlined
                    className={`rename-btn text-base p-1 mr-2 ${editNodeId === node.id ? "text-primary-color" : "text-[#555] cursor-pointer hover:text-primary-color"}`}
                  />
                }
              />
            </Tooltip> */}
              <Tooltip
                title={<span className="text-gray-2a">删除</span>}
                color="#fff"
              >
                <Button
                  disabled={isVersion}
                  onClick={delNode(node)}
                  type="link"
                  icon={
                    <DeleteOutlined className="text-[#555] p-1 text-base cursor-pointer rounded hover:text-primary-color hover:bg-white" />
                  }
                />
              </Tooltip>
            </div>
          </div>
        </div>
      </div>
      {isExpand &&
        node.children?.map((child: any) => {
          return (
            <TreeItem
              {...props}
              key={child.id}
              node={child}
              depth={depth + 1}
              onDrop={onDrop}
            />
          );
        })}
    </>
  );
};

export default TreeItem;
