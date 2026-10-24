import { Button, ConfigProvider, Form, Input, Modal } from "antd";
import { useForm } from "antd/es/form/Form";
import "../style.less";
import { useEffect, useMemo, useState } from "react";
import AutoTag from "./autoTag";

const CreateModal = ({
  showCreateModal,
  setShowCreateModal,
  type,
  data = {},
  loading,
  cb
}: any) => {
  const [form] = useForm();

  const handleCreate = () => {
    form.validateFields().then((res) => {
      console.log("res", res);
      cb && cb({ ...data, ...res });
    });
  };

  useEffect(() => {
    if (!showCreateModal) {
      form.resetFields();
      return;
    }
  }, [showCreateModal]);

  const modalStyles = {
    header: {
      padding: "20px 24px",
      margin: 0
    },
    body: { padding: "0 24px 0 24px" },
    mask: {},
    footer: { padding: "0 24px 20px 24px", marginTop: "-8px" },
    content: { padding: 0 }
  };

  return (
    <ConfigProvider
      modal={{
        styles: modalStyles
      }}
    >
      <Modal
        title="新建敏感词库"
        open={showCreateModal}
        width={520}
        onCancel={() => {
          setShowCreateModal(false);
          form.resetFields();
        }}
        footer={
          <div className="flex justify-end">
            <Button
              className="mr-[16px] w-[76px] border-[#EBEBEB]"
              onClick={() => {
                setShowCreateModal(false);
                form.resetFields();
              }}
            >
              取消
            </Button>
            <Button
              type="primary"
              loading={loading}
              className="w-[76px] border-none bg-[linear-gradient(90deg,#0359FF,#BD9CFF)]"
              onClick={handleCreate}
            >
              确认
            </Button>
          </div>
        }
      >
        <Form form={form}>
          <Form.Item label="" name="name" rules={[{ required: true }]}>
            <Input placeholder="请输入" />
          </Form.Item>
        </Form>
      </Modal>
    </ConfigProvider>
  );
};

export default CreateModal;
