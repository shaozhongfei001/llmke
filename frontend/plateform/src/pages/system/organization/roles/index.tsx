import React, { useState, useEffect } from 'react';
import { Card, Button, Table, Tabs, Tag, message, Form, Modal, Input, List, Space, Switch, Empty, Checkbox, Divider, Tree } from 'antd';
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined,
  ExclamationCircleOutlined,

} from '@ant-design/icons';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';
import SystemContainer from '../../SystemContainer';
import { RoleData, RoleUserData, PermissionGroup } from './types';
import RoleForm from './RoleForm';
import PermissionForm from './PermissionForm';
import UserAssignForm from './UserAssignForm';
import RoleList from './RoleList';
import RoleInfo from './RoleInfo';
import PermissionTree from './PermissionTree';
import UserTable from './UserTable';
import { useSystemApi } from '@/apis/system';
import type { MenuResourceDTO } from '@/apis/system/data-contracts';
import { useGlobalStore } from '@/storage/state/zustand';
import axios$ from "@root/src/apis";
const { TabPane } = Tabs;
const { TextArea } = Input;

const defaultResourceIds = ['1025', '1035'];

/**
 * 格式化日期时间
 * @param dateTimeStr 日期时间字符串
 * @returns 格式化后的日期时间
 */
const formatDateTime = (dateTimeStr: string) => {
  if (!dateTimeStr) return '-';
  
  const date = new Date(dateTimeStr);
  const year = date.getFullYear().toString().substr(-2);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  
  return `${year}/${month}/${day} ${hours}:${minutes}`;
};

/**
 * 角色管理页面组件
 */
