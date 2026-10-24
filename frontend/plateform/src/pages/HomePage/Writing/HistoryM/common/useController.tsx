import { useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { useNavigate, useSearchParams } from "react-router-dom";
import { message, Popover, Tag } from "antd";
import Article from "@/assets/writing/article.png";
import {
  cancleTaskById,
  pauseTaskByTaskId,
  resumeTaskByTaskId,
  retryTaskBySectionIds,
  useHServices
} from "./useHServices";
import {
  PauseCircleOutlined,
  PlayCircleOutlined,
  RedoOutlined,
  StopOutlined
} from "@ant-design/icons";
import dayjs from "dayjs";
import {
  DocumentFileIcon,
  FileDocIcon,
  FilePdfIcon,
  OdfFileIcon
} from "@/components/Icon";

enum ExportType {
  docx = "docx",
  wps = "wps",
  pdf = "pdf",
  odt = "odt"
}

const iconMap = {
  [ExportType.docx]: <FileDocIcon />,
  [ExportType.wps]: <FileDocIcon />,
  [ExportType.pdf]: <FilePdfIcon />,
  [ExportType.odt]: <OdfFileIcon />
};

const exportTypeList: ExportType[] = [
  ExportType.docx,
  ExportType.wps,
  ExportType.pdf,
  ExportType.odt
];

enum DocState {
  pending = 1,
  processing = 2,
  success = 3,
  failure = 4,
  paused = 5,
  stopped = 6
}

enum DocGenType {
  full = 0,
  partial = 1
}

const statusText = {
  [DocState.pending]: "等待中",
  [DocState.processing]: "写作中",
  [DocState.success]: "已完成",
  [DocState.failure]: "失败",
  [DocState.paused]: "暂停中",
  [DocState.stopped]: "已取消"
};

const statusColor = {
  [DocState.pending]: {
    backgroundColor: "#8c8c8c",
    color: "#f0f0f0"
  },
  [DocState.processing]: {
    backgroundColor: "#e3f2fd",
    color: "#0f74e7"
  },
  [DocState.success]: {
    backgroundColor: "#e6f4ea",
    color: "#37a33c"
  },
  [DocState.failure]: {
    backgroundColor: "#fff4f3",
    color: "#ff4d4f"
  },
  [DocState.paused]: {
    backgroundColor: "#fff8e1",
    color: "#ff8f00"
  },
  [DocState.stopped]: {
    backgroundColor: "#8c8c8c",
    color: "#f0f0f0"
  }
};

interface TableDataType {
  id: number;
  gmtModified: string;
  title: string;
  contentAbstract: string;
  totalSections: number;
  generatedSections: number;
  taskState: DocState;
  author: string;
  totalTasks: number;
  completedTasks: number;
  isOline: boolean;
  generateType?: DocGenType; // 是否分段写作
  exportType?: ExportType; // 导出类型
}

enum Action {
  OpenTaskDetal = "openTaskDetal",
  ToWrite = "toWrite",
  Export = "export",
  Delete = "delete",
  Pause = "pause",
  Continue = "continue",
  Retry = "Retry",
  View = "view",
  Add = "add",
  CancelTask = "cancelTask"
}

type TableAction = Exclude<Action, Action.Add>;

const actionObj: { [key in TableAction]: string } = {
  [Action.OpenTaskDetal]: "任务详情",
  [Action.ToWrite]: "编辑",
  [Action.Export]: "导出",
  [Action.Delete]: "删除",
  [Action.Pause]: "暂停",
  [Action.Continue]: "继续",
  [Action.Retry]: "重试",
  [Action.View]: "查看",
  [Action.CancelTask]: "取消"
};

const finishStatus = [DocState.success, DocState.failure, DocState.stopped];

const getStatusTag = (taskState: DocState) => {
  return (
    <Tag
      color={statusColor[taskState].backgroundColor}
      className="w-[52px] flex items-center justify-center"
    >
      <span
        style={{
          color: statusColor[taskState].color
        }}
      >
        {statusText[taskState]}
      </span>
    </Tag>
  );
};

const getDocAction = (
  record: TableDataType,
  handleEvent: (type: Action, d: TableDataType) => any
) => {
  const { isOline } = record;
  // 在线生成的文档没有任务状态
  const dosActionList: TableAction[] = isOline
    ? [Action.Export, Action.Delete]
    : [Action.OpenTaskDetal, Action.Export, Action.Delete];
  return (
    <div className="flex items-center gap-[16px]" id={uuidv4()}>
      {dosActionList.map((i: TableAction) => {
        if (i === Action.Export) {
          return (
            <Popover
              placement="top"
              content={
                <div className="py-2">
                  {exportTypeList.map((type) => (
                    <div
                      key={uuidv4()}
                      className="cursor-pointer h-[32px] w-[92px] flex items-center gap-3 hover:bg-[#F1F5FF] pl-4"
                      onClick={() =>
                        handleEvent(i, { ...record, exportType: type })
                      }
                    >
                      <span>{iconMap[type]}</span>
                      <span className="text-[#2A2A2A]">{type}</span>
                    </div>
                  ))}
                </div>
              }
              arrow={false}
              styles={{ root: { padding: 0 }, body: { padding: 0 } }}
            >
              <div
                id={uuidv4()}
                className="h-[32px] flex items-center cursor-pointer text-[#055aff]"
                // onClick={() => handleEvent(i, record)}
              >
                {actionObj[i]}
              </div>
            </Popover>
          );
        }
        return (
          <div
            id={uuidv4()}
            className="h-[32px] flex items-center cursor-pointer text-[#055aff]"
            onClick={() => handleEvent(i, record)}
          >
            {actionObj[i]}
          </div>
        );
      })}
    </div>
  );
};

const getTaskActionArr = (taskState: DocState): TableAction[] => {
  switch (taskState) {
    case DocState.success:
    case DocState.stopped:
      return [];
    case DocState.processing:
      return [Action.Pause, Action.CancelTask];
    case DocState.failure:
      return [Action.Retry];
    case DocState.paused:
      return [Action.Continue, Action.CancelTask];
    case DocState.pending:
      return [Action.CancelTask];
    default:
      return [];
  }
};

const taskActionIcon: any = {
  [Action.Pause]: <PauseCircleOutlined />,
  [Action.Continue]: <PlayCircleOutlined />,
  [Action.Retry]: <RedoOutlined />,
  [Action.CancelTask]: <StopOutlined />
};

const getTaskAction = (
  record: TableDataType,
  handleEvent: (type: Action, d: TableDataType) => any
) => {
  const { isOline, taskState } = record;
  if (isOline) return "-";
  const taskAction = getTaskActionArr(taskState);
  if (taskAction.length === 0) {
    return getStatusTag(taskState);
  }
  return (
    <Popover
      placement="rightTop"
      arrow={false}
      className="cursor-pointer"
      content={
        <div className="w-[76px]">
          {taskAction.map((action) => (
            <div
              key={uuidv4()}
              className="cursor-pointer h-[32px] flex items-center justify-center gap-2 px-[8px] hover:bg-[#f1f5f5]"
              onClick={() => handleEvent(action, record)}
            >
              {taskActionIcon[action]}
              {actionObj[action]}
            </div>
          ))}
        </div>
      }
      styles={{
        root: {
          padding: 0
        },
        body: {
          padding: 0
        }
      }}
    >
      {getStatusTag(taskState)}
    </Popover>
  );
};

const stateSelectOptions = [
  {
    label: "全部状态",
    value: "all"
  },
  ...Object.entries(statusText).map(([key, value]) => {
    return {
      label: value,
      value: key
    };
  })
];

const useController = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get("highlightId");

  const [listPostData, setListPostData] = useState<{
    pageNo: number;
    pageSize: number;
    totalCount: number;
    search: undefined | string;
    taskState?: DocState | "all";
  }>({
    pageNo: 1,
    pageSize: 10,
    totalCount: 0,
    search: undefined,
    taskState: "all"
  });

  const [taskDetailOpen, setTaskDetailOpen] = useState<boolean>(false);

  const [listData, setListData] = useState<TableDataType[]>([]);

  const { queryArticleList, deleteArticle, exportDoc } = useHServices({
    ...listPostData,
    taskDetailOpen: taskDetailOpen
  });

  const columns = [
    {
      title: <div className="ml-[24px]">名称</div>,
      dataIndex: "title",
      render: (text: string, record: TableDataType) => (
        <div className="flex items-center">
          {/* <img
            src={Article}
            alt="ellipse"
            className="w-[20px] h-[20px] mr-[8px]"
          /> */}
          <DocumentFileIcon size={20} className="mr-[8px]" />
          <div
            className="hover:text-[#055aff] hover:underline cursor-pointer"
            onClick={() => {
              const { isOline, taskState } = record;
              // 取消和完成能够进行编辑
              const allowEditorState = [
                DocState.success,
                DocState.failure,
                DocState.stopped
              ];
              // 在线生成的文档直接跳转到编辑页面
              if (isOline) {
                handleEvent(Action.ToWrite, record);
              }
              if (allowEditorState.includes(taskState)) {
                handleEvent(Action.ToWrite, record);
              } else {
                handleEvent(Action.View, record);
              }
            }}
          >
            {text}
          </div>
        </div>
      )
    },
    {
      title: "文档完成度",
      width: 100,
      dataIndex: "documentProgress",
      render: (_: any, record: TableDataType) => {
        const { totalSections, generatedSections, taskState, isOline } = record;
        // 没有章节信息，则认为是全文生成
        if (!totalSections)
          return (
            <div>
              1<span className="text-[#bbb]">/</span>1
            </div>
          );
        return (
          <div>
            <span
              style={{
                color: !finishStatus.includes(taskState) ? "#055aff" : ""
              }}
            >
              {generatedSections}
            </span>
            <span className="text-[#bbb]">/</span>
            {totalSections}
          </div>
        );
      }
    },
    {
      title: "来源",
      width: 100,
      dataIndex: "documentProgress",
      render: (_: any, record: TableDataType) => {
        const { isOline } = record;
        return isOline ? "在线生成" : "离线生成";
      }
    },
    {
      title: "任务状态",
      dataIndex: "taskState",
      width: 84,
      render: (_: DocState, record: TableDataType) => {
        return getTaskAction(record, handleEvent);
      }
    },
    {
      title: "任务进度",
      dataIndex: "taskProgress",
      width: 100,
      render: (_: any, record: TableDataType) => {
        const { completedTasks, totalTasks, taskState, isOline } = record;
        if (isOline) return "-";
        return (
          <div>
            <span
              style={{
                color: !finishStatus.includes(taskState) ? "#055aff" : ""
              }}
            >
              {completedTasks}
            </span>
            <span className="text-[#bbb]">/</span>
            <span>{totalTasks}</span>
          </div>
        );
      }
    },
    {
      title: "更新时间",
      dataIndex: "gmtModified",
      width: "160px",
      render: (text: string) => {
        return dayjs(text).format("YYYY-MM-DD HH:mm");
      }
    },
    {
      title: "操作",
      dataIndex: "",
      width: "194px",
      render: (_: any, record: TableDataType) => {
        return getDocAction(record, handleEvent);
      }
    }
  ];

  // 删除文档
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const deleteItems: any = useRef({});

  const closeDeleteModal = () => {
    setShowDeleteModal(false);
  };

  const showWarning = (item: any) => {
    deleteItems.current = item;
    setShowDeleteModal(true);
  };

  const confirmModal = async () => {
    if (!deleteItems.current?.id) {
      message.warning("删除文档为空");
      return;
    }
    setDeleteLoading(true);
    try {
      const res = await deleteArticle.mutateAsync(deleteItems.current.id);
      setDeleteLoading(false);
      setShowDeleteModal(false);
      if (res) {
        refresh();
      }
    } catch (e) {
      console.log("e", e);
      setDeleteLoading(false);
    }
  };

  // 导出文档
  const handleExportDoc = async (doc: TableDataType) => {
    const { generatedSections, exportType } = doc;
    if (typeof generatedSections === "number" && generatedSections < 1) {
      message.warning("文档未生成内容，无法导出");
      return;
    }
    if (doc.id) {
      const res: any = await exportDoc.mutateAsync({
        articleId: doc.id,
        version: exportType
      } as any);
      const file = new Blob([res], {
        type: "application/msword;charset=UTF-8"
      });
      const url = window.URL.createObjectURL(file);
      const a = document.createElement("a");
      a.download = `${doc.title || "export"}.${exportType || "docx"}`;
      a.href = url;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }
  };

  const onSearch = (val: string) => {
    setListPostData({
      ...listPostData,
      pageNo: 1,
      search: val
    });
  };

  const refresh = () => {
    setListPostData({
      ...listPostData,
      pageNo: 1
    });
    queryArticleList.refetch();
  };

  useEffect(() => {
    if (!queryArticleList?.data) return;
    const { details, totalCount, pageNo } = queryArticleList.data;
    setListData(
      details.map((i: any) => ({
        ...i,
        // 是否在线生成
        isOline: !i.taskType,
        // 全文没有状态，默认按已完成状态处理
        taskState: i?.taskState || 3
      }))
    );
    setListPostData({
      ...listPostData,
      totalCount,
      pageNo
    });
  }, [queryArticleList.data]);

  const onPageSizeChange = (page: number) => {
    setListPostData({
      ...listPostData,
      pageNo: page
    });
  };

  const [operationLoading, setOperationLoading] = useState(false);
  // 暂停任务
  const handlePause = async (d: any) => {
    try {
      setOperationLoading(true);
      const res = await pauseTaskByTaskId(d.taskId);
      queryArticleList.refetch();
      setOperationLoading(false);
    } catch (e) {
      setOperationLoading(false);
      console.error("暂停任务失败", e);
      return;
    }
  };
  // 继续任务
  const handleContinue = async (d: any) => {
    try {
      setOperationLoading(true);
      const res = await resumeTaskByTaskId(d.taskId);
      queryArticleList.refetch();
      setOperationLoading(false);
    } catch (e) {
      setOperationLoading(false);
      console.error("继续任务失败", e);
      return;
    }
  };
  // 重试任务
  const handleRetry = async (d: any) => {
    try {
      setOperationLoading(true);
      const res = await retryTaskBySectionIds({ taskId: d.taskId });
      queryArticleList.refetch();
      setOperationLoading(false);
    } catch (e) {
      setOperationLoading(false);
      console.error("重试任务失败", e);
      return;
    }
  };
  // 取消任务
  const handleCancel = async (d: any) => {
    try {
      setOperationLoading(true);
      const res = await cancleTaskById(d.taskId);
      queryArticleList.refetch();
      setOperationLoading(false);
    } catch (e) {
      setOperationLoading(false);
      console.error("取消任务失败", e);
      return;
    }
  };

  const handleEvent = (type: Action, d: any) => {
    switch (type) {
      case Action.Export:
        handleExportDoc(d);
        break;
      case Action.Delete:
        showWarning(d);
        break;
      case Action.ToWrite:
        if (d?.id) {
          navigate(`/docWriting/docs/${d.id}`);
        } else {
          message.warning("该文档为空");
        }
        break;
      case Action.Add:
        {
          const tempId = `temp_${uuidv4()}`;
          navigate(`/docWriting/docs/${tempId}?articleType=-3`);
        }
        break;
      case Action.OpenTaskDetal:
        setTaskDetailOpen(true);
        setCurDocTaskItem(d);
        break;
      case Action.Pause:
        handlePause(d);
        break;
      case Action.Continue:
        handleContinue(d);
        break;
      case Action.Retry:
        handleRetry(d);
        break;
      case Action.View:
        window.open(`/docWriting/docs/${d.id}/1`);
        break;
      case Action.CancelTask:
        handleCancel(d);
        break;
      default:
        return;
    }
  };

  // 处理上传
  const [fileRefresh, setFileRefresh] = useState(0);
  const handleFileChange = (event: { target: { files: any[] } }) => {
    const file = event.target.files[0];
    // const maxFileSize = 2 * 1024 * 1024; //最大上传2M文件
    // if (file.size > maxFileSize) {
    //   message.warning("文件大小不能超过2M");
    //   return;
    // }
    // navigate(`/docWriting/docs/temp_${uuidv4()}?articleTypeKey=normal`, {
    //   state: {
    //     file,
    //   },
    // });
    navigate(`/docWriting/docs/temp_${uuidv4()}?articleType=-3`, {
      state: {
        file
      }
    });
    setFileRefresh((fileRefresh) => fileRefresh + 1);
  };

  const searchValueRef = useRef("");

  // 任务详情弹窗
  const closeTaskDetail = () => {
    setTaskDetailOpen(false);
  };
  // 当前文章数据
  const [docTaskItem, setCurDocTaskItem] = useState<any>();
  // 状态筛选
  const stateSelectValueChange = (value: DocState | "all") => {
    setListPostData((prev) => ({
      ...prev,
      taskState: value,
      pageNo: 1 // 重置页码
    }));
  };
  // 状态筛选下拉框是否展开
  const [stateSelectOpen, setStateSelectOpen] = useState(false);
  const handleStateSelectToggle = () => {
    setStateSelectOpen((prev) => !prev);
  };

  return {
    listData,
    listPostData,
    columns,
    showWarning,
    showDeleteModal,
    closeDeleteModal,
    confirmModal,
    deleteLoading,
    handleExportDoc,
    onSearch,
    handleEvent,
    handleFileChange,
    fileRefresh,
    onPageSizeChange,
    searchValueRef,
    loading: queryArticleList.isLoading,
    taskDetailOpen,
    closeTaskDetail,
    docTaskItem,
    highlightId,
    operationLoading,
    stateSelectOptions,
    stateSelectValueChange,
    stateSelectOpen,
    handleStateSelectToggle
  };
};

export default useController;
