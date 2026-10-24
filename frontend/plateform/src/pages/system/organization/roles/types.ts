// 角色数据类型
export interface RoleData {
  id: string;
  name: string;
  description?: string;
  status: 0 | 1; // 0-禁用，1-启用
  createdTime?: string;
  updatedTime?: string;
  permissionIds?: string[];
  users?: RoleUserData[];  // 添加用户字段
}

// 权限数据类型
export interface PermissionData {
  id: string;
  key: string;
  name: string;
  code: string;
  type: string; // 权限类型：menu-菜单，button-按钮，api-接口
  parentId: string;
  children?: PermissionData[];
}
// 权限模块分组
export interface PermissionGroup {
  title: string;
  key: string;
  permissions: PermissionData[];
}

// 用户分配数据
export interface RoleUserData {
  id: string;
  username: string;
  realName: string;
  email: string;
  department: string;
  assignedTime?: string;
}

// 角色表单数据
export interface RoleFormData {
  name: string;
  description: string;
  status: 0 | 1;
}

// 权限表单数据
export interface PermissionFormData {
  permissionIds: string[];
}

// 角色列表组件属性
export interface RoleListProps {
  roleList: RoleData[];
  currentRole: RoleData | null;
  loading: boolean;
  searchText: string;
  onSearch: (value: string) => void;
  onSelectRole: (role: RoleData) => void;
  onAddRole: () => void;
  onEditRole: (role: RoleData) => void;
  onDeleteRole: (role: RoleData) => void;
  onStatusChange: (role: RoleData, newStatus: 0 | 1) => void;
}

// 角色信息组件属性
export interface RoleInfoProps {
  currentRole: RoleData;
  onStatusChange: (newStatus: 0 | 1) => void;
} 