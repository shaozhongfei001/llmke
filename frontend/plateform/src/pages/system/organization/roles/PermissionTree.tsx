import React from 'react';
import { Tree, Empty, Tag } from 'antd';
import { RoleData, PermissionGroup } from './types';

interface PermissionTreeProps {
  /**
   * 当前选中的角色
   */
  currentRole: RoleData | null;
  /**
   * 权限分组数据
   */
  permissionGroups: PermissionGroup[];
  /**
   * 已选中的权限ID列表
   */
  selectedPermissions: string[];
  /**
   * 权限数据是否在加载中
   */
  loading: boolean;
  /**
   * 权限选中状态变化的回调
   * @param permissions 选中的权限ID列表
   */
  onCheck: (permissions: string[]) => void;
}

/**
 * 权限树组件，用于显示和管理角色权限
 */
const PermissionTree: React.FC<PermissionTreeProps> = ({
  currentRole,
  permissionGroups,
  selectedPermissions,
  loading,
  onCheck
}) => {
  if (!currentRole) {
    return <Empty description="请选择一个角色" className="pt-8" />;
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64 text-gray-500">
        <span className="animate-pulse">正在加载权限数据...</span>
      </div>
    );
  }

 



  return (
    <div className="bg-white rounded-lg shadow-sm">
      <div className="h-[calc(100vh-375px)] overflow-y-auto w-full">
        <Tree
          checkable
          treeData={permissionGroups}
          checkedKeys={{ checked: selectedPermissions, halfChecked: [] }}
          onCheck={(checked) => onCheck(checked as string[])}
          titleRender={(nodeData: any) => (
            <div className="flex items-center">
              <span className="text-gray-700 font-normal">{nodeData.name}</span>
              {nodeData.code && (
                <Tag
                  color="geekblue"
                  className="text-xs ml-2 bg-blue-50 border border-blue-100 text-blue-600"
                >
                  {nodeData.code}
                </Tag>
              )}
            </div>
          )}
          fieldNames={{ title: 'name', key: 'key', children: 'children' }}
          className="permission-tree w-full"
          showLine={true}
          switcherIcon={({ expanded }) => (
            <div className="flex items-center justify-center w-5 h-5">
              <span className={`text-gray-400 ${expanded ? 'rotate-90' : 'rotate-0'}`} style={{ display: 'inline-block', transition: 'transform 0.2s ease' }}>▸</span>
            </div>
          )}
          selectable={false}
          blockNode
          defaultExpandAll
        />
      </div>
      
      <style>{`
        .permission-tree {
          padding: 4px;
          min-width: 100%;
          overflow-x: hidden;
        }
        
        /* 基本节点样式 */
        .permission-tree .ant-tree-treenode {
          padding: 4px 0;
          width: 100%;
          display: flex;
          cursor: pointer;
          position: relative;
          align-items: center;
          min-width: 0;
        }
        
        /* 重要：增加子节点的缩进 */
        .permission-tree .ant-tree-indent-unit {
          width: 24px;
          flex-shrink: 0;
        }
        
        /* 确保子节点有足够的缩进 */
        .permission-tree .ant-tree-indent-unit:not(:first-child) {
          padding-left: 6px;
        }
        
        /* 美化连接线 */
        .permission-tree .ant-tree-switcher {
          display: flex;
          align-items: center;
          justify-content: center;
          background: transparent !important;
          z-index: 3;
          flex-shrink: 0;
        }
        
        /* 禁用下拉按钮的hover效果 */
        .permission-tree .ant-tree-switcher:hover {
          background: transparent !important;
        }
        
        /* 确保下拉按钮图标不受hover影响 */
        .permission-tree .ant-tree-switcher span {
          color: #aaaaaa !important;
        }
        
        /* 确保连接线可见 */
        .permission-tree.ant-tree.ant-tree-show-line .ant-tree-indent-unit::before {
          border-right: 1px solid #d9d9d9;
        }
        
        /* 节点内容样式 */
        .permission-tree .ant-tree-node-content-wrapper {
          padding: 0 8px;
          display: flex;
          align-items: center;
          height: 32px;
          width: 100%;
          cursor: pointer;
          min-width: 0;
        }
        
        /* 去除默认hover背景 */
        .permission-tree .ant-tree-node-content-wrapper:hover {
          background: none !important;
        }
        
        /* 添加整行hover效果，但不包括下拉按钮区域 */
        .permission-tree .ant-tree-treenode::before {
          content: "";
          position: absolute;
          left: 29px; /* 向右偏移，避开下拉按钮区域 */
          right: 0;
          top: 0;
          bottom: 0;
          height: 110%;
          background-color: transparent;
          transition: background-color 0.2s;
          z-index: 1;
          border-radius: 4px;
        }
        
        .permission-tree .ant-tree-treenode:hover::before {
          background-color: #f3f4f6;
        }
        
        /* 保证内容在hover背景上方 */
        .permission-tree .ant-tree-checkbox, 
        .permission-tree .ant-tree-node-content-wrapper,
        .permission-tree .ant-tree-title,
        .permission-tree .ant-tree-switcher {
          position: relative;
          z-index: 2;
        }
        
        /* 复选框样式 */
        .permission-tree .ant-tree-checkbox {
          margin-right: 4px;
          flex-shrink: 0;
        }
        
        /* 标题样式 */
        .permission-tree .ant-tree-title {
          display: flex;
          align-items: center;
          padding: 4px 0;
          flex: 1;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        
        /* 滚动条样式 */
        .permission-tree::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }
        
        .permission-tree::-webkit-scrollbar-thumb {
          background: #d1d5db;
          border-radius: 3px;
        }
        
        .permission-tree::-webkit-scrollbar-track {
          background: #f3f4f6;
          border-radius: 3px;
        }
      `}</style>
    </div>
  );
};

export default PermissionTree; 