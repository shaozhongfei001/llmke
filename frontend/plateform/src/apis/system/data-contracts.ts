export interface ModelInfoDTO {
  /** 模型ID */
  id: string;
  /** 模型名称 */
  name: string;
  /** 模型描述 */
  description?: string;
  /** 模型类型 */
  type: string;
  /** 模型状态 */
  status: number;
  /** 是否共享 */
  isShared: boolean;
  /** 创建时间 */
  createTime: string;
  /** 更新时间 */
  updateTime: string;
}

export interface DepartmentDTO {
  pid: string;
}

export interface UserExportDTO {
  deptIds: string;
}

export interface SetUserStatusDTO {
  status: number;
  userIds: string;
}

export interface AddUserDTO {
  userName: string;
  userRealname: string;
  userPhone: string;
  userEmail: string;
  deptId: string;
  roleIds: number[];
}

export interface UpdateUserDTO {
  id: string;
  userName: string;
  userRealname: string;
  userPhone: string;
  userEmail: string;
  deptId: string;
  roleIds: number[];
}

export interface PageModelInfoDTO {
  records?: ModelInfoDTO[];
  /** @format int64 */
  total?: number;
  /** @format int64 */
  size?: number;
  /** @format int64 */
  current?: number;
  orders?: OrderItem[];
  /** @format int64 */
  pages?: number;
}

export interface OrderItem {
  column?: string;
  asc?: boolean;
}

export interface CreateModelDTO {
  /** 模型名称 */
  modelName: string;
  /** 模型描述 */
  dec?: string;
  modelIde: string;
  apiKey: string;
  url: string;
  /** 模型类型 */
  type: string;
  /** 是否共享 */
  isShared?: boolean;
}

export interface CreateDepartmentDTO {
  /** 模型名称 */
  name: string;
  code?: string;
  admin?: string;
  parentId: string;
}

export interface EditDepartmentDTO {
  /** 模型名称 */
  id: number;
  name: string;
  code?: string;
  admin?: string;
  parentId: string;
}

export interface ModelTypeDTO {
  code: string;
  name: string;
  description?: string;
}

export interface RoleInfoDTO {
  /** 角色ID */
  id: string;
  /** 角色名称 */
  name: string;
  /** 角色描述 */
  description?: string;
  /** 角色状态 */
  status: number;
  /** 创建时间 */
  gmtCreate: string;
  /** 更新时间 */
  gmtModified: string;
  /** 创建人 */
  createBy: string;
  /** 更新人 */
  updateBy: string;
  /** 角色类型 */
  roleType?: string | null;
}

export interface PageRoleInfoDTO {
  records: RoleInfoDTO[];
  total?: number;
  size?: number;
  current?: number;
  pages?: number;
}

export interface CreateRoleDTO {
  /** 角色名称 */
  name: string;
  /** 角色描述 */
  description?: string;
  /** 资源ID列表 */
  resourceIds?: string[];
}

export interface SetPermissionUserDTO {
  bizType: number;
  userIds: number[];
  targetId: string[];
  permission: number | null;
}

export interface SetPermissionGroupDTO {
  bizType: number;
  groupIds: number[];
  targetId: string[];
  permission: number | null;
}

export interface SetPermissionDeptDTO {
  bizType: number;
  deptIds: number[];
  targetId: string[];
  permission: number | null;
}

export interface SetPermissionDTO {
  bizType: number;
  deptId?: string;
  groupId?: string;
  userId?: string;
  targetId: string[];
  permission: number;
}

export interface UpdateRoleDTO {
  /** 角色ID */
  id: string;
  /** 角色名称 */
  name: string;
  /** 角色描述 */
  description?: string;
  /** 角色状态 */
  status: number;
  /** 资源ID列表 */
  resourceIds?: string[];
}

/** 菜单资源返回类型 */
export interface MenuResourceDTO {
  /** 菜单ID */
  id: string;
  /** 菜单名称 */
  name: string;
  /** 菜单编码 */
  code: string;
  /** 菜单类型 */
  type: string;
  /** 父菜单ID */
  parentId: string;
  /** 子菜单列表 */
  children?: MenuResourceDTO[];
  /** 创建时间 */
  gmtCreate?: string;
  /** 更新时间 */
  gmtModified?: string;
  /** 创建人 */
  createBy?: string;
  /** 更新人 */
  updateBy?: string;
  /** 排序 */
  sort?: number;
  /** 状态 */
  status?: number;
  /** 图标 */
  icon?: string;
  /** 路由路径 */
  path?: string;
  /** 组件路径 */
  component?: string;
  /** 权限标识 */
  permission?: string;
  /** 是否显示 */
  visible?: boolean;
  /** 是否缓存 */
  keepAlive?: boolean;
}

