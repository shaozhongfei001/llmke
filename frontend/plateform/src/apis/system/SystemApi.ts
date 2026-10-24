import type {
  ModelInfoDTO,
  PageModelInfoDTO,
  CreateModelDTO,
  ModelTypeDTO,
  RoleInfoDTO,
  CreateRoleDTO,
  UpdateRoleDTO,
  PageRoleInfoDTO,
  MenuResourceDTO,
  SetPermissionDTO,
  UserInfo,
  PageResult,
  GroupInfoDTO,
  CreateGroupDTO,
  UpdateGroupDTO,
  EditGroupUsersDTO,
  EditGroupDepartmentsDTO,
  GroupUserDTO,
  GroupDepartmentDTO,
  FrameElementDTO,
  CreateDepartmentDTO,
  EditDepartmentDTO,
  SetPermissionUserDTO,
  UpdateUserInfoDTO,
  UpdatePasswordDTO,
  UpdateHeaderPicDTO,
  EditGroupDepartmentsRequestDTO,
  SetPermissionGroupDTO,
  SetPermissionDeptDTO,
  AddUserDTO,
  UpdateUserDTO,
  SetUserStatusDTO,
  UserExportDTO,
  DepartmentDTO,
  UserOperateRecord
} from "./data-contracts";
import { HttpClient, RequestParams, ApiResponse } from "./http-client";

export class SystemApi<SecurityDataType = unknown> {
  http: HttpClient<SecurityDataType>;

  constructor(http: HttpClient<SecurityDataType>) {
    this.http = http;
  }

