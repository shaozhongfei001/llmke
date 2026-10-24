import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import { Input, Tooltip, Button } from "antd";
import {
  SearchOutlined,
  PlusOutlined,
  UpSquareOutlined,
  DownSquareOutlined
} from "@ant-design/icons";
import { useLocation } from "react-router-dom";
import { ITreeNode, IListItem } from "../common/type.ts";
import ChapterTree from "../ChapterModule/Tree.tsx";
import AnalysisTree from "../AnalyzeModule/Tree";
import ListItem from "./ListItem.tsx";
import {
  getAllNodeKeys,
  expandNodeAndParents,
  findFirstLeafKeyDFS,
  isLeafByKey,
  findFirstChildByParentKey
} from "../common/utils.ts";
import { useServices } from "../common/server.ts";
import { AddNodeHandle } from "../AnalyzeModule/Tree";
import "../common/style.less";

interface Iprops {
  componentType: "SECTION" | "ANALYSIS";
  initialData?: ITreeNode[];
  setTreeData: (tree: ITreeNode[]) => void;
  list?: IListItem[];
  detailId?: string;
  getTree: () => void;
  searchList: (searchVal: string) => void;
  setDetailId: (key?: string) => void;
  refreshTree: () => Promise<ITreeNode[]>;
  setRefreshDetail?: (isRefresh: boolean) => void;
}
const SearchTree = ({
  componentType,
  initialData,
  setTreeData,
  list,
  detailId,
  setDetailId,
  searchList,
  refreshTree,
  setRefreshDetail
}: Iprops) => {
  const [searchVal, setSearchVal] = useState<string>();
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
  const { addChapter } = useServices();
  const analysisTreeRef = useRef<AddNodeHandle>(null);
  const { state } = useLocation();
  // 判断是否搜索状态
  const isSearching = useMemo(() => {
    return searchVal && searchVal.trim()?.length > 0;
  }, [searchVal]);

  const clickListItem = async (id: string) => {
    const res = await refreshTree(); //点击跳转时，需要刷新树
    const isLeaf = isLeafByKey(id, res);
    // 如果点击叶子节点，选中并展开
    // 如果点击父节点， 选中该父节点下最深一级的叶子节点，选中并展开
    if (isLeaf) {
      expandById(id, res);
    } else {
      // 找到当前节点下的第一个叶子节点
      let selectedId = findFirstChildByParentKey(res, id);
      selectedId && expandById(selectedId, res);
    }

    setSearchVal(undefined);
  };
  const expandById = (id: string, tree: ITreeNode[]) => {
    setDetailId(id);
    const keys = expandNodeAndParents(expandedKeys as string[], id, tree);
    setExpandedKeys(keys);
  };
  useEffect(() => {
    if (initialData && initialData?.length > 0) {
      let selectedId: string | undefined = undefined;
      if (state && state.categoryId) {
        // 分析组件 详情页回退，需要展开并选中分类
        selectedId = state.categoryId;
      } else {
        // 初始化
        if (!detailId) {
          const firstNode = findFirstLeafKeyDFS(initialData);
          if (firstNode) {
            // 展开第一个根节点，选中第一个子节点
            selectedId = firstNode;
          }
        }
      }

      if (selectedId) {
        if (selectedId.indexOf("add") < 0) {
          //新增的节点不能选中
          setDetailId(selectedId);
          const keys = expandNodeAndParents(
            expandedKeys as string[],
            selectedId,
            initialData
          );
          setExpandedKeys(keys);
        }
      }
    }
  }, [initialData, state]);

  const toggleExpandAll = useCallback(
    (expand: boolean) => {
      if (expand) {
        const allKeys = initialData && getAllNodeKeys(initialData);
        allKeys && setExpandedKeys(allKeys);
      } else {
        setExpandedKeys([]);
      }
    },
    [initialData]
  );

  const handleAddChild = async () => {
    if (componentType == "SECTION") {
      const res = await addChapter.mutateAsync({
        parentId: 0,
        sectionTitle: "未命名章节"
      });
      if (res) {
        await refreshTree();
      }
    }

    if (componentType == "ANALYSIS") {
      analysisTreeRef.current?.handleAddNode({
        key: "0"
      });
    }
  };

  return (
    <div className="chapter-tree-container w-full h-full ">
      <Input
        placeholder={
          componentType == "SECTION" ? "搜索组件名称" : "搜索分类名称"
        }
        className="w-full h-[32px] mb-[12px] mr-[12px]"
        suffix={
          <SearchOutlined
            style={{ color: "#999", fontSize: 16 }}
            onClick={async () => {
              if (isSearching && searchVal) {
                await searchList(searchVal);
              }
            }}
          />
        }
        value={searchVal}
        onChange={(e) => {
          setSearchVal(e.target.value);
        }}
      />
      {isSearching && list ? (
        <></>
      ) : (
        <div className="flex h-[24px] mb-[12px] justify-between items-center">
          <Tooltip
            placement="top"
            color={"#fff"}
            title={
              <span className="text-[#2A2A2A]">
                {expandedKeys.length > 0 ? "一键收起" : "一键展开"}
              </span>
            }
          >
            <div
              className="text-[#555555] cursor-pointer hover:bg-[#f1f5ff] w-[88px] rounded-[4px] text-center"
              onClick={() => {
                if (expandedKeys.length == 0) {
                  toggleExpandAll(true);
                } else {
                  toggleExpandAll(false);
                }
              }}
            >
              <span className="mr-[4px]">
                所有{componentType == "SECTION" ? "章节" : "分类"}
              </span>
              {expandedKeys.length > 0 ? (
                <UpSquareOutlined />
              ) : (
                <DownSquareOutlined />
              )}
            </div>
          </Tooltip>
          <Tooltip
            placement="top"
            color={"#fff"}
            title={
              <span className="text-[#2A2A2A]">{`添加${componentType == "SECTION" ? "章节" : "分类"}`}</span>
            }
          >
            <Button
              type="text"
              size="small"
              className="add-btn"
              icon={<PlusOutlined width={24} height={24} />}
              onClick={handleAddChild}
            />
          </Tooltip>
        </div>
      )}

      <div className="relative overflow-y-auto h-[calc(100%-68px)] w-full pr-[6px]">
        {isSearching && list ? (
          <>
            {list.map((li: IListItem) => {
              return (
                <ListItem
                  title={li.title}
                  key={`list-${li.id}`}
                  path={li.path}
                  clickListItem={() => clickListItem(li.id)}
                />
              );
            })}
          </>
        ) : (
          <>
            {initialData &&
              (componentType == "SECTION" ? (
                <ChapterTree
                  treeData={initialData}
                  setTreeData={setTreeData}
                  clickDetail={(key?: string) => {
                    setDetailId(key);
                  }}
                  detailId={detailId}
                  refreshTree={refreshTree}
                  setRefreshDetail={setRefreshDetail}
                  initExpandedKeys={expandedKeys as string[]}
                />
              ) : (
                <AnalysisTree
                  treeData={initialData}
                  setTreeData={setTreeData}
                  clickDetail={(key?: string) => {
                    setDetailId(key);
                  }}
                  ref={analysisTreeRef}
                  detailId={detailId}
                  refreshTree={refreshTree}
                  initExpandedKeys={expandedKeys as string[]}
                />
              ))}
          </>
        )}
      </div>
    </div>
  );
};

export default SearchTree;
