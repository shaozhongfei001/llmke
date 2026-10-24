import {
  Modal,
  Form,
  Input,
  Button,
  UploadProps,
  UploadFile,
  Flex,
  ConfigProvider
} from "antd";
import { ReactNode, useEffect, useState } from "react";
import "@/assets/styles/knowledgebase.less";
import { message, Upload } from "antd";
import axios$ from "@root/src/apis";
import { baseURL } from "@root/src/apis/common";
import { UPLOAD_EVENTS } from "@root/src/components/UploadAfterConfirm";
import "./style.less";
const { Dragger } = Upload;
import warningLinear from "../../assets/img/warningLinear.png";
import upload from "../../assets/img/upload.png";
import File from "../../assets/img/File.png";
import { useAppPassport } from "@root/src/core/helps";

interface IEmpty {
  isShowCreateModal: boolean;
  closeModal: (isRefresh: boolean) => void;
  uploadType?: string;
  uploadEvents: (action: string, payload?: any) => void;
  accept?: string;
  children?: ReactNode;
  footerChildren?: ReactNode;
  title?: string | ReactNode;
  url: string;
  multiple?: boolean;
  subTitle?: string;
  fileName?: string;
}

const UploadModal = (props: IEmpty) => {
  const {
    isShowCreateModal,
    closeModal,
    uploadEvents,
    children,
    accept = ".csv,.txt",
    title,
    footerChildren,
    url,
    multiple = true,
    subTitle = "支持单次上传，支持 csv、txt格式。",
    fileName = "file"
  } = props;
  const [createForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const { userInfo }: any = useAppPassport();
  const [fileList, setFileList]: any = useState<UploadFile[]>([]);
  const modalStyles = {
    header: {
      padding: "20px 24px",
      borderBottom: "1px solid #F0F0F0",
      margin: 0
    },
    body: { padding: "16px 24px 20px 24px", borderBottom: "1px solid #F0F0F0" },
    mask: {},
    footer: { padding: "16px 24px", margin: 0 },
    content: { padding: 0, borderRadius: "4px" }
  };
  const successFn = () => {
    closeModal(false);
    setLoading(false);
    createForm.resetFields();
    uploadEvents("uploaded");
  };

  const handlerCancle = () => {
    createForm.resetFields();
    closeModal(false);
  };

  const handleOk = async () => {
    const formData = new FormData();
    fileList.forEach((file: any) => {
      formData.append(fileName, file);
    });

    setLoading(true);

    await axios$
      .put(`${baseURL}${url}`, formData, {
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
    multiple,
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
      if (fileList.length) {
        message.warning("只能上传一个文件");
        return;
      }
      setFileList((fileList: any) => {
        return [...fileList, file];
      });
      return false;
    }
  };

  const renderFooter = () => {
    return (
      <div className="flex justify-end">
        <Button
          className="mr-[16px] w-[76px] border-[#EBEBEB]"
          onClick={handlerCancle}
        >
          取消
        </Button>
        <Button
          type="primary"
          className="w-[76px] border-none bg-[linear-gradient(90deg,#0359FF,#BD9CFF)]"
          onClick={handleOk}
        >
          确认
        </Button>
      </div>
    );
  };

  useEffect(() => {
    if (!isShowCreateModal) {
      setFileList([]);
    }
  }, [isShowCreateModal]);

  return (
    <ConfigProvider
      modal={{
        styles: modalStyles
      }}
    >
      <Modal
        title={title || "上传文件"}
        open={isShowCreateModal}
        footer={renderFooter}
        onCancel={handlerCancle}
        width={650}
      >
        <div className="">
          <div className="h-[44px] bg-[#E6F4FF] flex items-center px-[12px] mb-[10px] rounded-[4px] justify-between">
            <div className="flex items-center">
              <img
                src={warningLinear}
                width={24}
                height={24}
                className="mr-[8px]"
              />
              <div className="text-text-color1">先下载模板后上传</div>
            </div>
            {children}
          </div>
          <Dragger
            {...upLoadProps}
            accept={accept}
            iconRender={() => {
              return <img src={File} width={12} height={12} />;
            }}
            style={{ backgroundColor: "#F9FAFC", borderColor: "#D9D9D9" }}
          >
            <img src={upload} width={48} height={48} />
            <p className="mt-[12px] text-[14px] text-text-color1 mb-[4px]">
              点击或将文件拖拽到此处上传
            </p>
            <span style={{ color: "#999", fontSize: "12px", fontWeight: 400 }}>
              {subTitle}
            </span>
          </Dragger>
        </div>
        <div className="btn-group"></div>
      </Modal>
    </ConfigProvider>
  );
};

export default UploadModal;
