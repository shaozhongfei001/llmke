import { CaretRightOutlined } from "@ant-design/icons";
import { Button } from "antd";
import { ChapterTreeNode } from ".";
import { useEffect, useState } from "react";
import { useDrag } from "react-dnd";
import { nodeTypes, dropItemtypes } from "..";
import "./style.less";

interface Iprops {
  node: ChapterTreeNode;
  depth: number;
  isLeaf?: boolean;
  isExpanded?: boolean;
  children?: React.ReactNode;
  isVersion?: boolean;
  isLast?: boolean;
  viewChapter?: (chapterId: string) => void;
}

export const ChapterItem = ({
  node,
  depth,
  isLeaf = true,
  isExpanded = false,
  children,
  isVersion = false,
  viewChapter
}: Iprops) => {
  const { sectionTitle } = node;
  const [isExpandedState, setIsExpandedState] = useState(false);

  const [{ isDragging }, drag] = useDrag({
    type: nodeTypes.externalNode,
    item: () => {
      if (node.subSections && node.subSections?.length > 0 && isExpandedState) {
        setIsExpandedState(false);
      }
      return { ...node, dropItemtype: dropItemtypes.chapter, isExternal: true };
    },
    canDrag: () => !isVersion,
    collect: (monitor) => ({
      isDragging: monitor.isDragging()
    })
  });

  const viewChapterHandler = (chapterId: string) => () => {
    viewChapter && viewChapter(chapterId);
  };

  const toggleExpand = () => {
    setIsExpandedState(!isExpandedState);
  };

  useEffect(() => {
    if (!isLeaf) {
      setIsExpandedState(isExpanded);
    }
  }, [isExpanded, isLeaf]);

  return (
    <div className={`${depth > 0 && isExpandedState ? "bg-[#e7ebf0]" : ""}`}>
      <div
        ref={drag}
        className={`chapter-item w-full relative pr-6 h-[40px] box-border flex items-center text-[14px] text-gray-2a font-normal ${isDragging ? "cursor-move" : "cursor-pointer"} ${depth === 0 ? "bg-white mt-1 rounded" : "bg-[#e7ebf0]"} ${depth > 0 ? "hover:bg-[#dadee6]" : "hover:opacity-80"}`}
        style={{
          paddingLeft: `${depth * 28 + 24}px`
        }}
      >
        {isLeaf ? (
          <Button
            onClick={viewChapterHandler(String(node.id))}
            className="absolute right-0 text-xs text-primary-color hidden preview-btn"
            type="link"
          >
            预览
          </Button>
        ) : null}
        <span
          className="pl-7 relative ellipsis overflow-hidden whitespace-nowrap text-ellipsis pr-4"
          onClick={!isLeaf ? toggleExpand : undefined}
        >
          {!isLeaf && (
            <span
              className="absolute left-0 cursor-pointer hover:opacity-85"
              // onClick={toggleExpand}
            >
              <CaretRightOutlined
                className="text-base text-[#888]"
                rotate={isExpandedState ? 90 : 0}
              />
            </span>
          )}
          {sectionTitle}
        </span>
      </div>
      {isExpandedState && children}
    </div>
  );
};

export default ChapterItem;
