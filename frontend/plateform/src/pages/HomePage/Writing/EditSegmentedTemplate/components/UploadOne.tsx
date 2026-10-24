import {
  Button,
  Cascader,
  CascaderProps,
  ConfigProvider,
  message,
  Modal,
  Progress,
  Upload,
  UploadFile,
  UploadProps,
  Checkbox
} from "antd";
import IconFile from "@/assets/knowledgebase/icon-file.svg";
import IconUpload from "@/assets/knowledgebase/icon-upload.svg";
import { useEffect, useMemo, useState } from "react";
import axios$ from "@root/src/apis";
const { Dragger } = Upload;

const modalStyles = {
  content: { padding: "0", borderRadius: "8px" },
  header: { margin: 0, padding: "24px" }
};
export enum UPLOAD_TYPE {
  TYPE_CHANGE = "type_change",
  CONFIRM = "confirm",
  MODAL_CLOSE = "modal_close"
}

interface UploadFileTypeProps {
  open: boolean;
  title?: string;
  uploadEvents?: (arg: any) => void;
  close: () => void;
}

export enum UPLOAD_EVENTS {
  MODAL_CLOSE = "upload_event:model_close",
  FILE_REMOVE = "upload_event:remove",
  FILE_UPLOADED = "upload_event:uploaded",
  MODAL_ONLY_CLOSE = "upload_event:model_only_close"
}

export enum FILE_STATUS {
  FINISHED = "finished"
}

