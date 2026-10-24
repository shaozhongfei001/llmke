import React, { useEffect, useState } from "react";
import {
  Modal,
  Form,
  Input,
  Button,
  Upload,
  Avatar,
  Space,
  message,
  Spin
} from "antd";
import { UserOutlined, LoadingOutlined, PlusOutlined } from "@ant-design/icons";
import type { UploadChangeParam } from "antd/es/upload";
import type { RcFile, UploadFile } from "antd/es/upload/interface";
import type { FormInstance } from "antd/es/form";
import { UserData, EditProfileFormData } from "./types";
import systemApi from "@/apis/system";

interface EditProfileModalProps {
  visible: boolean;
  onCancel: () => void;
  onSubmit: (values: EditProfileFormData) => void;
  userData: UserData | null;
  form: FormInstance;
  primaryButtonStyle?: React.CSSProperties;
  unitInfo: () => void;
}

const EditProfileModal: React.FC<EditProfileModalProps> = ({
  visible,
  onCancel,
  onSubmit,
  userData,
  form,
  primaryButtonStyle,
  unitInfo
}) => {
  const [loading, setLoading] = useState(false);
  const [imageUrl, setImageUrl] = useState<string>();
  const api = systemApi();

  useEffect(() => {
    if (visible) {
      form.setFieldsValue(userData);
    }
  }, [visible]);

  const handleChange = async ({
    file,
    onProgress,
    onSuccess,
    onError
  }: any) => {
    const userInfo = { ...userData };
    const formData: any = new FormData();
    formData.append("file", file);
    formData.append("userId", userInfo?.id);
    setLoading(true);
    try {
      const res: any = await api.updateHeaderPic(formData);
      setLoading(false);
      if (res.data) {
        unitInfo();
        message.success("头像修改成功！");
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  return (
    <Modal
      title="修改个人信息"
      open={visible}
      onCancel={onCancel}
      footer={null}
      width={600}
      className="rounded-lg"
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={onSubmit}
        initialValues={userData || {}}
      >
        <Form.Item name="url" label="头像">
          <Spin spinning={loading}>
            <Upload
              listType="picture-card"
              maxCount={1}
              showUploadList={false}
              customRequest={handleChange}
            >
              <div className="flex flex-col items-center">
                <Avatar
                  size={55}
                  icon={<UserOutlined />}
                  src={imageUrl || userData?.url}
                  className="mb-2"
                />
                <div className="opacity-50 text-xs">上传</div>
              </div>
            </Upload>
          </Spin>
        </Form.Item>

        <Form.Item
          name="userRealname"
          label="真实姓名"
          rules={[{ required: true, message: "请输入真实姓名" }]}
        >
          <Input />
        </Form.Item>

        <Form.Item
          name="userPhone"
          label="手机号码"
          rules={[{ required: true, message: "请输入手机号码" }]}
        >
          <Input />
        </Form.Item>

        <Form.Item
          name="userEmail"
          label="电子邮箱"
          rules={[
            { required: true, message: "请输入邮箱" },
            { type: "email", message: "请输入有效的邮箱" }
          ]}
        >
          <Input />
        </Form.Item>

        <Form.Item className="mb-0 text-right">
          <Space>
            <Button onClick={onCancel}>取消</Button>
            <Button type="primary" htmlType="submit" style={primaryButtonStyle}>
              保存
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default EditProfileModal;
