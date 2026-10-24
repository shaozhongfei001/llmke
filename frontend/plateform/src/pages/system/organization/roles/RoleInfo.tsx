import React from 'react';
import { Tag, Empty } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { RoleData } from './types';

interface RoleInfoProps {
  /**
   * 当前选中的角色
   */
  currentRole: RoleData | null;
}
/**
 * 角色基本信息组件，显示角色的名称、状态和描述
 */
const RoleInfo: React.FC<RoleInfoProps> = ({ currentRole }) => {
  if (!currentRole) {
    return <Empty description="请选择一个角色" />;
  }
  
  return (
    <div className="p-5 bg-white rounded-lg mb-4 shadow-sm border border-gray-100">
      <div className="grid grid-cols-2 gap-5">
        <div className="flex items-center">
          <div className="w-24 text-gray-500">角色名称</div>
          <div className="font-medium text-gray-800">{currentRole.name}</div>
        </div>
        <div className="flex items-center">
          <div className="w-24 text-gray-500">角色状态</div>
          {currentRole.status === 1 ? (
            <Tag icon={<CheckCircleOutlined />} color="success" className="flex items-center px-2 rounded-md border-0">启用</Tag>
          ) : (
            <Tag icon={<CloseCircleOutlined />} color="error" className="flex items-center px-2 rounded-md border-0">禁用</Tag>
          )}
        </div>
        <div className="col-span-2 flex">
          <div className="w-24 text-gray-500">角色描述</div>
          <div className="text-gray-700 flex-1">{currentRole.description}</div>
        </div>
      </div>
    </div>
  );
};

export default RoleInfo; 