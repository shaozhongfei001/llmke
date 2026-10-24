import {
  AddGroupReq,
  AddResourceReq,
  AddRoleReq,
  AddUserReq,
  EditUserGroupReq,
  GroupDTO,
  GroupPrivilegeDTO,
  GroupPrivilegeReq,
  GroupUserReq,
  LoginReq,
  MenuDTO,
  PageGroupDTO,
  PageRoleInfoDTO,
  PageUserInfoDTO,
  PrivilegeDTO,
  RoleInfoDTO,
  SearchGroupReq,
  SearchRoleListReq,
  SearchUserReq,
  SimpleLoginReq,
  SystemVersionDTO,
  UpdateGroupPermissionReq,
  UpdateGroupReq,
  UpdatePasswordReq,
  UpdateResourceReq,
  UpdateRoleReq,
  UpdateUserInfoReq,
  UpdateUserPermissionReq,
  UserInfoDTO,
  UserPrivilegeDTO,
  UserPrivilegeReq,
  UserRegistReq,
  UserRoleUpdateReq,
} from "./data-contracts";
import { ContentType, HttpClient, RequestParams } from "./http-client";

export class UserApi<SecurityDataType = unknown> {
  http: HttpClient<SecurityDataType>;

  constructor(http: HttpClient<SecurityDataType>) {
    this.http = http;
  }

