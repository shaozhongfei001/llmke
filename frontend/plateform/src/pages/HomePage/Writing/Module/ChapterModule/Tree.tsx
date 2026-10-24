import React, {
  useState,
  useMemo,
  useCallback,
  useEffect,
  useRef
} from "react";
import { Tree, message } from "antd";
import type { TreeProps } from "antd/es/tree";
import DeleteConfirm from "@/pages/HomePage/Writing/common/components/DeleteModal";
import TreeNode from "../components/TreeNode.tsx";
import { ITreeNode } from "../common/type.ts";
import {
  updateTreeData,
  removeNode,
  findNodeParentAndSibling,
  updateTreeDataProperty,
  handleSmartExpand
} from "../common/utils.ts";
import { useServices } from "../common/server.ts";

interface IProps {
  treeData: ITreeNode[];
  setTreeData: (tree: ITreeNode[]) => void;
  clickDetail: (key?: string) => void;
  detailId?: string;
  initExpandedKeys: string[];
  refreshTree: () => void;
  setRefreshDetail?: (isRefresh: boolean) => void;
}

const DraggableTree = ({
  treeData,
  clickDetail,
  detailId,
  setTreeData,
  initExpandedKeys,
  refreshTree,
  setRefreshDetail
}: IProps) => {
  const [draggedNodeKey, setDraggedNodeKey] = useState<string | null>(null);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
  const [showDeleteModal, setShowDeleteModal] = useState<{
    isShow: boolean;
    isLoading: boolean;
  }>({
    isShow: false,
    isLoading: false
  });
  const {
    deleteChapter,
    copyChapter,
    moveChapter,
    updateChanpter,
    addChapter
  } = useServices();

  const deleteItems: any = useRef<any>();

  useEffect(() => {
    if (initExpandedKeys !== undefined) {
      setExpandedKeys(initExpandedKeys);
    }
  }, [initExpandedKeys]);
  // 获取节点的所有子节点key（包括嵌套子节点）
  const getAllChildKeys = useCallback((node: ITreeNode): string[] => {
    let keys: string[] = [];
    if (node.children) {
      node.children.forEach((child) => {
        keys.push(child.key as string);
        keys = [...keys, ...getAllChildKeys(child)];
      });
    }
    return keys;
  }, []);

  // 检查目标节点是否是拖动节点的子节点
  const isDescendant = useCallback(
    (draggedKey: string, targetKey: string, tree: ITreeNode[]): boolean => {
      if (draggedKey === targetKey) return true;

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

      const draggedNode = findNode(tree, draggedKey);
      if (!draggedNode) return false;

      const childKeys = getAllChildKeys(draggedNode);
      return childKeys.includes(targetKey);
    },
    [getAllChildKeys]
  );

  // 拖拽开始处理
  const onDragStart: TreeProps["onDragStart"] = useCallback(({ node }: any) => {
    setDraggedNodeKey(node.key as string);
  }, []);

  // 拖拽结束处理
  const onDragEnd: TreeProps["onDragEnd"] = useCallback(() => {
    setDraggedNodeKey(null);
  }, []);

  // 节点展开/折叠处理
  const onExpand = (expandedKeys: React.Key[]) => {
    setExpandedKeys(expandedKeys);
  };

  // 更新所有节点的parentId
  const updateParentIds = (
    nodes: ITreeNode[],
    parentId: string = "0"
  ): ITreeNode[] => {
    return nodes.map((node) => {
      const newNode = { ...node, parentId };
      if (node.children) {
        newNode.children = updateParentIds(node.children, node.key as string);
      }
      return newNode;
    });
  };

  // 拖拽放置处理
  const onDrop = useCallback(
    async (info: {
      node: ITreeNode;
      dragNode: ITreeNode;
      dropPosition: number;
      dropToGap: boolean;
    }) => {
      const { dragNode, node, dropToGap } = info;
      const dragKey = dragNode.key as string;
      const dropKey = node.key as string;

      // 如果目标节点是拖动节点的子节点，则不允许放置
      if (isDescendant(dragKey, dropKey, treeData)) {
        message.warning("不能将父节点拖动到其子节点下");
        return;
      }

      const dropPos = node.pos.split("-");

      const dropPosition =
        info.dropPosition - Number(dropPos[dropPos.length - 1]);

      const loop = (
        data: ITreeNode[],
        key: React.Key,
        callback: (node: ITreeNode, i: number, data: ITreeNode[]) => void
      ) => {
        for (let i = 0; i < data.length; i++) {
          if (data[i].key === key) {
            return callback(data[i], i, data);
          }
          if (data[i].children) {
            loop(data[i].children!, key, callback);
          }
        }
      };

      const data = [...treeData];

      // 找到拖动节点并从原位置删除
      let dragObj: ITreeNode;
      loop(data, dragKey, (item, index, arr) => {
        arr.splice(index, 1);
        dragObj = item;
      });

      if (!dropToGap) {
        // 放置到节点内
        loop(data, dropKey, (item) => {
          item.children = item.children || [];
          item.children.unshift(dragObj);
        });
      } else {
        let ar: ITreeNode[] = [];
        let i: number;
        loop(data, dropKey, (item, index, arr) => {
          ar = arr;
          i = index;
        });
        if (dropPosition === -1) {
          ar.splice(i!, 0, dragObj);
        } else {
          ar.splice(i! + 1, 0, dragObj);
        }
      }
      const newdata = updateParentIds(data);
      const { parentId, preKey, nextKey } = findNodeParentAndSibling(
        newdata,
        dragNode.key as string
      );
      console.log(newdata, "tree");
      const res = await moveNode({
        id: Number(dragNode.key),
        newParentId: Number(parentId),
        prevId: preKey ? Number(preKey) : null,
        nextId: nextKey ? Number(nextKey) : null
      });
      res && setTreeData(newdata);
    },
    [treeData, isDescendant]
  );
  // 移动节点api
  const moveNode = async (props: any) => {
    try {
      const res = await moveChapter.mutateAsync(props);
      if (res) {
        return true;
      }
    } catch (e) {
      console.log("move chapter failed------>", e);
    }
  };
  // 添加子节点
  const handleAddChild = useCallback(
    async (node: ITreeNode) => {
      const res = await addChapter.mutateAsync({
        parentId: Number(node.key),
        sectionTitle: "未命名章节"
      });
      if (res) {
        const newNode: ITreeNode = {
          title: "未命名章节",
          key: res.id.toString()
        };

        const parentKey = res.parentId.toString();

        const newTreeData = updateTreeData(treeData, parentKey, newNode);
        setTreeData(newTreeData);
        // 展开节点

        const smartkeys = handleSmartExpand(expandedKeys as string[], node);
        setExpandedKeys(smartkeys);
      }
    },
    [treeData]
  );
  // 重命名
  const handleRenameNode = async (key: string, title: string) => {
    if (!title.trim()) {
      setEditingKey(null);
      return;
    }
    try {
      const res: any = await updateChanpter.mutateAsync({
        sectionTitle: title,
        id: Number(key)
      });
      if (res && res.success) {
        const newTreeData = updateTreeDataProperty(
          treeData,
          key,
          "title",
          title
        );
        if (detailId == key) {
          setRefreshDetail && setRefreshDetail((pre: boolean) => !pre);
        }

        setTreeData(newTreeData);
        setEditingKey(null);
      }
    } catch (e) {
      console.log("update chapter failed-------->", e);
    }
  };
  // 复制节点，刷新树
  const handleDuplicate = useCallback(async (node: ITreeNode) => {
    try {
      const res = await copyChapter.mutateAsync(Number(node.key));
      if (res) {
        message.success("组件复制成功！");
        refreshTree();
      }
    } catch (e) {
      console.log("copy section fail------>", e);
    }
  }, []);

  // 删除弹窗确认
  const deleteNode = useCallback(
    async (nodeKey: string) => {
      try {
        if (deleteItems?.current) {
          setShowDeleteModal({
            ...showDeleteModal,
            isLoading: true
          });
          const res = await deleteChapter.mutateAsync(deleteItems.current);
          if (res) {
            setTreeData((prev) => removeNode(prev, nodeKey));
            setShowDeleteModal({
              isShow: false,
              isLoading: false
            });
            if (nodeKey == detailId) {
              clickDetail(); //清除右边展示
            }

            message.success("组件删除成功！");
          }
        }
      } catch (e) {
        console.log("delete section fail------>", e);
      }
    },
    [showDeleteModal]
  );

  // 点击删除，先判断是否可直接删除
  const handleDelete = async (node: ITreeNode) => {
    const nodeKey = node.key;
    if (
      (!node.children || node?.children?.length == 0) &&
      !node.hasSectionPrompt
    ) {
      // 叶子节点 且无内容要求，可以直接删除
      const res = await deleteChapter.mutateAsync(Number(nodeKey));
      if (res) {
        setTreeData((prev) => removeNode(prev, nodeKey as string));
        if (nodeKey == detailId) {
          clickDetail(); //清除右边展示
        }
        message.success("组件删除成功！");
      }
    } else {
      // 非叶子节点，或者有内容要求，弹出删除确认框
      setShowDeleteModal({
        ...showDeleteModal,
        isShow: true
      });
      deleteItems.current = nodeKey;
    }
  };

  const onNodeClick = (selectedKeys: React.Key[], e: { node: ITreeNode }) => {
    const { key } = e.node;
    setExpandedKeys((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const renderNode = useCallback(
    (node: ITreeNode) => {
      const nodeKey = node.key;
      return (
        <TreeNode
          nodeType="SECTION"
          node={node}
          editingKey={editingKey}
          setEditingKey={setEditingKey}
          addNode={() => handleAddChild(node)}
          clickNode={clickDetail}
          renameNode={handleRenameNode}
          duplicateNode={handleDuplicate}
          deleteNode={() => handleDelete(node)}
        />
      );
    },
    [
      treeData,
      editingKey,
      handleDuplicate,
      handleAddChild,
      clickDetail,
      handleDelete
    ]
  );

  return (
    <>
      <Tree
        treeData={treeData}
        draggable
        blockNode
        expandedKeys={expandedKeys}
        onExpand={onExpand}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
        onDrop={onDrop}
        selectedKeys={[detailId?.toString() as React.Key]}
        titleRender={renderNode}
        onSelect={onNodeClick}
      />
      <DeleteConfirm
        isShowDeleteModal={showDeleteModal.isShow}
        confirmModal={() => deleteNode(deleteItems.current)}
        content="确认删除该文件及其所有子内容？此操作不可撤销"
        closeModal={() => {
          setShowDeleteModal({
            isShow: false,
            isLoading: false
          });
          deleteItems.current = undefined;
        }}
        loading={showDeleteModal.isLoading}
      />
    </>
  );
};

export default DraggableTree;