const RoleManagementPage: React.FC = () => {
  // 角色列表数据
  const [roleList, setRoleList] = useState<RoleData[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [currentRole, setCurrentRole] = useState<RoleData | null>(null);
  const [activeTab, setActiveTab] = useState('1'); // 权限编辑(1)和用户列表(2)切换
  const [roleSearchText, setRoleSearchText] = useState(''); // 角色搜索关键词
  
  // 监听角色搜索
  useEffect(() => {
    fetchRoles();
  }, [roleSearchText]);
  
  // 表单状态
  const [roleForm] = Form.useForm();
  const [showRoleForm, setShowRoleForm] = useState(false);
  const [roleFormType, setRoleFormType] = useState<'add' | 'edit'>('add');
  
  // 权限相关状态
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroup[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [permissionLoading, setPermissionLoading] = useState(false);
  const [showPermissionForm, setShowPermissionForm] = useState(false);
  
  // 用户相关状态
  const [showUserAssignForm, setShowUserAssignForm] = useState(false);
  const [userList, setUserList] = useState<any[]>([]);
  const [userLoading, setUserLoading] = useState(false);
  const [userSearchText, setUserSearchText] = useState('');
  
  // 过滤后的用户列表
  const filteredUserList = userList?.filter(user => {
    if (!user) return false;
    
    const searchText = (userSearchText || '').toLowerCase();
    return (
      user?.userRealname?.toLowerCase()?.includes(searchText) ||
      user?.userEmail?.toLowerCase()?.includes(searchText) ||
      user?.deptName?.toLowerCase()?.includes(searchText)
    );
  }) || [];
  
  // =================== API对接点1: 获取角色列表 ===================
  // TODO: 替换为实际的API请求
  // GET /api/roles
  // 响应格式: { success: boolean, data: RoleData[], message: string }
  const fetchRoles = async () => {
    setLoading(true);
    const api = useSystemApi();
    try {
      const response = await api.getRoleList({
        pageNo: 1,
        pageSize: 1000,
        name: roleSearchText
      });
      
      if (response?.data?.records) {
        const roleList = response.data.records.map(role => ({
          id: role.id,
          name: role.name,
          description: role.description || '',
          status: role.status as 0 | 1,
          createdTime: role.gmtCreate,
          updatedTime: role.gmtModified,
          createBy: role.createBy,
          updateBy: role.updateBy
        }));
        
        setRoleList(roleList);
        
        // 默认选中第一个角色
        if (roleList.length > 0 && !currentRole) {
          setCurrentRole(roleList[0]);
        } else if (currentRole) {
          // 如果当前有选中的角色，使用新列表中的对应角色数据更新
          const updatedRole = roleList.find(role => role.id === currentRole.id);
          if (updatedRole) {
            setCurrentRole(updatedRole);
          }
        }
      }
    } catch (error) {
      message.error('获取角色列表失败');
      console.error('获取角色列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // =================== API对接点2: 获取角色的权限 ===================
  // TODO: 替换为实际的API请求
  // GET /api/roles/:id/permissions
  // 响应格式: { success: boolean, data: { permissionGroups: PermissionGroup[], selectedPermissions: string[] }, message: string }
  useEffect(() => {
    if (currentRole && activeTab === '1') {
      loadRolePermissions();
    }
  }, [currentRole, activeTab]);

  /**
   * 加载角色权限
   */
  const loadRolePermissions = async () => {
    if (!currentRole) return;
    
    setPermissionLoading(true);
    const api = useSystemApi();
    try {
      // 获取所有菜单资源
      const roleMenusResponse = await api.getMenusByRole(currentRole.id);
      
      if (roleMenusResponse?.data) {
        // 打印 Zustand 中的全局菜单数据
        console.log('Zustand 全局菜单数据:', useGlobalStore.getState().globalMenu);
        console.log('当前 API 返回的菜单数据:', roleMenusResponse.data);

        // 将 MenuDTO 转换为 PermissionData
        const convertToPermissionData = (menu: any) => ({
          id: menu.id,
          key: menu.id,
          name: menu.name,
          code: menu.url || '',
          type: menu.resourceType === 1 ? 'menu' : 'button',
          parentId: menu.pid || '0',
          children: menu.subMenuDTOList?.map(convertToPermissionData) || []
        });

        // 转换所有菜单
        const permissions = roleMenusResponse.data.map(convertToPermissionData);

        // // 设置权限组
        setPermissionGroups([...permissions as any]);

        // 获取当前角色的权限列表
        try {
          // const roleMenusResponse = await api.getMenusByRole(currentRole.id);
          if (roleMenusResponse?.data) {
            // 递归收集所有权限ID，只收集有权限的节点
            const collectPermissionIds = (menus: any[]): string[] => {
              const ids = new Set<string>();
              const collect = (menu: any) => {
                // 直接检查 permission 是否为 true
                if (menu.permission === true) {
                  ids.add(menu.id);
                }
                // 继续遍历子节点
                if (menu.subMenuDTOList) {
                  menu.subMenuDTOList.forEach(collect);
                }
              };
              menus.forEach(collect);
              return Array.from(ids);
            };

            // 使用实际的角色权限数据
            const selectedPermissionIds = collectPermissionIds(roleMenusResponse.data);
            console.log('当前角色的权限列表:', selectedPermissionIds,'全部菜单数据:',permissions);
            setSelectedPermissions(selectedPermissionIds);
          }
        } catch (error) {
          console.error('获取角色权限列表失败:', error);
          message.error('获取角色权限列表失败');
        }
      }
    } catch (error) {
      message.error('获取权限数据失败');
      console.error('获取权限数据失败:', error);
    } finally {
      setPermissionLoading(false);
    }
  };

  /**
   * 处理添加角色按钮点击
   */
  const handleAddRole = () => {
    // 如果有当前选中的角色，使用它的权限列表作为默认值
    if (currentRole) {
      roleForm.setFieldsValue({
        resourceIds: selectedPermissions // 使用当前角色的权限列表
      });
    }
    
    setRoleFormType('add');
    setShowRoleForm(true);
    roleForm.resetFields(['name', 'description']); // 只重置名称和描述，保留权限设置
  };

  /**
   * 处理角色选择
   * @param role 选中的角色
   */
  const handleSelectRole = (role: RoleData) => {
    setCurrentRole(role);
  };

  /**
   * 处理编辑角色
   * @param role 要编辑的角色
   */
  const handleEditRole = (role: RoleData) => {
    setCurrentRole(role);
    setRoleFormType('edit');
    
    // 重置表单后再设置值
    roleForm.resetFields();
    roleForm.setFieldsValue({
      name: role.name,
      description: role.description,
      status: role.status === 1
    });
    
    setShowRoleForm(true);
  };

  /**
   * 处理删除角色
   * @param role 要删除的角色
   */
  const handleDeleteRole = (role: RoleData) => {
    Modal.confirm({
      title: '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: `确定要删除角色"${role.name}"吗？此操作不可恢复。`,
      okText: '确认',
      cancelText: '取消',
      okButtonProps: {
        style: {
          background: "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)",
          borderColor: "transparent"
        }
      },
      onOk: async () => {
        const api = useSystemApi();
        try {
          await api.deleteRole({ roleId: role.id });
          message.success('角色删除成功');
          
          // 重新获取角色列表
          const response = await api.getRoleList({
            pageNo: 1,
            pageSize: 1000,
            name: roleSearchText
          });
          
          if (response?.data?.records) {
            const newRoleList = response.data.records.map(role => ({
              id: role.id,
              name: role.name,
              description: role.description || '',
              status: role.status as 0 | 1,
              createdTime: role.gmtCreate,
              updatedTime: role.gmtModified,
              createBy: role.createBy,
              updateBy: role.updateBy
            }));
            
            setRoleList(newRoleList);
            
            // 如果删除的是当前选中的角色，则选择列表中的第一个角色
            if (currentRole && currentRole.id === role.id) {
              setCurrentRole(newRoleList.length > 0 ? newRoleList[0] : null);
            }
          }
        } catch (error) {
          console.error('删除角色失败:', error);
          message.error('删除角色失败');
        }
      }
    });
  };

  /**
   * 处理角色表单提交
   * @param values 表单值
   */
  const handleRoleFormSubmit = async (values: any) => {
    const isAdd = roleFormType === 'add';
    const api = useSystemApi();
    
    try {
      if (isAdd) {
        // 创建角色
        const response = await api.addRole({
          name: values.name,
          description: values.description || '无具体描述',
          resourceIds: defaultResourceIds,
        });
        
        if (response?.data) {
          message.success('角色创建成功');
          
          // 重新获取角色列表并选中新创建的角色
          const listResponse = await api.getRoleList({
            pageNo: 1,
            pageSize: 1000,
            name: roleSearchText
          });
          
          if (listResponse?.data?.records) {
            const newRoleList = listResponse.data.records.map(role => ({
              id: role.id,
              name: role.name,
              description: role.description || '无具体描述',
              status: role.status as 0 | 1,
              createdTime: role.gmtCreate,
              updatedTime: role.gmtModified,
              createBy: role.createBy,
              updateBy: role.updateBy
            }));
            
            setRoleList(newRoleList);
            
            // 找到并选中新创建的角色
            const newRole = newRoleList.find(role => role.name === values.name);
            if (newRole) {
              setCurrentRole(newRole);
            }
          }
          
          setShowRoleForm(false);
        }
      } else if (currentRole) {
        // 更新角色
        const response = await api.updateRole({
          id: currentRole.id,
          name: values.name,
          description: values.description || '无具体描述',
          status: values.status ? 1 : 0,
          resourceIds: selectedPermissions
        });
        
        if (response?.data) {
          message.success('角色更新成功');
          await fetchRoles();
          setShowRoleForm(false);
        }
      }
    } catch (error) {
      console.error(isAdd ? '创建角色失败:' : '更新角色失败:', error);
      message.error(isAdd ? '创建角色失败' : '更新角色失败');
    }
  };

  /**
   * 处理角色搜索
   * @param value 搜索文本
   */
  const handleRoleSearch = (value: string) => {
    setRoleSearchText(value);
  };

  /**
   * 打开用户分配弹窗
   */
  const openUserAssignModal = () => {
    if (!currentRole) {
      message.warning('请先选择一个角色');
      return;
    }
    setShowUserAssignForm(true);
  };

  const handlePermissionChange = async (checkedKeys: string[]) => {
    if (!currentRole) return;
    
    const api = useSystemApi();
    console.log('checkedKeys',checkedKeys);
    try {
      // 更新角色权限
      await api.updateRole({
        id: currentRole.id,
        name: currentRole.name,
        description: currentRole.description,
        status: currentRole.status,
        resourceIds: checkedKeys // 使用新的选中权限列表
      });
      
      // 更新本地状态
      setSelectedPermissions(checkedKeys);
      message.success('权限更新成功');
    } catch (error) {
      message.error('权限更新失败');
    }
  };

  // 加载用户列表
  const loadUserList = async () => {
    if (!currentRole) return;
    
    setUserLoading(true);
    const api = useSystemApi();
    try {
      const response = await api.searchUserByRole(currentRole.id);
      console.log('用户列表数据:', response);
      const users = response?.data?.records || [];
      
      setUserList(users.map((user: any) => ({
        id: user.id,
        userRealname: user.userRealname,
        userEmail: user.userEmail || '-',
        deptName: user.deptName || '-'
      })));
    } catch (error) {
      console.error('获取用户列表失败:', error);
      message.error('获取用户列表失败');
    } finally {
      setUserLoading(false);
    }
  };

  // 处理移除用户
  const handleRemoveUser = async (userId: string) => {
    if (!currentRole) return;
    
    try {
      const api = useSystemApi();
      await api.removeUserRole({
        roleId: currentRole.id,
        userId: userId
      });
      
      message.success('用户移除成功');
      await loadUserList(); // 重新加载用户列表
    } catch (error) {
      console.error('移除用户失败:', error);
      message.error('移除用户失败');
    }
  };

  // 监听角色变化时加载用户列表
  useEffect(() => {
    if (currentRole && activeTab === '2') {
      loadUserList();
    }
  }, [currentRole, activeTab]);

  // 处理用户分配
  const handleAssignUsers = async (userIds: string[]) => {
    if (!currentRole) return;
    try {
      const api = useSystemApi();
      await api.setUserRole({
        roleId: currentRole.id,
        userIds: userIds
      });
      
      message.success('用户分配成功');
      await loadUserList(); // 重新加载用户列表
    } catch (error) {
      console.error('用户分配失败:', error);
      message.error('用户分配失败');
    }
  };

  // 定义 tabs items
  const tabItems = [
    {
      key: "1",
      label: <span className="px-2">权限管理</span>,
      children: (
        <div className="flex flex-col">
          <div className="flex justify-end ">
          </div>
          <div className="bg-white rounded-lg p-6 shadow-sm">
            <div className="flex justify-between">
            </div>
            
            <PermissionTree
              currentRole={currentRole}
              permissionGroups={permissionGroups}
              selectedPermissions={selectedPermissions}
              loading={permissionLoading}
              onCheck={handlePermissionChange}
            />
          </div>
        </div>
      )
    },
    {
      key: "2",
      label: <span className="px-2">用户列表</span>,
      children: (
        <div className="flex flex-col">
          <div className="flex items-center justify-end gap-x-3 mb-4">
            <Input.Search
              className='mt-3'
              placeholder="搜索用户名或邮箱"
              style={{ width: 250 }}
              value={userSearchText}
              onChange={e => setUserSearchText(e.target.value)}
              allowClear
            />
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={openUserAssignModal}
              className="bg-gradient-to-r mt-3 from-indigo-500 to-blue-500 hover:from-indigo-600 hover:to-blue-600 border-none shadow-md"
            >
              添加用户
            </Button>
          </div>
          
          <UserTable
            loading={userLoading}
            dataSource={filteredUserList}
            onRemoveUser={handleRemoveUser}
          />
        </div>
      )
    }
  ];

  return (
    <SystemContainer title="角色管理" description="系统角色及权限管理">
      <div className="flex h-full text-sm">
        {/* 左侧角色列表 */}
        <div className="w-1/4 p-4 bg-white border-solid border-t-0 border-l-0 border-b-0 border-r border-gray-200">
          <RoleList
            roleList={roleList}
            currentRole={currentRole}
            loading={loading}
            searchText={roleSearchText}
            onSearch={handleRoleSearch}
            onSelectRole={handleSelectRole}
            onAddRole={handleAddRole}
            onEditRole={handleEditRole}
            onDeleteRole={handleDeleteRole}
          />
        </div>   
        {/* 右侧内容区域 */}
        <div className="flex-1 p-4 bg-white">
          {!currentRole ? (
            <div className="h-full flex items-center justify-center">
              <Empty description="请从左侧选择一个角色" />
            </div>
          ) : (
            <>
              <RoleInfo currentRole={currentRole} />
              
              <div className="bg-white rounded-lg">
                <Tabs 
                  size="small" 
                  activeKey={activeTab} 
                  onChange={setActiveTab}
                  className="custom-tabs"
                  tabBarStyle={{ marginBottom: 0, borderBottom: '1px solid #f0f0f0' }}
                  items={tabItems}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* 角色表单弹窗 */}
      <RoleForm
        visible={showRoleForm}
        onCancel={() => setShowRoleForm(false)}
        onSubmit={handleRoleFormSubmit}
        form={roleForm}
        type={roleFormType}
        currentRole={currentRole}
      />

      {/* 权限表单弹窗 */}
      {currentRole && (
        <PermissionForm
          visible={showPermissionForm}
          onCancel={() => setShowPermissionForm(false)}
          form={roleForm}
          currentRole={currentRole}
        />
      )}

      {/* 用户分配弹窗 */}
      {currentRole && (
        <UserAssignForm
          visible={showUserAssignForm}
          onCancel={() => setShowUserAssignForm(false)}
          currentRole={currentRole}
          onAssignUsers={handleAssignUsers}
        />
      )}
    </SystemContainer>
  );
};

export default RoleManagementPage;