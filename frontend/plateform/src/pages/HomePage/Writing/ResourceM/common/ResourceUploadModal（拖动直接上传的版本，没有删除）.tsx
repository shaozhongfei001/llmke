import { Modal, UploadProps, UploadFile } from "antd";
import { useCallback, useState } from "react";
import "@/assets/styles/knowledgebase.less";
import { message, Upload } from "antd";
import upload from "@/assets/writing/upload.png";
import { getTokenLocal } from "@root/src/apis/token";
import { useAppPassport } from "@root/src/core/helps";

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
  cb?: (action: string, data?: any) => void;
}

const ResourceUploadModal = (props: IEmpty) => {
  const { isShowCreateModal, closeModal, cb } = props;
  const { userInfo }: any = useAppPassport();
  const [fileList, setFileList] = useState([]);

  // 单个上传的版本，有进度，会抖动
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
  //   上传文件改变时
  const handleFileChange = async (info: any) => {
    const { file, fileList } = info;
    setFileList(fileList);
    if (file.status === "error") {
      message.error(file?.response?.errorMsg || "上传出错请联系管理员");
    }
    if (file.status === "removed") {
      const res = file?.response;
      res && cb && (await cb("material_delete", res?.data[0]?.id));
      cb && cb("material_refresh");
    }
    if (file.status === "done") {
      const res = file?.response;
      cb && cb("material_refresh");
    }
  };

  const upLoadProps: UploadProps = {
    multiple: true,
    name: "files",
    action: `/cecProxy/dw/articleMaterial`,
    headers: {
      Authorization: getTokenLocal()
    },
    beforeUpload: handleBeforeUpload,
    onChange: handleFileChange
  };

  const handleClose = () => {
    closeModal(false);
    setFileList([]);
  };

  return (
    <Modal
      title="上传素材"
      open={isShowCreateModal}
      width={512}
      destroyOnClose={true}
      onCancel={handleClose}
      className="upload-resources"
      onOk={handleClose}
    >
      <Dragger {...upLoadProps}>
        <p className="ant-upload-drag-icon">
          <img src={upload} alt="rectangle" className="w-[48px] h-[48px]" />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
        <p className="ant-upload-hint">
          支持单次或批量上传，支持 ppt、doc、excel、pdf格式。
        </p>
      </Dragger>
    </Modal>
  );
};

export default ResourceUploadModal;
