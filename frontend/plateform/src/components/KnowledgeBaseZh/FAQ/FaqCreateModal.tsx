import { Modal, Form, Input, Button, Select } from "antd";
import { useEffect, useState } from "react";
import "@/assets/styles/knowledgebase.less";
const { TextArea } = Input;
interface IRow {
  id?: number;
  kbName?: string;
  kbDes?: string | null;
  [key: string]: any;
}
interface IEmpty {
  confirmLoading: boolean;
  isShowCreateModal: boolean;
  closeModal: (isRefresh: boolean) => void;
  cb?: (type: string, arg: any) => void;
}

const FaqCreateModal = (props: IEmpty) => {
  const { isShowCreateModal, closeModal, cb, confirmLoading } = props;
  const [createForm] = Form.useForm();

  const handleCreate = async () => {
    createForm.validateFields().then((data: any) => {
      cb && cb("create", data);
    });
  };

  const handlerCancle = () => {
    createForm.resetFields();
    closeModal(false);
  };

  useEffect(() => {
    if (!isShowCreateModal) {
      createForm.resetFields();
    }
  }, [isShowCreateModal]);

  return (
    <Modal
      title="新建内容"
      className="create-modal"
      open={isShowCreateModal}
      width="55vw"
      onCancel={handlerCancle}
      footer={false}
    >
      <div className="create-form">
        <Form form={createForm}>
          <Form.Item label="问题" name="question" rules={[{ required: true }]}>
            <TextArea
              placeholder="请输入"
              rows={4}
              style={{ height: "100px", resize: "none" }}
            />
          </Form.Item>
          <Form.Item label="回答" name="answer" rules={[{ required: true }]}>
            <TextArea
              placeholder="请输入"
              rows={4}
              style={{ height: "100px", resize: "none" }}
            />
          </Form.Item>
        </Form>
      </div>
      <div className="btn-group">
        <Button key="back" onClick={handlerCancle} className="cancle-btn">
          取消
        </Button>
        <Button
          key="submit"
          type="primary"
          loading={confirmLoading}
          onClick={handleCreate}
        >
          确认
        </Button>
      </div>
    </Modal>
  );
};

export default FaqCreateModal;