export interface UserInfo {
  id: string;
  userName: string;
  userEmail?: string;
  userRealname?: string;
  userPhone?: string;
  url?: string;
  status: number;
  gmtCreate: string;
  deptId?: string;
  deptName?: string;
  position?: string;
  roles?: {
    id: string;
    name: string;
    description?: string;
    status: number;
  }[];
}

export interface PageResult<T> {
  records: T[];
  total: number;
  size: number;
  current: number;
}

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export interface GroupInfoDTO {
  /** 组ID */
  id: string;
  /** 组名称 */
  name: string;
  /** 组描述 */
  description?: string;
  /** 组状态 */
  status: number;
  /** 创建时间 */
  gmtCreate: string;
  /** 更新时间 */
  gmtModified: string;
  /** 创建人 */
  createBy: string;
  /** 更新人 */
  updateBy: string;
  /** 父组ID */
  parentId?: string;
  /** 子组列表 */
  children?: GroupInfoDTO[];
}

export interface CreateGroupDTO {
  /** 组名称 */
  name: string;
  /** 组描述 */
  description?: string;
  /** 父组ID */
  parentId?: string;
}

export interface UpdateGroupDTO {
  /** 组ID */
  id: string;
  /** 组名称 */
  name: string;
  /** 组描述 */
  description?: string;
  /** 组状态 */
  status: number;
  /** 父组ID */
  parentId?: string;
}

export interface EditGroupUsersDTO {
  /** 组ID */
  groupId: string;
  /** 用户ID列表 */
  userIds: string[];
}

export interface EditGroupDepartmentsDTO {
  /** 组ID */
  groupId: string;
  /** 部门ID列表 */
  deptIds: string[];
}

export interface EditGroupDepartmentsRequestDTO {
  /** 编辑组部门请求列表 */
  data: EditGroupDepartmentsDTO[];
}

export interface GroupUserDTO {
  /** 用户ID */
  id: string;
  /** 用户名 */
  userName: string;
  /** 真实姓名 */
  realName?: string;
  /** 邮箱 */
  email?: string;
  /** 手机号 */
  phone?: string;
  /** 状态 */
  status: number;
  /** 创建时间 */
  gmtCreate: string;
  /** 部门ID */
  deptId?: string;
  /** 部门名称 */
  deptName?: string;
}

export interface GroupDepartmentDTO {
  /** 部门ID */
  id: string;
  /** 部门名称 */
  name: string;
  /** 部门编码 */
  code: string;
  /** 父部门ID */
  parentId?: string;
  /** 状态 */
  status: number;
  /** 创建时间 */
  gmtCreate: string;
}

export interface FrameElementDTO {
  /** 元素ID */
  id: string;
  /** 元素名称 */
  name: string;
  /** 元素类型 */
  type: string;
  /** 元素编码 */
  code: string;
  /** 父元素ID */
  parentId?: string;
  /** 状态 */
  status: number;
  /** 创建时间 */
  gmtCreate: string;
}

export interface DepartmentTreeDTO {
  /** 部门ID */
  id: string;
  /** 部门名称 */
  name: string;
  /** 部门编码 */
  code: string;
  /** 父部门ID */
  parentId?: string;
  /** 状态 */
  status: number;
  /** 创建时间 */
  gmtCreate: string;
  /** 子部门列表 */
  children?: DepartmentTreeDTO[];
}

export interface UpdateUserInfoDTO {
  /** 用户ID */
  userIds: string[];
  deptId?: string;
  deptName?: string;
  /** 真实姓名 */
  userRealname?: string;
  /** 邮箱 */
  userEmail?: string;
  /** 手机号 */
  userPhone?: string;
}

export interface UpdatePasswordDTO {
  /** 新密码 */
  newPassword: string;
  /** 原密码 */
  oldPassword: string;
}

export interface UpdateHeaderPicDTO {
  /** 用户ID */
  userId: string;
  /** 头像URL */
  url: string;
}

export interface UserOperateRecord {
  /** 记录ID */
  id: string;
  /** 结束时间 */
  endTime: string;
  /** 创建时间 */
  gmtCreated: string;
  /** 修改时间 */
  gmtModified: string;
  /** IP地址 */
  ip: string;
  /** 操作名称 */
  name: string;
  /** 操作参数 */
  params: string;
  /** 开始时间 */
  startTime: string;
  /** 操作状态 */
  success: number;
  /** 请求URL */
  url: string;
  /** 用户ID */
  userId: string;
  /** 用户名 */
  userName: string;
}
