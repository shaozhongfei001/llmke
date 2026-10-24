import React from 'react';
import { Modal, Form, Input, Switch } from 'antd';
import type { FormInstance } from 'antd/es/form';
import { RoleData } from './types';

interface RoleFormProps {
  visible: boolean;
  onCancel: () => void;
  onSubmit: (values: any) => void;
  form: FormInstance;
  type: 'add' | 'edit';
  currentRole: RoleData | null;
}

const RoleForm: React.FC<RoleFormProps> = ({
  visible,
  onCancel,
  onSubmit,
  form,
  type,
  currentRole
}) => {
  return (
    <Modal
      title={type === 'add' ? '新建角色' : '编辑角色'}
      open={visible}
      onCancel={onCancel}
      onOk={() => form.submit()}
      destroyOnClose
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
        onFinish={onSubmit}
        preserve={false}
      >
        <Form.Item
          label="角色名称"
          name="name"
          rules={[{ required: true, message: '请输入角色名称' }]}
        >
          <Input placeholder="请输入角色名称" />
        </Form.Item>

        <Form.Item
          label="角色描述"
          name="description"
        >
          <Input.TextArea
            placeholder="请输入角色描述"
            rows={4}
          />
        </Form.Item>

        {type === 'edit' && (
          <Form.Item
            label="状态"
            name="status"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
};

export default RoleForm;