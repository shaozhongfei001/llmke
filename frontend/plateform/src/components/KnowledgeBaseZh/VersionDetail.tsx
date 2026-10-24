/* eslint-disable no-case-declarations */
import { useLocation, useNavigate, useParams } from "react-router-dom";
import {
  useEffect,
  useState,
  useMemo,
  useRef,
  ChangeEventHandler
} from "react";
import {
  Button,
  Spin,
  Input,
  message,
  Pagination,
  Select,
  Table,
  Popconfirm,
  Tooltip,
  Drawer,
  ConfigProvider
} from "antd";
import {
  SearchOutlined,
  CaretDownOutlined,
  CaretRightOutlined,
  CloseOutlined
} from "@ant-design/icons";
import { batchlist, batchType } from "./components/BatchOption";
import DownloadBtn from "./components/DownloadBtn";
import SynLog from "./components/SynLogModal";
import ModifyReviseDate from "./components/ModifyReviseDate";
import { useServices } from "./service";
import { ANALYSIS_STATUS, statusCfg, tabItems } from "@/const/knowledgebase";
import "@/assets/styles/knowledgebase.less";
import SdqaDrawer, { SdContentData } from "@root/src/components/SdqaDrawer";
import StatusLoading from "@/assets/gif/statusLoading.gif";
import PermisssonConfig, {
  TypeDrawConfig
} from "@root/src/pages/Components/PermissionConfig";
import {
  FILE_BTN,
  getBtnDisabled,
  PERMISSION_RULES,
  PERMISSION_STATUS
} from "@root/src/const/permission";
import { formatTime, judgeXlS } from "@root/src/core/helps";
import { useMyHttpClient } from "@root/src/apis/api/index.tsx";
import { Api } from "@root/src/apis/api/Api";
import TransferContent from "./components/TransferContent";
import AddFileContent from "./components/AddFileContent";
import TitleCom from "./components/TitleCom";
import { getFileIcon } from "./FolderDetail";
const pollingTime = 5000;
let pollingInterval = null as any;

const initialPage = {
  pageNo: 1,
  pageSize: 10
};
const initialStatus = 1;

interface IVersionDetail {
  tabKey: number | string;
  detailType: number | string;
  tableLoading: boolean;
  kbName: string;
  fetchKBDetail: () => void;
  setTableLoading: (sta: boolean) => void;
  platform?: string;
  kbInfo: any;
}

