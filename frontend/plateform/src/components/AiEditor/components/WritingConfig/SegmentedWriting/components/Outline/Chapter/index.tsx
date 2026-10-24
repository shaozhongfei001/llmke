import { Empty, Spin, Button } from "antd";
import { useEffect, useMemo, useState } from "react";
import axios$ from "@root/src/apis";
import { CloseOutlined } from "@ant-design/icons";
import { IconCollapseDown, IconCollapseUp } from "@/components/Icon";
import { useQuery } from "@tanstack/react-query";
import { useServices } from "@/pages/HomePage/Writing/Module/common/server.ts";
import ChapterItem from "./ChapterItem";
import ChapterDetail from "./ChapterDetail";

interface Iprops {
  isVersion?: boolean;
  closeDrawerHandler: () => void;
}

const mockTree = [
  {
    id: 1,
    sectionTitle: "第一章",
    subSections: [
      {
        id: 100,
        sectionTitle: "财务分析",
        subSections: [
          {
            id: 101,
            sectionTitle: "财务概况",
            subSections: [
              {
                id: 102,
                sectionTitle: "财务指标概览"
              },
              {
                id: 103,
                sectionTitle: "财务报表摘要"
              }
            ]
          }
        ]
      }
    ]
  },
  {
    id: 2,
    sectionTitle: "第二章",
    subSections: []
  },
  {
    id: 3,
    sectionTitle: "第三章",
    subSections: [
      {
        id: 300,
        sectionTitle: "财务分析",
        subSections: [
          {
            id: 301,
            sectionTitle: "财务概况",
            subSections: [
              {
                id: 302,
                sectionTitle: "财务指标概览"
              },
              {
                id: 303,
                sectionTitle: "财务报表摘要"
              }
            ]
          }
        ]
      }
    ]
  },
  {
    id: 4,
    sectionTitle: "第四章"
  }
];
export interface IChapterDetail {
  id: number;
  sectionTitle: string;
  description?: string;
  sectionPrompt?: string;
  sectionContentExample?: string;
}
export interface ChapterTreeNode {
  id: number;
  sectionTitle: string;
  subSections?: ChapterTreeNode[];
  [key: string]: any;
}

const getSectionTree = async (params?: { search: string }) => {
  return axios$
    .get(
      `/cecProxy/dw/component/section/tree?${new URLSearchParams(params).toString()}&canApply=true`
    )
    .then((res) => res?.data);
};

export const Chapter = (props: Iprops) => {
  const { closeDrawerHandler } = props;
  const [isAllExpand, setIsAllExpand] = useState<boolean>(false);
  // const [treeData, setTreeData] = useState<ChapterTreeNode[]>(mockTree);
  const [chapterId, setChapterId] = useState<string>("");
  const [chapterDetail, setChapterDetail] = useState<
    IChapterDetail | undefined
  >(undefined);
  const querySectionTree = useQuery({
    queryKey: ["queryArticleMaterial"],
    queryFn: () => getSectionTree()
  });
  const changeExpandSta = () => {
    setIsAllExpand(!isAllExpand);
  };
  const { getChapterById } = useServices();

  const fetchChapterDetail = async () => {
    const res = await getChapterById.mutateAsync(chapterId);
    if (res) {
      setChapterDetail({ ...res });
    } else {
      viewChapter("");
    }
  };

  const viewChapter = (id: string) => {
    setChapterId(id);
  };

  const closeViewChapter = () => {
    setChapterId("");
    setChapterDetail(undefined);
  };

  const treeData = useMemo(() => {
    return (querySectionTree || {})?.data || [];
  }, [querySectionTree.data]);

  useEffect(() => {
    if (chapterId) {
      fetchChapterDetail();
    }
  }, [chapterId]);

  const renderTree = (tree: ChapterTreeNode[], depth = 0): any => {
    const treeLen = tree && tree.length ? tree.length : 0;
    if (!tree || treeLen === 0) {
      return null;
    }
    return tree.map((node: ChapterTreeNode, idx: number) => {
      if (!node.subSections || node.subSections.length === 0) {
        return (
          <ChapterItem
            {...props}
            key={node.id}
            node={node}
            depth={depth}
            isExpanded={isAllExpand}
            viewChapter={viewChapter}
          />
        );
      } else {
        return (
          <ChapterItem
            {...props}
            key={node.id}
            node={node}
            depth={depth}
            isLeaf={false}
            isExpanded={isAllExpand}
            viewChapter={viewChapter}
          >
            {depth === 0 ? (
              <div className="rounded-b-md overflow-hidden">
                {renderTree(node.subSections, depth + 1)}
              </div>
            ) : (
              renderTree(node.subSections, depth + 1)
            )}
          </ChapterItem>
        );
      }
    });
  };

  return (
    <>
      {chapterId && chapterDetail ? (
        <ChapterDetail
          detail={chapterDetail}
          closeViewChapter={closeViewChapter}
        />
      ) : null}
      <div
        className={`pr-4 ${chapterId && chapterDetail ? "h-[calc(100vh-400px)] hidden" : ""}`}
      >
        <Spin spinning={querySectionTree.isLoading}>
          <div className={`py-2 h-10 leading-6 flex justify-between`}>
            <div className="text-base text-gray-2a">
              <b>章节组件</b>（
              <span className="text-text-color2">可拖拽到左侧大纲</span>）
            </div>
            <div className="-mt-1">
              <Button
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
              <Button
                type="link"
                title="关闭"
                icon={
                  <CloseOutlined className="text-[#666] scale-x-75 scale-y-75 hover:opacity-80" />
                }
                onClick={closeDrawerHandler}
              ></Button>
            </div>
          </div>
          {!treeData.length ? (
            <Empty className="mt-20" />
          ) : (
            <div className="-mt-1">{treeData && renderTree(treeData)}</div>
          )}
        </Spin>
      </div>
    </>
  );
};

export default Chapter;
