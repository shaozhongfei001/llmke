import { Modal, Form, Input, TreeSelect, message } from 'antd';
import { useState } from 'react';
import { GroupFormData } from '../types';
import systemApi from '@/apis/system';
import { GroupInfoDTO } from '@/apis/system/data-contracts';

interface GroupModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: (group: GroupInfoDTO) => void;
  initialValues?: GroupFormData;
}

export const GroupModal: React.FC<GroupModalProps> = ({
  visible,
  onClose,
  onSuccess,
  initialValues
}) => {
  const [form] = Form.useForm<GroupFormData>();
  const [loading, setLoading] = useState(false);
  const api = systemApi();

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();
      
      const response = await api.addGroup({
        name: values.name,
        description: values.description,
        parentId: values.parentId
      });

      if (response.data) {
        message.success('创建分组成功');
        form.resetFields();
        onSuccess?.(response.data);
        onClose();
      }
    } catch (error) {
      console.error('创建分组失败:', error);
      message.error('创建分组失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="创建分组"
      open={visible}
      onCancel={onClose}
      onOk={handleSubmit}
      confirmLoading={loading}
      okButtonProps={{
        style: {
          background: "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)",
          borderColor: "transparent"
        }
      }}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={initialValues}
      >
        <Form.Item
          name="name"
          label="分组名称"
          rules={[{ required: true, message: '请输入分组名称' }]}
        >
          <Input placeholder="请输入分组名称" />
        </Form.Item>
        <Form.Item
          name="description"
          label="分组描述"
        >
          <Input.TextArea placeholder="请输入分组描述" rows={4} />
        </Form.Item>
  
      </Form>
    </Modal>
  );
}; 