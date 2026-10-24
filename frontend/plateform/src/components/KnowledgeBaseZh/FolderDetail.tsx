/* eslint-disable no-case-declarations */
import { useLocation, useNavigate, useParams } from "react-router-dom";
import {
  useEffect,
  useState,
  useMemo,
  useRef,
  ChangeEventHandler,
  ReactNode,
  useContext
} from "react";
import {
  Button,
  Input,
  message,
  Modal,
  Pagination,
  Select,
  Table,
  Popconfirm,
  Tooltip,
  Drawer,
  ConfigProvider,
  TableProps,
  Switch,
  Tag,
  Popover
} from "antd";
import {
  SearchOutlined,
  UploadOutlined,
  PlusCircleOutlined,
  CloseOutlined,
  HolderOutlined,
  QuestionCircleOutlined
} from "@ant-design/icons";
import IconFolder from "@/assets/knowledgebase/icon-folder.svg";
import IconFile from "@/assets/knowledgebase/icon-file.svg";
import IconExcel from "@/assets/knowledgebase/icon-xls.svg";
import IconCsv from "@/assets/knowledgebase/icon-csv.svg";
import IconPdf from "@/assets/knowledgebase/icon-pdf.svg";
import IconPpt from "@/assets/knowledgebase/icon-ppt.svg";
import IconTxt from "@/assets/knowledgebase/icon-txt.svg";
import IconDoc from "@/assets/knowledgebase/icon-doc.svg";
import IconPic from "@/assets/knowledgebase/icon-pic.svg";
import IconCrumbs from "@/assets/knowledgebase/icon-crumbs.svg";
import IconKb from "@/components/AiEditor/assets/icon/icon-kb.svg";
import StatusLoading from "@/assets/gif/statusLoading.gif";
import UploadBox, { UPLOAD_EVENTS } from "./components/UploadBox";
import { batchlist, batchType } from "./components/BatchOption";
import DownloadBtn from "./components/DownloadBtn";
import SynLog from "./components/SynLogModal";
import ModifyReviseDate from "./components/ModifyReviseDate";
import { useServices } from "./service";
import {
  ANALYSIS_STATUS,
  chatPathPrefix,
  statusCfg,
  tabItems
} from "@/const/knowledgebase";
import "@/assets/styles/knowledgebase.less";
import SdqaDrawer from "@root/src/components/SdqaDrawer";
import PermisssonConfig, {
  TypeDrawConfig
} from "@root/src/pages/Components/PermissionConfig";
import { ColumnProps } from "antd/es/table";
import { formatTime, getMarkExcludeType, judgeXlS } from "@root/src/core/helps";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import EditTag from "@/assets/img/editTag.png";
import TagDrawerContent from "./components/TagDrawerContent";
import { SyntheticListenerMap } from "@dnd-kit/core/dist/hooks/utilities";
import React from "react";
import FileFolderTransferContent from "./components/FileFolderTransferContent ";
import TitleCom from "./components/TitleCom";
import dayjs from "dayjs";
import { removeNullOrUndefined } from "@root/src/core/helps/utils";

const showVideo = import.meta.env.VITE_CONFIG_SHOW_VIDEO === "true";
interface RowContextProps {
  setActivatorNodeRef?: (element: HTMLElement | null) => void;
  listeners?: SyntheticListenerMap;
}
const RowContext = React.createContext<RowContextProps>({});

const pollingTime = 5000;
let pollingInterval = null as any;

const initialPage = {
  pageNo: 1,
  pageSize: 10
};

const initialCrumbs = [{ id: null, name: "全部文件" }];
const crumbsObj = {} as any;
tabItems.forEach((i: any) => {
  crumbsObj[i.key] = [...initialCrumbs];
});
const initialStatus = "all";

interface IVersionDetail {
  kbInfo: any;
  tabKey: number | string;
  detailType: number | string;
  tableLoading: boolean;
  kbName: string;
  fetchKBDetail: () => void;
  setTableLoading: (sta: boolean) => void;
  pathPrefix?: string;
  hideQA?: boolean;
  uploadBoxOpt?: {
    docParse: boolean;
    faq: boolean;
    chunk: boolean;
  };
  operationOpt?: {
    uploadBtn?: ReactNode | false;
    newFolder?: ReactNode | false;
    moreOperation?: ReactNode | false;
    parseState?: ReactNode | false;
  };
  tableOpt?: {
    // antd Table组件传参ColumnProps, TableProps
    tableProps?: TableProps;
    column?: ColumnProps[];
    // 1，Detail组件内表格SelectChange时调用 2，选择/取消选择知识库时调用
    handleItem?: (item: any) => any;
  };
  isSelect?: boolean;
  kbId?: string;
  noPagination: boolean;
  getTableData?: (fileListInfo: any) => void;
  platform?: string;
}

interface ICrumbs {
  id: number | null;
  name: string;
}

export const getFileIcon = (fileType: string) => {
  const _type = fileType.toLocaleLowerCase();
  switch (_type) {
    case "folder":
      return getImg(IconFolder);
    case "pdf":
      return getImg(IconPdf);
    case "doc":
    case "docx":
      return getImg(IconDoc);
    case "txt":
      return getImg(IconTxt);
    case "ppt":
    case "pptx":
      return getImg(IconPpt);
    case "xls":
    case "xlsx":
      return getImg(IconExcel);
    case "csv":
      return getImg(IconCsv);
    case "png":
    case "jpg":
    case "jpeg":
      return getImg(IconPic);
    case "kb":
      return getImg(IconKb);
    default:
      return getImg(IconFile);
  }
};

const getImg = (src: any) => {
  return <img className="mr-2 relative h-5" src={src} />;
};

