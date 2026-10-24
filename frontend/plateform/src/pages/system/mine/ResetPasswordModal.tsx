import React from "react";
import { Modal, Form, Input, Button, Space } from "antd";
import { LockOutlined } from "@ant-design/icons";
import { ResetPasswordFormData } from "./types";
import { PASSWORD_REGEX, PASSWORD_WARN_MSG } from "@root/src/core/helps";

interface ResetPasswordModalProps {
  visible: boolean;
  onCancel: () => void;
  onSubmit: (values: ResetPasswordFormData) => void;
  form: any;
  primaryButtonStyle: React.CSSProperties;
}

const ResetPasswordModal: React.FC<ResetPasswordModalProps> = ({
  visible,
  onCancel,
  onSubmit,
  form,
  primaryButtonStyle
}) => {
  return (
    <Modal
      title="重置密码"
      open={visible}
      onCancel={onCancel}
      footer={null}
      width={500}
      className="rounded-lg"
    >
      <Form form={form} layout="vertical" onFinish={onSubmit}>
        <Form.Item
          name="oldPassword"
          label="当前密码"
          rules={[{ required: true, message: "请输入当前密码" }]}
        >
          <Input.Password
            placeholder="请输入当前密码"
            prefix={<LockOutlined />}
          />
        </Form.Item>

        <Form.Item
          name="newPassword"
          validateTrigger={false}
          label="新密码"
          rules={[
            { required: true, message: "请输入新密码" },
            {
              message: PASSWORD_WARN_MSG,
              pattern: PASSWORD_REGEX
            }
          ]}
        >
          <Input.Password
            placeholder={PASSWORD_WARN_MSG}
            prefix={<LockOutlined />}
          />
        </Form.Item>

        <Form.Item
          name="confirmPassword"
          validateTrigger="onBlur"
          label="确认新密码"
          dependencies={["newPassword"]}
          rules={[
            { required: true, message: "请确认新密码" },
            {
              message: PASSWORD_WARN_MSG,
              pattern: PASSWORD_REGEX
            },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue("newPassword") === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error("两次输入的密码不一致"));
              }
            })
          ]}
        >
          <Input.Password
            placeholder={PASSWORD_WARN_MSG}
            prefix={<LockOutlined />}
          />
        </Form.Item>

        <Form.Item className="mb-0 text-right">
          <Space>
            <Button onClick={onCancel}>取消</Button>
            <Button type="primary" htmlType="submit" style={primaryButtonStyle}>
              确认修改
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default ResetPasswordModal;
