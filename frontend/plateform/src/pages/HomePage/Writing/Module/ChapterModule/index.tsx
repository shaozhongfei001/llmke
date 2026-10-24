import { useState, useEffect, useMemo } from "react";
import { Empty } from "antd";
import type { DataNode } from "antd/es/tree";
import { IChapterListItem } from "../common/type.ts";
import { useServices } from "../common/server.ts";
import {
  updateTreeDataProperty,
  isLeafByKey,
  sectionTreeConvertRender
} from "../common/utils.ts";
import ChapterDetail from "./Detail";
import SearchTree from "../components/SearchTree";
import ResizableLayout from "../../../../../components/ResizableLayout/index.tsx";

interface TreeNode extends DataNode {
  parentId?: string;
  // status: number;
}
function ChapterModule() {
  const [tree, setTree] = useState<TreeNode[]>(); //展示组件树
  const [list, setList] = useState<IChapterListItem[]>(); //展示搜索结果list
  const [detailId, setDetailId] = useState<string>();
  const [refreshDetail, setRefreshDetail] = useState<boolean>(false);
  const { getChapterTree } = useServices();

  useEffect(() => {
    // 初始化 展开第一个子节点
    const initTree = async () => {
      await getTree();
    };
    initTree();
  }, []);

  // 获取搜索结果
  const getList = async (searchVal: string) => {
    const res = await getChapterTree.mutateAsync(searchVal);
    if (searchVal) {
      setList(res);
    }
  };

  //获取树
  const getTree = async () => {
    const res = await getChapterTree.mutateAsync(undefined);
    const tree = sectionTreeConvertRender(res);
    setTree(tree);
    return tree;
  };

  // 刷新树
  const refreshTree = async () => {
    const res = await getTree();
    setList(undefined);
    return res;
  };

  // detailId为叶子节点时，右侧展示详情
  const isLeaf = useMemo(() => {
    return detailId && tree && isLeafByKey(detailId, tree);
  }, [detailId, tree]);

  const updateTreeData = (key: string, property: string, value: any) => {
    if (tree) {
      setTree((pre) => {
        return updateTreeDataProperty(pre, key, property, value);
      });
    }
  };

  return (
    <div className="flex h-[calc(100%-60px)]">
      <ResizableLayout
        LeftComponent={
          <SearchTree
            initialData={tree}
            setTreeData={setTree}
            componentType="SECTION"
            detailId={detailId}
            getTree={getTree}
            searchList={getList}
            setDetailId={setDetailId}
            refreshTree={refreshTree}
            setRefreshDetail={setRefreshDetail}
            list={list?.map((li: IChapterListItem) => {
              return {
                title: li.sectionTitle,
                path: li.rootTitle,
                id: li.id.toString()
              };
            })}
          />
        }
        RightComponent={
          detailId && isLeaf ? (
            (reset) => (
              <ChapterDetail
                id={Number(detailId)}
                refreshDetail={refreshDetail}
                updateTreeData={updateTreeData}
                resetLayout={reset}
              />
            )
          ) : (
            <div className=" h-full flex justify-center items-center">
              <Empty />
            </div>
          )
        }
      />
    </div>
  );
}

export default ChapterModule;
