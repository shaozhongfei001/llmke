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
import { api_putArticleMaterialList } from "../AiEditor/core/services/servers";
import { useStateStore } from "../AiEditor/core/states/useStateStore";
import "./style.less";
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
  options?: Option[];
  uploadEvents?: (type: UPLOAD_TYPE, arg: any) => void;
  close: () => void;
}

export interface Option {
  value: string;
  label: string;
  children?: Option[];
}

const OPTIONS: Option[] = [
  {
    value: "zhejiang",
    label: "Zhejiang",
    children: [
      {
        value: "hangzhou",
        label: "Hanzhou",
        children: [
          {
            value: "xihu",
            label: "West Lake"
          }
        ]
      }
    ]
  },
  {
    value: "jiangsu",
    label: "Jiangsu",
    children: [
      {
        value: "nanjing",
        label: "Nanjing",
        children: [
          {
            value: "zhonghuamen",
            label: "Zhong Hua Men"
          }
        ]
      }
    ]
  }
];

export enum UPLOAD_EVENTS {
  MODAL_CLOSE = "upload_event:model_close",
  FILE_REMOVE = "upload_event:remove",
  FILE_UPLOADED = "upload_event:uploaded",
  MODAL_ONLY_CLOSE = "upload_event:model_only_close"
}

export enum FILE_STATUS {
  FINISHED = "finished"
}

export const dealOptions = (data: any[]): any[] => {
  return data.map((item: any) => {
    if (item.subTypeList?.length) {
      return {
        ...item,
        value: item.id,
        label: item.name,
        children: dealOptions(item.subTypeList)
      };
    }
    return { ...item, value: item.id, label: item.name };
  });
};

