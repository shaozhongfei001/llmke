import { Button, Select, Empty, Spin, Popconfirm, Tooltip } from "antd";
import { useEffect, useState, useMemo, useRef } from "react";
// import { useNavigate } from "react-router-dom";
import { WarningFilled } from "@ant-design/icons";
import { IconCollapseDown, IconCollapseUp } from "@/components/Icon";
import RowItem from "./RowItem";
import "./style.less";
import {
  getTaskByArticleId,
  getTaskDetailById,
  cancleTaskById,
  pauseTaskByTaskId,
  resumeTaskByTaskId,
  retryTaskBySectionIds
} from "../../common/useHServices";
// import {mockTreeData,taskTimeList} from './mockData';

interface Iprops {
  item: { [key: string]: any };
  isOpen: boolean;
  onClose?: () => any;
}

export enum taskStatuKeys {
  pending = 1,
  processing = 2,
  success = 3,
  failure = 4,
  paused = 5,
  stopped = 6
}

const taskStatus = {
  [taskStatuKeys.pending]: "等待中",
  [taskStatuKeys.processing]: "写作中",
  [taskStatuKeys.success]: "已完成",
  [taskStatuKeys.failure]: "失败",
  [taskStatuKeys.paused]: "暂停中",
  [taskStatuKeys.stopped]: "已取消"
};

const cssObj = {
  [taskStatuKeys.pending]: {
    backgroundColor: "#f3f4f6",
    color: "#5f6368"
  },
  [taskStatuKeys.processing]: {
    backgroundColor: "#e3f2fd",
    color: "#0f74e7"
  },
  [taskStatuKeys.success]: {
    backgroundColor: "#e6f4ea",
    color: "#37a33c"
  },
  [taskStatuKeys.failure]: {
    backgroundColor: "#fff4f3",
    color: "#ff4d4f"
  },
  [taskStatuKeys.paused]: {
    backgroundColor: "#fff8e1",
    color: "#ff8f00"
  },
  [taskStatuKeys.stopped]: {
    backgroundColor: "#f0f0f0",
    color: "#8c8c8c"
  }
};

const checkStatus = [
  // taskStatuKeys.failure,
  taskStatuKeys.pending,
  taskStatuKeys.processing
];

// export const checkUrlXSS = (url: string) => {
//   return url && Object.prototype.toString.call(url) === "[object String]"
//     ? !url.toLocaleLowerCase().includes("javascript:")
//       ? url
//       : ""
//     : "";
// };

export const findAllSectionIdsByStatus = (
  nodes: any,
  status: taskStatuKeys[] = [taskStatuKeys.failure]
) => {
  const result = [];
  const stack = Array.isArray(nodes) ? [...nodes] : [nodes];
  while (stack.length) {
    const node = stack.pop();

    if (!node.subParagraphs || node.subParagraphs.length === 0) {
      if (status.includes(node.status)) {
        result.push(node.sectionId);
      }
    } else {
      // 将子节点压入栈中
      stack.push(...node.subParagraphs);
    }
  }

  return result;
};

const getState = (node: any) => {
  const { section } = node;
  const sta = section ? section.state : undefined;
  if (!sta) {
    console.log("node miss state:", node);
  }
  return sta || "";
};

const addFieldImmutable = (
  treeData: any,
  depth: number,
  pardenId?: string | number
) => {
  return (treeData || []).map((node: any) => ({
    ...node,
    pardenId: pardenId ? pardenId : undefined,
    depth,
    isLeaf: !node.subParagraphs || node.subParagraphs.length === 0,
    status:
      !node.subParagraphs || node.subParagraphs.length === 0
        ? getState(node)
        : // Number(
          //   Object.keys(taskStatuKeys)[
          //     Math.floor(Math.random() * Object.keys(taskStatuKeys).length)
          //   ]
          // )
          undefined,
    subParagraphs: node.subParagraphs
      ? addFieldImmutable(node.subParagraphs, depth + 1, node.id)
      : []
  }));
};

const pollingTime = location.href.includes("localhost") ? 5000 : 10000;
let pollingInterval = null as any;

