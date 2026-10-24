import {
  Modal,
  Form,
  Input,
  Button,
  Select,
  UploadProps,
  UploadFile,
  Flex,
  Tag
} from "antd";
import { useCallback, useEffect, useRef, useState } from "react";
import "@/assets/styles/knowledgebase.less";
import { message, Upload } from "antd";
import axios$ from "@root/src/apis";
import { useMutation } from "@tanstack/react-query";
import { DocApi } from "@root/src/apis/docApi/DocApi";
import { useMyHttpClient } from "@root/src/apis/docApi";
import IconUpload from "@/assets/knowledgebase/icon-upload.svg";
import "../index.less";

const { Dragger } = Upload;
interface IRow {
  id?: number;
  kbName?: string;
  kbDes?: string | null;
  [key: string]: any;
}
interface IEmpty {
  isShowCreateModal: boolean;
  closeModal: (isRefresh: boolean) => void;
  type: string;
  cb?: (action: string, data?: any) => void;
}

enum UploadFileType {
  SUCCESS = 1,
  FAILED,
  EMPTY,
  REPEAT
}

const OPTIONS = [
  {
    value: "add",
    label: "空白文稿"
  },
  {
    value: "notice",
    label: "通知公告"
  }
];

const styleTags = [
  "通知公告",
  "工作报告",
  "调研报告",
  "邀请函",
  "心得体会",
  "讲话稿"
];
const senceTags = ["银行", "证券", "保险"];

const senceTagMap = [
  {
    key: "all",
    label: "全部"
  },
  {
    key: "bank",
    label: "银行"
  },
  {
    key: "insurance",
    label: "保险"
  },
  {
    key: "security",
    label: "证券"
  },
  {
    key: "other",
    label: "其他"
  }
];
const styleTagMap = [
  {
    key: "all",
    label: "全部"
  },
  {
    key: "notice",
    label: "通知公告"
  },
  {
    key: "report",
    label: "工作报告"
  },
  {
    key: "survey",
    label: "调研报告"
  },
  {
    key: "invitation",
    label: "邀请函"
  },
  {
    key: "understanding",
    label: "心得体会"
  },
  {
    key: "speech",
    label: "讲话稿"
  },
  {
    key: "other",
    label: "其他"
  }
];