const FolderDetail = (props: IVersionDetail) => {
  const {
    tabKey,
    detailType,
    tableLoading,
    kbName,
    fetchKBDetail,
    setTableLoading,
    pathPrefix = chatPathPrefix,
    hideQA = false,
    uploadBoxOpt,
    operationOpt,
    tableOpt,
    isSelect = false,
    kbId,
    noPagination = false,
    getTableData,
    platform = "rag-qa",
    kbInfo
  } = props;
  const {
    filesParse,
    abstractFaq,
    getFileStatusById,
    getFaqExtractStatusById,
    deleteFileById,
    filesReviseDate,
    getFolderList,
    createFolder,
    renameFolder,
    deleteFolder,
    saveBizLabel,
    getBizLabelList,
    setFolderTransfer,
    batchTransferFolder,
    getCountApi
  } = useServices(platform);

  const params = useParams();
  const navigator = useNavigate();
  const [fileList, setFileList] = useState<any[]>([]);
  const [page, setPage] = useState(
    noPagination
      ? {
          ...initialPage,
          pageSize: 1000
        }
      : initialPage
  );
  const pageRef = useRef(
    noPagination
      ? {
          ...initialPage,
          pageSize: 1000
        }
      : initialPage
  );
  const [totalCount, setTotalCount] = useState(0);
  const totalCountRef = useRef(0);
  const [fuzzyNameOrId, setFuzzyNameOrId] = useState("");
  const fileStatusRef: any = useRef(initialStatus);
  const [fileStatus, setFileStatus] = useState<
    ANALYSIS_STATUS | undefined | string
  >(initialStatus);

  useEffect(() => {
    fileStatusRef.current = fileStatus;
  }, [fileStatus]);

  const [batchValue, setBatchValue] = useState(null);
  const [fileIds, setFileIds] = useState<Array<number>>([]);
  const [pollingResult, setPollingResult] = useState<ANALYSIS_STATUS>(
    ANALYSIS_STATUS.SUCCESS
  );

  const [isShowLog, setIsShowLog] = useState(false);
  const [curRow, setCurRow] = useState([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selectedRows, setSelectedRows] = useState<Array<any>>([]);
  const selectedRowsRef = useRef<any>([]);
  const [uploadModalOpen, setUploadOpen] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [curFileInfo, setCurFileInfo] = useState<any>({});
  const [isCreateFolderShow, setIsCreateFolderShow] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [editFolder, setEditFolder] = useState<any>(undefined);
  const [openDraw, setOpenDraw] = useState(false);
  const [btnLoading, setBtnLoading] = useState(false);
  const [drawConfig, setDrawConfig] = useState<TypeDrawConfig>({
    type: "create"
  });
  const [reviseRow, setReviseRow] = useState<any>(undefined);
  const docCrumbsRef = useRef<Array<ICrumbs>>([...initialCrumbs]);
  const faqCrumbsRef = useRef<Array<ICrumbs>>([...initialCrumbs]);
  const [crumbs, setCrumbs] = useState<any>({ ...crumbsObj });
  const kbNameRef = useRef<string>("");
  const [bizLabelList, setBizLabelList] = useState<any>([]);

  const getBizType = (data: any) => {
    if (isFaq) {
      return isFolder(data) ? 9 : 11;
    } else {
      return isFolder(data) ? 6 : 4;
    }
  };
  // variable start
  const rowSelection = {
    onChange: (_selectedRowKeys: React.Key[], _selectedRows: any) => {
      setSelectedRowKeys(_selectedRowKeys);
      setSelectedRows(_selectedRows);
      selectedRowsRef.current = [..._selectedRows];
    },
    selectedRowKeys
  };

  const isCec = useMemo(() => {
    return platform && platform === "intelbrain-dw";
  }, [platform]);

  const isFaq = useMemo(() => {
    return tabKey === tabItems[1].key;
  }, [tabKey]);

  const parseOrAbstractTxt = useMemo(() => {
    return isFaq ? "抽取" : "解析";
  }, [isFaq]);

  const getCurFolderId = () => {
    const _crumbs = isFaq ? faqCrumbsRef.current : docCrumbsRef.current;
    return _crumbs.length ? _crumbs[_crumbs.length - 1].id : null;
  };

  const batch_operations = useMemo(() => {
    return batchlist
      .filter(
        (item: any) =>
          (!item.tabKey || item.tabKey === tabKey) &&
          // cec有是否作为切片检索，且ui与常规有差异，需要单独处理
          // 交互图上，cec批量无icon，无批量文字
          (isCec ? item.isCecShow !== false : item.isCecShow !== true) &&
          !item.isVersionShow
      )
      .map((item: any) => {
        const { icon, text, value, title } = item;
        if (title === "") {
          return { ...item };
        }
        const getDisabled = () => {
          if (!fileList.length) return true;

          if (value !== batchType.PARSE_ALL && !selectedRowKeys.length)
            return true;

          switch (value) {
            case batchType.DELETE:
              return getBtnDisabled(FILE_BTN.DELETE, kbInfo.permission);
            case batchType.CREATE_SET:
              return selectedRowKeys.length < 2;
            case batchType.DISSOLVE:
              const _selectedRows = selectedRows.filter(
                (i: any) => i.kbFiles && i.kbFiles.length
              );
              return _selectedRows.some((item: any) => {
                return item?.kbFiles?.length < 2;
              });
            default:
              return getBtnDisabled(FILE_BTN.ADD, kbInfo.permission);
          }
        };
        return {
          label: (
            <div
              className="h-full px-2 flex items-center"
              style={{ height: "100%", padding: "0 10px" }}
            >
              {!isCec ? icon : null}
              <span>{isCec ? text.replace("批量", "") : text}</span>
            </div>
          ),
          value,
          disabled: getDisabled()
        };
      });
  }, [tabKey, selectedRowKeys, isCec, fileList, kbInfo]);

  const getCount = async (data: any) => {
    console.log("load");
    try {
      const res: any = await getCountApi(data);
      setTimeout(() => {
        setFileList((pre) => {
          const item = pre.find((item: any) => item.fileId == data.fileId);
          item.queue = res;
          return [...pre];
        });
      }, 50);
    } catch (error) {
      console.log(error);
    }
  };

  const renderStatusCell = (_: any, record: any) => {
    const _status = getTextByKey(record, "status");
    const _cfg = statusCfg[_status];
    if (_cfg?.status == 99) {
      return (
        <Tooltip
          placement="top"
          title={
            <div className="flex items-center">
              前方有{" "}
              {record.queue !== undefined ? (
                record.queue
              ) : (
                <img
                  src={StatusLoading}
                  width={16}
                  height={16}
                  className="h-[16px]"
                />
              )}{" "}
              个文档正在排队解析中，请耐心等待
            </div>
          }
          mouseEnterDelay={0.5}
        >
          <div
            className="flex items-center w-[80px]"
            onMouseEnter={() => {
              getCount({ fileId: record.fileId });
            }}
          >
            {getIcon(_cfg.status)}
            <div>{getStatusText(_cfg)}</div>
          </div>
        </Tooltip>
      );
    } else if (
      _cfg?.status == ANALYSIS_STATUS.FAILURE &&
      record?.synLogs?.length
    ) {
      return _cfg ? (
        <Tooltip
          placement="top"
          title={record.synLogs[0].errorMessage}
          mouseEnterDelay={0.2}
        >
          <div className="flex items-center w-[120px]">
            {getIcon(_cfg.status)}
            <div>{getStatusText(_cfg)}</div>
          </div>
        </Tooltip>
      ) : null;
    } else {
      return _cfg ? (
        <div className="flex items-center w-[120px]">
          {getIcon(_cfg.status)}
          <div>{getStatusText(_cfg)}</div>
        </div>
      ) : null;
    }
  };

  const renderCell = (val: string, record: any) => {
    return (
      <div className={`custom-header`}>{!isFolder(record) ? val : ""}</div>
    );
  };

  const renderTime = (val: string, record: any) => {
    return <div className={`custom-header`}>{formatTime(val)}</div>;
  };

  const renderSwitch = (val: boolean, record: any) => {
    // 已作为切片检索的不可切换开关，状态为解析中也不可再次发请求
    return !record.isDir ? (
      <div className="text-right pr-4">
        {/* {JSON.stringify(record)} */}
        <Switch
          disabled={
            val ||
            record.status === ANALYSIS_STATUS.ANALYSISING ||
            record.status === ANALYSIS_STATUS.PENDING ||
            record.status === ANALYSIS_STATUS.RETRY ||
            record.status === ANALYSIS_STATUS.RE_ANALYSISING
          }
          value={val}
          onChange={isNeedChunkChange(record)}
        />
      </div>
    ) : null;
  };

  const commonColumns = {
    [tabItems[0].key]: [
      {
        title: <div className="custom-header min-w-[30px]">标签</div>,
        dataIndex: "label",
        key: "label",
        render: (_: any, record: any) => {
          const tags = _ ? _.split(",") : [];
          return (
            <div className="flex items-center">
              {tags.length ? (
                <>
                  <Popover
                    placement="bottom"
                    content={
                      <div className="w-[400px]">
                        {tags.reduce((acc: any, cur: any) => {
                          return `${acc}#${cur}# `;
                        }, "")}
                      </div>
                    }
                  >
                    <Tag
                      bordered={false}
                      color="processing"
                      className="max-w-[100px] text-ellipsis *:overflow-hidden whitespace-nowrap overflow-hidden cursor-default"
                    >
                      {tags[0]}
                    </Tag>
                  </Popover>
                  {tags.length > 1 ? (
                    <Tag
                      bordered={false}
                      color="processing"
                      className="cursor-default"
                    >
                      +{tags.length}
                    </Tag>
                  ) : null}
                </>
              ) : null}
              <img
                src={EditTag}
                width={24}
                height={24}
                className={`${
                  getBtnDisabled(FILE_BTN.EDIT, record.permission)
                    ? "cursor-not-allowed opacity-50"
                    : "cursor-pointer"
                }`}
                onClick={() => {
                  if (getBtnDisabled(FILE_BTN.EDIT, record.permission)) return;
                  setDrawConfig({
                    type: "tag",
                    data: { ...record, tags }
                  });
                  setOpenDraw(true);
                }}
              />
            </div>
          );
        }
      },
      {
        title: <span className="custom-header">分块数</span>,
        dataIndex: "chunkSize",
        key: "chunkSize",
        width: 90,
        render: renderCell
      },
      {
        title: <span className="custom-header">解析方法</span>,
        dataIndex: "parseType",
        key: "parseType",
        width: 110,
        render: (val: string, record: any) => {
          let renderval;
          if (!isFolder(record)) {
            if (val == "intelligent") {
              renderval = "智能切分";
            } else if (val == "naive") {
              renderval = "自定义切片";
            } else {
              renderval = val;
            }
          } else {
            renderval = "";
          }
          return <div className={`custom-header`}>{renderval}</div>;
        }
      },
      {
        title: (
          <span className="custom-header flex items-center">
            解析状态
            <Tooltip title="排队等待状态：在光标移到该状态上时展示您当前上传文档的等待位次，表示在当前文档之前排队的解析中及待解析文档的总数">
              <QuestionCircleOutlined className="ml-[2px] w-[12px] h-[12px] cursor-pointer" />
            </Tooltip>
          </span>
        ),
        dataIndex: "status",
        key: "status",
        width: 110,
        render: renderStatusCell
      },
      {
        title: <span className="custom-header">版本修订时间</span>,
        dataIndex: "reviseDate",
        key: "reviseDate",
        minWidth: 125,
        render: renderCell
      },
      {
        title: <span className="custom-header">上传时间</span>,
        dataIndex: "uploadTime",
        key: "uploadTime",
        width: 180,
        render: renderTime
      }
    ],
    [tabItems[1].key]: [
      {
        title: <span className="custom-header">问答对数</span>,
        dataIndex: "count",
        key: "count",
        width: 120,
        render: renderCell
      },
      {
        title: <span className="custom-header">上传时间</span>,
        dataIndex: "uploadTime",
        key: "uploadTime",
        width: 195,
        render: renderTime
      },
      {
        title: (
          <span className="custom-header">
            {
              <span className="custom-header flex items-center">
                抽取状态
                <Tooltip title="排队等待状态：在光标移到该状态上时展示您当前上传文档的等待位次，表示在当前文档之前排队的抽取中及待抽取文档的总数">
                  <QuestionCircleOutlined className="ml-[2px] w-[12px] h-[12px] cursor-pointer" />
                </Tooltip>
              </span>
            }
          </span>
        ),
        dataIndex: "status",
        key: "status",
        width: 120,
        render: renderStatusCell
      }
    ],
    [tabItems[2].key]: [],
    [tabItems[3].key]: []
  };

  if (isCec) {
    // cec多内容来源列
    commonColumns[String(tabItems[0].key)][5] = {
      title: <span className="custom-header">是否作为内容来源</span>,
      dataIndex: "needChunk",
      key: "needChunk",
      width: 145,
      render: renderSwitch
    };
  }

  const columnName = {
    [tabItems[0].key]: "操",
    [tabItems[1].key]: "动"
  };

  const recordClick = (record: any, isSelect = false) => {
    if (record) {
      isFolder(record)
        ? enterFolder(record)
        : isSelect
        ? null
        : handlePreviewFile(record);
    }
  };

  const kbColumns = useMemo(
    () => [
      {
        title: <div className=" min-w-[50px]">名称</div>,
        dataIndex: "name",
        key: "name",
        render: (val: string, record: any) => {
          return (
            <TitleCom
              isFolder={isFolder(record)}
              title={val}
              icon={getFileIcon(record.type)}
              handleClick={() => recordClick(record, isSelect)}
            />
          );
        }
      },
      ...(commonColumns[tabKey] || []),
      {
        title: <span className="custom-header">{columnName[tabKey]}作</span>,
        dataIndex: "operations",
        key: "operations",
        width: 250,
        render: (_: any, record: any) => {
          const { status } = record;

          if (isFolder(record)) {
            return (
              <div className="table-btn-group-wrap">
                <>
                  <Button
                    type="link"
                    size={"small"}
                    disabled={getBtnDisabled(FILE_BTN.EDIT, record.permission)}
                    onClick={() => {
                      setDrawConfig({
                        type: "transfer",
                        data: record
                      });
                      setOpenDraw(true);
                    }}
                  >
                    转移到
                  </Button>
                  <Button
                    type="link"
                    size={"small"}
                    onClick={() => {
                      setEditFolder(record);
                      setIsCreateFolderShow(true);
                      setNewFolderName(record.name);
                    }}
                    disabled={getBtnDisabled(FILE_BTN.EDIT, record.permission)}
                  >
                    重命名
                  </Button>
                  <Button
                    size={"small"}
                    type="link"
                    onClick={() => {
                      setDrawConfig({
                        type: "permission",
                        bizType: getBizType(record),
                        data: { ...record, id: record.folderId }
                      });
                      setOpenDraw(true);
                    }}
                    disabled={getBtnDisabled(
                      FILE_BTN.AUTHORIZE,
                      record.permission
                    )}
                  >
                    授权
                  </Button>
                  <Popconfirm
                    title="删除文件"
                    description={
                      <span>
                        删除后将连同子文件一并移
                        <br />
                        除，确定要继续吗?
                      </span>
                    }
                    okText="确认"
                    cancelText="取消"
                    onConfirm={() => deleteFileByParent(record.folderId)}
                  >
                    <Button
                      type="link"
                      size={"small"}
                      disabled={
                        tableLoading ||
                        getBtnDisabled(FILE_BTN.DELETE, record.permission)
                      }
                    >
                      删除
                    </Button>
                  </Popconfirm>
                </>
              </div>
            );
          } else {
            const file_type =
              record.fileName || record.name
                ? record.fileName.split(".").slice(-1)[0]
                : record.fileType;
            const isVideo = file_type == "mp4";
            if (isVideo) {
              return (
                <div className="btn-group-row">
                  <Button
                    type="link"
                    size={"small"}
                    disabled={
                      [
                        ANALYSIS_STATUS.ANALYSISING,
                        ANALYSIS_STATUS.FAILURE,
                        ANALYSIS_STATUS.SUCCESS,
                        ANALYSIS_STATUS.RE_ANALYSISING
                      ].includes(record.status) ||
                      getBtnDisabled(
                        FILE_BTN.ANALYSIS_OR_EXTRACT,
                        record.permission
                      )
                    }
                    onClick={() =>
                      handleAnalysis(record, undefined, !!record.needChunk)
                    }
                  >
                    解析
                  </Button>
                  <Button
                    type="link"
                    size={"small"}
                    disabled={
                      status !== ANALYSIS_STATUS.SUCCESS ||
                      getBtnDisabled(FILE_BTN.VIEW, record.permission)
                    }
                    onClick={() => goChunkDetail(record)}
                  >
                    查看解析块
                  </Button>
                </div>
              );
            }
            return (
              <div className="table-btn-group-wrap">
                {renderAnalysisBtn(record)}
                <div className="btn-group-row">
                  <Popconfirm
                    title="删除文件"
                    description="确认删除该文件吗？"
                    okText="确认"
                    cancelText="取消"
                    onConfirm={() => deleteByIds([record.fileId])}
                  >
                    {renderDeleteBtn(
                      [
                        ANALYSIS_STATUS.ANALYSISING,
                        ANALYSIS_STATUS.PENDING,
                        ANALYSIS_STATUS.RETRY,
                        ANALYSIS_STATUS.RE_ANALYSISING
                      ].includes(record.status) ||
                        getBtnDisabled(FILE_BTN.DELETE, record.permission)
                    )}
                  </Popconfirm>
                </div>
                <Tooltip
                  title={() => renderSubTableOperations(record)}
                  color="#fff"
                >
                  <span style={{ color: "#055aff", cursor: "pointer" }}>
                    ...
                  </span>
                </Tooltip>
              </div>
            );
          }
        }
      }
    ],
    [tabKey, isSelect]
  );

  const renderSubTableOperations = (record: any) => {
    const { status } = record;
    return (
      <>
        <div className="btn-group-row">
          <Button
            type="link"
            size={"small"}
            disabled={getBtnDisabled(FILE_BTN.EDIT, record.permission)}
            onClick={() => {
              setDrawConfig({
                type: "transfer",
                data: record
              });
              setOpenDraw(true);
            }}
          >
            转移到
          </Button>
        </div>
        {!isFaq ? (
          <>
            {renderDownLoadBtn(record)}
            <div className="btn-group-row">
              <Button
                size={"small"}
                type="link"
                disabled={
                  status !== ANALYSIS_STATUS.SUCCESS ||
                  getBtnDisabled(FILE_BTN.DATE, record.permission)
                }
                onClick={() => setReviseRow(record)}
              >
                订正修订时间
              </Button>
            </div>

            <div className="btn-group-row">
              <Button
                type="link"
                size={"small"}
                disabled={
                  status !== ANALYSIS_STATUS.SUCCESS ||
                  getBtnDisabled(FILE_BTN.VIEW, record.permission)
                }
                onClick={() => goChunkDetail(record)}
              >
                查看解析块
              </Button>
            </div>
            {/* 单文件查看抽取结果隐藏 */}
            {/* {platform !== "rag-qa" && (
              <div className="btn-group-row">
                <Button
                  type="link"
                  size={"small"}
                  onClick={() => goExtractRes(record)}
                >
                  查看抽取结果
                </Button>
              </div>
            )} */}
            <div className="btn-group-row">{renderLogBtn(record)}</div>
          </>
        ) : (
          <>
            <div className="btn-group-row">{renderLogBtn(record)}</div>
            {renderDownLoadBtn(record)}
          </>
        )}
        <div className="btn-group-row">
          <Button
            size={"small"}
            type="link"
            onClick={() => {
              setDrawConfig({
                type: "permission",
                data: { ...record, id: record.fileId }
              });
              setOpenDraw(true);
            }}
            disabled={getBtnDisabled(FILE_BTN.AUTHORIZE, record.permission)}
          >
            授权
          </Button>
        </div>
      </>
    );
  };

  const renderLogBtn = (row: any) => {
    return (
      <Button
        type="link"
        size={"small"}
        disabled={
          [
            ANALYSIS_STATUS.NORMAL,
            ANALYSIS_STATUS.ANALYSISING,
            ANALYSIS_STATUS.PENDING,
            ANALYSIS_STATUS.RE_ANALYSISING,
            ANALYSIS_STATUS.RETRY
          ].includes(row.status) ||
          getBtnDisabled(FILE_BTN.ERROR, row.permission)
        }
        onClick={() => {
          setCurRow(row || {});
          setIsShowLog(true);
        }}
      >
        错误日志
      </Button>
    );
  };

  const renderDownLoadBtn = (row: any) => {
    return (
      <div className="btn-group-row">
        <DownloadBtn
          disabled={!getBtnDisabled(FILE_BTN.DOWNLOAD, row.permission)}
          file={Object.assign({}, row, {
            filePath: row.filePath,
            fileName: row.name
          })}
        />
      </div>
    );
  };

  const renderEditBtn = (row: any) => {
    return (
      <Button
        size={"small"}
        type="link"
        disabled={
          row.status !== ANALYSIS_STATUS.SUCCESS ||
          getBtnDisabled(FILE_BTN.EDIT, row.permission)
        }
        onClick={() => {
          navigator(
            `/chats/knowledgeBase/${kbId || params.id}/faq/${row.fileId}`,
            {
              state: {
                prevTabKey: tabKey,
                prevDetailType: detailType,
                permission: row.permission
              }
            }
          );
        }}
      >
        编辑
      </Button>
    );
  };

  const renderAnalysisBtn = (row: any) => {
    return (
      <div className="btn-group-row">
        <Button
          type="link"
          size={"small"}
          disabled={
            (isFaq
              ? [
                  ANALYSIS_STATUS.ANALYSISING,
                  ANALYSIS_STATUS.PENDING,
                  ANALYSIS_STATUS.RETRY,
                  ANALYSIS_STATUS.RE_ANALYSISING
                ].includes(row.status)
              : ![
                  ANALYSIS_STATUS.NORMAL,
                  ANALYSIS_STATUS.FAILURE,
                  ANALYSIS_STATUS.SUCCESS
                ].includes(row.status)) ||
            getBtnDisabled(FILE_BTN.ANALYSIS_OR_EXTRACT, row.permission)
          }
          onClick={() => handleAnalysis(row, undefined, !!row.needChunk)}
        >
          {row.status == ANALYSIS_STATUS.SUCCESS && "重新"}
          {parseOrAbstractTxt}
        </Button>
      </div>
    );
  };

  const renderDeleteBtn = (disabled: boolean) => {
    return (
      <Button type="link" size={"small"} disabled={disabled}>
        删除
      </Button>
    );
  };

  const getStatusText = (item: any) => {
    return item.isBranch ? item.text[tabKey] : item.text;
  };

  const getTextByKey = (record: any, key: string) => {
    return isFolder(record) ? "" : record[key] ? record[key] : "-";
  };

  const statusOptions = useMemo(() => {
    return Object.keys(statusCfg)
      .filter((a: any, b) => {
        return (
          a != ANALYSIS_STATUS.RE_ANALYSISING && a != ANALYSIS_STATUS.RETRY
        );
      })
      .map((sta: string) => {
        const item = statusCfg[sta];
        return {
          value: item.status,
          label: <div className="status-option-cell">{getStatusText(item)}</div>
        };
      });
  }, [tabKey]);

  const isFolder = (record: any) => {
    return record.isDir;
  };

  const getIcon = (sta: ANALYSIS_STATUS) => {
    const { color, isLoading } = statusCfg[sta];
    return color ? (
      isLoading ? (
        <img src={StatusLoading} className="mr-[5px]" />
      ) : (
        <span className="status-dot" style={{ background: color }}></span>
      )
    ) : null;
  };
  // variable end

  // Function start
  const fetchFileList = (p: any = {}) => {
    const { pageSize, pageNo } = pageRef.current;
    const { id } = params;
    const curFolderId = getCurFolderId();
    const _params = {
      pageSize,
      pageNo,
      fileListType: tabKey,
      kbId: kbId || id,
      fuzzy: fuzzyNameOrId,
      folderId: curFolderId,
      ...p
    } as any;
    if (isFaq) {
      if (_params.status !== initialStatus) {
        _params.faqExtractStatus = _params.status;
        delete _params.status;
      }
      delete _params.status;
    } else {
      _params.statusList = [p.status || fileStatusRef.current];
      delete _params.status;
      if (_params.statusList[0] === initialStatus) {
        delete _params.statusList;
      }
      if (
        _params.statusList &&
        _params.statusList[0] == ANALYSIS_STATUS.ANALYSISING
      ) {
        _params.statusList = [
          ANALYSIS_STATUS.ANALYSISING,
          ANALYSIS_STATUS.RE_ANALYSISING,
          ANALYSIS_STATUS.RETRY
        ];
      }
    }

    if (_params.folderId === null) {
      delete _params.folderId;
    }

    setTableLoading(true);

    getFolderList(removeNullOrUndefined(_params))
      .then((res: any) => {
        if (res) {
          const { data, limit } = res;
          setTotalCount(limit || 0);
          totalCountRef.current = limit || 0;
          setFileList([...data]);
        }
      })
      .finally(() => {
        setTableLoading(false);
        setSelectedRowKeys([]);
        setSelectedRows([]);
      });
  };

  const onPageSizeChange = (pageNo: number, pageSize: number) => {
    const _page = {
      pageNo,
      pageSize
    };
    setPage({ ..._page });
    pageRef.current = { ..._page };
    fetchFileList({ ..._page });
  };

  const resetPageNo = () => {
    const _page = {
      ...pageRef.current,
      pageNo: 1
    };
    setPage({ ..._page });
    pageRef.current = { ..._page };
  };

  const docKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      onPageSizeChange(1, page.pageSize);
    }
  };

  const goChunkDetail = (record: any) => {
    const file_type =
      record.fileName || record.name
        ? record.fileName.split(".").slice(-1)[0]
        : record.fileType;
    if (file_type == "mp4" && showVideo) {
      navigator(
        `${pathPrefix}/KnowledgeAnalyVideo/${kbId || params.id}/${
          record.fileId || record.id
        }`,
        {
          state: {
            info: record
          }
        }
      );
    } else {
      navigator(
        `${pathPrefix}/KnowledgeAnalyBlock/${kbId || params.id}/${
          record.fileId || record.id
        }`,
        {
          state: {
            prevTabKey: tabKey,
            docId: record.fileId,
            parsedFilePath: getMarkExcludeType(file_type)
              ? record.filePath
              : record.convertedFilePath || record.url,
            permission: record.permission
          }
        }
      );
    }
  };

  const goExtractRes = (record: any) => {
    navigator(
      `${pathPrefix}/indicatorExtractRes/${kbId || params.id}/${
        record.fileId || record.id
      }`
    );
  };

  const isNeedChunkChange = (record: any) => (checked: boolean) => {
    // 只处理打开操作
    checked && handleAnalysis(record, undefined, checked);
  };

  const handleAnalysis = (
    item: any,
    filesObj?: any,
    need_chunk: boolean = false,
    batchName?: batchType
  ) => {
    let _files = [];
    let _folder_ids = [];
    let _fileIds = [] as number[];
    if (item) {
      _files.push({
        folder_id: item.folderId,
        file_path: judgeXlS(item)
          ? parseFilePath(item?.filePath || "")
          : parseFilePath(item?.convertedFilePath || ""),
        file_size: item.fileSize ? `${item.fileSize}MB` : `0MB`,
        file_id: item.fileId,
        parent_file_name: item.hasParent || ""
      });
      _fileIds = [Number(item.fileId)];
    } else {
      const { folder_ids, files } = filesObj;
      if (
        folder_ids.length === 0 &&
        files.length === 0 &&
        batchName !== batchType.PARSE_ALL
      ) {
        message.warning(`暂无可以${parseOrAbstractTxt}的文件`);
        return;
      }
      _fileIds = files.map((i: any) => Number(i.file_id));
      _files = files.map((item: any) => {
        return {
          folder_id: item.folderId,
          file_path: judgeXlS(item)
            ? parseFilePath(item?.filePath || "")
            : parseFilePath(item?.convertedFilePath || ""),
          file_size: item.fileSize ? `${item.fileSize}MB` : `0MB`,
          file_id: item.fileId,
          parent_file_name: item.hasParent || ""
        };
      });
      _folder_ids = folder_ids;
    }

    const _params: any = {
      files: _files,
      folder_ids: _folder_ids,
      knowledge_base_name: kbNameRef.current,
      knowledge_base_id: kbId || params.id,
      override: true,
      is_all: batchName === batchType.PARSE_ALL
      // save_txt: isCec,
      // need_chunk
    };
    _params.is_all && delete _params.files;
    _params.is_all && delete _params.folder_ids;
    if (isCec) {
      _params.save_txt = true;
      _params.need_chunk = need_chunk;
    }
    // console.log("params", _params);

    if (
      _fileIds.length ||
      _folder_ids.length ||
      batchName === batchType.PARSE_ALL
    ) {
      setTableLoading(true);

      const _apiFn = isFaq ? abstractFaq : filesParse;
      _apiFn(_params)
        .then(() => {
          setTableLoading(false);
          message.info(`开始${parseOrAbstractTxt}文件`, 2);
          // 启动轮询
          setTimeout(() => {
            fetchFileList();
            startPolling(Array.from(new Set([...fileIds, ..._fileIds])));
          }, 0);
        })
        .catch((e) => {
          console.log(e);
          setTableLoading(false);
        });
    }
  };

  // pollingInterval start
  const startPolling = (ids: number[]) => {
    clearPollingInterval();
    pollingInterval = setInterval(() => {
      // console.log("new ids:", JSON.stringify(ids))
      const _apiFn = isFaq ? getFaqExtractStatusById : getFileStatusById;
      Promise.all(ids.map((id: number) => _apiFn(Number(id))))
        .then((res: any) => {
          const oldFileList = new Map();
          const newFileList = new Map();
          const _list = (res || []).map(
            (sta: ANALYSIS_STATUS, index: number) => {
              newFileList.set(ids[index], { status: sta });
              return { id: ids[index], sta };
            }
          );
          const _doneList = _list.filter((item: any) =>
            [ANALYSIS_STATUS.FAILURE, ANALYSIS_STATUS.SUCCESS].includes(
              item.sta
            )
          );

          fileList.forEach((item: any) => {
            oldFileList.set(item.fileId, item);
          });

          if (_doneList.length === ids.length) {
            // console.log("done");
            clearPollingInterval();
            fetchFileList();
            if (
              pollingResult === ANALYSIS_STATUS.FAILURE ||
              _doneList[0].sta === ANALYSIS_STATUS.FAILURE
            ) {
              message.warning(
                `${parseOrAbstractTxt}结束，${
                  selectedRowKeys.length > 1
                    ? `有文件${parseOrAbstractTxt}失败，请查看列表结果！`
                    : `${parseOrAbstractTxt}失败！`
                }`
              );
              setPollingResult(ANALYSIS_STATUS.SUCCESS);
            } else {
              message.success(`${parseOrAbstractTxt}完成！`);
            }
            setFileIds([]);
          } else {
            // console.log("not done")
            _doneList.forEach((item: any) => {
              const _index = ids.findIndex((id: number) => id === item.id);
              ids.splice(_index, 1);
              if (
                pollingResult === ANALYSIS_STATUS.SUCCESS &&
                item.sta === ANALYSIS_STATUS.FAILURE
              ) {
                setPollingResult(item.sta);
              }
            });
            setFileIds([...ids]);
            if (_doneList.length) {
              fetchFileList();
            } else {
              const f = ids.some((id: any) => {
                return newFileList.get(id).status != oldFileList.get(id).status;
              });
              if (f) {
                fetchFileList();
              }
            }
          }
        })
        .catch((e) => {
          console.log(e);
          clearPollingInterval();
        });
    }, pollingTime);
  };

  const clearPollingInterval = () => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  };
  // pollingInterval end

  const resetSelectKeys = (
    fileOrFolderIds: Array<string>,
    isFolder: boolean = false
  ) => {
    const ids = selectedRows
      .filter((i) => fileOrFolderIds.includes(isFolder ? i.folderId : i.fileId))
      .map((i: any) => i.id);

    const newRows = selectedRowsRef.current.filter(
      (i: any) => !ids.includes(i.id)
    );
    const newkeys = newRows.map((i: any) => String(i.id));
    setSelectedRowKeys([...newkeys]);
    setSelectedRows([...newRows]);
    selectedRowsRef.current = [...newRows];
  };

  const deleteByIds = (ids: Array<string>, isFolder: boolean = false) => {
    setTableLoading(true);
    const { pageSize, pageNo } = pageRef.current;
    const _api = isFolder ? deleteFolder : deleteFileById;
    Promise.all(ids.map((id: string) => _api(id)))
      .then((res: any) => {
        const _p = {} as any;
        if (isFolder) {
          if (res) {
            if (!ids.length) return;
            message.success("文件夹删除成功！", 2);
          }
        } else {
          const failFiles = res.filter((s: boolean) => !s);
          if (failFiles.length) {
            message.warning(
              `${failFiles.length < res.length ? "部分" : ""}文件删除失败`
            );
          } else {
            message.success("文件删除成功！", 2);
          }
          const hasDeleteNum = res.length - failFiles.length;
          if (
            pageSize * (pageNo - 1) ===
            totalCountRef.current - hasDeleteNum
          ) {
            _p.pageNo = pageNo > 1 ? pageNo - 1 : 1;
          }
        }
        fetchFileList(_p);
        fetchKBDetail();
        resetSelectKeys(ids, isFolder);
      })
      .finally(() => {
        setTableLoading(false);
      })
      .catch((e) => {
        console.log(e);
      });
  };

  const deleteFileByParent = (id: string) => {
    if (id) {
      setTableLoading(true);
      deleteFolder(id)
        .then((res) => {
          if (res) {
            message.success("删除文件夹成功！");
            fetchFileList();
          }
        })
        .finally(() => {
          setTableLoading(false);
        })
        .catch((e) => {
          console.log(e);
        });
    }
  };

  const handleSd = (type: string, data?: any) => {
    switch (type) {
      case "open":
        if (!data.convertedFilePath) {
          return message.warning("没有convertedFilePath！");
        }
        const typeArr: any = data.convertedFilePath.split(".");
        const fType: string = typeArr[typeArr.length - 1];
        const p = {
          file_source: data.convertedFilePath,
          file_name: data.name,
          file_type: fType,
          pdfPages: data.pdfPage,
          metadata: {
            source: data.filePath
          }
        };
        setCurFileInfo(p);
        setShowPreviewModal(true);
        break;
      case "close":
        setShowPreviewModal(false);
        break;
    }
  };

  const handlePreviewFile = (data: any) => {
    if (data.status !== ANALYSIS_STATUS.SUCCESS) {
      getStatusText(statusCfg[data.status]);
      message.info(
        platform === "intelbrain-dw"
          ? `文件${parseOrAbstractTxt}状态为【${getStatusText(
              statusCfg[data.status]
            )}】，无法进行预览！`
          : `文件${parseOrAbstractTxt}状态为【${getStatusText(
              statusCfg[data.status]
            )}】，无法进行单文档问答！`
      );
      return;
    }
    handleSd("open", data);
  };

  const parseFilePath = (filePath: string) => {
    const pathArr = filePath.split("/");
    return pathArr.splice(3).join("/");
  };

  const fixBatchRowData = (isSource: boolean = false) => {
    // console.log(selectedRows);
    const folders = selectedRows.filter((i: any) => i.isDir);
    const allSelectFiles = selectedRows.filter((i: any) => !i.isDir);
    const parseFiles = allSelectFiles.filter((i: any) => {
      const r = getBtnDisabled(FILE_BTN.ANALYSIS_OR_EXTRACT, i.permission);
      if (r) {
        message.warning(`文件${i.fileName}没有权限`);
      }
      return (
        ![
          ANALYSIS_STATUS.ANALYSISING,
          ANALYSIS_STATUS.PENDING,
          ANALYSIS_STATUS.RETRY,
          ANALYSIS_STATUS.RE_ANALYSISING
        ].includes(i.status) && !r
      );
    });
    const folder_ids = folders.map((i: any) => i.folderId);
    return {
      folder_ids,
      files: getFilesData(parseFiles),
      allSelectFiles: getFilesData(allSelectFiles)
    };
  };

  const getFilesData = (files: Array<any>) => {
    return files.map((i: any) => ({
      ...i,
      folder_id: i.folderId,
      file_path:
        i.type === "xlsx" || i.type === "csv"
          ? parseFilePath(i?.filePath || "")
          : parseFilePath(i?.convertedFilePath || ""),
      file_size: i.fileSize ? `${i.fileSize}MB` : `0MB`,
      file_id: i?.fileId,
      parent_file_name: i.hasParent
    }));
  };

  const handleBatchMenu = (batchName: any) => {
    if (batchName === batchType.PARSE_ALL || selectedRows.length > 0) {
      const { files, folder_ids, allSelectFiles } = fixBatchRowData();
      switch (batchName) {
        case batchType.BATCH_TRANSFER:
          setDrawConfig({
            type: "transfer",
            data: selectedRows
          });
          setOpenDraw(true);
          break;
        case batchType.PARSE_ALL:
          handleAnalysis(undefined, { files, folder_ids }, false, batchName);
          break;
        case batchType.PARSE:
          if (files?.length) {
            handleAnalysis(undefined, { files, folder_ids }, false);
          }
          break;
        case batchType.DELETE:
          const deleteFileIds = allSelectFiles
            .filter((i: any) => {
              const r = getBtnDisabled(FILE_BTN.DELETE, i.permission);
              if (r) {
                message.warning(
                  `文件${i.fileName || i.parentFileName}没有删除权限`
                );
              }
              return !r;
            })
            .map((i: any) => i.file_id);
          if (deleteFileIds.length) {
            deleteByIds(deleteFileIds);
          }
          if (folder_ids.length) {
            deleteByIds(folder_ids, true);
          }
          break;
        case batchType.SOURCE:
          handleAnalysis(undefined, { files, folder_ids }, true);
          break;
      }
      setBatchValue(null);
    }
  };

  const fuzzyNameOrIdOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    setFuzzyNameOrId(inputElement.value.trim());
  };

  const newFolderNameOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    setNewFolderName(inputElement.value.trim());
  };

  const handleUploadEvents = (action: string, payload: any) => {
    switch (action) {
      case UPLOAD_EVENTS.FILE_UPLOADED:
        fetchFileList();
        fetchKBDetail();
        break;
      case UPLOAD_EVENTS.MODAL_CLOSE:
        fetchFileList();
        fetchKBDetail();
        setUploadOpen(false);
        break;
      case UPLOAD_EVENTS.MODAL_ONLY_CLOSE:
        setUploadOpen(false);
        break;
    }
  };

  const handleStatusChange = (value: ANALYSIS_STATUS | undefined | string) => {
    setFileStatus(value);
    resetPageNo();
    fetchFileList({
      pageNo: 1,
      status: value
    });
  };

  const modifyRecordReviseDate = (
    reviseDate: string,
    callback?: () => void
  ) => {
    const params = {
      fileId: reviseRow.fileId,
      reviseDate
    };

    filesReviseDate(params)
      .then((res: any) => {
        if (res === true) {
          setReviseRow(undefined);
          fetchFileList();
        } else {
          message.error(res || "修改失败！");
        }
        callback && callback();
      })
      .catch((e) => {
        console.log(e);
        callback && callback();
      });
  };

  const pollingCheck = () => {
    // console.log(fileList);
    const _fileList = (fileList || []).filter(
      (i: any) =>
        !isFolder(i) &&
        (i.status === ANALYSIS_STATUS.ANALYSISING ||
          i.status === ANALYSIS_STATUS.PENDING ||
          i.status === ANALYSIS_STATUS.RE_ANALYSISING ||
          i.status === ANALYSIS_STATUS.RETRY)
    );

    if (!pollingInterval && _fileList.length) {
      startPolling(
        Array.from(new Set([..._fileList.map((i: any) => i.fileId)]))
      );
    }
  };

  const closeCreateFolder = () => {
    setIsCreateFolderShow(false);
    setNewFolderName("");
  };

  const createFolderConfirm = () => {
    const curFolderId = getCurFolderId();
    const _params = {
      name: newFolderName,
      kbId: kbId || params.id,
      parentId: curFolderId,
      type: tabKey
    } as any;
    const isEdit = !!(editFolder && editFolder.folderId);
    if (isEdit) {
      delete _params.type;
      _params.id = editFolder.folderId;
    }
    const _api = isEdit ? renameFolder : createFolder;
    setTableLoading(true);
    _api(_params)
      .then((res: any) => {
        if (res) {
          message.success(`${isEdit ? "重命名" : "创建"}成功！`);
          fetchFileList();
          closeCreateFolder();
        }
      })
      .finally(() => {
        setTableLoading(false);
      })
      .catch((e) => {
        console.log(e);
      });
  };

  const enterFolder = (r: any) => {
    const { folderId, name } = r;
    const _tempCrumbs = isFaq ? faqCrumbsRef.current : docCrumbsRef.current;
    const _crumbs = [...[..._tempCrumbs, { id: folderId, name }]];
    // console.log("*******进入*********", _crumbs, "**********进入*******");
    crumbsOnChange(_crumbs);
  };

  const returnFolder = (id: number | null) => {
    let _crumbs: Array<ICrumbs> = [...initialCrumbs];
    if (id !== null) {
      const _tempCrumbs = isFaq ? faqCrumbsRef.current : docCrumbsRef.current;
      const idx = _tempCrumbs.findIndex((i: any) => i.id === id);
      _crumbs = [..._tempCrumbs.slice(0, idx + 1)];
      //   console.log("*******返回*********", _crumbs, "**********返回*******");
    }
    crumbsOnChange(_crumbs);
  };

  const crumbsOnChange = (items: Array<ICrumbs>) => {
    if (isFaq) {
      faqCrumbsRef.current = [...items];
      //   console.log("add faq crumb", items);
    } else {
      docCrumbsRef.current = [...items];
      //   console.log("add doc crumb", items);
    }
    setCrumbs({ ...crumbs, [tabKey]: [...items] });
    resetPageNo();

    fetchFileList({ folderId: items[items.length - 1].id, pageNo: 1 });
  };

  const emitEvent = (type: string, data?: any) => {
    switch (type) {
      case "saveTags":
        saveBizLabelFn({
          targetId: drawConfig.data.fileId || drawConfig.data.folderId,
          label: data,
          bizType: getBizType(drawConfig.data),
          kbName: kbInfo.primitiveName
        });
        break;
    }
  };

  const saveBizLabelFn = async (data: any) => {
    try {
      setBtnLoading(true);
      const res: any = await saveBizLabel(data);
      setBtnLoading(false);
      if (res) {
        getBizLabelListFn();
        fetchFileList();
        message.success("保存成功！");
        setOpenDraw(false);
        setDrawConfig({ type: "create" });
      }
    } catch (error) {
      setBtnLoading(false);
      console.log(error);
    }
  };

  const getBizLabelListFn = async () => {
    const res = await getBizLabelList(params);
    if (res) {
      setBizLabelList(res || []);
    }
  };

  const transferFn = async (param: {
    targetFolderId: number;
    targetId: number;
  }) => {
    try {
      setBtnLoading(true);

      const res: any = await setFolderTransfer({
        ...param,
        bizType: getBizType(drawConfig.data),
        kbName: kbInfo.primitiveName
      });
      setBtnLoading(false);
      if (res.success) {
        message.success("转移成功");
        fetchFileList();
        setOpenDraw(false);
      }
    } catch (error) {
      setBtnLoading(false);
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const transferBatchFn = async (param: {
    targetFolderId: number;
    target: any[];
  }) => {
    try {
      setBtnLoading(true);
      const res: any = await batchTransferFolder({
        ...param
      });
      setBtnLoading(false);
      if (res.success) {
        message.success("转移成功");
        fetchFileList();
        setOpenDraw(false);
      }
    } catch (error) {
      setBtnLoading(false);
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const handleEvent = (type: string, data?: any) => {
    switch (type) {
      case "closeDrawer":
        setOpenDraw(false);
        break;
      case "save:transfer":
        if (Array.isArray(drawConfig.data)) {
          transferBatchFn(data);
        } else {
          transferFn(data);
        }
        break;
      case "save:addFile":
        //addFileFn(data);
        break;
    }
  };

  // Function end

  // effect start
  useEffect(() => {
    getBizLabelListFn();
    return () => {
      clearPollingInterval();
    };
  }, []);

  useEffect(() => {
    handleStatusChange(initialStatus);
  }, [tabKey]);

  useEffect(() => {
    clearPollingInterval();
    setTimeout(() => {
      pollingCheck();
    }, 1000);
  }, [fileList]);

  useEffect(() => {
    if (kbName && kbName !== kbNameRef.current) {
      kbNameRef.current = kbName;
    }
  }, [kbName]);

  useEffect(() => {
    // 将数据传出使表格由父级控制
    getTableData &&
      getTableData({
        fileList,
        folderId: getCurFolderId(),
        kbId: kbId || params.id
      });
  }, [fileList, kbId]);
  // effect end

  return (
    <div style={{ height: `calc(100% - 65px)` }}>
      {/* {JSON.stringify(selectedRowKeys)}---{tabKey} */}
      {crumbs[String(tabKey)]?.length > 1 ? (
        <div className="pt-4 flex items-center">
          <img src={IconCrumbs} />
          <span className="ml-2 crumbs-wrap">
            {crumbs[String(tabKey)].map((c: ICrumbs, idx: number) => {
              return (
                <span
                  key={`crumbs_${c.id}_${idx}`}
                  className={`${
                    idx === crumbs[String(tabKey)].length - 1
                      ? ""
                      : "crumbs-link"
                  }`}
                >
                  <span onClick={() => returnFolder(c.id)}>{c.name}</span>
                </span>
              );
            })}
          </span>
        </div>
      ) : null}
      {/* <div>{JSON.stringify(selectedRows)}111</div> */}
      <div className="w-full py-4 flex gap-4 justify-between">
        <div className="flex gap-4">
          {!operationOpt && (
            <Button
              disabled={
                tableLoading || getBtnDisabled(FILE_BTN.ADD, kbInfo.permission)
              }
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => setUploadOpen(true)}
              style={{
                background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                color: "#fff",
                border: "none"
              }}
            >
              上传
            </Button>
          )}
          {operationOpt && operationOpt.uploadBtn}
          {!operationOpt && (
            <Button
              disabled={
                tableLoading || getBtnDisabled(FILE_BTN.ADD, kbInfo.permission)
              }
              icon={<PlusCircleOutlined />}
              style={{
                color: "#055aff",
                borderColor: "#eeeeee"
              }}
              onClick={() => {
                setEditFolder(undefined);
                setIsCreateFolderShow(true);
              }}
            >
              新建文件夹
            </Button>
          )}
          {operationOpt && operationOpt.newFolder}
          {!operationOpt && (
            <Select
              allowClear
              placeholder="更多操作"
              options={batch_operations}
              style={{
                width: "120px",
                borderRadius: "10px"
              }}
              value={batchValue}
              onSelect={handleBatchMenu}
            ></Select>
          )}
          {operationOpt && operationOpt.moreOperation}
        </div>
        <div>
          {!operationOpt && (
            <Select
              placeholder="状态"
              options={[
                {
                  value: initialStatus,
                  label: (
                    <div className="status-option-cell">
                      全部{isFaq ? "抽取" : "解析"}状态
                    </div>
                  )
                }
              ].concat(statusOptions)}
              style={{
                width: "150px",
                borderRadius: "10px",
                marginRight: "10px"
              }}
              value={fileStatus}
              onChange={handleStatusChange}
            ></Select>
          )}
          {operationOpt && operationOpt.parseState}
          <Input
            value={fuzzyNameOrId}
            disabled={tableLoading}
            placeholder="搜索内容"
            style={{ width: "240px" }}
            suffix={
              <div
                className="cursor-pointer"
                onClick={() => onPageSizeChange(1, page.pageSize)}
              >
                <SearchOutlined style={{ color: "#999", fontSize: 12 }} />
              </div>
            }
            onChange={fuzzyNameOrIdOnChange}
            onKeyDown={docKeyDown}
          />
        </div>
      </div>
      <div
        className={`${
          crumbs[String(tabKey)].length > 1
            ? "h-[calc(100%-125px)]"
            : "h-[calc(100%-85px)]"
        } my-4 overflow-x-hidden overflow-y-auto kb-table-wrap`}
      >
        <Table
          rowKey={(r: any) => (isSelect ? r.customId : r.id)}
          loading={tableLoading}
          columns={isSelect ? [kbColumns[0]] : kbColumns}
          dataSource={fileList}
          pagination={false}
          rowSelection={{
            type: "checkbox",
            ...rowSelection
          }}
          rowClassName="custom-files-row"
          {...((tableOpt || {}).tableProps || {})}
        />
      </div>
      {!noPagination && (
        <Pagination
          align="end"
          disabled={tableLoading}
          total={totalCount}
          pageSize={page.pageSize}
          current={page.pageNo}
          onChange={onPageSizeChange}
          showSizeChanger={true}
          size="small"
        />
      )}
      <ModifyReviseDate
        row={reviseRow}
        cancleHandle={() => {
          setReviseRow(undefined);
        }}
        confirmHandle={modifyRecordReviseDate}
      />
      <UploadBox
        open={uploadModalOpen}
        kbId={String(kbId || params.id)}
        fileListType={Number(tabKey)}
        crumbs={crumbs[tabKey]}
        uploadEvents={handleUploadEvents}
        getCurFolderId={getCurFolderId}
        uploadBoxOpt={uploadBoxOpt}
        platform={platform}
      />
      <SdqaDrawer
        open={showPreviewModal}
        title={curFileInfo.file_name}
        close={() => handleSd("close")}
        content={curFileInfo}
        setContent={setCurFileInfo}
        hideQA={hideQA}
      />
      <Modal
        destroyOnClose={true}
        footer={null}
        open={isCreateFolderShow}
        width={620}
        onCancel={closeCreateFolder}
        title={`${editFolder && editFolder.id ? "重命名文件夹" : "新建文件夹"}`}
      >
        <div className="create-folder-ipt my-5">
          <Input
            value={newFolderName}
            disabled={tableLoading}
            placeholder="请输入文件夹名称"
            style={{
              height: "40px"
            }}
            onChange={newFolderNameOnChange}
          />
        </div>
        <div className="flex mt-5 gap-4 flex-row-reverse">
          <Button
            loading={tableLoading}
            disabled={!newFolderName}
            type="primary"
            onClick={createFolderConfirm}
            style={{
              background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
              color: "#fff"
            }}
          >
            确认
          </Button>
          <Button
            disabled={tableLoading}
            style={{
              color: "#555"
            }}
            onClick={closeCreateFolder}
          >
            取消
          </Button>
        </div>
      </Modal>
      <Drawer
        id="config-drawer"
        open={isShowLog}
        title={
          <div className="sys-log-title">
            错误日志
            <span title="关闭" onClick={() => setIsShowLog(false)}>
              X
            </span>
          </div>
        }
        placement="right"
        closable={false}
        onClose={() => setIsShowLog(false)}
        mask={true}
        maskClosable={true}
        width={668}
        style={{
          borderRadius: "8px 0 0 8px",
          boxShadow: "-4px 6px 4.5px 3px #4E528A21"
        }}
      >
        <div className="sys-log-wrap">
          <SynLog row={curRow} />
        </div>
      </Drawer>
      <ConfigProvider
        drawer={{
          styles: {
            body: { padding: 0 },
            header: { padding: "20px 20px 16px 20px" }
          }
        }}
      >
        <Drawer
          title={
            <div className="flex justify-between items-center">
              <div className="text-[16px] font-bold">
                {drawConfig.type === "permission"
                  ? "权限配置"
                  : drawConfig.type === "tag"
                  ? "标签"
                  : drawConfig.type === "transfer"
                  ? "转移到"
                  : ""}
              </div>
              <CloseOutlined
                className="cursor-pointer"
                onClick={() => setOpenDraw(false)}
              />
            </div>
          }
          closable={false}
          width={557}
          onClose={() => setOpenDraw(false)}
          open={openDraw}
          destroyOnClose
        >
          <div className="h-[calc(100vh-100px)] relative px-[20px] pt-[10px] pb-[20px]">
            {drawConfig.type === "permission" && (
              <PermisssonConfig
                drawConfig={drawConfig}
                subTitle="文档公开范围"
                bizType={getBizType(drawConfig.data)}
                type="docuRight"
              />
            )}
            {drawConfig.type === "tag" && (
              <TagDrawerContent
                drawConfig={drawConfig}
                btnLoading={btnLoading}
                emitEvent={emitEvent}
                bizLabelList={bizLabelList}
              />
            )}
            {drawConfig.type === "transfer" && (
              <FileFolderTransferContent
                drawConfig={
                  { ...drawConfig, data: drawConfig.data || {} } as any
                }
                handleEvent={handleEvent}
                btnLoading={btnLoading}
                fileListType={Number(tabKey)}
                kbName={kbInfo.primitiveName}
                isFaq={isFaq}
              />
            )}
          </div>
        </Drawer>
      </ConfigProvider>
    </div>
  );
};

export default FolderDetail;
