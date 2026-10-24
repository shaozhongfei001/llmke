import {
  Button,
  Checkbox,
  Flex,
  Modal,
  UploadFile,
  UploadProps,
  message
} from "antd";
import Dragger from "antd/lib/upload/Dragger";
import { baseURL } from "@root/src/apis/common";
import axios$ from "@root/src/apis";
import { useEffect, useState } from "react";
import { useAppPassport } from "@root/src/core/helps";

interface UploadBoxProps {
  name?: string;
  knowledgeBaseId: number;
  open: any;
  uploadEvents: (action: string, payload?: any) => void;
}

enum UPLOAD_EVENTS {
  MODAL_CLOSE = "upload_event:model_close",
  FILE_REMOVE = "upload_event:remove",
  FILE_UPLOADED = "upload_event:uploaded",
  MODAL_ONLY_CLOSE = "upload_event:model_only_close"
}

const UploadModal = (props: UploadBoxProps) => {
  const { getToken } = useAppPassport();
  const { knowledgeBaseId, uploadEvents } = props;
  const [files, setFiles] = useState<FormData[]>([]);
  const [singleFormData, setSingleFormData] = useState<FormData>(
    new FormData()
  );
  const [filesInfo, setFilesInfo] = useState([]);
  const [isParseChecked, setIsParse] = useState(false);
  const [isExtract, setIsExtract] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // 单个上传的版本，有进度，会抖动
  const handleBeforeUpload = (file: UploadFile) => {
    const isPass = true;
    // const isPass = validateName(file.name.split('.')[0])
    if (isPass) {
      if (file.size === 0) {
        message.warning("请不要上传空文件");
        return false;
      }
    } else {
      message.warning("文件名不能以数字开头且不能包含特殊字符,长度在0-24");
      return false;
    }
    return Promise.resolve();
  };

  //   上传文件改变时
  const handleFileChange = async (info: any) => {
    const { file } = info;
    if (file.status === "error") {
      message.error(file?.response?.errorMsg || "上传出错请联系管理员");
    }
    if (file.status === "removed") {
      // console.log("remove files", files);
      // remove file from FormData array
      setFiles(
        files.filter((formData: FormData) => {
          return formData.get("files")?.name != file.name;
        })
      );
    }
    if (file.status === "done") {
    }
  };

  const handleFileDragged = (options: any) => {
    const { onSuccess, onError, onProgress, onChange, file } = options;
    // console.log('file', file)
    const formData = new FormData();
    formData.append("files", file);

    const curFiles = files;
    curFiles.push(formData);
    console.log("curFiles", curFiles);
    setFiles(curFiles);

    onProgress({ percent: 100 });
    onSuccess(true);
  };

  const handleFileDragged_new = (options: any) => {
    const { onSuccess, onError, onProgress, onChange, file } = options;
    // console.log("file", file);

    setFilesInfo((pre: any) => {
      pre.push({
        fileName: file.name,
        // type: "SKIP"
        type: "NEWVERSION"
      });
      return pre;
    });
    const temp_formData = singleFormData;
    temp_formData.append("files", file);

    setSingleFormData(temp_formData);

    onProgress({ percent: 100 });
    onSuccess(true);
  };

  const handleTriggerUpload_new = async () => {
    const request_files = {
      kbId: knowledgeBaseId,
      fileListType: 1,
      isParse: isParseChecked,
      isExtract: isExtract,
      fileList: filesInfo
    };
    console.log("singleFormData", singleFormData);
    const temp_formData = singleFormData;
    temp_formData.append("uploadFileParam", JSON.stringify(request_files));

    const res = await axios$.post(
      `${baseURL}/index/knowledgeBase/file/uploadFileList?kbId=${knowledgeBaseId}&isOverwrite=true&isParse=${isParseChecked}&isExtract=${isExtract}&fileListType=1`,
      singleFormData,
      {
        headers: {
          Authorization: getToken() || ""
          // "Content-Type": "multipart/form-data"
        }
      }
    );
    console.log("upload res", res);
  };

  const handleTriggerUpload = () => {
    const sequences = [];
    for (let i = 0; i < files.length; i++) {
      sequences.push(uploadSeq(files[i]));
    }
    setIsLoading(true);

    Promise.all(sequences)
      .then((results: any) => {
        console.log("file upload result", results);
        if (results.every((result: any) => result?.success == true)) {
          message.success("文件上传成功！", 2);
          uploadEvents(UPLOAD_EVENTS.MODAL_CLOSE);
        } else {
          const errors: any = [];
          results.forEach((result: any, index: any) => {
            if (result?.success != true) errors.push(index + 1);
          });
          console.log("File upload failed: ", errors.join(";"));
          message.error(`部分文件上传失败，序号:${errors.join("; ")}`);
        }

        setIsLoading(false);
        uploadEvents(UPLOAD_EVENTS.FILE_UPLOADED);
        setFiles([]);
      })
      .catch((e: any) => {
        console.log("Error when uploading file", e);

        message.error(`部分文件上传失败，序号:${1}`);
        setFiles([]);
      });
  };

  const uploadSeq = (file: FormData) => {
    return axios$.post(
      `${baseURL}/index/knowledgeBase/file/uploadFiles?kbId=${knowledgeBaseId}&isOverwrite=true&isParse=${isParseChecked}&isExtract=${isExtract}&fileListType=1`,
      file,
      {
        headers: {
          Authorization: getToken() || ""
        }
      }
    );
  };

  // useEffect(() => {
  //   console.log("files", files);
  // }, [files]);

  const UPLOAD_HEADERS = {
    Authorization: getToken() || ""
  };

  // 文件上传props
  const uploadProps: UploadProps = {
    name: "files",
    multiple: true,
    action: `${baseURL}/index/knowledgeBase/file/uploadFiles?kbId=${knowledgeBaseId}&isOverwrite=${true}`,
    beforeUpload: handleBeforeUpload,
    onChange: handleFileChange,
    headers: UPLOAD_HEADERS
  };

  const renderFooter = () => {
    return (
      <Flex
        style={{ width: "100%", gap: "10px" }}
        align="center"
        justify="center"
      >
        <Button
          type="primary"
          ghost
          onClick={() => uploadEvents(UPLOAD_EVENTS.MODAL_ONLY_CLOSE)}
        >
          取消
        </Button>
        <Button
          type="primary"
          onClick={handleTriggerUpload}
          loading={isLoading}
        >
          确定
        </Button>
        <Checkbox
          checked={isParseChecked}
          onChange={(event) => setIsParse(event.target.checked)}
        >
          上传后直接解析
        </Checkbox>
        <Checkbox
          checked={isExtract}
          onChange={(event) => setIsExtract(event.target.checked)}
        >
          上传后直接抽取
        </Checkbox>
      </Flex>
    );
  };

  useEffect(() => {
    if (!props.open) {
      setIsParse(false);
      setIsExtract(false);
    }
  }, [props.open]);

  return (
    <Modal
      open={props.open}
      title="上传文件"
      width={"55vw"}
      destroyOnClose={true}
      cancelText={"取消"}
      okText={"确定"}
      className="nlp-knowledage-base-upload-modal-main"
      footer={renderFooter}
      onCancel={() => uploadEvents(UPLOAD_EVENTS.MODAL_ONLY_CLOSE)}
    >
      <div className="h-[40vh]">
        <div className="px-[30px] h-[80%]">
          <Dragger
            multiple
            style={{ backgroundColor: "#F5F9FF", borderColor: "#014DDF" }}
            customRequest={handleFileDragged}
            onChange={handleFileChange}
            accept=".ppt,.pptx,.pub,.doc,.docx,.xls,.pdf,.xlsx,.csv,.txt"
          >
            <div className="nlp-knowledage-base-upload-icon"></div>
            <p className="ant-upload-text">点击或将文件拖拽到此处上传</p>
            <span style={{ color: "#999", fontSize: "12px", fontWeight: 400 }}>
              支持单次或批量上传，支持 ppt、doc、excel、pdf、text格式。
            </span>
          </Dragger>
        </div>
      </div>
    </Modal>
  );
};

export default UploadModal;

export { UPLOAD_EVENTS };
