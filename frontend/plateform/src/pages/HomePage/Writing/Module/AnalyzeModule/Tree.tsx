import React, {
  useState,
  useCallback,
  useEffect,
  forwardRef,
  useImperativeHandle,
  useRef
} from "react";
import { Tree, message } from "antd";
import DeleteConfirm from "@/pages/HomePage/Writing/common/components/DeleteModal";
import TreeNode from "../components/TreeNode.tsx";
import { ITreeNode } from "../common/type.ts";
import {
  updateTreeData,
  removeNode,
  handleSmartExpand,
  updateTreeDataProperty,
  findNodeAndChildrenKeys
} from "../common/utils.ts";
import { useServices } from "../common/server.ts";

type IProps = {
  treeData: ITreeNode[];
  setTreeData: (tree: ITreeNode[]) => void;
  clickDetail: (key?: string) => void;
  detailId?: string;
  initExpandedKeys: string[];
  refreshTree: () => void;
};
export type AddNodeHandle = {
  handleAddNode: (node: ITreeNode) => void;
};

const MAX_DEPTH = 10;

const AnalysisCategoryTree = forwardRef<AddNodeHandle, IProps>(
  (
    {
      treeData,
      setTreeData,
      clickDetail,
      detailId,
      initExpandedKeys,
      refreshTree
    },
    ref
  ) => {
    const [editingKey, setEditingKey] = useState<string | null>(null);
    const [addingParentKey, setAddingParentKey] = useState<React.Key | null>(
      null
    );

    const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
    const [showDeleteModal, setShowDeleteModal] = useState<{
      isShow: boolean;
      isLoading: boolean;
      content?: string;
    }>({
      isShow: false,
      isLoading: false
    });
    const {
      deleteAnalysisCategory,
      addAnalysisCategory,
      updateAnalysisCategory,
      getAnalysisList
    } = useServices();
    const deleteItems: any = useRef<any>();

    // 暴露方法给父组件
    useImperativeHandle(ref, () => ({
      handleAddNode: (node) => {
        handleAddChild(node);
      }
    }));

    useEffect(() => {
      if (initExpandedKeys !== undefined) {
        setExpandedKeys(initExpandedKeys);
      }
    }, [initExpandedKeys]);

    // 节点展开/折叠处理
    const onExpand = (expandedKeys: React.Key[]) => {
      setExpandedKeys(expandedKeys);
    };

    // 删除弹窗确认
    const deleteNode = useCallback(
      async (nodeKey: string) => {
        try {
          if (deleteItems?.current) {
            setShowDeleteModal({
              ...showDeleteModal,
              isLoading: true
            });
            const res: any = await deleteAnalysisCategory.mutateAsync({
              id: deleteItems.current,
              deleteComponent: true
            });

            if (res.success) {
              setTreeData((prev) => removeNode(prev, nodeKey));
              setShowDeleteModal({
                isShow: false,
                isLoading: false
              });
              if (nodeKey == detailId) {
                clickDetail(); //清除右边展示
              }
              message.success("分类删除成功！");
            }
          }
        } catch (e) {
          console.log("delete section fail------>", e);
        }
      },
      [showDeleteModal]
    );
    // 点击删除，先判断是否可直接删除
    const handleDelete = async (nodeKey: string) => {
      deleteItems.current = nodeKey;
      const keys = findNodeAndChildrenKeys(treeData, nodeKey);
      try {
        const res: any = await getAnalysisList.mutateAsync({
          id: keys.join(",")
        });
        if (res && res.totalCount && res.totalCount > 0) {
          setShowDeleteModal({
            ...showDeleteModal,
            isShow: true,
            content: `本次删除操作将同时删除其下的${res.totalCount}个组件，操作一旦执行无法撤销`
          });
          return;
        } else {
          const res: any = await deleteAnalysisCategory.mutateAsync({
            id: nodeKey,
            deleteComponent: true
          });
          if (res.success) {
            setTreeData((prev) => removeNode(prev, nodeKey));
            if (nodeKey == detailId) {
              clickDetail(); //清除右边展示
            }
            message.success("分类删除成功！");
          }
        }
      } catch (e) {
        console.log("delete analysis category fail------>", e);
      }
    };

    const onNodeClick = (selectedKeys: React.Key[], e: { node: ITreeNode }) => {
      const { key } = e.node;
      setExpandedKeys((prev) =>
        prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
      );
    };
    // 添加子节点
    const handleAddChild = (node: ITreeNode) => {
      if (node?.level && node?.level >= MAX_DEPTH - 1) {
        message.warning(`不能添加超过${MAX_DEPTH}层的节点`);
        return;
      }

      if (editingKey) {
        return;
      }

      const newKey = `add-${Date.now()}`;
      const newNode: ITreeNode = {
        title: "",
        key: newKey,
        level: node?.level ? node?.level + 1 : 0
      };
      const newTreeData = updateTreeData(treeData, node.key as string, newNode);
      setTreeData(newTreeData);
      setEditingKey(newKey);
      setAddingParentKey(node.key);
      // 展开节点

      const smartkeys = handleSmartExpand(expandedKeys as string[], node);
      setExpandedKeys(smartkeys);
    };

    // 删除空节点（取消编辑时）
    const handleDeleteEmptyNode = (key: React.Key) => {
      const updateTreeDataAfterDel = (list: ITreeNode[]): ITreeNode[] => {
        return list
          .filter((node) => node.key !== key)
          .map((node) => {
            if (node.children) {
              return {
                ...node,
                children: updateTreeDataAfterDel(node.children)
              };
            }
            return node;
          });
      };

      const newData = updateTreeDataAfterDel(treeData);
      setTreeData(newData);
    };

    // 保存节点(包括新增和重命名)
    const handleSaveNode = async (key: string, value: string) => {
      const isAdd = key.indexOf("add") > -1;
      let res: any;
      if (!value.trim()) {
        if (isAdd) {
          handleDeleteEmptyNode(key);
        }
        setEditingKey(null);
        setAddingParentKey(null);
        return;
      }
      try {
        if (isAdd) {
          res = await addAnalysisCategory.mutateAsync({
            parentId: addingParentKey as string,
            categoryName: value
          });
        } else {
          res = await updateAnalysisCategory.mutateAsync({
            id: key,
            categoryName: value
          });
        }
      } catch (e) {
        if (isAdd) {
          console.error("Add category failed------>", e);
        } else {
          console.error("Rename category failed------>", e);
        }
      }
      if (res) {
        const newData = updateTreeDataProperty(
          treeData,
          key,
          "title",
          value,
          res?.id
        );
        if (isAdd) {
          clickDetail(res.id);
          if (addingParentKey == "0") {
            //根节点新增时，需要刷新树
            refreshTree();
          }
        }
        setTreeData(newData);
        setEditingKey(null);
        setAddingParentKey(null);
      }
    };

    const renderNode = useCallback(
      (node: ITreeNode) => {
        const nodeKey = node.key;
        return (
          <TreeNode
            nodeType="ANALYSIS"
            node={node}
            editingKey={editingKey}
            setEditingKey={setEditingKey}
            addNode={() => handleAddChild(node)}
            clickNode={clickDetail}
            deleteNode={() => handleDelete(nodeKey as string)}
            renameNode={(key, value) => handleSaveNode(key, value)}
          />
        );
      },
      [treeData, editingKey, handleAddChild, handleSaveNode, clickDetail]
    );

    return (
      <>
        <Tree
          treeData={treeData}
          blockNode
          expandedKeys={expandedKeys}
          onExpand={onExpand}
          selectedKeys={[detailId?.toString() as React.Key]}
          titleRender={renderNode}
          onSelect={onNodeClick}
        />
        <DeleteConfirm
          isShowDeleteModal={showDeleteModal.isShow}
          confirmModal={() => deleteNode(deleteItems.current)}
          content={showDeleteModal.content}
          closeModal={() => {
            setShowDeleteModal({
              isShow: false,
              isLoading: false,
              content: undefined
            });
            deleteItems.current = undefined;
          }}
          loading={showDeleteModal.isLoading}
        />
      </>
    );
  }
);

export default AnalysisCategoryTree;
