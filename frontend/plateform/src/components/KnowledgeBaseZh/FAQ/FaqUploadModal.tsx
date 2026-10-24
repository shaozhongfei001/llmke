import {
  Modal,
  Form,
  Input,
  Button,
  Select,
  UploadProps,
  UploadFile,
  Flex,
  Checkbox,
  Dropdown
} from "antd";
import { useEffect, useState } from "react";
import "@/assets/styles/knowledgebase.less";
import { message, Upload } from "antd";
import axios$ from "@root/src/apis";
import { baseURL } from "@root/src/apis/common";
import { UPLOAD_EVENTS } from "@root/src/components/UploadAfterConfirm";
import { DownloadOutlined } from "@ant-design/icons";
import { getUrlPrefix, useAppPassport } from "@root/src/core/helps";
import FolderSelect from "./FolderSelect";

const { Dragger } = Upload;

interface IEmpty {
  isShowCreateModal: boolean;
  closeModal: (isRefresh: boolean) => void;
  uploadType?: string;
  knowledgeBaseId: number;
  uploadEvents: (action: string, payload?: any) => void;
}

const FaqUploadModal = (props: IEmpty) => {
  const {
    isShowCreateModal,
    closeModal,
    uploadType = "upload",
    knowledgeBaseId,
    uploadEvents
  } = props;
  const [createForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const { userInfo }: any = useAppPassport();
  const [fileList, setFileList]: any = useState<UploadFile[]>([]);
  const [isExtract, setIsExtract] = useState(false);
  const [folder, setFolder] = useState<any>(null);
  const { getToken } = useAppPassport();
  const successFn = () => {
    closeModal(true);
    setLoading(false);
    createForm.resetFields();
    uploadEvents(UPLOAD_EVENTS.FILE_UPLOADED);
  };

  const handlerCancle = () => {
    createForm.resetFields();
    closeModal(false);
  };

  const handleOk = async () => {
    const formData = new FormData();
    fileList.forEach((file: any) => {
      formData.append("files", file);
    });

    // const p: any = {
    //   method: "POST",
    //   body: formData,
    //   headers: {
    //     Authorization: userInfo.token,
    //     userId: 1, //userInfo.id,
    //     userName: "system" //userInfo.userName
    //   }
    // };

    setLoading(true);

    let url = `${baseURL}/index${
      uploadType === "upload"
        ? "/knowledgeBase/file/uploadFiles"
        : "/faq/uploadFiles"
    }?${
      uploadType === "upload" ? "fileListType=2" : ""
    }&kbId=${knowledgeBaseId}&isOverwrite=true${
      uploadType === "upload" ? `&isExtract=${isExtract}` : ""
    }`;
    if (uploadType !== "upload") {
      if (!folder) return message.warning("请选择文件夹");
      if (folder.dataType === 1) {
        url = `${url}&folderId=${folder.folderId}`;
      } else {
        url = `${url}&fileId=${folder.fileId}`;
      }
    }
    await axios$
      .post(url, formData, {
        headers: {
          Authorization: userInfo.token || ""
        }
      })
      .then((res: any) => {
        if (res.success) {
          successFn();
        } else {
          message.error("上传失败");
        }

        console.log("upload", res);
      })
      .finally(() => {
        setLoading(false);
      });
  };
  const upLoadProps: UploadProps = {
    multiple: true,
    fileList,
    onRemove: (file) => {
      setFileList((fileList: any) => {
        const fileListIds = fileList.map((item: any) => item.uid);
        const index = fileListIds.indexOf(file.uid);
        const newFileList = fileList.slice();
        newFileList.splice(index, 1);
        return [...newFileList];
      });
    },
    beforeUpload(file) {
      setFileList((fileList: any) => {
        return [...fileList, file];
      });
      return false;
    }
  };

  const renderFooter = () => {
    return (
      <Flex
        style={{ width: "100%", gap: "10px" }}
        align="center"
        justify="center"
      >
        <Button key="back" onClick={handlerCancle} className="cancle-btn">
          取消
        </Button>
        <Button
          key="submit"
          type="primary"
          loading={loading}
          disabled={
            uploadType !== "upload"
              ? !fileList.length || !folder
              : !fileList.length
          }
          onClick={handleOk}
        >
          确认
        </Button>
        {uploadType === "upload" ? (
          <Checkbox
            checked={isExtract}
            onChange={(event) => setIsExtract(event.target.checked)}
          >
            上传后直接抽取
          </Checkbox>
        ) : (
          <></>
        )}
      </Flex>
    );
  };
  const handleDownload = async (payload: any) => {
    fetch(`${getUrlPrefix()}/index/faq/downloadTemplate?fileType=${payload}`, {
      method: "GET",
      headers: {
        Authorization: getToken() || ""
      }
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.blob(); // 获取Blob对象
      })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        a.download = `FAQ.${payload}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url); // 释放URL对象
        document.body.removeChild(a);
      })
      .catch((error) => {
        console.error(
          "There has been a problem with your fetch operation:",
          error
        );
      });
  };

  useEffect(() => {
    if (!isShowCreateModal) {
      setFolder(null);
      setIsExtract(false);
      setFileList([]);
    }
  }, [isShowCreateModal]);

  return (
    <Modal
      title={
        uploadType === "upload" ? (
          "上传文件"
        ) : (
          <div className="flex justify-center items-end">
            导入文件
            <div className="text-[12px] mb-[3.5px] text-[#CC3C29]">
              （请先下载模板）
            </div>
          </div>
        )
      }
      destroyOnClose
      className=""
      open={isShowCreateModal}
      width={"55vw"}
      footer={renderFooter}
      onCancel={handlerCancle}
    >
      <div
        className={`${uploadType === "upload" ? "h-[380px] " : "h-[480px]"} uploadB`}
      >
        <div className="px-[30px] h-[80%]">
          {uploadType !== "upload" && (
            <div className="flex h-[100px] items-start overflow-y-auto overflow-x-hidden mb-[8px]">
              <div className={` question-title mb-[8px] flex items-center`}>
                <div className="text-red-700 mr-[5px]">*</div>
                <div>文件夹</div>
              </div>
              {isShowCreateModal && (
                <FolderSelect
                  kbId={knowledgeBaseId as any}
                  setValue={setFolder}
                />
              )}
            </div>
          )}

          <div
            className={`${uploadType === "upload" ? "h-[300px]" : "h-[250px]"}`}
          >
            <Dragger
              {...upLoadProps}
              itemRender={(originNode) => {
                return originNode;
              }}
              accept={
                uploadType === "upload"
                  ? ".ppt,.pptx,.pub,.doc,.docx,.xls,.pdf,.xlsx,.csv,.txt"
                  : ".xlsx,.csv,.txt"
              }
              style={{
                backgroundColor: "#F5F9FF",
                borderColor: "#014DDF"
              }}
            >
              <div className="nlp-knowledage-base-upload-icon"></div>
              <p className="ant-upload-text">点击或将文件拖拽到此处上传</p>
              {uploadType === "upload" ? (
                <span
                  style={{ color: "#999", fontSize: "12px", fontWeight: 400 }}
                >
                  支持单次或批量上传，支持 ppt、doc、excel、pdf、txt格式。
                </span>
              ) : (
                <span
                  style={{ color: "#999", fontSize: "12px", fontWeight: 400 }}
                >
                  导入文件仅支持csv、excel、txt文件，且严格遵循
                  <Dropdown
                    menu={{
                      items: [
                        {
                          key: "xlsx",
                          label: "xlsx"
                        },
                        {
                          key: "csv",
                          label: "csv"
                        },
                        {
                          key: "txt",
                          label: "txt"
                        }
                      ]
                    }}
                    dropdownRender={(menu) => (
                      <div
                        onClick={(e: any) => {
                          e.stopPropagation();
                          handleDownload(e.target.innerText);
                        }}
                      >
                        {menu}
                      </div>
                    )}
                    placement="bottom"
                  >
                    <Button
                      type="primary"
                      ghost
                      icon={<DownloadOutlined />}
                      size="small"
                      className="ml-[4px]"
                      onClick={(e) => {
                        e.stopPropagation();
                      }}
                    >
                      模板格式
                    </Button>
                  </Dropdown>
                </span>
              )}
            </Dragger>
          </div>
        </div>
      </div>
      <div className="btn-group"></div>
    </Modal>
  );
};

export default FaqUploadModal;
