import { useState, useEffect, useMemo } from "react";
import { Empty } from "antd";

import { ITreeNode, IAnalysisCategoryTreeItem } from "../common/type.ts";
import { useServices } from "../common/server.ts";
import {
  isLeafByKey,
  analysisCategoryTreeConvertRender
} from "../common/utils.ts";
import AnalysisCategoryDetail from "./Detail";
import SearchTree from "../components/SearchTree";
import ResizableLayout from "../../../../../components/ResizableLayout/index.tsx";

function AnalysisModule() {
  const [tree, setTree] = useState<ITreeNode[]>(); //展示组件树
  const [list, setList] = useState<IAnalysisCategoryTreeItem[]>(); //展示搜索结果list

  const [detailId, setDetailId] = useState<string>();
  const { getAnalysisCategoryTree } = useServices();

  useEffect(() => {
    // 初始化 展开第一个子节点
    const initTree = async () => {
      await getTree();
    };
    initTree();
  }, []);

  // 获取搜索结果
  const getList = async (searchVal: string) => {
    const res = await getAnalysisCategoryTree.mutateAsync(searchVal);
    if (searchVal) {
      setList(res);
    }
  };

  //获取树
  const getTree = async () => {
    const res = await getAnalysisCategoryTree.mutateAsync(undefined);
    const tree = analysisCategoryTreeConvertRender(res);
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

  return (
    <div className="flex w-full h-[calc(100%-60px)]">
      <ResizableLayout
        LeftComponent={
          <SearchTree
            initialData={tree}
            setTreeData={setTree}
            componentType="ANALYSIS"
            detailId={detailId}
            setDetailId={setDetailId}
            getTree={getTree}
            searchList={getList}
            refreshTree={refreshTree}
            list={list?.map((li: IAnalysisCategoryTreeItem) => {
              return {
                title: li.categoryName,
                path: (li.path && li.path[0]) || "-",
                id: li.id
              };
            })}
          />
        }
        RightComponent={
          detailId && isLeaf ? (
            <AnalysisCategoryDetail id={detailId} refreshTree={refreshTree} />
          ) : (
            <div className="h-full flex justify-center items-center">
              <Empty />
            </div>
          )
        }
      />
    </div>
  );
}

export default AnalysisModule;
