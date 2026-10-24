import React from 'react';
import { Button, Input, Empty } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import { RoleData } from './types';

interface RoleListProps {
  /**
   * 角色列表数据
   */
  roleList: RoleData[];
  /**
   * 当前选中的角色
   */
  currentRole: RoleData | null;
  /**
   * 角色列表是否在加载中
   */
  loading: boolean;
  /**
   * 搜索关键词
   */
  searchText: string;
  /**
   * 搜索关键词变化的回调
   * @param value 新的搜索关键词
   */
  onSearch: (value: string) => void;
  /**
   * 选择角色的回调
   * @param role 选中的角色
   */
  onSelectRole: (role: RoleData) => void;
  /**
   * 添加角色的回调
   */
  onAddRole: () => void;
  /**
   * 编辑角色的回调
   * @param role 要编辑的角色
   */
  onEditRole: (role: RoleData) => void;
  /**
   * 删除角色的回调
   * @param role 要删除的角色
   */
  onDeleteRole: (role: RoleData) => void;
}

/**
 * 角色列表组件，用于显示和管理角色列表
 */
const RoleList: React.FC<RoleListProps> = ({
  roleList,
  currentRole,
  loading,
  searchText,
  onSearch,
  onSelectRole,
  onAddRole,
  onEditRole,
  onDeleteRole
}) => {
  // 根据搜索关键词过滤角色列表
  const filteredRoleList = roleList.filter(role => 
    role.name.toLowerCase().includes(searchText.toLowerCase()) || 
    (role.description || '').toLowerCase().includes(searchText.toLowerCase())
  );

  /**
   * 渲染单个角色项
   * @param role 角色数据
   */
  const renderRoleItem = (role: RoleData) => {
    const isSelected = currentRole && currentRole.id === role.id;
    
    return (
      <div 
        className={`flex items-center p-3 cursor-pointer hover:bg-gray-50 ${isSelected ? 'bg-blue-50' : ''}`}
        onClick={() => onSelectRole(role)}
      >
        <div className="w-5 h-5 flex-shrink-0 mr-2">
          <div className={`w-5 h-5 ${role.status === 1 ? 'bg-green-100' : 'bg-red-100'} rounded-sm flex items-center justify-center`}>
            <div className={`w-2 h-2 ${role.status === 1 ? 'bg-green-500' : 'bg-red-500'} rounded-full`}></div>
          </div>
        </div>
        <div className="flex-1">
          {role.name}
        </div>
        {isSelected && (
          <div className="flex space-x-1">
            <Button 
              type="text" 
              size="small"
              icon={<EditOutlined />}
              className="text-gray-500 hover:text-blue-500"
              onClick={(e) => {
                e.stopPropagation();
                onEditRole(role);
              }}
            />
            <Button 
              type="text" 
              size="small" 
              icon={<DeleteOutlined />}
              className="text-gray-500 hover:text-red-500"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteRole(role);
              }}
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="w-full h-full flex flex-col">
      {/* 角色搜索框 */}
      <div className="mb-4">
        <Input
          placeholder="搜索角色"
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={e => onSearch(e.target.value)}
          allowClear
        />
      </div>
      
      <div className="mb-4">
        <Button 
          block
          icon={<PlusOutlined />}
          onClick={onAddRole}
          style={{
            background: "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)",
            borderColor: "transparent",
            color: "#fff"
          }}
          className="flex items-center justify-center rounded-md"
        >
          添加新角色
        </Button>
      </div>
      
      {loading ? (
        <div className="flex justify-center items-center h-32">
          <p>加载中...</p>
        </div>
      ) : (
        <div className="border-t border-gray-100 text-sm text-secondary font-SC flex-1 overflow-auto">
          {filteredRoleList.map(role => (
            <div className='py-[1px] hover:bg-gray-50 transition-colors' key={role.id}>
              <div className={`rounded ${currentRole?.id === role.id ? 'bg-blue-50' : ''}`}>
                {renderRoleItem(role)}
              </div>
            </div>
          ))}
          {filteredRoleList.length === 0 && (
            <div className="p-4 text-center text-gray-500">
              {roleList.length === 0 ? '暂无角色数据' : '没有找到匹配的角色'}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RoleList; 