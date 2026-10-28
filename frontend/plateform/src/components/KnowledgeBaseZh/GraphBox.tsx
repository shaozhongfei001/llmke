import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState, useRef, ChangeEventHandler } from "react";
import {
  Button,
  Input,
  message,
  Pagination,
  Popconfirm,
  Table,
  Tooltip
} from "antd";
import {
  QuestionCircleOutlined,
  SearchOutlined,
  UploadOutlined
} from "@ant-design/icons";
import IconCrumbs from "@/assets/knowledgebase/icon-crumbs.svg";
import StatusLoading from "@/assets/gif/statusLoading.gif";

import UploadBox, { UPLOAD_EVENTS } from "./components/UploadBox";
import { useServices } from "./service";
import { getWholeGraphSearch } from "./common/faqService";
import { ANALYSIS_STATUS, statusCfg, tabItems } from "@/const/knowledgebase";
import { getFileIcon } from "./FolderDetail";
import GraphDetail from "./GraphDetail";
import "@/assets/styles/knowledgebase.less";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";

const pollingTime = 30000;
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
interface IVersionDetail {
  kbInfo: any;
  tabKey: number | string;
  detailType: number | string;
  tableLoading: boolean;
  kbName: string;
  fetchKBDetail: () => void;
  setTableLoading: (sta: boolean) => void;
}
interface ICrumbs {
  id: number | null;
  name: string;
}