  /**
   * 获取所有模型列表（分页）
   * @tags 模型
   * @name GetAllModelList
   * @summary 获取自建和共享模型列表数据
   * @request GET:/modelInfo/allPage
   */
  getAllModelList = (
    query: {
      pageNum: number;
      pageSize: number;
      status?: number;
      type?: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<PageModelInfoDTO, any>({
      path: `index/modelInfo/allPage`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * 获取所有模型列表（分页）
   * @tags 模型
   * @name GetAllModelList
   * @summary 获取自建和共享模型列表数据
   * @request GET:/modelInfo/allPage
   */
  getConfigItemLimit = () =>
    this.http.request<PageModelInfoDTO, any>({
      path: `/qa/search/config/configItemLimit`,
      method: "GET",
      query: {},
      ...{}
    });

  /**
   * 获取我的模型列表（分页）
   * @tags 模型
   * @name GetMyModelList
   * @summary 获取我的模型列表数据
   * @request GET:/modelInfo/page
   */
  getMyModelList = (
    query: {
      pageNum: number;
      pageSize: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<PageModelInfoDTO, any>({
      path: `index/modelInfo/page`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 获取共享模型列表（分页）
   * @tags 模型
   * @name GetSharedModelList
   * @summary 获取共享模型列表数据
   * @request GET:/modelInfo/share/page
   */
  getSharedModelList = (
    query: {
      pageNum: number;
      pageSize: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<PageModelInfoDTO, any>({
      path: `index/modelInfo/share/page`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 获取所有模型列表（不分页）
   * @tags 模型
   * @name GetModelList
   * @summary 获取所有模型列表
   * @request GET:/modelInfo/list
   */
  getModelList = (params: RequestParams = {}) =>
    this.http.request<ModelInfoDTO[], any>({
      path: `index/modelInfo/list`,
      method: "GET",
      ...params
    });

  /**
   * 创建模型
   * @tags 模型
   * @name CreateModel
   * @summary 创建新模型
   * @request POST:/modelInfo/create
   */
  createModel = (data: CreateModelDTO, params: RequestParams = {}) =>
    this.http.request<ModelInfoDTO, any>({
      path: `index/modelInfo/create`,
      method: "POST",
      body: data,
      ...params
    });
  /**
   * 创建模型
   * @tags 模型
   * @name CreateModel
   * @summary 创建新模型
   * @request POST:/modelInfo/create
   */
  updateModel = (data: CreateModelDTO, params: RequestParams = {}) =>
    this.http.request<ModelInfoDTO, any>({
      path: `index/modelInfo/update`,
      method: "PUT",
      body: data,
      ...params
    });

  /**
   * 获取模型类型列表
   * @tags 模型
   * @name GetModelTypes
   * @summary 获取所有可用的模型类型
   * @request GET:/modelInfo/getModelTypes
   */
  getModelTypes = (params: RequestParams = {}) =>
    this.http.request<ModelTypeDTO[], any>({
      path: `index/modelInfo/getModelTypes`,
      method: "GET",
      ...params
    });

  /**
   * 获取模型详情
   * @tags 模型
   * @name GetModelById
   * @summary 根据ID获取模型详情
   * @request GET:/modelInfo/getById
   */
  getModelById = (
    query: {
      id: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<ModelInfoDTO, any>({
      path: `index/modelInfo/getById`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 删除模型
   * @tags 模型
   * @name DeleteModel
   * @summary 删除指定模型
   * @request DELETE:/modelInfo/delete
   */
  deleteModel = (
    query: {
      id: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<void, any>({
      path: `index/modelInfo/delete`,
      method: "DELETE",
      query: query,
      ...params
    });

  /**
   * 获取角色列表
   * @tags 角色管理
   * @name GetRoleList
   * @summary 获取角色列表（分页）
   * @request GET:/roleInfo/list
   */
  getRoleList = (
    query?: {
      /** 当前页码 */
      pageNo?: number;
      /** 每页大小 */
      pageSize?: number;
      /** 角色名称（模糊搜索） */
      name?: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<PageRoleInfoDTO, any>({
      path: `auth/roleInfo/list`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 获取角色详情
   * @tags 角色
   * @name GetRoleInfo
   * @summary 获取角色详细信息
   * @request GET:/roleInfo/getRoleInfo
   */
  getRoleInfo = (
    query: {
      id: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/roleInfo/getRoleInfo`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 获取用户角色
   * @tags 角色
   * @name GetUserRole
   * @summary 获取指定用户的角色信息
   * @request GET:/roleInfo/getByUserId
   */
  getUserRole = (
    query: {
      userId: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/roleInfo/getByUserId`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 创建角色
   * @tags 角色管理
   * @name AddRole
   * @summary 创建新角色
   * @request POST:/roleInfo/addRole
   */
  addRole = (data: CreateRoleDTO, params: RequestParams = {}) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/roleInfo/addRole`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 更新角色
   * @tags 角色管理
   * @name UpdateRole
   * @summary 更新角色信息
   * @request PUT:/roleInfo/updateRole
   */
  updateRole = (data: UpdateRoleDTO, params: RequestParams = {}) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/roleInfo/updateRole`,
      method: "PUT",
      body: data,
      ...params
    });

  /**
   * 删除角色
   * @tags 角色管理
   * @name DeleteRole
   * @summary 删除指定角色
   * @request DELETE:/roleInfo/deleteRole
   */
  deleteRole = (
    query: {
      /** 角色ID */
      roleId: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<void, any>({
      path: `auth/roleInfo/deleteRole`,
      method: "DELETE",
      query: query,
      ...params
    });

  /**
   * 获取所有菜单资源
   * @tags 资源管理
   * @name GetAllMenus
   * @summary 获取所有菜单资源列表
   * @request GET:/resource/getAllMenus
   */
  getAllMenus = (params: RequestParams = {}) =>
    this.http.request<MenuResourceDTO[], any>({
      path: `auth/resource/getAllMenus`,
      method: "GET",
      ...params
    });

  /**
   * 获取用户菜单资源
   * @returns Promise<ApiResponse<MenuResourceDTO[]>>
   */
  getMenusByUser = () =>
    this.http.request<MenuResourceDTO[], any>({
      path: `/auth/resource/getMenusByUser`,
      method: "GET"
    });

  getCollaborators = (
    query: {
      bizType: number;
      targetId: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<PageModelInfoDTO, any>({
      path: `auth/privilege/collaborators`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 获取所有模型列表（分页）
   * @tags 模型
   * @name GetAllPrivilegeList
   * @summary 获取数据权限下所有用人、用户、部门、用户组
   * @request GET:/privilege/getAllList
   */
  getAllPrivilegeList = (
    query: {
      bizType: number;
      targetId: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<PageModelInfoDTO, any>({
      path: `auth/privilege/getAllList`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 获取所有部门和用户
   * @tags 模型
   * @name GetAllPrivilegeList
   * @summary 获取所有用人、用户、部门
   * @request GET:/departmentInfo/treeFrame
   */
  getTreeFrame = (query: {}, params: RequestParams = {}) =>
    this.http.request<PageModelInfoDTO, any>({
      path: `auth/departmentInfo/treeFrame`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 获取角色的菜单资源
   * @tags 资源管理
   * @name GetMenusByRole
   * @summary 获取指定角色的菜单资源列表
   * @request GET:/resource/getMenusByRole
   * @param roleId 角色ID
   */
  getMenusByRole = (roleId: string, params: RequestParams = {}) =>
    this.http.request<MenuResourceDTO[], any>({
      path: `/auth/resource/getMenusByRole`,
      method: "GET",
      query: { roleId },
      ...params
    });

  /**
   * 获取所有用户组
   * @tags 模型
   * @name GetTreeGroup
   * @summary 获取所有用户组
   * @request GET:/departmentInfo/treeGroup
   */
  getTreeGroup = (query: {}, params: RequestParams = {}) =>
    this.http.request<PageModelInfoDTO, any>({
      path: `auth/group/treeGroup`,
      method: "GET",
      query: query,
      ...params
    });

  /*
   * 根据角色ID搜索用户列表
   */
  searchUserByRole = (roleId: string, params: RequestParams = {}) =>
    this.http.request<any>({
      path: `/auth/user/searchUserByRole`,
      method: "GET",
      query: {
        roleId,
        pageSize: 1000, // 设置较大的页面大小
        pageNo: 1
      },
      ...params
    });

  /**
   * @tags 模型
   * @name getTreeFrameById
   * @summary 根据部门id查树形部门+用户列表
   * @request GET:/departmentInfo/treeFrame/ID
   */
  getTreeFrameById = (query: { id: string }, params: RequestParams = {}) =>
    this.http.request<PageModelInfoDTO, any>({
      path: `auth/departmentInfo/treeFrame/${query.id}`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * @tags 模型
   * @name getTreeDeptById
   * @summary 获取所有用人、用户、部门
   * @request GET:/departmentInfo/treeDept/ID
   */
  getTreeDeptById = (query: { id?: string }, params: RequestParams = {}) =>
    this.http.request<PageModelInfoDTO, any>({
      path: `auth/departmentInfo/treeDept${query.id ? `/${query.id}` : ""}`,
      method: "GET",
      query: query,
      ...params
    });

  // 搜索用户列表
  searchUserList = (
    params: {
      pageSize?: number;
      pageNo?: number;
      deptId?: string;
      idOrName?: string;
    } = {}
  ) =>
    this.http.request<PageResult<UserInfo>>({
      path: `auth/user/searchUserList`,
      method: "GET",
      query: params
    });

  /**
   * 设置 用户数据权限
   * @tags 角色
   * @name UpdateRole
   * @summary 更新角色信息
   * @request POST:/roleInfo/updateRole
   */
  setUserPermission = (
    data: SetPermissionUserDTO,
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/privilege/setUserPermission`,
      method: "POST",
      body: data,
      ...params
    });

  setGroupPermission = (
    data: SetPermissionGroupDTO,
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/privilege/setGroupPermission`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 设置 部门数据权限
   * @tags 角色
   * @name UpdateRole
   * @summary 更新角色信息
   * @request POST:/roleInfo/updateRole
   */

  setDeptPermission = (
    data: SetPermissionDeptDTO,
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/privilege/setDeptPermission`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 设置 用户数据权限
   * @tags 角色
   * @name UpdateRole
   * @summary 更新角色信息
   * @request POST:/roleInfo/updateRole
   */
  updateUserPermission = (
    data: SetPermissionUserDTO,
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/privilege/updateUserPermission`,
      method: "PUT",
      body: data,
      ...params
    });

  updateGroupPermission = (
    data: SetPermissionGroupDTO,
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/privilege/updateGroupPermission`,
      method: "PUT",
      body: data,
      ...params
    });

  /**
   * 设置 部门数据权限
   * @tags 角色
   * @name UpdateRole
   * @summary 更新角色信息
   * @request POST:/roleInfo/updateRole
   */

  updateDeptPermission = (
    data: SetPermissionDeptDTO,
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/privilege/updateDeptPermission`,
      method: "PUT",
      body: data,
      ...params
    });

  /**
   * 批量删除组
   * @tags 组管理
   * @name DeleteGroupsByIds
   * @summary 批量删除组
   * @request DELETE:/group/deleteByIds
   */
  deleteDeptPermission = (
    query: {
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<void, any>({
      path: `auth/privilege/deleteDeptPermission`,
      method: "DELETE",
      query: query,
      ...params
    });

  /**
   * 批量删除组
   * @tags 组管理
   * @name DeleteGroupsByIds
   * @summary 批量删除组
   * @request DELETE:/group/deleteByIds
   */
  deleteGroupPermission = (
    query: {
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<void, any>({
      path: `auth/privilege/deleteGroupPermission`,
      method: "DELETE",
      query: query,
      ...params
    });

  /**
   * 批量删除组
   * @tags 组管理
   * @name DeleteGroupsByIds
   * @summary 批量删除组
   * @request DELETE:/group/deleteByIds
   */
  deleteUserPermission = (
    query: {
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<void, any>({
      path: `auth/privilege/deleteUserPermission`,
      method: "DELETE",
      query: query,
      ...params
    });

  /**
   * 设置 用户数据权限
   * @tags 角色
   * @name UpdateRole
   * @summary 更新角色信息
   * @request POST:/roleInfo/updateRole
   */
  setBatchUserPermission = (
    data: SetPermissionDTO,
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/privilege/setBatchUserPermission`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 设置 机构组数据权限
   * @tags 角色
   * @name UpdateRole
   * @summary 更新角色信息
   * @request POST:/roleInfo/updateRole
   */

  setBatchGroupPermission = (
    data: SetPermissionDTO,
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/privilege/setBatchGroupPermission`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 设置 部门数据权限
   * @tags 角色
   * @name UpdateRole
   * @summary 更新角色信息
   * @request POST:/roleInfo/updateRole
   */

  setBatchDeptPermission = (
    data: SetPermissionDTO,
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/privilege/setBatchDeptPermission`,
      method: "POST",
      body: data,
      ...params
    });
  /** 移除用户角色
   * @param params 请求参数
   * @returns 响应结果
   */
  removeUserRole = (params: { roleId: string; userId: string }) =>
    this.http.request<any, any>({
      path: `auth/userRole/removeRole`,
      method: "DELETE",
      query: {
        userId: params.userId,
        roleIds: params.roleId.toString()
      }
    });

  // 搜索用户列表
  frameSearch = (query: { fuzzy: string }) =>
    this.http.request<PageResult<UserInfo>>({
      path: `auth/departmentInfo/frameSearch`,
      method: "GET",
      query
    });

  /**
   * 为用户设置角色
   * @param params 请求参数
   * @returns 响应结果
   */
  setUserRole = (params: { roleId: string; userIds: string[] }) =>
    this.http.request<ApiResponse<void>, any>({
      path: `auth/userRole/setUserRole`,
      method: "POST",
      body: params
    });

  /**
   * 为用户设置角色
   * @param params 请求参数
   * @returns 响应结果
   */
  setUserRoles = (params: { userId: string; roleIds: string[] }) =>
    this.http.request<ApiResponse<void>, any>({
      path: `auth/userRole/setRoles`,
      method: "POST",
      body: {
        userId: params.userId,
        roleIds: params.roleIds.join(",")
      }
    });

  /**
   * 更新组信息
   * @tags 组管理
   * @name UpdateGroup
   * @summary 更新组信息
   * @request PUT:/group/update
   */
  updateGroup = (data: UpdateGroupDTO, params: RequestParams = {}) =>
    this.http.request<GroupInfoDTO, any>({
      path: `auth/group/update`,
      method: "PUT",
      body: data,
      ...params
    });

  /**
   * 编辑组用户
   * @tags 组管理
   * @name EditGroupUsers
   * @summary 编辑组的用户列表
   * @request POST:/group/editGroupUsers
   */
  editGroupUsers = (data: EditUserGroupReq[], params: RequestParams = {}) =>
    this.http.request<void, any>({
      path: `auth/group/editGroupUsers`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 编辑群组部门
   * @tags 群组管理
   * @name EditGroupDepartments
   * @summary 编辑群组部门列表
   * @request POST:/group/editGroupDepartments
   */
  editGroupDepartments = (
    data: EditGroupDepartmentsDTO[],
    params: RequestParams = {}
  ) =>
    this.http.request<ApiResponse<void>, any>({
      path: `auth/group/editGroupDepartments`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 创建组
   * @tags 组管理
   * @name AddGroup
   * @summary 创建新组
   * @request POST:/group/add
   */
  addGroup = (data: CreateGroupDTO, params: RequestParams = {}) =>
    this.http.request<GroupInfoDTO, any>({
      path: `auth/group/add`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 获取组树形结构
   * @tags 组管理
   * @name GetGroupTree
   * @summary 获取组的树形结构
   * @request GET:/group/treeGroup
   */
  getGroupTree = (params: RequestParams = {}) =>
    this.http.request<GroupInfoDTO[], any>({
      path: `auth/group/treeGroup`,
      method: "GET",
      ...params
    });

  /**
   * 获取组列表
   * @tags 组管理
   * @name GetGroupList
   * @summary 获取组列表
   * @request GET:/group/list
   */
  getGroupList = (params: any) =>
    this.http.request<{ records: GroupInfoDTO[] }, any>({
      path: `auth/group/list?pageSize=${params.pageSize || 20}`,
      method: "GET",
      ...params
    });

  /**
   * 获取组用户列表
   * @tags 组管理
   * @name GetGroupUsers
   * @summary 获取组内的用户列表
   * @request GET:/group/listGroupUsers
   */
  getGroupUsers = (
    query: {
      groupId: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<GroupUserDTO[], any>({
      path: `auth/group/listGroupUsers`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 获取框架元素列表
   * @tags 组管理
   * @name GetFrameElements
   * @summary 获取框架元素列表
   * @request GET:/group/listFrameElements
   */
  getFrameElements = (params: RequestParams = {}) =>
    this.http.request<PageResult<FrameElementDTO>, any>({
      path: `auth/group/listFrameElements`,
      method: "GET",
      ...params
    });

  /**
   * 获取组详情
   * @tags 组管理
   * @name GetGroupById
   * @summary 根据ID获取组详情
   * @request GET:/group/getGroupById
   */
  getGroupById = (
    query: {
      id: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<GroupInfoDTO, any>({
      path: `auth/group/getGroupById`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 删除组
   * @tags 组管理
   * @name DeleteGroup
   * @summary 删除指定组
   * @request DELETE:/group/delete
   */
  deleteGroup = (
    query: {
      id: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<void, any>({
      path: `auth/group/delete`,
      method: "DELETE",
      query: query,
      ...params
    });

  /**
   * 批量删除组成员
   * @tags 组管理
   * @name DeleteGroupsByIds
   * @summary 批量删除组成员
   * @request DELETE:/group/deleteByIds
   */
  deleteGroupsByIds = (
    data: {
      groupId: string;
      userIds: string[];
      deptIds: string[];
    },
    params: RequestParams = {}
  ) =>
    this.http.request<void, any>({
      path: `auth/group/deleteByIds`,
      method: "DELETE",
      body: data,
      ...params
    });

  /**
   * 添加部门
   * @tags 模型
   * @name CreateModel
   * @summary 创建新模型
   * @request POST:/modelInfo/create
   */
  createDepartment = (data: CreateDepartmentDTO, params: RequestParams = {}) =>
    this.http.request<ModelInfoDTO, any>({
      path: `auth/departmentInfo/create`,
      method: "POST",
      body: data,
      ...params
    });
  /**
   * 添加部门
   * @tags 模型
   * @name CreateModel
   * @summary 创建新模型
   * @request POST:/modelInfo/create
   */
  editDepartment = (data: EditDepartmentDTO, params: RequestParams = {}) =>
    this.http.request<ModelInfoDTO, any>({
      path: `auth/departmentInfo/edit`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 删除模型
   * @tags 模型
   * @name DeleteModel
   * @summary 删除指定模型
   * @request DELETE:/modelInfo/delete
   */
  deleteDepartment = (
    query: {
      id: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<void, any>({
      path: `auth/departmentInfo/${query.id}`,
      method: "DELETE",
      ...params
    });

  deleteBatchDepartment = (
    query: {
      ids: string[];
    },
    params: RequestParams = {}
  ) =>
    this.http.request<void, any>({
      path: `auth/departmentInfo/recursiveDeleteByIds?ids=${query.ids}`,
      method: "DELETE",
      ...params
    });

  /**
   * 获取部门树形结构
   * @summary 获取所有部门的树形结构
   * @request GET:/departmentInfo/treeDept
   */
  getDepartmentTree = (params: RequestParams = {}) =>
    this.http.request<any>({
      path: `auth/departmentInfo/treeDept`,
      method: "GET",
      ...params
    });

  /**
   * 获取当前用户信息
   * @tags 用户管理
   * @name GetCurrentUserInfo
   * @summary 获取当前登录用户信息
   * @request GET:/user/current
   */
  getCurrentUserInfo = (params: RequestParams = {}) =>
    this.http.request<UserInfo, any>({
      path: `auth/user/getUserInfo`,
      method: "GET",
      ...params
    });

  /**
   * 更新用户信息
   * @tags 用户管理
   * @name UpdateUserInfo
   * @summary 更新当前用户信息
   * @request PUT:/user/update
   */
  updateUserInfo = (data: UpdateUserInfoDTO, params: RequestParams = {}) =>
    this.http.request<ApiResponse<UserInfo>, any>({
      path: `auth/user/updateUserInfo`,
      method: "POST",
      body: data,
      ...params
    });

  updateUserInfoBatch = (data: UpdateUserInfoDTO, params: RequestParams = {}) =>
    this.http.request<ApiResponse<UserInfo>, any>({
      path: `auth/user/updateUserInfoBatch`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 更新用户密码
   * @tags 用户管理
   * @name UpdatePassword
   * @summary 更新当前用户密码
   * @request PUT:/user/password
   */
  updatePassword = (data: UpdatePasswordDTO, params: RequestParams = {}) =>
    this.http.request<ApiResponse<void>, any>({
      path: `auth/user/updatePassword`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 用户登出
   * @tags 用户管理
   * @name UserLogout
   * @summary 用户登出系统
   * @request POST:/user/logout
   */
  userLogout = (params: RequestParams = {}) =>
    this.http.request<ApiResponse<void>, any>({
      path: `auth/user/logout`,
      method: "POST",
      ...params
    });

  /**
   * 更新用户头像
   * @tags 用户管理
   * @name UpdateHeaderPic
   * @summary 更新用户头像
   * @request PUT:/user/avatar
   */
  updateHeaderPic = (data: UpdateHeaderPicDTO, params: RequestParams = {}) =>
    this.http.request<ApiResponse<UserInfo>, any>({
      path: `auth/user/updateHeaderPic`,
      method: "POST",
      body: data,
      ...params
    });

  searchResignedUserList = (
    query: {
      pageNo: number;
      pageSize: number;
      startTime?: string;
      endTime?: string;
      userName?: string;
      userRealname?: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<PageModelInfoDTO, any>({
      path: `auth/user/searchResignedUserList`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 删除用户
   * @tags 模型
   * @name DeleteModel
   * @summary 删除指定模型
   * @request DELETE:/modelInfo/delete
   */
  deleteUsersByIds = (
    query: {
      userIds: any;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<void, any>({
      path: `auth/user/deleteByIds`,
      method: "DELETE",
      query: query,
      ...params
    });

  /**
   * 设置 添加成员
   * @tags 角色
   * @name UpdateRole
   * @summary 更新角色信息
   * @request POST:/roleInfo/updateRole
   */

  addUser = (data: AddUserDTO, params: RequestParams = {}) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/user/addUser`,
      method: "POST",
      body: data,
      ...params
    });

  /**
   * 设置 添加成员
   * @tags 角色
   * @name UpdateRole
   * @summary 更新角色信息
   * @request POST:/roleInfo/updateRole
   */

  updateUser = (data: UpdateUserDTO, params: RequestParams = {}) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/user/update`,
      method: "POST",
      body: data,
      ...params
    });

  //  setUserStatus
  setUserStatus = (data: SetUserStatusDTO, params: RequestParams = {}) => {
    const p = new URLSearchParams(data as any);
    return this.http.request<RoleInfoDTO, any>({
      path: `auth/user/setUserStatus?${p}`,
      method: "POST",
      body: data,
      ...params
    });
  };

  departmentExport = (data: DepartmentDTO, params: RequestParams = {}) => {
    const p = new URLSearchParams(data as any);
    return this.http.request<any>({
      path: `/auth/departmentInfo/export?${p}`,
      method: "GET",
      ...params
    });
  };

  userExport = (data: UserExportDTO, params: RequestParams = {}) => {
    const p = new URLSearchParams(data as any);
    return this.http.request<any>({
      path: `/auth/user/export?${p}`,
      method: "GET",
      ...params
    });
  };

  getTransferType = (params: any) =>
    this.http.request<PageResult<UserInfo>>({
      path: `auth/privilege/transferType`,
      method: "GET",
      query: params
    });

  /**
   * 删除用户
   * @tags 模型
   * @name DeleteModel
   * @summary 删除指定模型
   * @request DELETE:/modelInfo/delete
   */
  clearResignedUsers = (query: {}, params: RequestParams = {}) =>
    this.http.request<void, any>({
      path: `auth/user/clearResignedUsers`,
      method: "DELETE",
      query: query,
      ...params
    });

  transferProperty = (data: UpdateUserDTO, params: RequestParams = {}) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/privilege/transferProperty`,
      method: "POST",
      body: data,
      ...params
    });

  updateUserStatusBatch = (data: any, params: RequestParams = {}) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/user/updateUserStatusBatch`,
      method: "POST",
      body: data,
      ...params
    });

  updateCurrentPermissionByBizType = (
    data: {
      bizType: number;
      targetId: number;
      currentPermission: number;
      targetPermission: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `auth/privilege/updateCurrentPermissionByBizType`,
      method: "POST",
      body: data,
      ...params
    });

  getUserType = (params: { userName: string; userId: string }) =>
    this.http.request<PageResult<UserInfo>>({
      path: `auth/user/getUserType`,
      method: "GET",
      query: params
    });

  /**
   * 获取用户操作记录列表
   * @tags 用户操作记录
   * @name GetUserOperateList
   * @summary 获取用户操作记录列表
   * @request GET:/userOperate
   */
  getUserOperateList = (
    query?: {
      /** 当前页码 */
      pageNo?: number;
      /** 每页大小 */
      pageSize?: number;
      /** 用户名（模糊搜索） */
      username?: string;
      /** 操作类型 */
      operationType?: string;
      /** 开始时间 */
      start?: string;
      /** 结束时间 */
      end?: string;
      /** 状态 */
      status?: number;

      fuzzy?: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<PageResult<UserOperateRecord>, any>({
      path: `auth/userOperate`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * 获取用户操作记录详情
   * @tags 用户操作记录
   * @name GetUserOperateById
   * @summary 获取指定ID的用户操作记录详情
   * @request GET:/userOperate/{id}
   */
  getUserOperateById = (id: string, params: RequestParams = {}) =>
    this.http.request<UserOperateRecord, any>({
      path: `auth/userOperate/${id}`,
      method: "GET",
      ...params
    });

  /**
   * 获取重排模型列表
   * @tags 检索召回
   * @name GetRerankModelInfos
   * @request GET:/ai/getRerankModelInfos
   */
  getRerankModelInfos = (params: RequestParams = {}) =>
    this.http.request<any, any>({
      path: `/qa/ai/getRerankModelInfos`,
      method: "GET",
      ...params
    });
  /**
   * 批量创建特征
   * @tags 批量创建特征
   * @name CreateModel
   * @summary 批量创建特征
   * @request POST:auth/user/batchUpdateUserFeature
   */
  batchUpdateUserFeature = (
    data: { userIds: any[]; feature: string },
    params: RequestParams = {}
  ) =>
    this.http.request<ModelInfoDTO, any>({
      path: `auth/user/batchUpdateUserFeature`,
      method: "POST",
      body: data,
      ...params
    });
}

interface EditUserGroupReq {
  groupId: string;
  userIds: string[];
}
