export interface UpdateRoleReq {
  /** @format int64 */
  id: number;
  name: string;
  description?: string;
  /** @format int32 */
  status: number;
  resourceIds?: number[];
}

export interface UpdateResourceReq {
  /** @format int64 */
  id: number;
  name: string;
  url: string;
  description?: string;
  icon?: string;
  /** @format int64 */
  pid: number;
  /** @format int64 */
  seq: number;
  /** @format int32 */
  resourceType: number;
}

export interface UpdateUserPermissionReq {
  /** @format int64 */
  userId: number;
  /** @format int32 */
  bizType: number;
  /** @format int32 */
  permission: number;
  /** @format int64 */
  targetId: number;
}

export interface UpdateGroupPermissionReq {
  /** @format int64 */
  groupId: number;
  /** @format int64 */
  targetId: number;
  /** @format int32 */
  bizType: number;
  /** @format int32 */
  permission: number;
}

export interface UpdateGroupReq {
  /** @format int64 */
  id: number;
  name?: string;
  description?: string;
}

export interface UserRoleUpdateReq {
  /** @format int64 */
  userId: number;
  roleIds?: number[];
}

export interface UpdateUserInfoReq {
  userRealname?: string;
  userPhone?: string;
  userEmail?: string;
  deptId?: string;
  deptName?: string;
}

export interface RoleInfoDTO {
  createBy?: string;
  /** @format date-time */
  gmtCreate?: string;
  updateBy?: string;
  /** @format date-time */
  gmtModified?: string;
  /** @format int64 */
  id?: number;
  name?: string;
  description?: string;
  /** @format int32 */
  status?: number;
}

export interface UserInfoDTO {
  /** @format int64 */
  id?: number;
  userName?: string;
  userRealname?: string;
  userPhone?: string;
  userEmail?: string;
  url?: string;
  /** @format int32 */
  status?: number;
  token?: string;
  /** @format date-time */
  gmtCreate?: string;
  userPassword?: string;
  deptId?: string;
  deptName?: string;
  roles?: RoleInfoDTO[];
}

export interface UpdatePasswordReq {
  oldPassword: string;
  newPassword: string;
}

export interface SimpleLoginReq {
  userName: string;
  password: string;
}

export interface UserRegistReq {
  userName: string;
  userRealname: string;
  /** @pattern ^((13[0-9])|(14[5-9])|(15([0-3]|[5-9]))|(16[6-7])|(17[1-8])|(18[0-9])|(19[1|3])|(19[5|6])|(19[8|9]))\d{8}$ */
  userIphone: string;
  /** @pattern \w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)* */
  userEmail: string;
  password: string;
  passwordAffirm: string;
  deptId?: string;
  deptName?: string;
}

export interface LoginReq {
  userName: string;
  password: string;
  verifyCode: string;
}

export interface AddUserReq {
  userName: string;
  userRealname: string;
  /** @pattern ^((13[0-9])|(14[5-9])|(15([0-3]|[5-9]))|(16[6-7])|(17[1-8])|(18[0-9])|(19[1|3])|(19[5|6])|(19[8|9]))\d{8}$ */
  userPhone: string;
  /** @pattern \w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)* */
  userEmail: string;
  deptId?: string;
  deptName?: string;
  roleIds: number[];
}

export interface AddRoleReq {
  name: string;
  description?: string;
  resourceIds: number[];
}

export interface AddResourceReq {
  name: string;
  url: string;
  description?: string;
  icon?: string;
  /** @format int64 */
  pid?: number;
  /** @format int64 */
  seq: number;
  /** @format int32 */
  resourceType: number;
}

export interface UserPrivilegeReq {
  /** @format int32 */
  bizType: number;
  /** @format int64 */
  targetId: number;
  userIds: number[];
  /** @format int32 */
  permission: number;
}

export interface GroupPrivilegeReq {
  /** @format int32 */
  bizType: number;
  groupIds: number[];
  /** @format int64 */
  targetId: number;
  /** @format int32 */
  permission: number;
}

export interface EditUserGroupReq {
  /** @format int64 */
  groupId: number;
  userIds: number[];
}

