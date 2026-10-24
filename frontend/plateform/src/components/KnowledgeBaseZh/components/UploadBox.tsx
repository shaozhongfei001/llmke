import {
  Button,
  Switch,
  Flex,
  Modal,
  UploadFile,
  UploadProps,
  message,
  Spin,
  Table,
  Tooltip,
  Input,
  Tabs,
  Popover
} from "antd";
import Dragger from "antd/lib/upload/Dragger";
import { baseURL } from "@root/src/apis/common";
import { useAppPassport } from "@/core/helps";
import axios$ from "@root/src/apis";
import { useState, useMemo, useRef } from "react";
import {
  QuestionCircleOutlined,
  PlusCircleOutlined,
  ExclamationCircleOutlined
} from "@ant-design/icons";
import IconUpload from "@/assets/knowledgebase/icon-upload.svg";
import IconFile from "@/assets/knowledgebase/icon-file.svg";
import "@/assets/styles/duplicateModal.less";
import { tabItems, urlPattern } from "@/const/knowledgebase";

const showVideo = import.meta.env.VITE_CONFIG_SHOW_VIDEO === "true";

interface UploadBoxProps {
  name?: string;
  kbId: string;
  open: any;
  fileListType: number;
  crumbs?: Array<any>;
  isGraph?: boolean;
  getCurFolderId?: () => number | null;
  uploadEvents: (action: string, payload?: any) => void;
  uploadBoxOpt?: {
    docParse: boolean;
    faq: boolean;
    chunk: boolean;
  };
  platform?: string;
}

export enum UPLOAD_EVENTS {
  MODAL_CLOSE = "upload_event:model_close",
  FILE_REMOVE = "upload_event:remove",
  FILE_UPLOADED = "upload_event:uploaded",
  MODAL_ONLY_CLOSE = "upload_event:model_only_close"
}

enum UploadType {
  SKIP = "SKIP", // 跳过
  OVERWRITE = "OVERWRITE", // 覆盖
  NEWVERSION = "NEWVERSION" // 新版本
}

const tabList = [
  {
    label: "上传文件",
    key: "file"
  },
  {
    label: "URL导入",
    key: "url"
  }
];

type TFileList = {
  fileName: string;
  type?: UploadType;
};

interface IUrlCell {
  id: number;
  url: string;
  title: string;
  isUrlErr: boolean;
  isTitleErr: boolean;
}

const initialUrlList = [
  {
    id: 0,
    url: "",
    title: "",
    isUrlErr: false,
    isTitleErr: false
  }
];

type TCallback = (res?: any) => void;