const TaskDetail = (props: Iprops) => {
  const { item, isOpen } = props;
  const [curTaskId, setCurTaskId] = useState<string>("");
  const curTaskIdRef = useRef<string>("");
  const [totalFailedNum, setTotalFailedNum] = useState<number>(0);
  const [curStatus, setCurStatus] = useState<taskStatuKeys | undefined>(
    undefined
  );
  const curStatusRef = useRef<taskStatuKeys | undefined>(undefined);
  const [treeData, setTreeData] = useState<any[]>([]);
  const [taskList, setTaskList] = useState<any[]>([]);
  const [taskDetail, setTaskDetail] = useState<any>({});
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isShowConfirm, setIsShowConfirm] = useState<boolean>(false);
  const [isAllExpand, setIsAllExpand] = useState<boolean>(false);
  const [expandIds, setExpandIds] = useState<string[]>([]);
  const aRef = useRef(null);
  // const navigator = useNavigate();

  const changeExpandSta = () => {
    setIsAllExpand(!isAllExpand);
  };

  const viewDocHandler = () => {
    // console.log("查看文档");
    const _a: any = aRef.current;
    if (item.id && _a) {
      _a.href = `/docWriting/docs/${item.id}${curStatus && [taskStatuKeys.success, taskStatuKeys.failure, taskStatuKeys.stopped].includes(curStatus) ? "" : "/1"}`;
      setTimeout(() => {
        const event = new MouseEvent("click", {
          view: window,
          bubbles: true,
          cancelable: true
        });
        _a.dispatchEvent(event);
      }, 0);

      // navigator(`/docWriting/docs/${item.id}/1`);
    }
  };

  const taskTimeChangeHandler = (value: string) => {
    console.log(`taskTimeChangeHandler ${value}`);
    setCurTaskId(value);
    curTaskIdRef.current = value;
  };

  const pauseHandler = () => {
    setIsLoading(true);
    console.log("暂停:", curTaskIdRef.current);
    pauseTaskByTaskId(curTaskIdRef.current)
      .then((res: any) => {
        if (res) {
          fetchTaskDetail();
        }
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  const continueHandler = () => {
    setIsLoading(true);
    console.log("继续:", curTaskIdRef.current);
    resumeTaskByTaskId(curTaskIdRef.current)
      .then((res: any) => {
        if (res) {
          fetchTaskDetail();
        }
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  const cancleHandler = () => {
    setIsLoading(true);
    console.log("取消", curTaskIdRef.current);
    cancleTaskById(curTaskIdRef.current)
      .then((res: any) => {
        if (res) {
          fetchTaskDetail();
        }
      })
      .finally(() => {
        setIsLoading(false);
        setIsShowConfirm(false);
      });
  };

  const onRowRetryHandler = (sectionId: string) => {
    reTryHandler(sectionId);
  };

  const reTryAll = () => {
    // const sectionIds = findAllSectionIdsByStatus(treeData);
    // if (sectionIds && sectionIds.length) {
    //   reTryHandler(sectionIds.join(","));
    // }
    reTryHandler();
  };

  const reTryHandler = (sectionIds?: string | undefined) => {
    setIsLoading(true);
    console.log("全部重试", curTaskIdRef.current, sectionIds);
    retryTaskBySectionIds(
      sectionIds
        ? { taskId: curTaskIdRef.current, sectionIds }
        : { taskId: curTaskIdRef.current }
    )
      .then((res: any) => {
        if (res) {
          fetchTaskDetail();
        }
      })
      .finally(() => {
        setIsLoading(false);
        setIsShowConfirm(false);
      });
  };

  const toggleConfirm = (sta: boolean) => () => {
    if (sta !== isShowConfirm) {
      setIsShowConfirm(!isShowConfirm);
    }
  };

  const getNodeStatus = (childrenStatus: number[]): taskStatuKeys | "" => {
    const { processing, pending, failure, paused, stopped, success } =
      taskStatuKeys;
    if (childrenStatus.includes(processing)) {
      return processing;
    } else if (childrenStatus.includes(pending)) {
      return pending;
    } else if (childrenStatus.includes(failure)) {
      return failure;
    } else if (childrenStatus.includes(paused)) {
      return paused;
    } else if (childrenStatus.includes(stopped)) {
      return stopped;
    } else if (childrenStatus.includes(success)) {
      return success;
    } else {
      return "";
    }
  };

  const structuredClone = (data: any) => {
    let _data: any;
    try {
      _data = JSON.parse(JSON.stringify(data));
    } catch (e) {
      console.log(e);
    }
    return _data || data;
  };

  const calculateStatus = (root: any): void => {
    const traverse = (node: any): void => {
      if (!node.subParagraphs?.length) return;

      node.subParagraphs.forEach((child: any) => traverse(child));

      const childStatuses = node.subParagraphs.map(
        (child: any) => child.status!
      );
      node.status = getNodeStatus(childStatuses);
    };

    traverse(root);
  };

  const countFailedLeaves = (root: any | null): number => {
    if (root) {
      if (!root.subParagraphs?.length) {
        return root.status === taskStatuKeys.failure ? 1 : 0;
      }
      let count = 0;
      root.subParagraphs.forEach((child: any) => {
        count += countFailedLeaves(child);
      });
      return count;
    }
    return 0;
  };

  const iterativeFaileCount = (root: any): number => {
    const stack: any[] = [root];
    let count = 0;

    while (stack.length) {
      const node = stack.pop()!;
      if (!node.subParagraphs?.length) {
        count += node.status === taskStatuKeys.failure ? 1 : 0;
      } else {
        stack.push(...node.subParagraphs);
      }
    }
    return count;
  };

  const fetchTaskList = async () => {
    const { id, taskId } = item;
    if (taskId) {
      setCurTaskId(String(taskId));
      curTaskIdRef.current = String(taskId);
    }
    const _taskList: any = await getTaskByArticleId({ articleId: id });
    if (_taskList && _taskList.length) {
      setTaskList([..._taskList]);
    }
  };

  const fetchTaskDetail = async (cb?: any) => {
    const _taskDetail: any = await getTaskDetailById(curTaskIdRef.current);
    if (_taskDetail && _taskDetail.id) {
      setTaskDetail({ ..._taskDetail });
      fixTreeData({ ..._taskDetail });
      cb && cb();
    }
  };

  const fixDataTime = (_d: string) => {
    const _date = new Date(_d);
    const _year = _date.getFullYear();
    const _month = _date.getMonth() + 1;
    const _day = _date.getDate();
    const _hour = _date.getHours();
    const _minute = `0${_date.getMinutes()}`.slice(-2);
    return `${_year}-${_month}-${_day} ${_hour}:${_minute}`;
  };

  const fixTreeData = (detail?: any) => {
    const _taskDetail = detail || taskDetail;
    const { articleSnapshot, state } = _taskDetail;
    const _list =
      articleSnapshot &&
      articleSnapshot.outlines &&
      articleSnapshot.outlines.paragraphs
        ? articleSnapshot.outlines.paragraphs
        : [];
    // const _list = mockTreeData;
    const _subParagraphs = structuredClone([...addFieldImmutable(_list, 0)]);
    if (_subParagraphs) {
      const clonedData = {
        status: undefined,
        subParagraphs: _subParagraphs
      };
      calculateStatus(clonedData);
      const { subParagraphs, status } = clonedData;
      let failureNum = 0;
      (subParagraphs || []).forEach((node: any) => {
        failureNum += iterativeFaileCount(node);
      });
      setTotalFailedNum(failureNum);
      setTreeData(subParagraphs);
      setCurStatus(state);
      curStatusRef.current = state;
      // setCurStatus(taskStatuKeys.failure);
    }
  };

  // pollingInterval start
  const startPolling = () => {
    clearPollingInterval();
    pollingInterval = setInterval(() => {
      fetchTaskDetail(() => {
        setTimeout(() => {
          pollingCheck();
        }, 100);
      });
    }, pollingTime);
  };

  const clearPollingInterval = () => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  };

  const countPollingSectionIds = () => {
    const sectionIds = findAllSectionIdsByStatus(treeData, checkStatus) || [];
    // console.log("sectionIds:", sectionIds);
    return sectionIds;
  };

  const pollingCheck = () => {
    const sectionIds = countPollingSectionIds();
    if (isFull) {
      if (checkStatus.includes(curStatusRef.current as any)) {
        sectionIds.push(item.id);
      }
      // console.log(
      //   "全文离线，直接检测状态：",
      //   checkStatus,
      //   curStatusRef.current
      // );
      // console.log(item, treeData);
    }
    if (!pollingInterval && sectionIds.length) {
      // console.log("startPolling!!", pollingInterval);
      startPolling();
    } else {
      if (sectionIds.length === 0) {
        console.log("clear polling!!");
        clearPollingInterval();
      } else {
        console.log("continue polling!!");
      }
    }
  };

  const resetData = () => {
    setTotalFailedNum(0);
    setCurStatus(undefined);
    curStatusRef.current = undefined;
    setTreeData([]);
    setTaskList([]);
    setTaskDetail({});
    curTaskIdRef.current = "";
  };

  const timeList = useMemo(() => {
    return (taskList || []).map((i: any) => ({
      value: String(i.id),
      label: `任务时间：${fixDataTime(i.gmtCreate)}`
    }));
  }, [taskList]);

  const isFull = useMemo(() => {
    return !!(item.generateType === 0);
  }, [item]);

  useEffect(() => {
    if (treeData && treeData.length) {
      clearPollingInterval();
      setTimeout(() => {
        pollingCheck();
      }, 100);
    }
  }, [treeData]);

  useEffect(() => {
    if (curTaskIdRef.current) {
      console.log("fetch detail:", curTaskIdRef.current);
      fetchTaskDetail();
    }
  }, [curTaskIdRef.current]);

  useEffect(() => {
    clearPollingInterval();
    if (isOpen) {
      if (item && item.taskId && item.id) {
        fetchTaskList();
      }
      setTimeout(() => {
        pollingCheck();
      }, 100);
    } else {
      setIsAllExpand(false);
      resetData();
      clearPollingInterval();
    }
  }, [isOpen, item]);

  useEffect(() => {
    return () => {
      clearPollingInterval();
    };
  }, []);

  return (
    <div className="my-5 ml-5 mr-3">
      <a
        ref={aRef}
        href=""
        target="_blank"
        className="hidden"
        rel="noopener noreferrer"
      ></a>
      <Spin spinning={isLoading}>
        <div className="h-8 leading-8 pb-4 box-content flex justify-between mr-2 border-solid border-0 border-b border-b-[#eee]">
          <b className="text-xl select-none">{item.title}</b>
          <Button disabled={!(item && item.id)} onClick={viewDocHandler}>
            <span className="text-gray-2a text-sm">查看文档</span>
          </Button>
        </div>
        {/* <div className="a">{JSON.stringify(item)}</div> */}
        <div className="flex justify-between h-8 leading-8 box-content py-3 mr-2 text-gray-2a text-sm border-solid border-0 border-b-[#eee]">
          {/* border-b 250620增加一键展开，取消下横线*/}
          <div className="task-time-select flex justify-between w-[290px]">
            <Select
              style={{ width: 220 }}
              value={curTaskId}
              onChange={taskTimeChangeHandler}
              options={[...timeList]}
            />
            <span
              className={`w-14 h-5 text-xs mt-[6px] box-content text-center rounded-sm select-none`}
              style={
                curStatus
                  ? {
                      ...cssObj[curStatus],
                      lineHeight: "20px"
                    }
                  : {}
              }
            >
              {curStatus ? taskStatus[curStatus] : ""}
            </span>
          </div>
          <div className="flex gap-2">
            {totalFailedNum > 0 ? (
              <span className="text-[#ff4d4f] text-xs mt-2">
                {totalFailedNum}个章节失败
                <WarningFilled className="mr-2 ml-1" />
              </span>
            ) : null}

            {curStatus === taskStatuKeys.processing ? (
              <Button onClick={pauseHandler} className="group">
                <span className="text-gray-2a text-sm group-hover:text-primary-color">
                  暂停
                </span>
              </Button>
            ) : curStatus === taskStatuKeys.paused ? (
              <Button onClick={continueHandler} className="group">
                <span className="text-gray-2a text-sm group-hover:text-primary-color">
                  继续
                </span>
              </Button>
            ) : curStatus === taskStatuKeys.failure ? (
              <Button onClick={reTryAll} className="group">
                <span className="text-gray-2a text-sm group-hover:text-primary-color">
                  {isFull ? "" : "全部"}重试
                </span>
              </Button>
            ) : null}
            {curStatus &&
            [
              taskStatuKeys.paused,
              taskStatuKeys.pending,
              taskStatuKeys.processing
            ].includes(curStatus) ? (
              <Popconfirm
                title="取消"
                description="写作任务在进行中，是否确认取消？"
                open={isShowConfirm}
                onConfirm={cancleHandler}
                okButtonProps={{ loading: isLoading }}
                onCancel={toggleConfirm(false)}
              >
                <Button onClick={toggleConfirm(true)}>
                  <span className="text-gray-2a text-sm hover:text-primary-color">
                    取消
                  </span>
                </Button>
              </Popconfirm>
            ) : null}
          </div>
        </div>
        {item && !isFull ? (
          <div className="mt-3 mb-2 px-1">
            <b className="text-base">大纲</b>
            <Tooltip
              placement="top"
              color="white"
              title={
                <span className="text-gray-2a my-1 inline-block">
                  一键{`${!isAllExpand ? "展开" : "收起"}`}
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
        ) : null}
        {item && !isFull ? (
          // {item ? (
          <div className="pr-1 h-[calc(100vh-190px)] overflow-y-auto overflow-x-hidden">
            {treeData.length ? (
              treeData.map((rootNode: any, idx: number) => {
                return (
                  <RowItem
                    key={`outline-row-${idx}`}
                    isAllExpand={isAllExpand}
                    node={{ ...rootNode, key: `outline-row-${idx}` }}
                    taskStatus={curStatus}
                    expandIds={expandIds}
                    setExpandIds={setExpandIds}
                    onRowRetry={onRowRetryHandler}
                  />
                );
              })
            ) : (
              <Empty className="mt-10" />
            )}
          </div>
        ) : null}
        {item && isFull && curStatus === taskStatuKeys.failure ? (
          <div className="pt-4">
            <div className="text-text-color2 text-sm mb-3">失败日志:</div>
            <div className="text-sm text-[#ff4d4f] break-all">
              {taskDetail.taskLogs || "-"}
            </div>
          </div>
        ) : null}
      </Spin>
    </div>
  );
};

export default TaskDetail;