const UploadFileType = (props: UploadFileTypeProps) => {
  const { open, title = "上传文档", uploadEvents, close } = props;

  const [fList, setFList] = useState<any[]>([]);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const closeModal = () => {
    close();
  };

  const deleteFileFromlist = (fileName: string) => {
    setFList(fList.filter((f: UploadFile) => f.name !== fileName));
  };

  const makeFormData = (files: any) => {
    const formData = new FormData();
    formData.append("file", files);
    return formData;
  };

  const uploadSeq = async (files: any, cb?: (res: any) => void) => {
    const params = makeFormData(files);
    try {
      const res = await axios$.post(
        `/cecProxy/dw/articleMaterial/parseText`,
        params,
        {
          headers: {
            "Content-Type": "multipart/form-data"
          }
        }
      );
      if (res) {
        console.log("res-----", res);
        cb && cb(res);
      }
    } catch (error) {
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const handleFileStatus = (options: any) => {
    const { onSuccess, onProgress, file } = options;

    uploadSeq(file, (res) => {
      const { data } = res;
      const id = data?.[0]?.id;
      onProgress({ percent: 100 });
      onSuccess(true);
      setFList((pre) => {
        const curFile = pre.find((item) => {
          return item.uid === file.uid;
        });
        curFile.id = id;
        curFile.status = FILE_STATUS.FINISHED;
        curFile.fileUpload = data;
        curFile.originFile = file;
        return [...pre];
      });
    });
  };

  const handleBeforeUpload = (file: UploadFile) => {
    const { name, size } = file;
    let errMsg = "";
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
    let progress = 0;
    const interval = setInterval(() => {
      if (file.percent === 100) {
        clearInterval(interval);
      } else if (progress < 90) {
        progress += 10;
        file.percent = progress;
        setFList((pre) => {
          const cur = pre.find((item) => item.uid === file.uid);
          if (cur) {
            cur.percent = file.percent;

            return [...pre];
          } else {
            return [...pre, file];
          }
        });
      } else {
        clearInterval(interval);
      }
    }, 500);
    const { status, response } = file;
    const errMsg = "上传出错请联系管理员";
    switch (status) {
      case "error":
        message.error(response ? response.errorMsg || errMsg : errMsg);
        break;
      case "removed":
        deleteFileFromlist(file.name);
        break;
      case "uploading":
        setFList((pre) => {
          const cur = pre.find((item) => item.uid === file.uid);
          if (cur) {
            cur.percent = file.percent;

            return [...pre];
          } else {
            return [...pre, file];
          }
        });
        break;
      case "done":
        setFList((pre) => {
          const cur = pre.find((item) => item.uid === file.uid);
          if (cur) {
            cur.percent = file.percent;
          }
          return [...pre];
        });
        break;
    }
  };

  const uploadProps: UploadProps = {
    style: {
      backgroundColor: "#f9fafc",
      borderColor: "#d9d9d9",
      marginBottom: "16px"
    },
    multiple: false,
    customRequest: handleFileStatus,
    beforeUpload: handleBeforeUpload,
    onChange: handleFileChange,
    accept: ".docx,.doc",
    showUploadList: false
  };

  const handleConfirm = async () => {
    const isUploaded = fList.every((item) => {
      return item.status === FILE_STATUS.FINISHED;
    });
    if (!isUploaded) {
      message.warning("文件未上传完成");
      return;
    }
    const file = fList?.length > 0 && fList[0];
    if (file) {
      const params = makeFormData(file.originFile);
      try {
        const res = await axios$.post(
          `/cecProxy/dw/articleType/genOutlinesByDocx`,
          params,
          {
            headers: {
              "Content-Type": "multipart/form-data"
            }
          }
        );
        if (res) {
          file.extractRes = res?.data;
          close();
          uploadEvents && uploadEvents(file);
        }
      } catch (error) {
        console.log("====================================");
        console.log("error", error);
        console.log("====================================");
      }
    }
  };

  useEffect(() => {
    if (open) {
      setFList([]);
    }
  }, [open]);

  return (
    <>
      <ConfigProvider
        modal={{
          styles: modalStyles
        }}
      >
        <Modal
          open={open}
          title={<span className="text-base font-normal">{title}</span>}
          width={528}
          destroyOnClose={true}
          cancelText={"取消"}
          okText={"确定"}
          footer={null}
          onCancel={closeModal}
          closable={false}
        >
          <div className="px-6">
            <div className="min-h-9">
              <Dragger {...uploadProps} disabled={fList.length >= 1}>
                <div className="mb-4 flex justify-center">
                  <img src={IconUpload} />
                </div>
                <p className="text-gray-2a text-sm">
                  点击或将文件拖拽到此处上传
                </p>
                <span className="text-text-color3 text-xs">
                  支持单篇上传，支持 doc、docx格式
                </span>
              </Dragger>
            </div>
            <div className="upload-list-wrap">
              <div className="upload-list-container max-h-[200px] overflow-y-auto overflow-x-hidden">
                {fList.map((f: UploadFile, idx: number) => {
                  return (
                    <div
                      key={`file_${f.name}_${idx}`}
                      className="flex justify-between h-8 mb-2 items-center rounded"
                      style={{ border: "1px solid #eeeeee" }}
                    >
                      <div className="flex items-center">
                        <img
                          src={IconFile}
                          style={{
                            position: "relative",
                            marginRight: "8px",
                            top: "1px",
                            marginLeft: "8px"
                          }}
                        />
                        <div
                          style={{
                            fontSize: "12px",
                            color: "#555",
                            width: "330px"
                          }}
                          className="text-ellipsis break-words line-clamp-1"
                        >
                          {f.name}
                        </div>
                      </div>
                      <div className="flex items-center">
                        {(f.status as any) === "finished" ? (
                          <></>
                        ) : (
                          <Progress
                            percent={f.percent}
                            className="w-[256px]"
                            size="small"
                          />
                        )}
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
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
          <div
            className="flex justify-end px-[24px] py-[16px]"
            style={{ borderTop: "1px solid #eeeeee" }}
          >
            <Button
              style={{
                border: "1px solid #ebebeb",
                color: "#555",
                marginRight: "16px",
                borderRadius: "4px"
              }}
              onClick={closeModal}
            >
              取消
            </Button>
            <Button
              type="primary"
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                opacity: fList.length === 0 ? "50%" : "100%",
                color: fList.length === 0 ? "#ddd" : "#fff",
                border: "none",
                borderRadius: "4px"
              }}
              onClick={handleConfirm}
              loading={confirmLoading}
              disabled={fList.length === 0}
            >
              抽取大纲
            </Button>
          </div>
        </Modal>
      </ConfigProvider>
    </>
  );
};

export default UploadFileType;
