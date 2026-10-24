import { Tooltip, Button } from "antd";
import { useEffect, useState } from "react";
import {
  CaretRightFilled,
  CaretDownFilled,
  CloseCircleFilled,
  CheckCircleFilled,
  WarningFilled,
  PauseCircleFilled
} from "@ant-design/icons";

import { ProcessingIcon, PendingIcon, CancleIcon } from "@/components/Icon";
import { taskStatuKeys, findAllSectionIdsByStatus } from "./";
import "./style.less";

interface Iprops {
  isAllExpand?: boolean;
  node: { [key: string]: any };
  depth?: number;
  taskStatus: taskStatuKeys | undefined;
  expandIds: string[];
  onRowRetry: (node: any) => void;
  setExpandIds: (ids: string[]) => void;
}

const subPadding = 32;
const RowItem = (props: Iprops) => {
  const {
    node,
    isAllExpand = false,
    depth = 0,
    taskStatus,
    expandIds,
    onRowRetry,
    setExpandIds
  } = props;
  const [isExpand, setIsExpand] = useState<boolean>(false);
  const [isRetry, setIsRetry] = useState<boolean>(false);

  const onToggle = () => {
    setIsExpand(!isExpand);
    const idx = expandIds.findIndex((i: string) => i === node.key);
    if (!isExpand && idx < 0) {
      setExpandIds([...expandIds, node.key]);
    }
    if (isExpand && idx >= 0) {
      const _expandIds = [...expandIds];
      _expandIds.splice(idx, 1);
      setExpandIds([..._expandIds]);
    }
  };

  const taskRetryHandler = () => {
    const sectionIds = findAllSectionIdsByStatus(node);
    if (sectionIds && sectionIds.length) {
      onRowRetry(sectionIds.join(","));
    }
  };

  const getErrorMessage = () => {
    const { section } = node;
    let msg = "-";
    if (section && section.taskLogs) {
      msg = section.taskLogs;
      // try {
      //   const taskLogs = JSON.parse(section.taskLogs);
      //   if (taskLogs && taskLogs.length) {
      //     msg = taskLogs[0].message;
      //   }
      // } catch (e) {
      //   console.log(e);
      // }
    }
    return msg;
  };

  const getIcon = (sta: taskStatuKeys) => {
    switch (sta) {
      case taskStatuKeys.processing:
        return <ProcessingIcon className="animate-spin text-base " />;
      case taskStatuKeys.paused:
        return <PauseCircleFilled className="text-[#bbb] text-base " />;
      case taskStatuKeys.failure:
        return (
          <CloseCircleFilled
            // className={`text-[#ff4d4f] text-base failure-icon`}
            className={`text-[#ff4d4f] text-base ${taskStatus !== taskStatuKeys.stopped ? "failure-icon" : ""}`}
          />
        );
      case taskStatuKeys.pending:
        return <PendingIcon className="text-base" />;
      case taskStatuKeys.success:
        return <CheckCircleFilled className="text-[#52c41a] text-base" />;
      case taskStatuKeys.stopped:
        return <CancleIcon className="text-[#52c41a] text-base" />;
    }
  };

  useEffect(() => {
    if (
      isAllExpand !== isExpand &&
      Object.prototype.toString.call(isAllExpand) === "[object Boolean]" &&
      node.subParagraphs &&
      node.subParagraphs.length
    ) {
      setIsExpand(!isExpand);
    }
  }, [isAllExpand, node.subParagraphs]);

  useEffect(() => {
    if (node && node.key && expandIds.length) {
      if (expandIds.includes(node.key)) {
        setIsExpand(true);
      }
    }
  }, [expandIds, node]);

  return (
    <div
      className={`${isExpand ? "bg-[#f1f5ff] " : ""}${depth === 0 ? "pr-2 border-solid border-0 border-b border-b-[#eee] " : ""}${depth === 0 && isExpand && node.subParagraphs.length ? "pb-4 " : ""}${!isExpand && depth === 0 ? "hover:bg-[#f5f5f5]" : ""}`}
    >
      <div
        className={`${depth === 0 ? "py-2" : "hover:bg-[#e8ebff]"} h-8 leading-8 box-content rounded node-row`}
        style={{
          paddingLeft: `${depth * subPadding}px`
        }}
      >
        <div className="pl-6 relative flex select-none">
          <div className="absolute left-0">
            {node.subParagraphs && node.subParagraphs.length ? (
              isExpand ? (
                <CaretDownFilled
                  className="p-1 text-base text-[#888] hover:opacity-80"
                  title="关闭"
                  onClick={onToggle}
                />
              ) : (
                <CaretRightFilled
                  className="p-1 text-base text-[#888] hover:opacity-80"
                  title="展开"
                  onClick={onToggle}
                />
              )
            ) : null}
          </div>
          <div className="flex-1 flex justify-between overflow-hidden">
            <span
              className={`${String(node.status) ? "" : "text-[#bbb]"} truncate relative pr-5`}
              title={node.title}
            >
              {node.title}
              {node.isLeaf && node.status === taskStatuKeys.failure ? (
                <Tooltip
                  placement="top"
                  color="white"
                  title={
                    <span className="text-gray-2a text-sm">
                      失败原因：{getErrorMessage()}
                    </span>
                  }
                >
                  <WarningFilled className="absolute right-0 top-1/2 -mt-[7px] text-[#f4484a] cursor-pointer" />
                </Tooltip>
              ) : null}
            </span>
            <div className="pr-1 w-10 text-right">
              {String(node.status) &&
              (node.isLeaf || (!node.isLeaf && !isExpand))
                ? getIcon(node.status)
                : null}
              {/* {node.status === taskStatuKeys.failure && node.isLeaf ? ( */}
              {node.status === taskStatuKeys.failure &&
              !isExpand &&
              taskStatus !== taskStatuKeys.stopped ? (
                <Button
                  disabled={isRetry}
                  type="link"
                  className="retry-btn px-0 hidden hover:opacity-80"
                  onClick={taskRetryHandler}
                >
                  <span className="text-primary-color text-xs">重试</span>
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      </div>
      {isExpand &&
        node.subParagraphs?.map((child: any, idx: number) => {
          return (
            <RowItem
              {...props}
              key={`row-item-${depth}-${idx}`}
              node={{ ...child, key: `row-item-${depth}-${idx}` }}
              depth={depth + 1}
            />
          );
        })}
    </div>
  );
};

export default RowItem;