const VersionDetail = (props: IVersionDetail) => {
  const {
    tabKey,
    detailType,
    tableLoading,
    kbName,
    fetchKBDetail,
    setTableLoading,
    platform,
    kbInfo
  } = props;
  const {
    filesParse,
    abstractFaq,
    getFileStatusById,
    getFaqExtractStatusById,
    deleteFileById,
    filesReviseDate,
    getParentList
  } = useServices();
  const api = new Api(useMyHttpClient());
  const { state } = useLocation();
  const params: any = useParams();
  const navigator = useNavigate();
  const [fileList, setFileList] = useState<any[]>([]);
  const [page, setPage] = useState(initialPage);
  const pageRef = useRef(initialPage);
  const [totalCount, setTotalCount] = useState(0);
  const totalCountRef = useRef(0);
  const [fuzzyNameOrId, setFuzzyNameOrId] = useState("");
  const [fileStatus, setFileStatus] = useState<
    ANALYSIS_STATUS | undefined | string
  >(initialStatus);
  const [openDraw, setOpenDraw] = useState(false);
  const [drawConfig, setDrawConfig] = useState<TypeDrawConfig>({
    type: "create"
  });
  const [batchValue, setBatchValue] = useState(null);
  const [fileIds, setFileIds] = useState<Array<number>>([]);
  const [pollingItemList, setPollingItemList] = useState<Array<number>>([]);
  const [pollingResult, setPollingResult] = useState<ANALYSIS_STATUS>(
    ANALYSIS_STATUS.SUCCESS
  );
  const [expandedRowKeys, setExpandedRowKeys] = useState<any[]>([]);
  const [isShowLog, setIsShowLog] = useState(false);
  const [curRow, setCurRow] = useState([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selectedRows, setSelectedRows] = useState<Array<any>>([]);
  const selectedRowsRef = useRef<any>([]);
  const [btnLoading, setBtnLoading] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [curFileInfo, setCurFileInfo] = useState<SdContentData | any>({});

  const [reviseRow, setReviseRow] = useState<any>(undefined);
  const kbNameRef = useRef<string>("");

  const createCollectFn = async (params: {
    kbId: number | string;
    fileIds: number[];
    groupIds: number[];
  }) => {
    try {
      const res: any = await api.createCollect({
        ...params,
        fileListType: Number(tabKey)
      });
      if (res.success) {
        fetchFileList({
          pageNo: 1
        });
        clearSelectKeys();
      }
    } catch (error) {
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const dissolveFn = async (params: {
    kbId: number | string;
    groupIds: string[];
  }) => {
    try {
      const res: any = await api.dissolve({
        ...params,
        fileListType: Number(tabKey)
      });
      if (res.success) {
        fetchFileList({
          pageNo: 1
        });
      }
    } catch (error) {
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const transferFn = async (param: any) => {
    try {
      setBtnLoading(true);
      const res: any = await api.fileGroupTransfer({
        ...param,
        fileListType: Number(tabKey)
      });
      setBtnLoading(false);
      if (res.success) {
        message.success("转移成功");
        fetchFileList({
          pageNo: 1
        });
        setOpenDraw(false);
      }
    } catch (error) {
      setBtnLoading(false);
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  // fileRemove
  const fileRemoveFn = async (param: any) => {
    try {
      setBtnLoading(true);
      const res: any = await api.fileRemove(param);
      setBtnLoading(false);
      if (res.success) {
        message.success("移除成功");
        fetchFileList({
          pageNo: 1
        });
      }
    } catch (error) {
      setBtnLoading(false);
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const addFileFn = async (param: any) => {
    try {
      setBtnLoading(true);
      const res: any = await api.fileGroupTransfer(param);
      setBtnLoading(false);
      if (res.success) {
        message.success("新增文件成功");
        fetchFileList({
          pageNo: 1
        });
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
        transferFn(data);
        break;
      case "save:addFile":
        addFileFn(data);
        break;
    }
  };

  const clearSelectKeys = () => {
    setSelectedRowKeys([]);
    setSelectedRows([]);
    selectedRowsRef.current = [];
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

  const isFaq = useMemo(() => {
    return tabKey === tabItems[1].key;
  }, [tabKey]);

  const parseOrAbstractTxt = useMemo(() => {
    return isFaq ? "抽取" : "解析";
  }, [isFaq]);

  const isCec = useMemo(() => {
    return platform && platform === "intelbrain-dw";
  }, [platform]);

  const batch_operations = useMemo(() => {
    return batchlist
      .filter(
        (item: any) =>
          (!item.tabKey || item.tabKey === tabKey) &&
          (isCec ? item.isCecShow !== false : item.isCecShow !== true)
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
              return (
                selectedRowKeys.length < 2 ||
                getBtnDisabled(FILE_BTN.EDIT, kbInfo.permission)
              );
            case batchType.DISSOLVE:
              const _selectedRows = selectedRows.filter(
                (i: any) => i.kbFiles && i.kbFiles.length
              );
              return (
                _selectedRows.some((item: any) => {
                  return item?.kbFiles?.length < 2;
                }) || getBtnDisabled(FILE_BTN.EDIT, kbInfo.permission)
              );
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
              {icon}
              <span>{text}</span>
            </div>
          ),
          value,
          disabled: getDisabled()
        };
      });
  }, [tabKey, selectedRowKeys, fileList, kbInfo]);

  const commonColumns: any = {
    [tabItems[0].key]: [
      {
        title: <span className="custom-header">分块数</span>,
        dataIndex: "chunkSize",
        key: "chunkSize",
        width: 80,
        render: (_: any, record: any) => {
          return <>{getTextByKey(record, "chunkSize")}</>;
        }
      },
      {
        title: <span className="custom-header">解析方法</span>,
        dataIndex: "fileType",
        key: "fileType",
        width: 110,
        render: (_: any, record: any) => {
          return <>{getTextByKey(record, "fileType")}</>;
        }
      },
      {
        title: <span className="custom-header">解析状态</span>,
        dataIndex: "status",
        key: "status",
        width: 110,
        render: (_: any, record: any) => {
          const _status = getTextByKey(record, "status");
          const _cfg = statusCfg[_status];
          return _cfg ? (
            <div className="flex items-center">
              {getIcon(_cfg.status)}
              <div>{getStatusText(_cfg)}</div>
            </div>
          ) : null;
        }
      },
      {
        title: <span className="custom-header">版本修订时间</span>,
        dataIndex: "reviseDate",
        key: "reviseDate",
        width: 125,
        render: (_: any, record: any) => {
          return <>{getTextByKey(record, "reviseDate")}</>;
        }
      },
      {
        title: <span className="custom-header">上传时间</span>,
        dataIndex: "uploadTime",
        key: "uploadTime",
        width: 180,
        render: (_: any, record: any) => {
          return <>{formatTime(getTextByKey(record, "uploadTime"))}</>;
        }
      }
    ],
    [tabItems[1].key]: [
      {
        title: <span className="custom-header">问答对数</span>,
        dataIndex: "count",
        key: "count",
        width: 120,
        render: (_: any, record: any) => {
          return <>{getTextByKey(record, "count")}</>;
        }
      },
      {
        title: <span className="custom-header">上传时间</span>,
        dataIndex: "uploadTime",
        key: "uploadTime",
        width: 180,
        render: (_: any, record: any) => {
          return <>{formatTime(getTextByKey(record, "uploadTime"))}</>;
        }
      },
      {
        title: <span className="custom-header">抽取状态</span>,
        dataIndex: "faqExtractStatus",
        key: "faqExtractStatus",
        width: 120,
        render: (_: any, record: any) => {
          const _status = getTextByKey(record, "faqExtractStatus");
          const _cfg = statusCfg[_status];
          return _cfg ? (
            <>
              {getIcon(_cfg.status)}
              {getStatusText(_cfg)}
            </>
          ) : null;
        }
      }
    ],
    [tabItems[2].key]: []
  };

  // 知识库第一层table
  const columnName = {
    [tabItems[0].key]: "操",
    [tabItems[1].key]: "动"
  };
  const kbColumns = useMemo(
    () => [
      {
        title: <span className="custom-header block min-w-72">名称</span>,
        dataIndex: "fullFolderPath",
        key: "fullFolderPath",
        render: (val: string, record: any) => {
          return isMoreFiles(record) ? (
            <TitleCom
              isFolder={true}
              title={val || record.parentFileName.split(".")[0]}
              icon={getFileIcon("folder")}
              handleClick={() => {}}
            />
          ) : (
            <>
              {record.kbFiles && record.kbFiles.length ? (
                <TitleCom
                  isFolder={true}
                  title={getTextByKey(record.kbFiles[0], "fullFolderPath")}
                  icon={getFileIcon(getFileType(record.kbFiles[0]))}
                  handleClick={() => handlePreviewFile(record.kbFiles[0])}
                />
              ) : (
                "-"
              )}
            </>
          );
        }
      },
      ...commonColumns[tabKey],
      {
        title: <span className="custom-header">{columnName[tabKey]}作</span>,
        dataIndex: "operations",
        key: "operations",
        width: 250,
        render: (_: any, record: any) => {
          const _status = !isFaq
            ? record.kbFiles[0].status
            : record.kbFiles[0].faqExtractStatus;
          return isMoreFiles(record) ? (
            <div className="table-btn-group-wrap">
              <div className="btn-group-row">
                <Button
                  type="link"
                  size={"small"}
                  disabled={getBtnDisabled(FILE_BTN.EDIT, record.permission)}
                  onClick={() => {
                    setDrawConfig({
                      type: "addFile",
                      data: record
                    });
                    setOpenDraw(true);
                  }}
                >
                  新增文件
                </Button>
              </div>
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
              <div className="btn-group-row">
                <Button
                  type="link"
                  size={"small"}
                  disabled={getBtnDisabled(FILE_BTN.EDIT, record.permission)}
                  onClick={() => {
                    dissolveFn({
                      kbId: params.id,
                      groupIds: [record.groupId]
                    });
                  }}
                >
                  解散
                </Button>
              </div>
              <div className="btn-group-row">
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
                  onConfirm={() => deleteFileByParent(record)}
                >
                  {renderDeleteBtn(
                    !record.kbFiles ||
                      (record.kbFiles && !record.kbFiles.length) ||
                      getBtnDisabled(FILE_BTN.DELETE, record.permission)
                  )}
                </Popconfirm>
              </div>
            </div>
          ) : (
            <div className="table-btn-group-wrap">
              <div className="btn-group-row">
                {renderAnalysisBtn(record.kbFiles[0], _status)}
              </div>
              <div className="btn-group-row">
                <Popconfirm
                  title="删除文件"
                  description="确认删除该文件吗？"
                  okText="确认"
                  cancelText="取消"
                  onConfirm={() =>
                    deleteFileByIds([record.id], () => {
                      const { sta, parentFileName } = checkIsDelKb(record.id);
                      sta && resetSelectKeys(parentFileName);
                    })
                  }
                >
                  {renderDeleteBtn(
                    [
                      ANALYSIS_STATUS.ANALYSISING,
                      ANALYSIS_STATUS.PENDING,
                      ANALYSIS_STATUS.RETRY,
                      ANALYSIS_STATUS.RE_ANALYSISING
                    ].includes(_status) ||
                      getBtnDisabled(FILE_BTN.DELETE, record.permission)
                  )}
                </Popconfirm>
              </div>
              <Tooltip
                title={() => renderSubTableOperations(record.kbFiles[0])}
                color="#fff"
              >
                <span style={{ color: "#055aff", cursor: "pointer" }}>...</span>
              </Tooltip>
            </div>
          );
        }
      }
    ],
    [tabKey]
  );

  // 知识库第二层table
  const kbSubColumns = useMemo(
    () => [
      {
        title: <span className="custom-header">名称</span>,
        dataIndex: "fileName",
        key: "fileName",
        width: 250,
        render: (text: string, record: any) => (
          <TitleCom
            isFolder={false}
            title={text}
            icon={getFileIcon(getFileType(record))}
            handleClick={() => handlePreviewFile(record)}
          />
        )
      },
      // {
      //   title: <span className="custom-header">版本号</span>,
      //   dataIndex: "version",
      //   key: "version",
      //   width: 100,
      //   render: (val: string) => <span>{val || "-"}</span>
      // },
      ...(commonColumns?.[tabKey] || []),
      {
        title: <span className="custom-header">操作</span>,
        dataIndex: "operations",
        key: "operations",
        width: 150,
        render: (_: any, record: any) => {
          return (
            <div className="table-btn-group-wrap">
              <div className="btn-group-row">
                <Popconfirm
                  title="移除文件"
                  description="确认移除该文件吗？"
                  okText="确认"
                  cancelText="取消"
                  onConfirm={() =>
                    fileRemoveFn({
                      kbId: params.id,
                      fileIds: [record.id]
                    })
                  }
                >
                  <Button
                    type="link"
                    size={"small"}
                    disabled={getBtnDisabled(FILE_BTN.EDIT, kbInfo.permission)}
                  >
                    移除
                  </Button>
                </Popconfirm>
              </div>
              <div className="btn-group-row">
                <DownloadBtn
                  disabled={
                    !getBtnDisabled(FILE_BTN.DOWNLOAD, record.permission)
                  }
                  file={record}
                />
              </div>
              <Tooltip
                title={() => renderSubTableOperations(record, true)}
                color="#fff"
              >
                <span style={{ color: "#055aff", cursor: "pointer" }}>...</span>
              </Tooltip>
            </div>
          );
        }
      }
    ],
    [tabKey]
  );

  const getStatusText = (item: any) => {
    return item.isBranch ? item.text[tabKey] : item.text;
  };

  const statusOptions = useMemo(() => {
    return Object.keys(statusCfg).map((sta: string) => {
      const item = statusCfg[sta];
      return {
        value: item.status,
        label: <div className="status-option-cell">{getStatusText(item)}</div>
      };
    });
  }, [tabKey]);

  const renderSubTableOperations = (record: any, isSecond: boolean = false) => {
    const { status, faqExtractStatus } = record;
    const _status = !isFaq ? status : faqExtractStatus;
    return (
      <>
        <Spin spinning={pollingItemList.includes(record.id)}>
          {!isFaq ? (
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
              {!isSecond && (
                <div className="btn-group-row">
                  <DownloadBtn
                    disabled={
                      !getBtnDisabled(FILE_BTN.DOWNLOAD, record.permission)
                    }
                    file={record}
                  />
                </div>
              )}
              <div className="btn-group-row">
                <Button
                  size={"small"}
                  type="link"
                  onClick={() => setReviseRow(record)}
                  disabled={getBtnDisabled(FILE_BTN.DATE, record.permission)}
                >
                  订正修订时间
                </Button>
              </div>
            </>
          ) : (
            <>
              {isSecond
                ? renderAnalysisBtn(record, record.faqExtractStatus)
                : null}
              {isSecond ? renderEditBtn(record) : null}
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
              {isSecond ? (
                <div className="btn-group-row">
                  <Popconfirm
                    title="移除文件"
                    description="确认移除该文件吗？"
                    okText="确认"
                    cancelText="取消"
                    onConfirm={() =>
                      fileRemoveFn({
                        kbId: params.id,
                        fileIds: [record.id]
                      })
                    }
                  >
                    <Button
                      type="link"
                      size={"small"}
                      disabled={getBtnDisabled(
                        FILE_BTN.EDIT,
                        kbInfo.permission
                      )}
                    >
                      移除
                    </Button>
                  </Popconfirm>
                </div>
              ) : null}
              <div className="btn-group-row">
                <DownloadBtn
                  disabled={
                    !getBtnDisabled(FILE_BTN.DOWNLOAD, record.permission)
                  }
                  file={record}
                />
              </div>
            </>
          )}
        </Spin>
      </>
    );
  };

  const renderEditBtn = (row: any) => {
    return (
      <div className="btn-group-row">
        <Button
          size={"small"}
          type="link"
          disabled={
            row.faqExtractStatus !== ANALYSIS_STATUS.SUCCESS ||
            getBtnDisabled(FILE_BTN.EDIT, row.permission)
          }
          onClick={() => {
            navigator(`/chats/knowledgeBase/${params.id}/faq/${row.id}`, {
              state: {
                prevTabKey: tabKey,
                prevDetailType: detailType,
                permission: row.permission
              }
            });
          }}
        >
          编辑
        </Button>
      </div>
    );
  };

  const renderLogBtn = (row: any, status: ANALYSIS_STATUS) => {
    return (
      <Button
        type="link"
        size={"small"}
        disabled={
          status === ANALYSIS_STATUS.NORMAL ||
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

  const renderAnalysisBtn = (row: any, status: ANALYSIS_STATUS) => {
    return (
      <Button
        type="link"
        size={"small"}
        disabled={
          (isFaq
            ? [
                ANALYSIS_STATUS.ANALYSISING,
                ANALYSIS_STATUS.RE_ANALYSISING,
                ANALYSIS_STATUS.PENDING,
                ANALYSIS_STATUS.RETRY
              ].includes(status)
            : ![
                ANALYSIS_STATUS.NORMAL,
                ANALYSIS_STATUS.FAILURE,
                ANALYSIS_STATUS.SUCCESS
              ].includes(status)) ||
          getBtnDisabled(FILE_BTN.ANALYSIS_OR_EXTRACT, row.permission)
        }
        onClick={() => handleAnalysis(row)}
      >
        {row.status == ANALYSIS_STATUS.SUCCESS && "重新"}
        {parseOrAbstractTxt}
      </Button>
    );
  };

  const renderDeleteBtn = (disabled: boolean) => {
    return (
      <Button type="link" size={"small"} disabled={disabled}>
        删除
      </Button>
    );
  };

  const getTextByKey = (record: any, key: string) => {
    return isMoreFiles(record)
      ? ""
      : !record.kbFiles
      ? record[key]
      : record.kbFiles[0][key];
  };

  const getFileType = (record: any) => {
    const { fileName } = record;
    if (fileName) {
      const fileParts = fileName.split(".");
      return fileParts[fileParts.length - 1];
    } else {
      return "";
    }
  };

  const kbExpandedRowRender = () => {
    return {
      expandedRowRender: (record: any) => {
        const { kbFiles } = record;
        console.log("kbFiles", kbFiles);

        return isMoreFiles(record) ? (
          <div className="expand-table">
            {/* <div>{JSON.stringify(kbFiles)}</div> */}
            <Table
              rowKey="id"
              columns={kbSubColumns}
              dataSource={JSON.parse(JSON.stringify(kbFiles))}
              pagination={false}
              scroll={{ y: 400 }}
            />
          </div>
        ) : null;
      },
      expandIcon: ({ expanded, onExpand, record }: any) =>
        isMoreFiles(record) ? (
          expanded ? (
            <CaretDownOutlined onClick={(e) => onExpand(record, e)} />
          ) : (
            <CaretRightOutlined onClick={(e) => onExpand(record, e)} />
          )
        ) : null
    };
  };

  const isMoreFiles = (record: any) => {
    return record.kbFiles && record.kbFiles.length > 1;
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
    // let _icon: any;
    // let isAnimation = false;
    // switch (sta) {
    //   case ANALYSIS_STATUS.NORMAL:
    //     _icon = iconStatus1;
    //     break;
    //   case ANALYSIS_STATUS.ANALYSISING:
    //     isAnimation = true;
    //     _icon = iconStatus2;
    //     break;
    //   case ANALYSIS_STATUS.SUCCESS:
    //     _icon = iconStatus3;
    //     break;
    //   case ANALYSIS_STATUS.FAILURE:
    //     _icon = iconStatus4;
    //     break;
    // }
    // return _icon ? (
    //   <img
    //     src={_icon}
    //     className={`${isAnimation ? "icon-animation-circle " : ""}status-icon`}
    //   />
    // ) : null;
  };
  // variable end

  // Function start
  const checkIsDelKb = (id: string) => {
    const res = {
      sta: false,
      parentFileName: undefined
    };
    const _row = (selectedRowsRef.current || []).find((s: any) =>
      (s.kbFiles || []).map((i: any) => i.id).includes(id)
    );
    if (_row && _row.kbId && _row.kbFiles.length === 1) {
      res.sta = true;
      res.parentFileName = _row.parentFileName;
    }
    return res;
  };

  const fetchFileList = (p: any = {}) => {
    const { pageSize, pageNo } = pageRef.current;
    const { id } = params;
    const _params = {
      pageSize,
      pageNo,
      fileListType: tabKey,
      kbId: id,
      fuzzy: fuzzyNameOrId,
      showType: fileStatus,
      ...p
    };

    const { status } = _params;

    if (status !== initialStatus) {
      if (isFaq) {
        _params.faqExtractStatus = status;
        delete _params.status;
      }
    } else {
      delete _params.status;
    }

    setTableLoading(true);
    // console.log(_params);
    getParentList(_params)
      .then((res: any) => {
        const { records, total } = res;
        if (records) {
          setTotalCount(total || 0);
          totalCountRef.current = total || 0;
          const { pageNo, pageSize } = pageRef.current;
          if (pageNo > 1 && pageSize * (pageNo - 1) === totalCountRef.current) {
            const _page = {
              ...pageRef.current,
              pageNo: pageNo > 1 ? pageNo - 1 : 1
            };
            setPage({
              ..._page
            });
            pageRef.current = { ..._page };
          } else {
            setFileList([...records]);
          }
        }
      })
      .finally(() => {
        setTableLoading(false);
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

  const handleAnalysis = (
    item: any,
    file_path?: any,
    batchName?: batchType
  ) => {
    const _files = [];
    let _fileIds = [] as number[];
    if (item) {
      _files.push({
        folder_id: item.folderId,
        file_path: judgeXlS(item)
          ? parseFilePath(item?.filePath || "")
          : parseFilePath(item?.convertedFilePath || ""),
        file_size: item.fileSize ? `${item.fileSize}MB` : `0MB`,
        file_id: item.id,
        parent_file_name: item.parentFileName
      });
      _fileIds = [Number(item.id)];
    } else {
      if (file_path.length === 0 && batchName !== batchType.PARSE_ALL) {
        message.warning(`暂无可以${parseOrAbstractTxt}的文件`);
        return;
      }
      _fileIds = (selectedRows || [])
        .map((i) => i.kbFiles)
        .flat(Infinity)
        // .filter((s: any) => s.status !== ANALYSIS_STATUS.SUCCESS)
        .map((s: any) => Number(s.id));
    }
    setPollingItemList([..._fileIds]);

    const _params: any = {
      files: _files.length ? _files : file_path,
      knowledge_base_name: kbNameRef.current,
      knowledge_base_id: params.id,
      override: true,
      is_all: batchName === batchType.PARSE_ALL
    };

    _params.is_all && delete _params.files;
    _params.is_all && delete _params.folder_ids;

    // console.log("params", params);

    if (_fileIds.length || batchName === batchType.PARSE_ALL) {
      setTableLoading(true);

      const _apiFn = isFaq ? abstractFaq : filesParse;
      _apiFn(_params)
        .then(() => {
          setTableLoading(false);
          message.info(`开始${parseOrAbstractTxt}文件`, 2);
          // 启动轮询
          setTimeout(() => {
            console.log("1");
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
          const _list = (res || []).map(
            (sta: ANALYSIS_STATUS, index: number) => {
              return { id: ids[index], sta };
            }
          );
          const _doneList = _list.filter((item: any) =>
            [ANALYSIS_STATUS.FAILURE, ANALYSIS_STATUS.SUCCESS].includes(
              item.sta
            )
          );
          const _notDoneList = _list
            .filter((item: any) =>
              [
                ANALYSIS_STATUS.ANALYSISING,
                ANALYSIS_STATUS.RE_ANALYSISING,
                ANALYSIS_STATUS.PENDING,
                ANALYSIS_STATUS.RETRY
              ].includes(item.sta)
            )
            .map((i: any) => i.id);
          setPollingItemList(_notDoneList);

          // console.log("has done:", JSON.stringify(_doneList))
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

  const resetSelectKeys = (parentFileName?: string | undefined) => {
    const _parentFileNames = parentFileName
      ? [parentFileName]
      : selectedRowsRef.current.map((r: any) => String(r.parentFileName));
    const newRows = selectedRowsRef.current.filter(
      (item: any) => !_parentFileNames.includes(item.parentFileName)
    );
    const newkeys = newRows.map((r: any) => String(r.parentFileName));
    setSelectedRowKeys([...newkeys]);
    setSelectedRows([...newRows]);
    selectedRowsRef.current = [...newRows];
  };

  const deleteFileByIds = (ids: Array<string>, cb?: any) => {
    setTableLoading(true);
    Promise.all(ids.map((id: string) => deleteFileById(id)))
      .then((res: any) => {
        const failFiles = res.filter((s: boolean) => !s);
        if (failFiles.length) {
          message.warning(
            `${failFiles.length < res.length ? "部分" : ""}文件删除失败`
          );
        } else {
          if (!ids.length) return;
          message.success("文件删除成功！", 2);
        }

        fetchFileList();
        fetchKBDetail();
        setTimeout(() => {
          cb && cb();
        }, 1000);
      })
      .finally(() => {
        setTableLoading(false);
      })
      .catch((e) => {
        console.log(e);
      });
  };

  const deleteFileByParent = (row: any) => {
    const { kbFiles, parentFileName } = row;

    if (kbFiles && kbFiles.length) {
      deleteFileByIds(
        kbFiles.map((i: any) => i.id),
        () => {
          resetSelectKeys(parentFileName);
        }
      );
    }
  };

  const handlePreviewFile = (data: any) => {
    if (data.status !== ANALYSIS_STATUS.SUCCESS) {
      getStatusText(statusCfg[data.status]);
      message.info(
        `文件${parseOrAbstractTxt}状态为【${getStatusText(
          statusCfg[data.status]
        )}】，无法进行单文档问答！`
      );
      return;
    }
    handleSd("open", data);
  };

  const parseFilePath = (convertedFilePath: string) => {
    const pathArr = convertedFilePath.split("/");
    return pathArr.splice(3).join("/");
  };

  const handleBatchMenu = (batchName: any) => {
    if (batchName === batchType.PARSE_ALL || selectedRows.length > 0) {
      const _selectedRows = selectedRows.filter(
        (i: any) => i.kbFiles && i.kbFiles.length
      );
      switch (batchName) {
        case batchType.DISSOLVE:
          dissolveFn({
            kbId: params.id,
            groupIds: selectedRows
              .filter((item: any) => {
                return isMoreFiles(item);
              })
              .map((item: any) => item.groupId)
          });
          break;
        case batchType.BATCH_TRANSFER:
          setDrawConfig({
            type: "transfer",
            data: _selectedRows
          });
          setOpenDraw(true);
          break;
        case batchType.CREATE_SET:
          createCollectFn({
            kbId: params.id,
            fileIds: _selectedRows
              .filter((item: any) => !isMoreFiles(item))
              .map((item: any) => item.id),
            groupIds: _selectedRows
              .filter((item: any) => isMoreFiles(item))
              .map((item: any) => item.groupId)
          });
          break;
        case batchType.PARSE_ALL:
        case batchType.PARSE:
          handleAnalysis(
            undefined,
            _selectedRows
              .map((i: any) =>
                i.kbFiles.map((j: any) =>
                  Object.assign({}, j, {
                    parent_file_name: i.parentFileName
                  })
                )
              )
              .flat(Infinity)
              .filter((i: any) => {
                const r = getBtnDisabled(
                  FILE_BTN.ANALYSIS_OR_EXTRACT,
                  i.permission
                );
                if (r) {
                  message.warning(`文件${i.fileName}没有权限`);
                }
                return (
                  ![
                    ANALYSIS_STATUS.ANALYSISING,
                    ANALYSIS_STATUS.RE_ANALYSISING,
                    ANALYSIS_STATUS.PENDING,
                    ANALYSIS_STATUS.RETRY
                  ].includes(i.status) && !r
                );
              })
              .map((i: any) => ({
                folder_id: i.folderId,
                file_path: judgeXlS(i)
                  ? parseFilePath(i?.filePath || "")
                  : parseFilePath(i?.convertedFilePath || ""),
                file_size: i.fileSize ? `${i.fileSize}MB` : "0MB",
                file_id: i?.id,
                parent_file_name: i.parentFileName
                // status: k.status,
              })),
            batchName
          );
          break;
        case batchType.DELETE:
          deleteFileByIds(
            _selectedRows
              .filter((i: any) => {
                const r = getBtnDisabled(FILE_BTN.DELETE, i.permission);
                if (r) {
                  message.warning(
                    `文件${i.fileName || i.parentFileName}没有删除权限`
                  );
                  return false;
                }
                return !r;
              })
              .map((i: any) => i.kbFiles.map((j: any) => j.id))
              .flat(Infinity),
            resetSelectKeys
          );
          break;
      }
      setBatchValue(null);
    }
  };

  const fuzzyNameOrIdOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    setFuzzyNameOrId(inputElement.value.trim());
  };

  //   const handleUploadEvents = (action: string, payload: any) => {
  //     switch (action) {
  //       case UPLOAD_EVENTS.FILE_UPLOADED:
  //         fetchFileList();
  //         fetchKBDetail();
  //         break;
  //       case UPLOAD_EVENTS.MODAL_CLOSE:
  //         fetchFileList();
  //         fetchKBDetail();
  //         setUploadOpen(false);
  //         break;
  //       case UPLOAD_EVENTS.MODAL_ONLY_CLOSE:
  //         setUploadOpen(false);
  //         break;
  //     }
  //   };

  const hanldeRowExpand = (expanded: boolean, record: any) => {
    setExpandedRowKeys((prevKeys) =>
      expanded
        ? [...prevKeys, record.parentFileName]
        : prevKeys.filter((key) => key !== record.parentFileName)
    );
  };

  const handleStatusChange = (value: ANALYSIS_STATUS | undefined | string) => {
    setFileStatus(value);
    resetPageNo();
    fetchFileList({
      pageNo: 1,
      showType: value
    });
  };

  const modifyRecordReviseDate = (
    reviseDate: string,
    callback?: () => void
  ) => {
    const params = {
      fileId: reviseRow.id,
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
    const _fileList = (fileList || [])
      .map((i: any) => i.kbFiles)
      .flat(Infinity)
      .filter((i: any) =>
        !isFaq
          ? [
              ANALYSIS_STATUS.ANALYSISING,
              ANALYSIS_STATUS.PENDING,
              ANALYSIS_STATUS.RETRY,
              ANALYSIS_STATUS.RE_ANALYSISING
            ].includes(i.status)
          : [
              ANALYSIS_STATUS.ANALYSISING,
              ANALYSIS_STATUS.PENDING,
              ANALYSIS_STATUS.RETRY,
              ANALYSIS_STATUS.RE_ANALYSISING
            ].includes(i.faqExtractStatus)
      );
    if (!pollingInterval && _fileList.length) {
      startPolling(Array.from(new Set([..._fileList.map((i: any) => i.id)])));
    }
  };

  const expandedRowCheck = () => {
    if (expandedRowKeys.length > 0) {
      const _files = fileList.filter((i) =>
        expandedRowKeys.some((j) => j === i.parentFileName)
      );
      const _expandedRowKeys = [] as any;
      (_files || []).forEach((i: any) => {
        const { parentFileName, kbFiles } = i;
        if (kbFiles && kbFiles.length > 1) {
          _expandedRowKeys.push(parentFileName);
        }
      });
      setExpandedRowKeys([..._expandedRowKeys]);
    }
  };
  console.log("fileList", fileList);

  const renderTable = () => {
    return (
      <Table
        rowKey={(r: any) => String(r.parentFileName)}
        loading={tableLoading}
        columns={kbColumns}
        dataSource={fileList}
        pagination={false}
        scroll={{
          y: "calc(100vh - 510px)"
        }}
        expandable={{
          expandedRowKeys,
          onExpand: hanldeRowExpand,
          ...kbExpandedRowRender()
        }}
        rowSelection={{
          type: "checkbox",
          ...rowSelection
        }}
        rowClassName="custom-files-row"
      />
    );
  };

  const handleSd = (type: string, data?: any) => {
    switch (type) {
      case "open":
        if (!data.convertedFilePath) {
          return message.warning("没有convertedFilePath！");
        }
        const typeArr: any = data.convertedFilePath.split(".");
        const fType: string = typeArr[typeArr.length - 1];
        const name = data.fileName || data.name;
        const oTypeArr: any = name.split(".");
        const oType: any = oTypeArr[oTypeArr.length - 1];
        const p = {
          file_source: data.convertedFilePath,
          file_name: name,
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

  // effect start
  useEffect(() => {
    return () => {
      clearPollingInterval();
    };
  }, []);

  useEffect(() => {
    handleStatusChange(initialStatus);
  }, [tabKey]);

  useEffect(() => {
    clearPollingInterval();
    expandedRowCheck();
    setTimeout(() => {
      pollingCheck();
    }, 1000);
  }, [fileList]);

  useEffect(() => {
    if (kbName && kbName !== kbNameRef.current) {
      kbNameRef.current = kbName;
    }
  }, [kbName]);
  // effect end
  return (
    <>
      <div style={{ height: `calc(100% - 65px)` }}>
        <div className="w-full py-4 flex gap-4 justify-between">
          <div className="flex gap-4">
            {/* <Button
              disabled={tableLoading}
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => setUploadOpen(true)}
              style={{
                background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
              }}
            >
              上传
            </Button> */}
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
          </div>
          <div>
            <Select
              // allowClear
              placeholder="状态"
              options={[
                {
                  value: 1,
                  label: <div className="status-option-cell">显示全部文件</div>
                },
                {
                  value: 2,
                  label: (
                    <div className="status-option-cell">只显示版本集合</div>
                  )
                }
              ]}
              style={{
                width: "150px",
                borderRadius: "10px",
                marginRight: "10px"
              }}
              value={fileStatus}
              onChange={handleStatusChange}
            ></Select>
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
        <div className="h-[calc(100%-85px)] my-4 overflow-hidden kb-table-wrap ">
          {renderTable()}
        </div>
        <SdqaDrawer
          open={showPreviewModal}
          title={curFileInfo.file_name}
          close={() => handleSd("close")}
          content={curFileInfo}
          setContent={setCurFileInfo}
        />
        <Pagination
          align="end"
          disabled={tableLoading}
          total={totalCount}
          pageSize={page.pageSize}
          current={page.pageNo}
          onChange={onPageSizeChange}
          showSizeChanger={false}
          size="small"
        />
        <ModifyReviseDate
          row={reviseRow}
          cancleHandle={() => {
            setReviseRow(undefined);
          }}
          confirmHandle={modifyRecordReviseDate}
        />
      </div>
      <Drawer
        id="config-drawer"
        open={isShowLog}
        title={
          <div className="sys-log-title">
            错误日志
            <span title="关闭" onClick={() => setIsShowLog(false)}></span>
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
              <div className="text-[16px] font-bold">{`${
                drawConfig.type === "permission"
                  ? "权限配置"
                  : drawConfig.type === "create"
                  ? "新建会话助手"
                  : drawConfig.type === "view"
                  ? "会话助手详情"
                  : drawConfig.type === "transfer"
                  ? "转移到"
                  : drawConfig.type === "addFile"
                  ? "新增文件"
                  : "编辑会话助手"
              }`}</div>
              <CloseOutlined
                className="cursor-pointer"
                onClick={() => setOpenDraw(false)}
              />
            </div>
          }
          closable={false}
          width={557}
          destroyOnClose
          onClose={() => setOpenDraw(false)}
          open={openDraw}
        >
          <div className="h-[calc(100vh-61px)] relative px-[20px] pt-[10px] pb-[20px]">
            {drawConfig.type === "permission" && (
              <PermisssonConfig
                drawConfig={drawConfig}
                subTitle="文档公开范围"
                bizType={4}
                type="docuRight"
              />
            )}
            {drawConfig.type === "transfer" && (
              <TransferContent
                drawConfig={
                  { ...drawConfig, data: drawConfig.data || {} } as any
                }
                handleEvent={handleEvent}
                btnLoading={btnLoading}
                isFaq={isFaq}
                fileListType={Number(tabKey)}
              />
            )}
            {drawConfig.type === "addFile" && (
              <AddFileContent
                drawConfig={
                  { ...drawConfig, data: drawConfig.data || {} } as any
                }
                handleEvent={handleEvent}
                btnLoading={btnLoading}
                isFaq={isFaq}
              />
            )}
          </div>
        </Drawer>
      </ConfigProvider>
    </>
  );
};

export default VersionDetail;
