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
  Tabs
} from "antd";
import Dragger from "antd/lib/upload/Dragger";
import { baseURL } from "@root/src/apis/common";
import { useAppPassport } from "@/core/helps";
import axios$ from "@root/src/apis";
import { useState, useMemo, useRef } from "react";
import { QuestionCircleOutlined, PlusCircleOutlined } from "@ant-design/icons";
import IconUpload from "@/assets/knowledgebase/icon-upload.svg";
import IconFile from "@/assets/knowledgebase/icon-file.svg";
import "@/assets/styles/duplicateModal.less";
import { tabItems } from "@/const/knowledgebase";

interface UploadBoxProps {
  name?: string;
  kbId: number;
  open: any;
  fileListType: number;
  crumbs?: Array<any>;
  getCurFolderId?: () => number | null;
  uploadEvents: (action: string, payload?: any) => void;
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

type TCallback = (res?: any) => void;

const UploadBox = (props: UploadBoxProps) => {
  const { getToken } = useAppPassport();
  const { kbId, open, fileListType, crumbs, uploadEvents, getCurFolderId } =
    props;
  const [fList, setFList] = useState<any[]>([]);
  const [isParse, setIsParse] = useState(false);
  const [isExtract, setIsExtract] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isDuplicateShow, setIsDuplicateShow] = useState(false);
  const [duplicateLoading, setDuplicateLoading] = useState(false);
  const [duplicateList, setDuplicateList] = useState<Array<string>>([]);
  const [duplicateDoneList, setDuplicateDoneList] = useState<Array<string>>([]);
  const [duplicateRowKeys, setDuplicateRowKeys] = useState<React.Key[]>([]);
  const [currentTab, setCurrentTab] = useState<string>(tabList[0].key);
  const urlWrapRef = useRef(null);

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
    const fNameList = (fList || []).map((f: any) => f.name);
    const _formData = makeFormData(fNameList);
    uploadFilesOrUrls(_formData, allFileDone, failFn);
  };

  const failFn = (res?: any) => {
    if (res) {
      const { data, errorCode, errorMsg } = res;
      if (errorCode === "10014") {
        // const _fileNameList = (data || []).map((i: any) => i.fileName);
        const _fileNameList = [...data].map((i: string) =>
          isUpFile ? i : getUrlTitle(i)
        );
        if (_fileNameList && _fileNameList.length) {
          setDuplicateList(_fileNameList || []);
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
    const _uploadFileParam = {
      kbId,
      fileListType,
      isParse,
      isExtract,
      fileList
    } as any;
    const folderId = getCurFolderId ? getCurFolderId() : null;

    if (folderId) {
      _uploadFileParam.folderId = folderId;
    }

    fileListType === Number(tabItems[1].key) && delete _uploadFileParam.isParse;

    if (isUpFile) {
      const { fileNames, zips } = getZipAndFileList(list);
      if (fileNames.length) {
        (fileNames || []).forEach((fName: string) => {
          const _f = fList.find((f: any) => f.name === fName);
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

      console.log("uploadFileParam:", _uploadFileParam);
      _formData.append("uploadFileParam", JSON.stringify(_uploadFileParam));
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
    const _url = `/cecProxy/dw/articleMaterial`;

    setIsUploading(true);
    axios$
      .post(_url, formData, {
        headers: {
          Authorization: getToken() || ""
        }
      })
      .then((res: any) => {
        if (res) {
          console.log(res);
          const { success, data } = res;
          if (success) {
            sucFn && sucFn(data);
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
    resetModal();
  };

  const allFileDone = (data?: any) => {
    message.success(`${isUpFile ? "文件上传" : "URL导入"}成功！`);
    if (data?.length) {
      uploadEvents(UPLOAD_EVENTS.MODAL_CLOSE, data);
    }
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
    setFList([]);
    setCurrentTab(tabList[0].key);
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
    accept: ".ppt,.pptx,.pub,.doc,.docx,.xls,.pdf,.xlsx,.csv,.txt",
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

  const capKeyToUpperCase = (key: string) => {
    return key.replace(/^\S/, function (letter: string) {
      return letter.toUpperCase();
    });
  };

  return (
    <Modal
      open={open}
      title="上传文档"
      width={650}
      destroyOnClose={true}
      cancelText={"取消"}
      okText={"确定"}
      footer={null}
      onCancel={closeModal}
    >
      {/* <div className="upload-header">
        <div className="close-btn-wrap">
          <b title="关闭" onClick={closeModal}></b>
        </div>
      </div> */}
      <div className="bottom-line relative -top-[1px]"></div>
      {/* <div>{JSON.stringify(urlList)}</div> */}
      <div className="min-h-36">
        {isUpFile ? (
          <Dragger {...uploadProps}>
            <div className="mb-4">
              <img src={IconUpload} />
            </div>
            <p className="text-[#2a2a2a] text-sm">点击或将文件拖拽到此处上传</p>
            <span style={{ color: "#999", fontSize: "12px", fontWeight: 400 }}>
              {/* 支持单次或批量上传doc(x)、xlsx、pdf、text、html、jp(e)g、png格式。 */}
              支持单篇或批量上传，支持 doc、docx、excel、pdf、txt、ppt格式
            </span>
          </Dragger>
        ) : (
          <></>
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
                  <div>
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
      <Flex className="justify-end" align="center" justify="center">
        {/* <div className="flex gap-6">
          {!isFaq ? (
            <div>
              <span style={{ color: "#555", marginRight: "8px" }}>
                上传即解析
              </span>
              <Switch onChange={(checked: boolean) => setIsParse(checked)} />
            </div>
          ) : null}
          <div>
            <span style={{ color: "#555", marginRight: "8px" }}>
              上传即抽取
            </span>
            <Switch onChange={(checked: boolean) => setIsExtract(checked)} />
          </div>
        </div> */}
        <div className="flex gap-3">
          <Button
            style={{
              border: "1px solid #ebebeb",
              color: "#555",
              borderRadius: "4px"
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
                background: "linear-gradient(#2867FF, #8789FF)",
                border: "none",
                borderRadius: "4px",
                color: "white"
              }}
              onClick={handleTriggerUpload}
              loading={isUploading}
              disabled={fList.length === 0}
            >
              确定
            </Button>
          ) : (
            <></>
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