export interface AddGroupReq {
  name: string;
  description?: string;
}

export interface SystemVersionDTO {
  version?: string;
  subVersion?: string;
  detail?: string;
  date?: string;
}

export interface SearchUserReq {
  /** @format int32 */
  status?: number;
  idOrName?: string;
  /** @format int64 */
  pageNo?: number;
  /** @format int64 */
  pageSize?: number;
}

export interface OrderItem {
  column?: string;
  asc?: boolean;
}

export interface PageUserInfoDTO {
  records?: UserInfoDTO[];
  /** @format int64 */
  total?: number;
  /** @format int64 */
  size?: number;
  /** @format int64 */
  current?: number;
  orders?: OrderItem[];
  optimizeCountSql?: PageUserInfoDTO;
  searchCount?: PageUserInfoDTO;
  optimizeJoinOfCountSql?: boolean;
  /** @format int64 */
  maxLimit?: number;
  countId?: string;
  /** @format int64 */
  pages?: number;
}

export interface SearchRoleListReq {
  /** @format int32 */
  status?: number;
  idOrName?: string;
  /** @format int64 */
  pageNo?: number;
  /** @format int64 */
  pageSize?: number;
}

export interface PageRoleInfoDTO {
  records?: RoleInfoDTO[];
  /** @format int64 */
  total?: number;
  /** @format int64 */
  size?: number;
  /** @format int64 */
  current?: number;
  orders?: OrderItem[];
  optimizeCountSql?: PageRoleInfoDTO;
  searchCount?: PageRoleInfoDTO;
  optimizeJoinOfCountSql?: boolean;
  /** @format int64 */
  maxLimit?: number;
  countId?: string;
  /** @format int64 */
  pages?: number;
}

export interface MenuDTO {
  /** @format int64 */
  id?: number;
  name?: string;
  url?: string;
  icon?: string;
  /** @format int64 */
  pid?: number;
  /** @format int32 */
  resourceType?: number;
  permission?: boolean;
  code?: string;
  subMenuDTOList?: MenuDTO[];
}

export interface UserPrivilegeDTO {
  /** @format int64 */
  id?: number;
  /** @format int64 */
  targetId?: number;
  /** @format int64 */
  userId?: number;
  userName?: string;
  /** @format int32 */
  bizType?: number;
  /** @format int32 */
  permission?: number;
}

export interface PrivilegeDTO {
  /** @format int64 */
  targetId?: number;
  /** @format int32 */
  bizType?: number;
  /** @format int32 */
  permission?: number;
}

export interface GroupPrivilegeDTO {
  /** @format int64 */
  id?: number;
  groupName?: string;
  /** @format int64 */
  targetId?: number;
  /** @format int64 */
  groupId?: number;
  /** @format int32 */
  bizType?: number;
  /** @format int32 */
  permission?: number;
  /** @format int64 */
  userCount?: number;
}

export interface SearchGroupReq {
  name?: string;
  /** @format int64 */
  pageNo?: number;
  /** @format int64 */
  pageSize?: number;
}

export interface GroupDTO {
  /** @format int64 */
  id?: number;
  /** @format int64 */
  pid?: number;
  name?: string;
  description?: string;
  /** @format date-time */
  gmtCreate?: string;
  /** @format date-time */
  gmtModified?: string;
  createBy?: string;
  updateBy?: string;
  /** @format int64 */
  userCount?: number;
}

export interface PageGroupDTO {
  records?: GroupDTO[];
  /** @format int64 */
  total?: number;
  /** @format int64 */
  size?: number;
  /** @format int64 */
  current?: number;
  orders?: OrderItem[];
  optimizeCountSql?: PageGroupDTO;
  searchCount?: PageGroupDTO;
  optimizeJoinOfCountSql?: boolean;
  /** @format int64 */
  maxLimit?: number;
  countId?: string;
  /** @format int64 */
  pages?: number;
}

export interface GroupUserReq {
  /** @format int64 */
  groupId?: number;
  /** @format int64 */
  pageNo?: number;
  /** @format int64 */
  pageSize?: number;
}
