import React from 'react';
import { Form, Button, Switch } from 'antd';
import { ModelItem, Collaborator } from './types';

interface AuthModelFormProps {
  model: ModelItem | null;
  collaborators: Collaborator[];
  onSubmit?: (values: any) => void;
  form?: any;
}

const AuthModelForm: React.FC<AuthModelFormProps> = ({ model, collaborators, onSubmit, form: externalForm }) => {
  const [form] = Form.useForm(externalForm);

  const handleFinish = (values: any) => {
    if (onSubmit) {
      onSubmit(values);
    }
  };

  if (!model) {
    return <div className="p-4 text-red-500">无效的模型数据</div>;
  }

  return (
    <Form 
      form={form} 
      onFinish={handleFinish}
      initialValues={{ isVisibleToAll: model.isVisibleToAll }}
      className="w-full pr-1"
    >
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <span className="text-md font-semibold">模型公开范围</span>
        </div>
        <div className="flex justify-between items-center mt-3">
          <span className="text-sm">所有人可访问</span>
          <Form.Item name="isVisibleToAll" valuePropName="checked" noStyle>
            <Switch />
          </Form.Item>
        </div>
      </div>

      <div className="mb-2">
        <div className="flex items-center justify-between">
          <span className="text-sm">协作者</span>
          <Button 
            type="text" 
            size="small"
            className="text-indigo-600 text-xs"
          >
            添加
          </Button>
        </div>
      </div>

      <div className="border-b pb-2 mb-2 flex items-center text-xs text-gray-500">
        <div className="w-1/3">用户</div>
        <div className="w-1/3">角色</div>
        <div className="w-1/3">操作</div>
      </div>

      {collaborators.map(collab => (
        <div key={collab.id} className="flex items-center py-2">
          <div className="w-1/3 flex items-center">
            {collab.id === 'all' ? (
              <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 mr-2">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                </svg>
              </div>
            ) : (
              <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center text-white mr-2">
                {collab.name.charAt(0)}
              </div>
            )}
            <div className="overflow-hidden">
              <div className="truncate">{collab.name}</div>
              {collab.id !== 'all' && <div className="text-xs text-gray-500 truncate">{collab.role}</div>}
            </div>
          </div>
          <div className="w-1/3 text-gray-600">
            {collab.permission}
          </div>
          <div className="w-1/3 flex items-center">
            <Button type="text" size="small" className="text-xs text-blue-600">
              {collab.id === 'all' ? '修改' : '删除'}
            </Button>
          </div>
        </div>
      ))}
    </Form>
  );
};

export default AuthModelForm; 