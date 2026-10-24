import { UploadFile, UploadProps, message } from "antd";
import Dragger from "antd/lib/upload/Dragger";
import { baseURL } from "@root/src/apis/common";
import { InboxOutlined } from "@ant-design/icons";
import { useAppPassport } from "@root/src/core/helps";

interface UploadBoxProps {
  name?: string;
  deleteFileById: any;
  id?: number;
  handleSuccessUpload?: (id: number, type?: "del") => void;
}
const UploadBox = (props: UploadBoxProps) => {
  const { getToken } = useAppPassport();
  const { deleteFileById, id, handleSuccessUpload } = props;

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
      const res = file?.response;
      res && deleteFileById.mutateAsync(res?.data[0]?.id);
      handleSuccessUpload && handleSuccessUpload(res?.data[0]?.id, "del");
    }
    if (file.status === "done") {
      const res = file?.response;
      handleSuccessUpload && handleSuccessUpload(res?.data[0]?.id);
    }
  };

  const UPLOAD_HEADERS = {
    Authorization: getToken() || ""
  };

  // 文件上传props
  const uploadProps: UploadProps = {
    name: "files",
    multiple: true,
    action: `${baseURL}/index/knowledgeBase/file/uploadFiles?kbId=${id}&isOverwrite=${true}`,
    beforeUpload: handleBeforeUpload,
    onChange: handleFileChange,
    headers: UPLOAD_HEADERS
  };

  return (
    <div className="h-[40vh] overflow-y-auto">
      <div className="px-[30px]">
        <Dragger {...uploadProps}>
          <InboxOutlined style={{ fontSize: "50px" }} />
          <p className="ant-upload-text">
            点击或将文件拖拽到这里上传，支持文件类型：pdf、doc、docx、txt
          </p>
        </Dragger>
      </div>
    </div>
  );
};
export default UploadBox;