const ResourceUploadModal = (props: IEmpty) => {
  const { isShowCreateModal, closeModal, cb, type } = props;
  const [fileList, setFileList] = useState<any[]>([]);
  const [selectOpen, setSelectOpen] = useState(false);

  const api = new DocApi(useMyHttpClient());
  const deleteMaterial = useMutation({
    mutationFn: (id: number) => api.deleteByIdUsingDelete(id).then((res) => res)
  });

  // 上传的请求列表
  const filesUploadReq = useRef<FormData[]>([]);
  const cancelRef = useRef(new AbortController());

  const handleBeforeUpload = (file: UploadFile) => {
    const isExit = fileIsExit(file.name.split(".")[0]);
    if (!isExit) {
      if (file.size === 0) {
        message.warning("请不要上传空文件");
        return Upload.LIST_IGNORE;
      }
    } else {
      message.warning("请不要上传重复文件");
      return Upload.LIST_IGNORE;
    }
    return Promise.resolve();
  };

  const fileIsExit = useCallback(
    (fileName: string) => {
      const isExit = fileList.find(
        (f: UploadFile) => f.name.split(".")[0] == fileName
      );
      return isExit;
    },
    [fileList]
  );

  const uploadReq = (files: FormData) => {
    const sence = senceTagMap.find((s) => s.label == selectedSenceTag);
    const articleStyle = styleTagMap.find((s) => s.label == selectedStyleTag);
    files.append("bizType", type);
    sence && files.append("scene", sence.key);
    articleStyle && files.append("articleStyle", articleStyle.key);
    return axios$.post(`/cecProxy/dw/articleMaterial`, files, {
      signal: cancelRef.current?.signal,
      headers: {
        "Content-Type": "multipart/form-data"
      }
    });
  };

  //   上传文件改变时
  const handleFileChange = async (info: any) => {
    const { file, fileList } = info;
    setFileList(fileList);
    if (file.status === "done") {
      const formData = new FormData();
      formData.append("files", file.originFileObj);
      filesUploadReq.current.push(formData);
    }
    if (file.status === "error") {
      message.error(file?.response?.errorMsg || "上传出错请联系管理员");
    }
    if (file.status === "removed") {
      setFileList(
        fileList.filter((curFile: any) => {
          return curFile.uid !== file.uid;
        })
      );
    }
  };

  const handleFileDragged = (options: any) => {
    const { onSuccess, onProgress } = options;
    onProgress({ percent: 100 });
    onSuccess(true);
  };

  const upLoadProps: UploadProps = {
    multiple: true,
    customRequest: handleFileDragged,
    beforeUpload: handleBeforeUpload,
    onChange: handleFileChange,
    accept: ".ppt,.pptx,.pub,.doc,.docx,.xls,.pdf,.xlsx,.csv,.txt"
  };

  // 上传成功的文件id,点击取消时记得删除
  const [resulitCount, setResulitCount] = useState(0);
  useEffect(() => {
    if (filesUploadReq.current.length === resulitCount && resulitCount !== 0) {
      setUploadLoading(false);
      cb && cb("material_refresh");
      handleClose();
    }
  }, [resulitCount]);

  const [successFileIds, setSuccessFileIds] = useState<number[]>([]);
  const [uploadLoading, setUploadLoading] = useState<boolean>(false);
  const handleTriggerUpload = async () => {
    try {
      setUploadLoading(true);
      (filesUploadReq.current || []).forEach(async (i: FormData) => {
        uploadReq(i).then((res: any) => {
          setResulitCount((p) => p + 1);
          const { data, success } = res;
          if (data.length || success) {
            const { id, status, fileName } = data[0];
            if (status !== UploadFileType.SUCCESS) {
              message.error(fileName + "上传失败");
            } else {
              setSuccessFileIds((p) => [...p, id]);
            }
          }
        });
      });
    } catch (err) {
      setUploadLoading(false);
      handleClose();
    }
  };

  const handleClose = () => {
    closeModal(false);
    setFileList([]);
    filesUploadReq.current = [];
    setResulitCount(0);
    setSuccessFileIds([]);
    setSelected([]);
    setSelectedSenceTag("");
    setSelectedStyleTag("");
    setUploadLoading(false);
  };

  const [cancelLoading, setCancelLoading] = useState<boolean>(false);
  const handleCancel = async () => {
    setCancelLoading(true);
    cancelRef.current.abort();
    cancelRef.current = new AbortController();
    if (successFileIds.length) {
      Promise.all(successFileIds.map((i) => deleteMaterial.mutateAsync(i)))
        .then((res) => {
          setCancelLoading(false);
          handleClose();
        })
        .catch((err) => {
          console.log(err, "+++++++++++++++++");
        });
    } else {
      setCancelLoading(false);
      handleClose();
    }
  };

  const [selected, setSelected] = useState<string[]>([]);

  const [selectedSenceTag, setSelectedSenceTag] = useState<string>("");
  const handleSenceTagChange = (tag: string) => {
    setSelectedSenceTag(tag);
  };

  const [selectedStyleTag, setSelectedStyleTag] = useState<string>("");
  const handleStyleTagChange = (tag: string) => {
    setSelectedStyleTag(tag);
  };

  const onFinish = () => {
    setSelected([selectedStyleTag, selectedSenceTag].filter((f) => !!f));
    setSelectOpen(false);
  };

  return (
    <Modal
      title="上传素材"
      open={isShowCreateModal}
      width={512}
      destroyOnClose={true}
      onCancel={handleCancel}
      className="upload-resources"
      okButtonProps={{ loading: uploadLoading, disabled: cancelLoading }}
      cancelButtonProps={{ loading: cancelLoading }}
      footer={null}
    >
      {type !== "commonLib" && (
        <Select
          className="w-full mb-[10px]"
          placeholder="选择上传类型"
          mode="multiple"
          showSearch={false}
          value={selected}
          open={selectOpen}
          onDropdownVisibleChange={() => {
            setSelectOpen(true);
          }}
          onDeselect={(value) => {
            setSelectedSenceTag((pre) => (pre == value ? "" : pre));
            setSelectedStyleTag((pre) => (pre == value ? "" : pre));
            setSelected((pre) => pre.filter((p) => p !== value));
          }}
          dropdownRender={(menu) => (
            <div className="material p-[10px]">
              {type == "demoLib" && (
                <Flex>
                  <div className="font-bold w-[50px] h-[32px] leading-[32px]">
                    文体:
                  </div>
                  <div>
                    {styleTags.map<React.ReactNode>((tag) => (
                      <Tag.CheckableTag
                        key={tag}
                        checked={selectedStyleTag == tag}
                        onChange={(checked) => handleStyleTagChange(tag)}
                        className="bg-[#F5F6FA] hover:text-[#055AFF] hover:bg-[#E2E9FF] text-[14px] mb-[12px] h-[32px] leading-[32px]"
                      >
                        {tag}
                      </Tag.CheckableTag>
                    ))}
                  </div>
                </Flex>
              )}
              {(type == "lawLib" || type == "demoLib") && (
                <Flex>
                  <div className="font-bold w-[40px] h-[32px] leading-[32px]">
                    场景:
                  </div>
                  <div>
                    {senceTags.map<React.ReactNode>((tag) => (
                      <Tag.CheckableTag
                        key={tag}
                        checked={selectedSenceTag == tag}
                        onChange={(checked) => handleSenceTagChange(tag)}
                        className="bg-[#F5F6FA] hover:text-[#055AFF] hover:bg-[#E2E9FF] text-[14px] mb-[12px] h-[32px] leading-[32px]"
                      >
                        {tag}
                      </Tag.CheckableTag>
                    ))}
                  </div>
                </Flex>
              )}
              <div className="w-full ml-[12px] flex flex-row justify-end align-center">
                <Button
                  type="primary"
                  onClick={() => {
                    if (selected.length > 0) {
                      setSelectOpen(false);
                    } else {
                      setSelectOpen(false);
                      setSelected([]);
                      setSelectedSenceTag("");
                      setSelectedStyleTag("");
                    }
                  }}
                  style={{
                    color: `#555555`,
                    backgroundColor: "#fff",
                    borderRadius: "4px",
                    border: "1px solid #dedede"
                  }}
                >
                  取消
                </Button>
                <Button
                  ghost
                  onClick={onFinish}
                  style={{
                    background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                    color: "#fff",
                    border: "none",
                    marginLeft: "10px"
                  }}
                >
                  确认
                </Button>
              </div>
            </div>
          )}
        />
      )}

      <Dragger {...upLoadProps}>
        <p className="ant-upload-drag-icon">
          <img src={IconUpload} alt="rectangle" className="w-[48px] h-[48px]" />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
        <p className="ant-upload-hint">
          支持单次或批量上传，支持 ppt、doc、excel、pdf格式。
        </p>
      </Dragger>

      <div
        className="flex justify-end px-[24px] pt-[16px]"
        style={{ borderTop: "1px solid #eeeeee" }}
      >
        <Button
          style={{
            border: "1px solid #ebebeb",
            color: "#555",
            marginRight: "16px",
            borderRadius: "8px"
          }}
          onClick={handleCancel}
        >
          取消
        </Button>
        <Button
          type="primary"
          style={{
            background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
            border: "none",
            borderRadius: "8px",
            opacity: fileList.length === 0 ? "50%" : "100%",
            color: fileList.length === 0 ? "#ddd" : "#fff"
          }}
          onClick={handleTriggerUpload}
          disabled={fileList.length === 0}
        >
          确定
        </Button>
      </div>
    </Modal>
  );
};

export default ResourceUploadModal;
