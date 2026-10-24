import { ExclamationCircleFilled } from "@ant-design/icons";
import { Button, Modal } from "antd";
import "./deleteConfirm.less";
interface IEmpty {
  isShowDeleteModal: boolean;
  closeModal: (isRefresh: boolean) => void;
  confirmModal: () => void;
  cb?: (arg: string) => void;
  content?: string;
  loading: boolean;
  okText?: string;
  cancleText?: string;
}

const DeleteConfirm = (props: IEmpty) => {
  const {
    isShowDeleteModal,
    closeModal,
    content = "确定删除吗?",
    loading,
    confirmModal,
    cancleText,
    okText
  } = props;

  const handlerCancle = () => {
    closeModal(false);
  };

  return (
    <Modal
      className="delete-modal"
      open={isShowDeleteModal}
      width={512}
      onCancel={handlerCancle}
      footer={
        <div className="flex justify-end gap-4">
          <Button
            key="back"
            onClick={handlerCancle}
            className="border-solid border-[1px] border-[#ebebeb]"
          >
            <span className="text-[#555]">{cancleText || "取消"}</span>
          </Button>
          <Button
            key="submit"
            style={{
              background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
              color: "#fff",
              border: "none"
            }}
            loading={loading}
            onClick={confirmModal}
          >
            <span> {okText || "确认"}</span>
          </Button>
        </div>
      }
      closable={false}
    >
      <div className="-mx-1 -my-1">
        <div className="flex mb-3 text-[#2a2a2a]">
          <ExclamationCircleFilled className="text-xl text-[#faad14]" />
          <b className="ml-3  text-base">删除提醒</b>
        </div>
        <div className="pl-8 mb-5">{content}</div>
      </div>
    </Modal>
  );
};

export default DeleteConfirm;
