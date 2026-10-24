import React, { useState, useEffect } from 'react';
import { Modal, Form, Tabs, Checkbox, Button, Card, Space, message, Row, Col, Divider } from 'antd';
import { RoleData, PermissionData, PermissionGroup } from './types';

const { TabPane } = Tabs;
const { Group: CheckboxGroup } = Checkbox;

interface PermissionFormProps {
  visible: boolean;
  onCancel: () => void;
  form: any;
  currentRole: RoleData;
  primaryButtonStyle?: React.CSSProperties;
}

const PermissionForm: React.FC<PermissionFormProps> = ({
  visible,
  onCancel,
  form,
  currentRole,
  primaryButtonStyle
}) => {
  const [activeTab, setActiveTab] = useState('1');
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroup[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  
  // =================== API对接点1: 获取所有权限 ===================
  // TODO: 替换为实际的API请求
  // GET /api/permissions
  // 响应格式: { success: boolean, data: PermissionData[], message: string }
  useEffect(() => {
    if (visible) {
      setLoading(true);
      const fetchPermissions = async () => {
        try {
          // 模拟API请求
          // const response = await api.get('/api/permissions');
          
          // 仅用于演示
          setTimeout(() => {
            const mockPermissionGroups: PermissionGroup[] = [];
            setPermissionGroups(mockPermissionGroups);
            setLoading(false);
          }, 500);
        } catch (error) {
          message.error('获取权限列表失败');
          console.error('获取权限列表失败:', error);
          setLoading(false);
        }
      };

      // =================== API对接点2: 获取角色已有权限 ===================
      // TODO: 替换为实际的API请求
      // GET /api/roles/:id/permissions
      // 响应格式: { success: boolean, data: string[], message: string }
      const fetchRolePermissions = async () => {
        try {
          // 模拟API请求
          // const response = await api.get(`/api/roles/${currentRole.id}/permissions`);
          
          // 仅用于演示
          setTimeout(() => {
            // 根据角色类型模拟不同权限
            let mockPermissions: string[] = [];
            
            
            setSelectedPermissions(mockPermissions);
          }, 500);
        } catch (error) {
          message.error('获取角色权限失败');
          console.error('获取角色权限失败:', error);
        }
      };

      fetchPermissions();
      fetchRolePermissions();
    }
  }, [visible, currentRole]);

  // =================== API对接点3: 保存角色权限 ===================
  // TODO: 替换为实际的API请求
  // PUT /api/roles/:id/permissions
  // 请求参数: { permissionIds: string[] }
  // 响应格式: { success: boolean, message: string }
  const handleSavePermissions = async () => {
    try {
      // 模拟API请求
      // await api.put(`/api/roles/${currentRole.id}/permissions`, { permissionIds: selectedPermissions });
      
      message.success('权限更新成功');
      onCancel();
    } catch (error) {
      message.error('更新权限失败');
      console.error('更新权限失败:', error);
    }
  };

  // 处理全选/全不选的逻辑
  const handleCheckAll = (groupKey: string, checked: boolean) => {
    const group = permissionGroups.find(g => g.key === groupKey);
    if (group) {
      const permissionIds = group.permissions.map(p => p.id);
      if (checked) {
        // 添加当前分组所有权限ID
        setSelectedPermissions(prev => 
          [...new Set([...prev, ...permissionIds])]
        );
      } else {
        // 移除当前分组所有权限ID
        setSelectedPermissions(prev => 
          prev.filter(id => !permissionIds.includes(id))
        );
      }
    }
  };

  // 处理权限选择变更
  const handlePermissionChange = (groupKey: string, checkedValues: string[]) => {
    const group = permissionGroups.find(g => g.key === groupKey);
    if (group) {
      const groupPermissionIds = group.permissions.map(p => p.id);
      
      // 移除当前分组内的所有权限
      const otherPermissions = selectedPermissions.filter(id => 
        !groupPermissionIds.includes(id)
      );
      
      // 添加新选中的权限
      setSelectedPermissions([...otherPermissions, ...checkedValues]);
    }
  };

  // 检查分组是否全部选中
  const isGroupAllSelected = (groupKey: string) => {
    const group = permissionGroups.find(g => g.key === groupKey);
    if (group) {
      return group.permissions.every(p => selectedPermissions.includes(p.id));
    }
    return false;
  };

  // 获取分组已选中的权限列表
  const getGroupSelectedPermissions = (groupKey: string) => {
    const group = permissionGroups.find(g => g.key === groupKey);
    if (group) {
      return group.permissions
        .filter(p => selectedPermissions.includes(p.id))
        .map(p => p.id);
    }
    return [];
  };

  // 根据标签渲染不同模块的权限
  const renderPermissionsByTab = () => {
    let filteredGroups: PermissionGroup[] = [];
    
    switch (activeTab) {
      case '1': // 智能对话
        filteredGroups = permissionGroups.filter(g => g.key === 'ai-chat' || g.key === 'knowledge');
        break;
      case '2': // 文档操作
        filteredGroups = permissionGroups.filter(g => g.key === 'document');
        break;
      case '3': // 系统管理
        filteredGroups = permissionGroups.filter(g => g.key === 'system');
        break;
      default:
        filteredGroups = permissionGroups;
    }
    
    return (
      <>
        {filteredGroups.map(group => (
          <div key={group.key} className="mb-6">
            <Card
              title={
                <div className="flex items-center">
                  <span className="mr-4">{group.title}</span>
                  <Checkbox
                    checked={isGroupAllSelected(group.key)}
                    onChange={(e) => handleCheckAll(group.key, e.target.checked)}
                  >
                    全选
                  </Checkbox>
                </div>
              }
              className="shadow-sm"
              bordered={false}
            >
              <CheckboxGroup
                value={getGroupSelectedPermissions(group.key)}
                onChange={(checkedValues) => handlePermissionChange(group.key, checkedValues as string[])}
              >
                <Row>
                  {group.permissions.map(permission => (
                    <Col span={8} key={permission.id} className="mb-3">
                      <Checkbox value={permission.id}>{permission.name}</Checkbox>
                    </Col>
                  ))}
                </Row>
              </CheckboxGroup>
            </Card>
          </div>
        ))}
      </>
    );
  };

  return (
    <Modal
      title={`设置权限 - ${currentRole?.name}`}
      open={visible}
      onCancel={onCancel}
      width={800}
      footer={null}
      destroyOnClose
      className="rounded-lg permission-modal"
    >
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="智能对话" key="1" />
        <TabPane tab="文档操作" key="2" />
        <TabPane tab="系统管理" key="3" />
      </Tabs>
      
      <div className="py-4">
        {loading ? (
          <div className="flex justify-center items-center h-64">
            <p>正在加载权限数据...</p>
          </div>
        ) : (
          renderPermissionsByTab()
        )}
      </div>
      
      <Divider className="mt-0" />
      
      <div className="flex justify-end">
        <Space>
          <Button onClick={onCancel}>取消</Button>
          <Button 
            type="primary" 
            onClick={handleSavePermissions}
            style={{
              background: "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)",
              borderColor: "transparent"
            }}
          >
            保存
          </Button>
        </Space>
      </div>
    </Modal>
  );
};

export default PermissionForm;