const UploadFileType = (props: UploadFileTypeProps) => {
  const {
    open,
    title = "上传文档",
    options = OPTIONS,
    uploadEvents,
    close
  } = props;
  const { serverInfo } = useStateStore();
  const [fList, setFList] = useState<any[]>([]);
  const [fileList, setFileList] = useState<any[]>([]);
  const [mOpen, setMOpen] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const closeModal = () => {
    close();
  };

  const deleteFileFromlist = (fileName: string) => {
    setFList(fList.filter((f: UploadFile) => f.name !== fileName));
  };

  const deleteFileFromlist2 = (fileName: string) => {
    setFileList(fileList.filter((f: UploadFile) => f.name !== fileName));
  };

  const makeFormData = (files: any) => {
    const formData = new FormData();
    formData.append("files", files);
    return formData;
  };

  const uploadSeq = async (files: any, cb?: (res: any) => void) => {
    const params = makeFormData(files);
    try {
      const res = await axios$.post(`/cecProxy/dw/articleMaterial`, params, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });
      if (res) {
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
        return [...pre];
      });
    });
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
    multiple: true,
    //action: `${baseURL}/cecProxy/dw/articleMaterial`,
    customRequest: handleFileStatus,
    beforeUpload: handleBeforeUpload,
    onChange: handleFileChange,
    accept: ".ppt,.pptx,.pub,.doc,.docx,.xls,.pdf,.xlsx,.csv,.txt",
    showUploadList: false
  };

  const onChange: any = (value: string, f: UploadFile) => {
    setFList((pre) => {
      const curFile = pre.find((item) => {
        return item.uid === f.uid;
      });
      curFile.chooseType = value;
      return [...pre];
    });
  };

  const handleConfirm = () => {
    const isUploaded = fList.every((item) => {
      return item.status === FILE_STATUS.FINISHED;
    });
    if (!isUploaded) {
      message.warning("文件未上传完成");
      return;
    }
    setFileList(fList);
    setMOpen(true);
    close();
    //uploadEvents && uploadEvents(UPLOAD_TYPE.CONFIRM, fList);
  };

  useEffect(() => {
    if (open) {
      setFList([]);
      setFileList([]);
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
          title={<span className="text-[16px] font-normal">{title}</span>}
          width={768}
          destroyOnClose={true}
          cancelText={"取消"}
          okText={"确定"}
          footer={null}
          onCancel={closeModal}
          closable={false}
        >
          <div className="px-[24px]">
            <div className="min-h-36">
              <Dragger {...uploadProps}>
                <div className="mb-4">
                  <img src={IconUpload} />
                </div>
                <p className="text-[#2a2a2a] text-sm">
                  点击或将文件拖拽到此处上传
                </p>
                <span
                  style={{ color: "#999", fontSize: "12px", fontWeight: 400 }}
                >
                  支持单篇或批量上传，支持 doc、docx、excel、pdf、txt、ppt格式
                  {/* 支持单次或批量上传doc(x)、xlsx、pdf、text、html、jp(e)g、png格式以及zip、tar等压缩文件。 */}
                </span>
              </Dragger>
            </div>
            <div className="upload-list-wrap">
              <div className="upload-list-container max-h-[200px] overflow-y-auto overflow-x-hidden">
                {fList.map((f: UploadFile, idx: number) => {
                  return (
                    <div
                      key={`file_${f.name}_${idx}`}
                      className="flex justify-between h-[32px] mb-[8px] items-center rounded-[4px]"
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
                          // <Cascader
                          //   options={options}
                          //   onChange={(value) => onChange(value, f)}
                          //   changeOnSelect
                          //   size="small"
                          //   className="w-[256px]"
                          // />
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
                borderRadius: "8px"
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
                borderRadius: "8px"
              }}
              onClick={handleConfirm}
              loading={confirmLoading}
              disabled={fList.length === 0}
            >
              确定
            </Button>
          </div>
        </Modal>
      </ConfigProvider>
      <ChooseMaterialType
        open={mOpen}
        closeModal={() => setMOpen(false)}
        handleConfirm={() => {
          handleConfirmFiles(
            fileList,
            serverInfo,
            () => setMOpen(false),
            uploadEvents
          );
        }}
        fileList={fileList}
        deleteFileFromlist2={deleteFileFromlist2}
        options={options}
        onChange={onChange}
        firstMaterialClassify={(checkFristMaterial: boolean) => {
          if (checkFristMaterial) {
            setFList((pre) => {
              const curFile = pre[0];
              curFile &&
                pre.forEach((item) => {
                  item.chooseType = curFile.chooseType;
                });

              return [...pre];
            });
          }
        }}
      />
    </>
  );
};

export default UploadFileType;

export const handleConfirmFiles = async (
  fileList: any[],
  serverInfo: any,
  cb: any,
  uploadEvents: any
) => {
  try {
    const vali = fileList.every((item) => {
      return item?.chooseType?.length;
    });
    if (!vali) {
      message.warning("请选择类型");
      return;
    }
    const filePromises = fileList.map((item, index) => {
      const ma = (item.chooseType || []).map((item: any) => {
        return item[item.length - 1];
      });
      return api_putArticleMaterialList({
        data: { id: item.id, params: { materialType: ma } },
        config: {
          ...serverInfo,
          enableMock: false
        }
      });
    });
    const responses = await Promise.all(filePromises);
    if (responses) {
      cb();
      uploadEvents && uploadEvents(UPLOAD_TYPE.MODAL_CLOSE, fileList);
    }
  } catch (error) {
    console.log("====================================");
    console.log("error", error);
    console.log("====================================");
  }
};

export const ChooseMaterialType = ({
  open,
  closeModal,
  handleConfirm,
  fileList,
  deleteFileFromlist2,
  options,
  onChange,
  firstMaterialClassify
}: any) => {
  const [checkFristMaterial, setCheckFristMaterial] = useState(false);
  return (
    <ConfigProvider
      modal={{
        styles: modalStyles
      }}
    >
      <Modal
        open={open}
        title={<span className="text-[16px] font-normal">选择素材类型</span>}
        width={768}
        destroyOnClose={true}
        cancelText={"取消"}
        okText={"确定"}
        footer={null}
        onCancel={closeModal}
        closable={false}
      >
        <div className="h-[210px] px-[24px] overflow-y-auto overflow-x-hidden uploadFileType">
          <Checkbox
            className="mb-[10px]"
            onChange={(e) => {
              firstMaterialClassify(e.target.checked);
            }}
          >
            使用第一个素材标识标记所有文件
          </Checkbox>
          {fileList.map((f: UploadFile, idx: number) => {
            return (
              <div
                key={`file_${f.name}_${idx}`}
                className="flex justify-between h-[40px] mb-[8px] items-center rounded-[4px]"
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
                  <Cascader
                    options={options}
                    onChange={(value) => onChange(value, f)}
                    value={
                      f?.chooseType && f?.chooseType?.length > 0
                        ? f.chooseType
                        : []
                    }
                    className="w-[256px]"
                    showCheckedStrategy="SHOW_CHILD"
                    multiple
                    maxTagCount={1}
                  />
                  <Button
                    type="link"
                    style={{
                      fontSize: "12px",
                      color: "#055aff"
                    }}
                    onClick={() => {
                      deleteFileFromlist2(f.name);
                    }}
                  >
                    删除
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
        <div
          className="flex justify-end px-[24px] py-[16px]"
          style={{ borderTop: "1px solid #eeeeee" }}
        >
          <Button
            style={{
              border: "1px solid #ebebeb",
              color: "#555",
              marginRight: "16px"
            }}
            onClick={closeModal}
          >
            取消
          </Button>
          <Button
            type="primary"
            style={{
              background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
              color: "#fff",
              border: "none"
            }}
            onClick={handleConfirm}
          >
            确定
          </Button>
        </div>
      </Modal>
    </ConfigProvider>
  );
};