const UploadBox = (props: UploadBoxProps) => {
  const { getToken } = useAppPassport();
  const {
    kbId,
    open,
    fileListType,
    crumbs,
    isGraph = false,
    uploadEvents,
    getCurFolderId,
    uploadBoxOpt,
    platform = "rag-qa"
  } = props;
  const [fList, setFList] = useState<any[]>([]);
  const [isParse, setIsParse] = useState(false);
  const [isExtract, setIsExtract] = useState(false);
  const [isGraphParse, setIsGraphParse] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isDuplicateShow, setIsDuplicateShow] = useState(false);
  const [duplicateLoading, setDuplicateLoading] = useState(false);
  const [duplicateList, setDuplicateList] = useState<Array<string>>([]);
  const [duplicateDoneList, setDuplicateDoneList] = useState<Array<string>>([]);
  const [duplicateRowKeys, setDuplicateRowKeys] = useState<React.Key[]>([]);
  const [currentTab, setCurrentTab] = useState<string>(tabList[0].key);
  const [urlList, setUrlList] = useState<Array<IUrlCell>>([...initialUrlList]);
  const urlWrapRef = useRef(null);

  const isCec = useMemo(() => {
    return platform && platform === "intelbrain-dw";
  }, [platform]);

  const isFaq = useMemo(() => {
    return String(fileListType) === tabItems[1].key;
  }, [fileListType]);

  const isUpFile = useMemo(() => {
    return String(currentTab) === tabList[0].key;
  }, [currentTab]);

  const tableList = useMemo(() => {
    return duplicateList.map((name: string) => {
      const disabled = duplicateDoneList.includes(name);
      return { name, disabled };
    });
  }, [duplicateList, duplicateDoneList]);

  const duplicateColumns = [
    {
      title: <span className="custom-duplicate-header">名称</span>,
      dataIndex: "name",
      key: "name",
      render: (val: string) => (
        <span className="custom-duplicate-header">{renderFileName(val)}</span>
      )
    },
    {
      title: <span className="custom-duplicate-header">操作</span>,
      dataIndex: "operations",
      key: "operations",
      width: 200,
      render: (_: any, record: any) => {
        return (
          <div className="duplicate-table-btn-group-wrap">
            <Button
              type="link"
              size="small"
              className={`${record.disabled ? "btn-disabled" : ""}`}
              disabled={record.disabled}
              // onClick={() => singleConfirm([record.name], UploadType.SKIP)}
              onClick={() => singleStop([record.name])}
            >
              停止
            </Button>
            <Button
              type="link"
              size="small"
              className={`${record.disabled ? "btn-disabled" : ""}`}
              disabled={record.disabled}
              onClick={() => singleConfirm([record.name], UploadType.OVERWRITE)}
            >
              替换
            </Button>
            <Button
              type="link"
              size="small"
              className={`${record.disabled ? "btn-disabled" : ""}`}
              disabled={record.disabled}
              onClick={() =>
                singleConfirm([record.name], UploadType.NEWVERSION)
              }
            >
              保存为新版本
            </Button>
          </div>
        );
      }
    }
  ];

  const getZipAndFileList = (list: Array<string>) => {
    const zipNames = list.filter((n: string) => n.includes(":"));
    const fileNames = list.filter((n: string) => !n.includes(":"));

    return {
      zips: (zipNames || []).map((n: string) => getFileName(n)),
      fileNames
    };
  };

  const getFileName = (nameStr: string) => {
    if (!nameStr) {
      return {
        zipName: "",
        pathStr: "",
        fileName: "",
        isHasFolder: false
      };
    }
    const [zipName, fileName] = nameStr.split(":");
    const result = fileName ? fileName.match(/[^/]+$/) : [];
    const isHasFolder = result && result.length && result[0] !== fileName;

    return {
      zipName: fileName ? zipName : "",
      pathStr: isHasFolder ? fileName.replace(result[0], "") : "",
      fileName: fileName && result && result.length ? result[0] : zipName,
      isHasFolder
    };
  };

  const renderFileName = (nameStr: string) => {
    if (!nameStr) {
      return null;
    }
    const { zipName, pathStr, fileName, isHasFolder } = getFileName(nameStr);
    // console.log(result, isHasFolder);
    return zipName ? (
      <>
        <div className="zip-name-wrap">
          <span title={zipName}>
            <b>来源：</b>
            {zipName}
          </span>
          {isHasFolder ? (
            <span title={pathStr}>
              <b>路径：</b>
              {pathStr}
            </span>
          ) : null}
        </div>
        <div className="file-name-wrap">{fileName}</div>
      </>
    ) : (
      <>{fileName}</>
    );
  };

  const rowSelection = {
    getCheckboxProps: (record: any) => ({
      disabled: record.disabled
    }),
    onChange: (_duplicateRowKeys: React.Key[]) => {
      setDuplicateRowKeys(_duplicateRowKeys);
    },
    selectedRowKeys: duplicateRowKeys
  };

  const handleTriggerUpload = () => {
    // setDuplicateList((fList || []).map((i) => i.name));
    // setDuplicateDoneList((fList || []).map((i) => i.name).slice(1, 2));
    // setIsDuplicateShow(true);
    // return;

    const fNameList = (fList || []).map((f: any) => f.name);
    const _formData = makeFormData(fNameList);
    let maxSize = 5000 * 1024 * 1024;
    let size = 0;
    for (let [key, value] of _formData) {
      if (value instanceof File) {
        size += value.size;
      }
    }
    if (size > maxSize) {
      message.warning("上传文件大小不能超过5000M");
      return;
    }
    uploadFilesOrUrls(_formData, allFileDone, failFn);
  };

  const checkUrlList = () => {
    return urlList.map((i: any) =>
      Object.assign({}, i, {
        isUrlErr: !urlPattern.test(i.url),
        isTitleErr: !i.title
      })
    );
  };

  const handleUrlUpload = () => {
    // setDuplicateList((urlList || []).map((i) => i.title));
    // setDuplicateDoneList((urlList || []).map((i) => i.title).slice(1, 2));
    // setIsDuplicateShow(true);
    // return;

    const _urlList = checkUrlList();
    if (_urlList.some((i: any) => i.isUrlErr || i.isTitleErr)) {
      setUrlList([...JSON.parse(JSON.stringify(_urlList))]);
      return;
    }
    const _formData = makeFormData(urlList);
    uploadFilesOrUrls(_formData, allFileDone, failFn);
  };

  const failFn = (res?: any) => {
    // url res
    // (res?: any) => {
    // {
    //   "success": false,
    //   "errorMsg": "文件名重复",
    //   "errorCode": "10014",
    //   "data": [
    //       "https://iigrsya13pv.feishu.cn/wiki/Ps12wyRzwiTjGak4gEJcMHWxnfe|规范.html"
    //   ]
    // }
    // });
    if (res) {
      const { data, errorCode, errorMsg } = res;
      if (errorCode === "10014") {
        // const _fileNameList = (data || []).map((i: any) => i.fileName);
        const _fileNameList = [...data].map((i: string) =>
          isUpFile ? i : getUrlTitle(i)
        );
        if (_fileNameList && _fileNameList.length) {
          let _list = _fileNameList;
          if (
            Object.prototype.toString.call(_fileNameList[0]) ===
            "[object Object]"
          ) {
            _list = _fileNameList.map((i: any) => i.fileName);
          }
          setDuplicateList(_list || []);
          setIsDuplicateShow(true);
        }
      } else {
        message.error(errorMsg);
      }
    }
  };

  const getUrlTitle = (urlStr: string) => {
    const [url, titleStr] = urlStr.split("|");
    if (titleStr) {
      const [title, suffix] = titleStr.split(".");
      if (title) {
        return title;
      }
    }
    return urlStr;
  };

  const makeFormData = (list: Array<any>, type?: UploadType) => {
    const _formData = new FormData();
    const fileList: Array<any> = [];
    let _uploadFileParam = {
      kbId,
      fileListType,
      fileList
    } as any;
    const folderId = getCurFolderId ? getCurFolderId() : null;

    if (isGraph) {
      _uploadFileParam.isGraphParse = isGraphParse;
    } else {
      if (fileListType === Number(tabItems[0].key)) {
        _uploadFileParam.isParse = isParse;
      }
      _uploadFileParam.isExtract = isExtract;
    }
    if (folderId) {
      _uploadFileParam.folderId = folderId;
    }

    if (isUpFile) {
      const { fileNames, zips } = getZipAndFileList(list);
      if (fileNames.length) {
        fileNames.forEach((fName: string) => {
          const _f = fList.find((f: any) => {
            return f.name.replace(/\s+/g, "") === fName.replace(/\s+/g, "");
          });
          try {
            const { name, originFileObj } = _f;
            const _fRow = {
              fileName: name,
              type
            };

            !type && delete _fRow.type;

            fileList.push({
              ..._fRow
            });
            _formData.append("files", originFileObj);
          } catch (e) {
            console.log(e);
          }
        });
      }

      if (zips.length) {
        const zipNames = Array.from([...new Set(zips.map((i) => i.zipName))]);
        zipNames.forEach((zipName: string) => {
          const zipFiles = zips.filter((z: any) => z.zipName === zipName);
          const _f = fList.find((f: any) => f.name === zipName);
          const { name, originFileObj } = _f;
          // 压缩包里的文件存储在compressedFileList中
          const compressedFileList: Array<any> = [];
          zipFiles.forEach((z: any) => {
            const { pathStr, fileName } = z;
            const _zRow = {
              filePath: pathStr + fileName,
              type
            };
            compressedFileList.push({ ..._zRow });
          });
          const _fRow = {
            fileName: name,
            compressedFileList
          };
          fileList.push({
            ..._fRow
          });
          _formData.append("files", originFileObj);
        });
      }

      if (uploadBoxOpt && uploadBoxOpt.chunk) {
        _uploadFileParam = {
          ..._uploadFileParam,
          isParse: true,
          isExtract: false,
          chunking: chunkParse
        };
      }
      console.log("uploadFileParam:", _uploadFileParam);
      _formData.append("uploadFileParam", JSON.stringify(_uploadFileParam));
    } else {
      const _list = type
        ? urlList.filter((i: any) => list.includes(i.title))
        : urlList;
      (_list || []).forEach((i: IUrlCell) => {
        try {
          const { url, title } = i;
          const _fRow = {
            fileName: title,
            type,
            sourceUrl: url
          };

          !type && delete _fRow.type;

          fileList.push({
            ..._fRow
          });
        } catch (e) {
          console.log(e);
        }
      });

      if (uploadBoxOpt && uploadBoxOpt.chunk) {
        _uploadFileParam = {
          ..._uploadFileParam,
          isParse: true,
          isExtract: false,
          chunking: chunkParse
        };
      }
      console.log("importUrlListParam:", _uploadFileParam);
      _formData.append("importUrlListParam", JSON.stringify(_uploadFileParam));
    }
    return _formData;
  };

  const singleStop = (list: Array<string>) => {
    syncDuplicateDoneList(
      [...list],
      () => {
        message.success(`“${list[0]}” 停止 成功！`);
      },
      true
    );
  };

  const moreStop = () => {
    const _list = duplicateRowKeys.map((key: any) => String(key));
    syncDuplicateDoneList(
      [..._list],
      () => {
        message.success(`多文件批量 停止 成功！`);
      },
      true
    );
  };

  const uploadFilesOrUrls = (
    formData: FormData,
    sucFn?: TCallback,
    failFn?: TCallback,
    finFn?: TCallback
  ) => {
    const _url = `${baseURL}/index/knowledgeBase/file/${
      isUpFile ? "uploadFileList" : "importUrlList"
    }`;

    setIsUploading(true);

    axios$
      .post(_url, formData, {
        headers: {
          Authorization: getToken() || "",
          "X-Platform": platform
        },
        timeout: 3600000 // 视频上传设置60分钟超时
      })
      .then((res: any) => {
        if (res) {
          console.log(res);
          const { success } = res;
          if (success) {
            sucFn && sucFn();
          } else {
            failFn && failFn(res);
          }
        }
      })
      .finally(() => {
        if (finFn) {
          finFn();
        } else {
          setIsUploading(false);
        }
      })
      .catch((e) => {
        console.log(e);
      });
  };

  const closeUploadModal = () => {
    resetDuplicateModal();
    uploadEvents(UPLOAD_EVENTS.MODAL_CLOSE);
    resetModal();
  };

  const allFileDone = () => {
    message.success(`${isUpFile ? "文件上传" : "URL导入"}成功！`);
    closeUploadModal();
  };

  const handleBeforeUpload = (file: UploadFile) => {
    const { name, size } = file;
    let errMsg = "";
    if (fList.find((f: UploadFile) => f.name === name)) {
      errMsg = `文件《${name}》已存在上传队列中,请勿重复添加`;
    }
    if (size === 0) {
      errMsg = `《${name}》是空文件,请勿添加`;
    }
    if (errMsg) {
      message.warning(errMsg);
      return false;
    }

    return Promise.resolve();
  };

  const handleFileChange = async (info: any) => {
    const { file } = info;
    const { status, response } = file;
    const errMsg = "上传出错请联系管理员";
    switch (status) {
      case "error":
        message.error(response ? response.errorMsg || errMsg : errMsg);
        break;
      case "removed":
        deleteFileFromlist(file.name);
        break;
      case "done":
        setFList([...fList, file]);
        break;
    }
  };

  const handleFileStatus = (options: any) => {
    const { onSuccess, onProgress } = options;
    onProgress({ percent: 100 });
    onSuccess(true);
  };

  const deleteFileFromlist = (fileName: string) => {
    setFList(fList.filter((f: UploadFile) => f.name !== fileName));
  };

  const closeModal = () => {
    uploadEvents(UPLOAD_EVENTS.MODAL_ONLY_CLOSE);
    resetModal();
  };

  const resetModal = () => {
    setIsParse(false);
    setIsExtract(false);
    setIsGraphParse(false);
    setFList([]);
    setCurrentTab(tabList[0].key);
    setUrlList([...initialUrlList]);
  };

  const uploadProps: UploadProps = {
    style: {
      backgroundColor: "#f9fafc",
      borderColor: "#d9d9d9",
      marginBottom: "16px"
    },
    multiple: true,
    customRequest: handleFileStatus,
    beforeUpload: handleBeforeUpload,
    onChange: handleFileChange,
    // accept: ".pdf,.docx,.txt,.xlsx,.html,.jpeg,.jpg,.png,.doc",
    accept: `.ppt,.pptx,.pdf,.docx,.txt,.xlsx,.xls,.csv,.html,.jpeg,.jpg,.png,.doc,.zip,.md,.json${
      showVideo ? ",.mp4" : ""
    },.tar${isCec ? ",.odf" : ""}`,
    // accept: ".ppt,.pptx,.pub,.doc,.docx,.xls,.pdf,.xlsx,.csv,.txt,.html,.htm",
    showUploadList: false
  };

  const singleConfirm = (list: Array<string>, type: UploadType) => {
    const _formData = makeFormData([...list], type);
    uploadFilesOrUrls(
      _formData,
      () => {
        syncDuplicateDoneList([...list], () => {
          let _type = "";
          switch (type) {
            case UploadType.SKIP:
              _type = "停止";
              break;
            case UploadType.OVERWRITE:
              _type = "替换";
              break;
            case UploadType.NEWVERSION:
              _type = "保存新版本";
              break;
          }
          message.success(`“${list[0]}” ${_type} 成功！`);
        });
      },
      duplicateFailFn,
      duplicateFinlFn
    );
  };

  const syncDuplicateDoneList = (
    list: Array<string>,
    cb: any,
    isNoMessage?: boolean
  ) => {
    const _list = Array.from(new Set([...duplicateDoneList, ...list]));
    if (_list.length === duplicateList.length) {
      if (isNoMessage) {
        // 停止上传无需提示成功！
        closeUploadModal();
      } else {
        // cb && cb();
        closeDuplicateModal();
      }
    } else {
      setDuplicateDoneList([..._list]);
      setDuplicateRowKeys([
        ...[...duplicateRowKeys.filter((name: any) => !list.includes(name))]
      ]);
      duplicateList.length && cb();
    }
  };

  const duplicateFailFn = (res: any) => {
    const { errorMsg } = res;
    message.error(errorMsg || "错误！");
  };

  const duplicateFinlFn = () => {
    setDuplicateLoading(false);
    setIsUploading(false);
  };

  const moreConfirm = (type: UploadType) => {
    const _list = duplicateRowKeys.map((key: any) => String(key));
    const _formData = makeFormData([..._list], type);
    uploadFilesOrUrls(
      _formData,
      () => {
        syncDuplicateDoneList([..._list], () => {
          let _type = "";
          switch (type) {
            case UploadType.SKIP:
              _type = "停止";
              break;
            case UploadType.OVERWRITE:
              _type = "替换";
              break;
            case UploadType.NEWVERSION:
              _type = "保存新版本";
              break;
          }
          message.success(`多文件批量 ${_type} 成功！`);
        });
      },
      duplicateFailFn,
      duplicateFinlFn
    );
  };

  const resetDuplicateModal = () => {
    setDuplicateList([]);
    setDuplicateDoneList([]);
    setDuplicateRowKeys([]);
    setIsDuplicateShow(false);
  };

  const closeDuplicateModal = () => {
    resetDuplicateModal();
    allFileDone();
  };

  const tabClick = (tabKey: string) => {
    setCurrentTab(tabKey);
  };

  const addUrlIpt = () => {
    const lastCell = urlList[urlList.length - 1];
    const newRow = {
      ...initialUrlList[0],
      id: lastCell.id + 1
    };

    setUrlList([...urlList, newRow]);

    setTimeout(() => {
      const el = urlWrapRef.current as any;
      if (el && el.scrollHeight > el.clientHeight && el.scrollTo) {
        el.scrollTo({
          top: el.scrollHeight,
          behavior: "smooth"
        });
      }
    }, 500);
  };

  const capKeyToUpperCase = (key: string) => {
    return key.replace(/^\S/, function (letter: string) {
      return letter.toUpperCase();
    });
  };

  const iptChangeHandler = (
    e: any,
    idx: number,
    key: string,
    type: string = "change"
  ) => {
    const value = e.target.value.trim();
    const item = { ...urlList[idx] } as any;
    item[key] = value;
    const _key = capKeyToUpperCase(key);
    item[`is${_key}Err`] =
      type !== "change" && _key === "Url" ? !urlPattern.test(value) : !value;
    const _urlList = urlList;
    _urlList.splice(idx, 1, { ...item });
    setUrlList([..._urlList]);
  };

  const deleteRow = (idx: number) => {
    const _urlList = urlList;
    _urlList.splice(idx, 1);
    setUrlList([..._urlList]);
  };

  // 是否直接解析切片
  const [chunkParse, setChunkParse] = useState(true);

  return (
    <Modal
      open={open}
      title={null}
      width={650}
      destroyOnClose={true}
      cancelText={"取消"}
      okText={"确定"}
      footer={null}
      onCancel={closeModal}
      closable={false}
    >
      <div className="upload-header">
        <div className="tabs-wrap">
          <Tabs
            items={isGraph ? [{ ...tabList[0] }] : tabList}
            onChange={tabClick}
            activeKey={currentTab}
          />
        </div>
        <div className="close-btn-wrap">
          <b title="关闭" onClick={closeModal}>
            X
          </b>
        </div>
      </div>
      <div className="bottom-line relative -top-[1px]"></div>
      {!isGraph && crumbs && crumbs.length ? (
        <div className="path-wrap">
          <div className="path-label">当前文件上传地址：</div>
          <div className="path-item">
            {crumbs.map((i: any, idx: number) => {
              let label = i.name;
              if (idx === 0) {
                const item = tabItems.find(
                  (t: any) => t.key === String(fileListType)
                );
                if (item && item.label) {
                  label = item.label;
                }
              }
              return <span key={`path_cell_${idx}`}> / {label}</span>;
            })}
          </div>
        </div>
      ) : null}
      {/* <div>{JSON.stringify(urlList)}</div> */}
      <div className="min-h-36">
        {isUpFile ? (
          <Dragger {...uploadProps}>
            <div className="mb-4 flex justify-center">
              <img src={IconUpload} />
            </div>
            <p className="text-[#2a2a2a] text-sm">点击或将文件拖拽到此处上传</p>
            <span style={{ color: "#999", fontSize: "12px", fontWeight: 400 }}>
              {/* 支持单次或批量上传doc(x)、xlsx、pdf、text、html、jp(e)g、png格式。 */}
              {`支持单次或批量上传ppt(x)、doc(x)、xlsx、csv、pdf、text、html、jp(e)g、md、json、png${
                isCec ? "、odf" : ""
              }${showVideo ? "、mp4格式" : ""}`}
              <br />
              以及zip、tar等压缩文件。
            </span>
          </Dragger>
        ) : (
          <div className="upload-url-wrap">
            <div className="url-thead">
              <div className="cell-url">
                <span className="url-text">导入URL</span>
                <Tooltip
                  placement="right"
                  title={
                    "支持大部分政府网站、微信、微博文章、企鹅号、今日头条、一点资讯等等新媒体平台的文章链接"
                  }
                >
                  <QuestionCircleOutlined />
                </Tooltip>
              </div>
              <div className="cell-title">文件名</div>
              <div className="cell-action">操作</div>
            </div>
            <div className="upload-url-container">
              <div className="upload-url-scroll" ref={urlWrapRef}>
                {urlList.map((i: IUrlCell, idx: number) => {
                  return (
                    <div className="url-ipt-wrap" key={`upload_url_${idx}`}>
                      <span className="ipt-url">
                        <Input
                          className={`${i.isUrlErr ? "err-ipt" : ""}`}
                          placeholder="输入或黏贴链接上传文件"
                          value={i.url}
                          onChange={(e) => {
                            iptChangeHandler(e, idx, "url");
                          }}
                          onBlur={(e) => {
                            iptChangeHandler(e, idx, "url", "blur");
                          }}
                        />
                      </span>
                      <span className="ipt-title">
                        <Input
                          placeholder="输入文件名"
                          className={`${i.isTitleErr ? "err-ipt" : ""}`}
                          value={i.title}
                          onChange={(e) => {
                            iptChangeHandler(e, idx, "title");
                          }}
                          onBlur={(e) => {
                            iptChangeHandler(e, idx, "title");
                          }}
                        />
                      </span>
                      <span className="btn-del">
                        <Button
                          type="link"
                          disabled={urlList.length <= 1}
                          onClick={() => deleteRow(idx)}
                        >
                          删除
                        </Button>
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="add-row">
              <span onClick={addUrlIpt}>
                <PlusCircleOutlined style={{ color: "#055AFF" }} />
                添加URL
              </span>
            </div>
          </div>
        )}
      </div>
      {isUpFile ? (
        <div className="upload-list-wrap">
          <div className="upload-list-container">
            {fList.map((f: UploadFile, idx: number) => {
              return (
                <div
                  key={`file_${f.name}_${idx}`}
                  className="flex justify-between"
                >
                  <div className="flex items-center">
                    <img
                      src={IconFile}
                      style={{
                        position: "relative",
                        marginRight: "8px",
                        top: "1px"
                      }}
                    />
                    <span style={{ fontSize: "12px", color: "#555" }}>
                      {f.name}
                    </span>
                  </div>
                  <Button
                    type="link"
                    style={{
                      fontSize: "12px",
                      color: "#055aff"
                    }}
                    onClick={() => {
                      deleteFileFromlist(f.name);
                    }}
                  >
                    删除
                  </Button>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
      <div className="mb-8 bottom-line"></div>
      <Flex className="justify-between" align="center" justify="center">
        <div className="flex gap-6">
          {(!uploadBoxOpt || uploadBoxOpt.docParse) && (
            <>
              {!isFaq && !isGraph ? (
                <div>
                  <span style={{ color: "#555", marginRight: "8px" }}>
                    文档解析
                  </span>
                  <Switch
                    onChange={(checked: boolean) => setIsParse(checked)}
                  />
                </div>
              ) : null}
            </>
          )}

          {(!uploadBoxOpt || uploadBoxOpt.faq) && (
            <>
              {!isGraph ? (
                <div>
                  <span style={{ color: "#555", marginRight: "8px" }}>
                    FAQ抽取
                  </span>
                  <Switch
                    onChange={(checked: boolean) => setIsExtract(checked)}
                  />
                </div>
              ) : null}
            </>
          )}

          {uploadBoxOpt && uploadBoxOpt.chunk ? (
            <div>
              <span style={{ color: "#555", marginRight: "12px" }}>
                作为切片检索使用&nbsp;
                <Popover
                  content={
                    <div className="w-[200px]">
                      开启开关，上传文档自动解析切片作为写作的切片检索。
                    </div>
                  }
                >
                  <ExclamationCircleOutlined
                    style={{
                      fontSize: "16px",
                      color: "#055AFF"
                    }}
                  />
                </Popover>
              </span>
              <Switch
                defaultChecked={chunkParse}
                onChange={(checked: boolean) => setChunkParse(checked)}
              />
            </div>
          ) : null}

          {isGraph ? (
            <div>
              <span style={{ color: "#555", marginRight: "8px" }}>
                图谱解析
              </span>
              <Switch
                onChange={(checked: boolean) => setIsGraphParse(checked)}
              />
            </div>
          ) : null}
        </div>
        <div className="flex gap-3">
          <Button
            style={{
              border: "1px solid #ebebeb",
              color: "#555"
            }}
            disabled={isUploading}
            onClick={closeModal}
          >
            取消
          </Button>
          {isUpFile ? (
            <Button
              type="primary"
              style={{
                background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                color: fList.length === 0 ? "#ddd" : "#fff"
              }}
              onClick={handleTriggerUpload}
              loading={isUploading}
              disabled={fList.length === 0}
            >
              确定
            </Button>
          ) : (
            <Button
              type="primary"
              style={{
                background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                color: urlList.length === 0 ? "#ddd" : "#fff"
              }}
              onClick={handleUrlUpload}
              loading={isUploading}
              disabled={urlList.length === 0}
            >
              确定
            </Button>
          )}
        </div>
      </Flex>
      <Modal
        open={isDuplicateShow}
        style={{ top: duplicateList.length > 1 ? 100 : 200 }}
        title={
          <span className="duplicate-modal-title">
            {duplicateList.length > 1 ? "文件名重复" : ""}提醒
          </span>
        }
        width={duplicateList.length > 1 ? 650 : 450}
        closable={duplicateList.length > 1}
        maskClosable={false}
        destroyOnClose={true}
        footer={null}
        onCancel={resetDuplicateModal}
      >
        {/* <div>{JSON.stringify(duplicateDoneList)}</div>
        <div>{JSON.stringify(duplicateList)}</div>
        <div>{JSON.stringify(duplicateRowKeys)}</div> */}
        {duplicateList.length > 1 ? (
          <div className="more-file-wrap">
            <Table
              rowKey="name"
              loading={duplicateLoading}
              columns={duplicateColumns}
              dataSource={tableList}
              pagination={false}
              rowSelection={{
                type: "checkbox",
                ...rowSelection
              }}
              scroll={{ y: 400 }}
            />
            <div className="pb-5 mb-5 bottom-line"></div>
            <div className="more-file-footer">
              <div className="total-wrap">
                {duplicateRowKeys.length}
                <span>/</span>
                {duplicateList.length - duplicateDoneList.length}
              </div>
              <div className="more-btn-group">
                <Button
                  className="skip-btn"
                  disabled={!duplicateRowKeys.length}
                  // onClick={() => moreConfirm(UploadType.SKIP)}
                  onClick={moreStop}
                >
                  停止
                </Button>
                <Button
                  className="overwrite-btn"
                  disabled={!duplicateRowKeys.length}
                  onClick={() => moreConfirm(UploadType.OVERWRITE)}
                >
                  替换
                </Button>
                <Button
                  className="newversion-btn"
                  disabled={!duplicateRowKeys.length}
                  onClick={() => moreConfirm(UploadType.NEWVERSION)}
                >
                  保存为新版本
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="single-file-wrap">
            <div className="file-name">
              <span>{renderFileName(duplicateList[0])}</span>存在同名文件
            </div>
            <Spin spinning={duplicateLoading}>
              <div className="single-btn-group">
                <Button
                  className="skip-btn"
                  // onClick={() => singleConfirm(duplicateList, UploadType.SKIP)}
                  onClick={() => singleStop(duplicateList)}
                >
                  停止
                </Button>
                <Button
                  className="overwrite-btn"
                  onClick={() =>
                    singleConfirm(duplicateList, UploadType.OVERWRITE)
                  }
                >
                  替换
                </Button>
                <Button
                  className="newversion-btn"
                  onClick={() =>
                    singleConfirm(duplicateList, UploadType.NEWVERSION)
                  }
                >
                  保存为新版本
                </Button>
              </div>
            </Spin>
          </div>
        )}
      </Modal>
    </Modal>
  );
};
export default UploadBox;