const GraphBox = (props: IVersionDetail) => {
  const [showGraph, setShowGraph] = useState(false);
  const [gientechServer, setGientechServera] = useState<any>({});

  return (
    <>
      {showGraph ? (
        <GraphDetail
          gientechServer={gientechServer}
          setShowGraph={setShowGraph}
          kbInfo={props.kbInfo}
        />
      ) : (
        <GraphList
          {...props}
          setShowGraph={setShowGraph}
          setGientechServera={setGientechServera}
        />
      )}
    </>
  );
};
// 列表
const GraphList = (
  props: IVersionDetail & {
    setShowGraph: (arg: boolean) => void;
    setGientechServera: (data: any) => void;
    kbInfo: any;
  }
) => {
  const {
    tabKey,
    tableLoading,
    kbName,
    setTableLoading,
    setShowGraph,
    fetchKBDetail,
    setGientechServera,
    kbInfo
  } = props;
  // R14-LIVE-05：图空间的键是知识库的原始名（primitiveName，如 kb_9），不是中文展示名。
  // 原实现把 kbName（"R12验收主链"）直接当 spaceName 传给 /graph/*，
  // 后端拼成 g_R12验收主链 这个不存在的空间 -> NebulaGraph pool init failed -> 页面空白。
  // 实测：spaceName=kb_9 -> 200（g_kb_9，87 节点）；spaceName=R12验收主链 -> 500。
  const graphSpace = kbInfo?.primitiveName || kbName;
  const {
    getGraphParseStatusById,
    getFolderList,
    graphParse,
    deleteFileById,
    getCountApi
  } = useServices();
  const params = useParams();
  const [fileList, setFileList] = useState<any[]>([]);
  const [page, setPage] = useState(initialPage);
  const pageRef = useRef(initialPage);
  const [totalCount, setTotalCount] = useState(0);
  const totalCountRef = useRef(0);
  const [fuzzyNameOrId, setFuzzyNameOrId] = useState("");

  const [fileIds, setFileIds] = useState<Array<number>>([]);
  const [pollingResult, setPollingResult] = useState<ANALYSIS_STATUS>(
    ANALYSIS_STATUS.SUCCESS
  );

  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const docCrumbsRef = useRef<Array<ICrumbs>>([...initialCrumbs]);
  const [crumbs, setCrumbs] = useState<any>({ ...crumbsObj });
  const kbNameRef = useRef<string>("");
  const [uploadModalOpen, setUploadOpen] = useState(false);
  const [curFileInfo, setCurFileInfo] = useState<any>({});
  const rowSelection = {
    onChange: (_selectedRowKeys: React.Key[], _selectedRows: any) => {
      setSelectedRowKeys(_selectedRowKeys);
    },
    selectedRowKeys
  };

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

  const getCurFolderId = () => {
    const _crumbs = docCrumbsRef.current;
    return _crumbs.length ? _crumbs[_crumbs.length - 1].id : null;
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
    }
    return _cfg ? (
      <div className="flex items-center">
        {getIcon(_cfg.status)}
        {getStatusText(_cfg)}
      </div>
    ) : null;
  };

  const renderCell = (val: string, record: any) => {
    return (
      <span className={`custom-header`}>{!isFolder(record) ? val : ""}</span>
    );
  };

  const kbColumns = [
    {
      title: <span className="custom-header block min-w-72 pl-5">名称</span>,
      dataIndex: "name",
      key: "name",
      render: (val: string, record: any) => {
        return (
          <span className={`custom-header`}>
            <span
              onClick={() =>
                isFolder(record)
                  ? enterFolder(record)
                  : handlePreviewFile(record)
              }
              className={`${
                isFolder(record) ? "text-[#2a2a2a]" : "text-[#305eba]"
              } cursor-pointer flex`}
            >
              {getFileIcon(record.type)}
              <span>{val}</span>
            </span>
          </span>
        );
      }
    },
    {
      title: <span className="custom-header">节点数</span>,
      dataIndex: "nodeCount",
      key: "nodeCount",
      width: 100,
      render: renderCell
    },
    {
      title: <span className="custom-header">关系数</span>,
      dataIndex: "edgeCount",
      key: "edgeCount",
      width: 100,
      render: renderCell
    },
    {
      title: (
        <span className="custom-header">
          {
            <span className="custom-header flex items-center">
              图谱解析状态
              <Tooltip title="排队等待状态：在光标移到该状态上时展示您当前上传文档的等待位次，表示在当前文档之前排队的解析中及待解析文档的总数">
                <QuestionCircleOutlined className="ml-[2px] w-[12px] h-[12px] cursor-pointer" />
              </Tooltip>
            </span>
          }
        </span>
      ),
      dataIndex: "status",
      key: "status",
      width: 150,
      render: renderStatusCell
    },
    {
      title: <span className="custom-header">操作</span>,
      dataIndex: "operations",
      key: "operations",
      width: 140,
      render: (_: any, record: any) => {
        return <div className="table-btn-group-wrap">{renderBtn(record)}</div>;
      }
    }
  ];
  const deleteFile = (id: string) => {
    if (id) {
      setTableLoading(true);
      deleteFileById(id)
        .then((res: any) => {
          if (res) {
            message.success("删除文件成功！");
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

  const renderBtn = (record: any) => {
    const { status } = record;
    const deleteBtn = (
      <Popconfirm
        title="删除文件"
        description="确认删除该文件吗？"
        okText="确认"
        cancelText="取消"
        onConfirm={() => deleteFile(record.fileId)}
      >
        <Button
          type="link"
          size={"small"}
          disabled={
            tableLoading || getBtnDisabled(FILE_BTN.DELETE, kbInfo.permission)
          }
        >
          删除
        </Button>
      </Popconfirm>
    );
    if (status) {
      switch (status) {
        case ANALYSIS_STATUS.NORMAL:
        case ANALYSIS_STATUS.ANALYSISING:
        case ANALYSIS_STATUS.RE_ANALYSISING:
        case ANALYSIS_STATUS.PENDING:
        case ANALYSIS_STATUS.RETRY:
          return (
            <>
              <Button
                type="link"
                size={"small"}
                disabled={
                  status === ANALYSIS_STATUS.ANALYSISING ||
                  status === ANALYSIS_STATUS.PENDING ||
                  status === ANALYSIS_STATUS.RETRY ||
                  status === ANALYSIS_STATUS.RE_ANALYSISING ||
                  getBtnDisabled(FILE_BTN.ADD, kbInfo.permission)
                }
                onClick={parseGraphRow(record)}
              >
                图谱解析
              </Button>
              {deleteBtn}
            </>
          );
        case ANALYSIS_STATUS.FAILURE:
          return (
            <>
              {" "}
              <Button
                type="link"
                size={"small"}
                onClick={parseGraphRow(record)}
                disabled={getBtnDisabled(FILE_BTN.ADD, kbInfo.permission)}
              >
                重新解析
              </Button>
              {deleteBtn}
            </>
          );
        case ANALYSIS_STATUS.SUCCESS:
          return (
            <>
              <Button
                type="link"
                size={"small"}
                onClick={showGraphByRowHandler(record)}
              >
                可视化图谱
              </Button>
              {deleteBtn}
            </>
          );
      }
    }
    return null;
  };

  const getStatusText = (item: any) => {
    return item.isBranch ? item.text[tabKey] : item.text;
  };

  const getTextByKey = (record: any, key: string) => {
    return isFolder(record) ? "" : record[key] ? record[key] : "-";
  };

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
      fileListType: 3,
      kbId: id,
      fuzzy: fuzzyNameOrId,
      folderId: curFolderId,
      ...p
    } as any;

    if (_params.folderId === null) {
      delete _params.folderId;
    }
    // console.log("fetchFileList param:", p, _params, crumbs[String(tabKey)]);

    setTableLoading(true);
    console.log(_params);
    getFolderList(_params)
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

  const showUploadModalHandler = () => {
    setUploadOpen(true);
  };

  const showGraphHandler = () => {
    // if (wholeGraphData && Object.keys(wholeGraphData).length) {
    setGientechServera({ spaceName: graphSpace, type: "allGraph", fileName: "" });
    setShowGraph(true);
    // } else {
    //   fetchGraphData(
    //     {
    //       spaceName: graphSpace,
    //     },
    //     (res: any) => {
    //       const _res = res || {}
    //       setWholeGraphData({ ..._res })
    //       setGientechServera({
    //         spaceName: graphSpace,
    //         type: "allGraph",
    //         fileName: "",
    //       })
    //       setShowGraph(true)
    //     }
    //   )
    // }
  };

  const pageSizeChange = () => () => {
    onPageSizeChange(1, page.pageSize);
  };

  const handleUploadEvents = (action: string, payload?: any) => {
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
  const navigator = useNavigate();
  const handlePreviewFile = (data: any) => {
    if (data.status !== ANALYSIS_STATUS.SUCCESS) {
      getStatusText(statusCfg[data.status]);
      message.info(
        `文件解析状态为【${getStatusText(statusCfg[data.status])}】，无法预览！`
      );
      return;
    }
    navigator(`/chats/knowledgeBase/KnowledgeAnalyGraph/${params.id}`, {
      state: {
        fileId: data.fileId,
        parsedFilePath: data.url || data.convertedFilePath,
        filePath: data.filePath,
        pdfPage: data.pdfPage,
        fileType: data.type,
        spaceName: graphSpace
      }
    });
    setCurFileInfo(data);
  };

  const handleAnalysis = (item: any, filesObj?: any) => {
    let _files = [];
    let _folder_ids = [];
    let _fileIds = [] as number[];

    if (item) {
      _files.push({
        file_path: item?.url ? parseFilePath(item?.url) : "",
        file_size: item.fileSize ? `${item.fileSize}MB` : `0MB`,
        file_id: item.fileId,
        parent_file_name: item.hasParent || ""
      });
      _fileIds = [Number(item.fileId)];
    } else {
      const { folder_ids, files } = filesObj;
      if (folder_ids.length === 0 && files.length === 0) {
        message.warning(`暂无可以解析的文件`);
        return;
      }
      _fileIds = files.map((i: any) => Number(i.file_id));
      _files = files;
      _folder_ids = folder_ids;
    }

    const _params: any = {
      files: _files,
      folder_ids: _folder_ids,
      knowledge_base_name: kbNameRef.current,
      knowledge_base_id: params.id,
      override: true
    };
    // console.log("params", _params);

    if (_fileIds.length || _folder_ids.length) {
      setTableLoading(true);

      graphParse(_params)
        .then(() => {
          setTableLoading(false);
          message.info(`开始解析文件`, 2);
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

  const parseFilePath = (convertedFilePath: string) => {
    const pathArr = convertedFilePath.split("/");
    return pathArr.splice(3).join("/");
  };

  // pollingInterval start
  const startPolling = (ids: number[]) => {
    clearPollingInterval();
    const fn = () => {
      Promise.all(ids.map((id: number) => getGraphParseStatusById(Number(id))))
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

          if (_doneList.length === ids.length) {
            clearPollingInterval();
            fetchFileList();
            if (
              pollingResult === ANALYSIS_STATUS.FAILURE ||
              _doneList[0].sta === ANALYSIS_STATUS.FAILURE
            ) {
              message.warning(
                `解析结束，${
                  selectedRowKeys.length > 1
                    ? `有文件解析失败，请查看列表结果！`
                    : `解析失败！`
                }`
              );
              setPollingResult(ANALYSIS_STATUS.SUCCESS);
            } else {
              message.success(`解析完成！`);
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
    };
    pollingInterval = setInterval(fn, pollingTime);
    fn();
  };

  const clearPollingInterval = () => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  };
  // pollingInterval end

  const fuzzyNameOrIdOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    setFuzzyNameOrId(inputElement.value.trim());
  };

  const pollingCheck = () => {
    // console.log(fileList);
    const _fileList = (fileList || []).filter(
      (i: any) =>
        !isFolder(i) &&
        (i.status === ANALYSIS_STATUS.ANALYSISING ||
          i.status === ANALYSIS_STATUS.PENDING ||
          i.ststus === ANALYSIS_STATUS.RE_ANALYSISING ||
          i.status === ANALYSIS_STATUS.RETRY)
    );

    if (!pollingInterval && _fileList.length) {
      startPolling(
        Array.from(new Set([..._fileList.map((i: any) => i.fileId)]))
      );
    }
  };

  const goBackFolder = (id: number | null) => () => {
    returnFolder(id);
  };

  const enterFolder = (r: any) => {
    const { folderId, name } = r;
    const _tempCrumbs = docCrumbsRef.current;
    const _crumbs = [...[..._tempCrumbs, { id: folderId, name }]];
    // console.log("*******进入*********", _crumbs, "**********进入*******");
    crumbsOnChange(_crumbs);
  };

  const returnFolder = (id: number | null) => {
    let _crumbs: Array<ICrumbs> = [...initialCrumbs];
    if (id !== null) {
      const _tempCrumbs = docCrumbsRef.current;
      const idx = _tempCrumbs.findIndex((i: any) => i.id === id);
      _crumbs = [..._tempCrumbs.slice(0, idx + 1)];
      //   console.log("*******返回*********", _crumbs, "**********返回*******");
    }
    crumbsOnChange(_crumbs);
  };

  const crumbsOnChange = (items: Array<ICrumbs>) => {
    docCrumbsRef.current = [...items];
    //   console.log("add doc crumb", items);
    setCrumbs({ ...crumbs, [tabKey]: [...items] });
    resetPageNo();
    fetchFileList({ folderId: items[items.length - 1].id, pageNo: 1 });
  };

  const parseGraphHandler = () => {
    const { files, folder_ids } = fixBatchRowData();
    handleAnalysis(undefined, { files, folder_ids });
  };

  const parseGraphRow = (record: any) => () => {
    console.log(record);
    handleAnalysis(record);
  };

  const fixBatchRowData = () => {
    const selectedRows = fileList.filter((i: any) =>
      selectedRowKeys.includes(i.id)
    );
    const folders = selectedRows.filter((i: any) => i.isDir);
    const allSelectFiles = selectedRows.filter((i: any) => !i.isDir);
    const parseFiles = allSelectFiles.filter(
      (i: any) =>
        ![
          ANALYSIS_STATUS.SUCCESS,
          ANALYSIS_STATUS.ANALYSISING,
          ANALYSIS_STATUS.RE_ANALYSISING,
          ANALYSIS_STATUS.PENDING,
          ANALYSIS_STATUS.RETRY
        ].includes(i.status)
    );
    const folder_ids = folders.map((i: any) => i.folderId);
    return {
      folder_ids,
      files: getFilesData(parseFiles)
      // allSelectFiles: getFilesData(allSelectFiles),
    };
  };

  const getFilesData = (files: Array<any>) => {
    return files.map((i: any) => ({
      file_path: i.url ? parseFilePath(i.url) : "",
      file_size: i.fileSize ? `${i.fileSize}MB` : `0MB`,
      file_id: i?.fileId,
      parent_file_name: i.hasParent
    }));
  };

  const showGraphByRowHandler = (record: any) => () => {
    console.log(record);
    const { fileId, fileName } = record;
    setGientechServera({
      spaceName: graphSpace,
      fileId,
      type: "subGraph",
      fileName
    });
    setShowGraph(true);
  };

  const fetchGraphData = (params: any, cb?: any) => {
    if (params) {
      getWholeGraphSearch({ ...params }).then((res: any) => {
        cb && cb(res);
      });
    }
  };
  // Function end

  // effect start
  useEffect(() => {
    fetchFileList();
    return () => {
      clearPollingInterval();
    };
  }, []);

  // useEffect(() => {
  //   if (kbName) {
  //     fetchGraphData(
  //       {
  //         spaceName: graphSpace,
  //       },
  //       (res: any) => {
  //         const _res = res || {}
  //         setWholeGraphData({ ..._res })
  //       }
  //     )
  //   }
  // }, [kbName])

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
  // effect end

  return (
    <div style={{ height: `calc(100% - 65px)` }}>
      {crumbs[String(tabKey)].length > 1 ? (
        <div className="pt-4">
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
                  <span onClick={goBackFolder(c.id)}>{c.name}</span>
                </span>
              );
            })}
          </span>
        </div>
      ) : null}
      {/* <div>{JSON.stringify(selectedRowKeys)}</div> */}
      <div className="w-full py-4 flex gap-4 justify-between">
        <div className="flex gap-4">
          <Button
            disabled={
              tableLoading || getBtnDisabled(FILE_BTN.ADD, kbInfo.permission)
            }
            type="primary"
            icon={<UploadOutlined />}
            onClick={showUploadModalHandler}
            style={{
              background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
              color: "#fff",
              border: "none"
            }}
          >
            上传
          </Button>
          <Button
            disabled={tableLoading}
            type="primary"
            onClick={showGraphHandler}
            style={{
              background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
              color: "#fff",
              border: "none"
            }}
          >
            可视化图谱
          </Button>
          <Button
            disabled={
              tableLoading ||
              selectedRowKeys.length === 0 ||
              getBtnDisabled(FILE_BTN.ADD, kbInfo.permission)
            }
            style={{
              color: "#055aff",
              borderColor: "#eeeeee"
            }}
            onClick={parseGraphHandler}
          >
            图谱解析
          </Button>
        </div>
        <div>
          <Input
            value={fuzzyNameOrId}
            disabled={tableLoading}
            placeholder="搜索内容"
            style={{ width: "240px" }}
            suffix={
              <div className="cursor-pointer" onClick={pageSizeChange()}>
                <SearchOutlined style={{ color: "#999", fontSize: 12 }} />
              </div>
            }
            onChange={fuzzyNameOrIdOnChange}
            onKeyDown={docKeyDown}
          />
        </div>
      </div>
      <div className="h-[calc(100%-85px)] my-4 overflow-hidden kb-table-wrap">
        <Table
          rowKey={(r: any) => r.id}
          loading={tableLoading}
          columns={kbColumns}
          dataSource={fileList}
          pagination={false}
          scroll={{
            y: "calc(100vh - 510px)"
          }}
          rowSelection={{
            type: "checkbox",
            ...rowSelection
          }}
          rowClassName="custom-files-row"
        />
      </div>
      <Pagination
        align="end"
        disabled={tableLoading}
        total={totalCount}
        pageSize={page.pageSize}
        current={page.pageNo}
        onChange={onPageSizeChange}
        showSizeChanger={true}
      />
      <UploadBox
        open={uploadModalOpen}
        kbId={String(params.id)}
        fileListType={3}
        crumbs={crumbs[tabKey]}
        isGraph={true}
        uploadEvents={handleUploadEvents}
        getCurFolderId={getCurFolderId}
      />
    </div>
  );
};

export default GraphBox;
