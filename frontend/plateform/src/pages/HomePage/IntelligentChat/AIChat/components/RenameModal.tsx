import { BorderBottomOutlined } from "@ant-design/icons";
import { Button, ConfigProvider, Form, Input, Modal } from "antd";
import { useForm } from "antd/es/form/Form";
import { useEffect } from "react";

export const RenameModal = ({
  isModalOpen,
  handleOk,
  handleCancel,
  data
}: any) => {
  const modalStyles = {
    header: {
      height: "60px",
      borderBottom: "1px solid #F0F0F0",
      display: "flex",
      paddingLeft: "24px",
      alignItems: "center",
      marginBottom: "16px"
    },
    title: { fontSize: "16px" },
    body: { padding: "0 24px" },
    mask: {},
    footer: { marginTop: "0px", padding: "0 24px 16px 24px" },
    content: { padding: 0 }
  };
  const [rename_form] = useForm();
  useEffect(() => {
    if (!isModalOpen) {
      rename_form.resetFields();
      return;
    }
    rename_form.setFieldValue("new_name", data?.label);
  }, [data, isModalOpen]);
  return (
    <ConfigProvider
      modal={{
        styles: modalStyles
      }}
    >
      <Modal
        title={<div className="text-[16px]">编辑会话名称</div>}
        closeIcon={null}
        open={isModalOpen}
        width={520}
        centered
        className="[&:[.ant-modal-content]]:bg-red"
        footer={
          <div className="mt-[16px] flex justify-end">
            <Button
              children="取消"
              onClick={handleCancel}
              className="mr-[8px]"
            />
            <Button
              children="确认"
              onClick={async () => {
                try {
                  const data = await rename_form.validateFields();
                  handleOk("ok_rename", data);
                } catch (e) {
                  console.log(e);
                  return;
                }
              }}
              type="primary"
              className="border-none"
            />
          </div>
        }
      >
        <Form form={rename_form}>
          <Form.Item
            name="new_name"
            rules={[
              { required: true, message: "请输入" },
              { max: 100, message: "最大字数限制100" }
            ]}
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </ConfigProvider>
  );
};