  /**
   * No description
   *
   * @tags 角色
   * @name UpdateRole
   * @request PUT:/roleInfo/updateRole
   * @response `200` `boolean` OK
   */
  updateRole = (data: UpdateRoleReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/roleInfo/updateRole`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 资源接口
   * @name UpdateResource
   * @request PUT:/resource/update
   * @response `200` `boolean` OK
   */
  updateResource = (data: UpdateResourceReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/resource/update`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 数据权限
   * @name UpdateUserPermission
   * @summary 修改用户数据权限
   * @request PUT:/privilege/updateUserPermission
   * @response `200` `boolean` OK
   */
  updateUserPermission = (data: UpdateUserPermissionReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/privilege/updateUserPermission`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 数据权限
   * @name UpdateGroupPermission
   * @summary 修改机构组数据权限
   * @request PUT:/privilege/updateGroupPermission
   * @response `200` `boolean` OK
   */
  updateGroupPermission = (data: UpdateGroupPermissionReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/privilege/updateGroupPermission`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 机构组
   * @name UpdateGroup
   * @summary 更新
   * @request PUT:/group/update
   * @response `200` `boolean` OK
   */
  updateGroup = (data: UpdateGroupReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/group/update`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 角色分配
   * @name SetRoles
   * @request POST:/userRole/setRoles
   * @response `200` `boolean` OK
   */
  setRoles = (data: UserRoleUpdateReq[], params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/userRole/setRoles`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 角色分配
   * @name SetRole
   * @request POST:/userRole/setRole
   * @response `200` `boolean` OK
   */
  setRole = (data: UserRoleUpdateReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/userRole/setRole`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name UpdatePersonalInfo
   * @request POST:/user/updateUserInfo
   * @response `200` `UserInfoDTO` OK
   */
  updatePersonalInfo = (data: UpdateUserInfoReq, params: RequestParams = {}) =>
    this.http.request<UserInfoDTO, any>({
      path: `/user/updateUserInfo`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name UpdatePassword
   * @request POST:/user/updatePassword
   * @response `200` `boolean` OK
   */
  updatePassword = (data: UpdatePasswordReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/user/updatePassword`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name UpdateHeaderPicture
   * @request POST:/user/updateHeaderPic
   * @response `200` `Record<string,object>` OK
   */
  updateHeaderPicture = (
    data: {
      /** @format binary */
      file: File;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<Record<string, object>, any>({
      path: `/user/updateHeaderPic`,
      method: "POST",
      body: data,
      type: ContentType.FormData,
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name SimpleLogin
   * @request POST:/user/simpleLogin
   * @response `200` `UserInfoDTO` OK
   */
  simpleLogin = (data: SimpleLoginReq, params: RequestParams = {}) =>
    this.http.request<UserInfoDTO, any>({
      path: `/user/simpleLogin`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name SetUserStatus
   * @request POST:/user/setUserStatus
   * @response `200` `boolean` OK
   */
  setUserStatus = (
    query: {
      userIds: number[];
      /**
       * @format int32
       * @default 1
       */
      status?: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<boolean, any>({
      path: `/user/setUserStatus`,
      method: "POST",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name ResetPassword
   * @request POST:/user/resetPassword
   * @response `200` `boolean` OK
   */
  resetPassword = (data: number[], params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/user/resetPassword`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name Regist
   * @request POST:/user/regist
   * @response `200` `boolean` OK
   */
  regist = (data: UserRegistReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/user/regist`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name Logout
   * @request POST:/user/logout
   * @response `200` `boolean` OK
   */
  logout = (params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/user/logout`,
      method: "POST",
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name Login
   * @request POST:/user/login
   * @response `200` `UserInfoDTO` OK
   */
  login = (data: LoginReq, params: RequestParams = {}) =>
    this.http.request<UserInfoDTO, any>({
      path: `/user/login`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name AddUser
   * @request POST:/user/addUser
   * @response `200` `UserInfoDTO` OK
   */
  addUser = (data: AddUserReq, params: RequestParams = {}) =>
    this.http.request<UserInfoDTO, any>({
      path: `/user/addUser`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 角色
   * @name AddRole
   * @request POST:/roleInfo/addRole
   * @response `200` `boolean` OK
   */
  addRole = (data: AddRoleReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/roleInfo/addRole`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 资源接口
   * @name AddResource
   * @request POST:/resource/add
   * @response `200` `boolean` OK
   */
  addResource = (data: AddResourceReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/resource/add`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 数据权限
   * @name SetUserPermission
   * @summary 设置用户检索配置的数据权限
   * @request POST:/privilege/setUserPermission
   * @response `200` `boolean` OK
   */
  setUserPermission = (data: UserPrivilegeReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/privilege/setUserPermission`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 数据权限
   * @name SetGroupPermission
   * @summary 设置机构组检索配置的数据权限
   * @request POST:/privilege/setGroupPermission
   * @response `200` `boolean` OK
   */
  setGroupPermission = (data: GroupPrivilegeReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/privilege/setGroupPermission`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 机构组
   * @name EditGroupUsers
   * @summary 编辑机构组的用户成员
   * @request POST:/group/editGroupUsers
   * @response `200` `boolean` OK
   */
  editGroupUsers = (data: EditUserGroupReq[], params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/group/editGroupUsers`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 机构组
   * @name AddGroup
   * @summary 新增
   * @request POST:/group/add
   * @response `200` `boolean` OK
   */
  addGroup = (data: AddGroupReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/group/add`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });
  /**
   * No description
   *
   * @tags 系统版本
   * @name GetCurrentVersion
   * @summary 查询当前版本
   * @request GET:/version/getCurrentVersion
   * @response `200` `SystemVersionDTO` OK
   */
  getCurrentVersion = (params: RequestParams = {}) =>
    this.http.request<SystemVersionDTO, any>({
      path: `/version/getCurrentVersion`,
      method: "GET",
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name SearchUserList
   * @request GET:/user/searchUserList
   * @response `200` `PageUserInfoDTO` OK
   */
  searchUserList = (
    query: {
      arg0: SearchUserReq;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<PageUserInfoDTO, any>({
      path: `/user/searchUserList`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name GetKaptchaImage
   * @request GET:/user/kaptcha
   * @response `200` `void` OK
   */
  getKaptchaImage = (params: RequestParams = {}) =>
    this.http.request<void, any>({
      path: `/user/kaptcha`,
      method: "GET",
      ...params,
    });
  /**
   * No description
   *
   * @tags 用户相关接口
   * @name GetUserInfo
   * @request GET:/user/getUserInfo
   * @response `200` `UserInfoDTO` OK
   */
  getUserInfo = (params: RequestParams = {}) =>
    this.http.request<UserInfoDTO, any>({
      path: `/user/getUserInfo`,
      method: "GET",
      ...params,
    });
  /**
   * No description
   *
   * @tags 角色
   * @name List
   * @request GET:/roleInfo/list
   * @response `200` `PageRoleInfoDTO` OK
   */
  list = (
    query: {
      arg0: SearchRoleListReq;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<PageRoleInfoDTO, any>({
      path: `/roleInfo/list`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 角色
   * @name GetRoleInfo
   * @request GET:/roleInfo/getRoleInfo
   * @response `200` `RoleInfoDTO` OK
   */
  getRoleInfo = (
    query: {
      /** @format int64 */
      roleId: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<RoleInfoDTO, any>({
      path: `/roleInfo/getRoleInfo`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 角色
   * @name GetByUserId
   * @request GET:/roleInfo/getByUserId
   * @response `200` `(RoleInfoDTO)[]` OK
   */
  getByUserId = (params: RequestParams = {}) =>
    this.http.request<RoleInfoDTO[], any>({
      path: `/roleInfo/getByUserId`,
      method: "GET",
      ...params,
    });
  /**
   * No description
   *
   * @tags 资源接口
   * @name GetMenusByUser
   * @request GET:/resource/getMenusByUser
   * @response `200` `(MenuDTO)[]` OK
   */
  getMenusByUser = (params: RequestParams = {}) =>
    this.http.request<MenuDTO[], any>({
      path: `/resource/getMenusByUser`,
      method: "GET",
      ...params,
    });
  /**
   * No description
   *
   * @tags 资源接口
   * @name GetMenusByRole
   * @request GET:/resource/getMenusByRole
   * @response `200` `(MenuDTO)[]` OK
   */
  getMenusByRole = (
    query: {
      /** @format int64 */
      roleId: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<MenuDTO[], any>({
      path: `/resource/getMenusByRole`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 资源接口
   * @name GetAllMenus
   * @request GET:/resource/getAllMenus
   * @response `200` `(MenuDTO)[]` OK
   */
  getAllMenus = (params: RequestParams = {}) =>
    this.http.request<MenuDTO[], any>({
      path: `/resource/getAllMenus`,
      method: "GET",
      ...params,
    });
  /**
   * No description
   *
   * @tags 数据权限
   * @name IsPermission
   * @summary 判断数据是否有权限（bizType 1:知识库;2:检索配置）
   * @request GET:/privilege/isPermission
   * @response `200` `boolean` OK
   */
  isPermission = (
    query: {
      /**
       * @format int32
       * @default 1
       */
      bizType?: number;
      /** @format int64 */
      targetId: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<boolean, any>({
      path: `/privilege/isPermission`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 数据权限
   * @name GetUsers
   * @summary 获取数据权限下的用户
   * @request GET:/privilege/getUsers
   * @response `200` `(UserPrivilegeDTO)[]` OK
   */
  getUsers = (
    query: {
      /**
       * @format int32
       * @default 1
       */
      bizType?: number;
      /** @format int64 */
      targetId: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<UserPrivilegeDTO[], any>({
      path: `/privilege/getUsers`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 数据权限
   * @name GetPermission
   * @summary 获取权限数据（bizType 1:知识库;2:检索配置）
   * @request GET:/privilege/getPermission
   * @response `200` `Record<string,PrivilegeDTO>` OK
   */
  getPermission = (
    query?: {
      /**
       * @format int32
       * @default 1
       */
      bizType?: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<Record<string, PrivilegeDTO>, any>({
      path: `/privilege/getPermission`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 数据权限
   * @name GetGroup
   * @summary 获取数据权限下的分组
   * @request GET:/privilege/getGroups
   * @response `200` `(GroupPrivilegeDTO)[]` OK
   */
  getGroup = (
    query: {
      /**
       * @format int32
       * @default 1
       */
      bizType?: number;
      /** @format int64 */
      targetId: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<GroupPrivilegeDTO[], any>({
      path: `/privilege/getGroups`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 机构组
   * @name List1
   * @summary 机构组列表
   * @request GET:/group/list
   * @response `200` `PageGroupDTO` OK
   */
  list1 = (
    query: {
      arg0: SearchGroupReq;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<PageGroupDTO, any>({
      path: `/group/list`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 机构组
   * @name ListGroupUsers
   * @summary 机构组成员列表
   * @request GET:/group/listGroupUsers
   * @response `200` `PageUserInfoDTO` OK
   */
  listGroupUsers = (
    query: {
      arg0: GroupUserReq;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<PageUserInfoDTO, any>({
      path: `/group/listGroupUsers`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 机构组
   * @name GetGroupById
   * @summary 通过id获取详情
   * @request GET:/group/getGroupById
   * @response `200` `GroupDTO` OK
   */
  getGroupById = (
    query: {
      /** @format int64 */
      id: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<GroupDTO, any>({
      path: `/group/getGroupById`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 鉴权相关接口
   * @name Authenticate
   * @request GET:/authenticate
   * @response `200` `boolean` OK
   */
  authenticate = (
    query: {
      userName: string;
      url: string;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<boolean, any>({
      path: `/authenticate`,
      method: "GET",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 角色分配
   * @name RemoveRole
   * @request DELETE:/userRole/removeRole
   * @response `200` `boolean` OK
   */
  removeRole = (
    query: {
      /** @format int64 */
      userId: number;
      roleIds: number[];
    },
    params: RequestParams = {},
  ) =>
    this.http.request<boolean, any>({
      path: `/userRole/removeRole`,
      method: "DELETE",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 角色
   * @name DeleteRole
   * @request DELETE:/roleInfo/deleteRole
   * @response `200` `boolean` OK
   */
  deleteRole = (
    query: {
      /** @format int64 */
      roleId: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<boolean, any>({
      path: `/roleInfo/deleteRole`,
      method: "DELETE",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 资源接口
   * @name DeleteResource
   * @request DELETE:/resource/delete
   * @response `200` `boolean` OK
   */
  deleteResource = (
    query: {
      /** @format int64 */
      resourceId: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<boolean, any>({
      path: `/resource/delete`,
      method: "DELETE",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 数据权限
   * @name DeleteUserPermission
   * @summary 删除用户数据权限
   * @request DELETE:/privilege/deleteUserPermission
   * @response `200` `boolean` OK
   */
  deleteUserPermission = (
    query: {
      /** @format int64 */
      id: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<boolean, any>({
      path: `/privilege/deleteUserPermission`,
      method: "DELETE",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 数据权限
   * @name DeleteGroupPermission
   * @summary 删除机构组数据权限
   * @request DELETE:/privilege/deleteGroupPermission
   * @response `200` `boolean` OK
   */
  deleteGroupPermission = (
    query: {
      /** @format int64 */
      id: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<boolean, any>({
      path: `/privilege/deleteGroupPermission`,
      method: "DELETE",
      query: query,
      ...params,
    });
  /**
   * No description
   *
   * @tags 机构组
   * @name DeleteGroup
   * @summary 通过id删除
   * @request DELETE:/group/delete
   * @response `200` `boolean` OK
   */
  deleteGroup = (
    query: {
      /** @format int64 */
      id: number;
    },
    params: RequestParams = {},
  ) =>
    this.http.request<boolean, any>({
      path: `/group/delete`,
      method: "DELETE",
      query: query,
      ...params,
    });
}
