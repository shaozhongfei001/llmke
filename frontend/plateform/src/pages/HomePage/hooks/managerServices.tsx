import axios$ from "@root/src/apis";
import { getLocalUserInfo } from "@root/src/apis/index";
import { getUrlPrefix } from "@root/src/core/helps";
interface InfoList {
  pageNo: number;
  pageSize: number;
}

const resInfo = (name: string, res: any) => {
  console.log(`${name}---------->`, res);
};

const getInfoList = async (params: InfoList) => {
  try {
    const res: any = await axios$.get(
      `/auth/roleInfo/list?pageNo=${params.pageNo}&pageSize=${params.pageSize}`
    );
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

// /user/getUserInfo
const getUserInfo = async () => {
  try {
    const res: any = await axios$.get(`/auth/user/getUserInfo`);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const updateUserInfo = async (params: any) => {
  try {
    const res = await axios$.post("/auth/user/updateUserInfo", params);
    resInfo("updateUserInfo", res);
    return res;
  } catch (e) {
    console.log("e", e);
  }
};

const updatePassword = async (params: any) => {
  try {
    const res = await axios$.post("/auth/user/updatePassword", params);
    resInfo("updatePassword", res);
    return res;
  } catch (e) {
    console.log("e", e);
  }
};

const userLogout = async () => {
  try {
    const res = await axios$.post(`${getUrlPrefix()}/auth/user/logout`);
    resInfo("userLogout", res);
    return res;
  } catch (e) {
    console.log("e", e);
  }
};

const updateHeaderPic = async (params: any) => {
  try {
    const res = await axios$.post("/auth/user/updateHeaderPic", params, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    resInfo("userLogout", res);
    return res;
  } catch (e) {
    console.log("e", e);
  }
};

interface RoleByUserId {
  id: string | number;
}

const getByUserId = async (params: RoleByUserId, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `/auth/roleInfo/getByUserId?id=${params.id}`
    );
    const { success, data } = res;
    resInfo("setUserStatus", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

// 获取用户列表
const searchUserList = async (params: InfoList, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `/auth/user/searchUserList?pageNo=${params.pageNo}&pageSize=${params.pageSize}`
    );
    const { success, data } = res;
    cb && cb();
    resInfo("searchUserList", data);
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const setRoles = async (params: any, cb?: () => void) => {
  try {
    const res = await axios$.post("/auth/userRole/setRoles", params);
    cb && cb();
    resInfo("setRoles", res);
    return res;
  } catch (e) {
    cb && cb();
    console.log("e", e);
  }
};

const setUserStatus = async (params: any, cb?: () => void) => {
  try {
    const res = await axios$.post(
      `/auth/user/setUserStatus?status=${params.status}&userIds=${params.userIds}`,
      {}
    );
    cb && cb();
    resInfo("setUserStatus", res);
    return res;
  } catch (e) {
    cb && cb();
    console.log("e", e);
  }
};

const addUserFn = async (params: any, cb?: () => void) => {
  try {
    const res = await axios$.post("/auth/user/addUser", params);
    cb && cb();
    resInfo("addUser", res);
    return res;
  } catch (e) {
    cb && cb();
    console.log("e", e);
  }
};

const editUserFn = async (params: any, cb?: () => void) => {
  try {
    const res = await axios$.post("/auth/user/update", params);
    cb && cb();
    resInfo("editUser", res);
    return res;
  } catch (e) {
    cb && cb();
    console.log("e", e);
  }
};

const deleteUserFn = async (userIds: string, cb?: () => void) => {
  try {
    const res = await axios$.delete(
      `/auth/user/deleteByIds?userIds=${userIds}`
    );
    cb && cb(); // 用于关闭loading
    resInfo("deleteUser", res);
    return res;
  } catch (e) {
    cb && cb();
    console.log("e", e);
  }
};

const getRoleInfo = async (params: RoleByUserId, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `/auth/roleInfo/getRoleInfo?roleId=${params.id}`
    );
    const { success, data } = res;
    resInfo("getRoleInfo", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const updateRole = async (params: any, cb?: () => void) => {
  try {
    const res: any = await axios$.put("/auth/roleInfo/updateRole", params);
    const { success, data } = res;
    resInfo("updateRole", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const getAllMenus = async (params: any, cb?: () => void) => {
  try {
    const res: any = await axios$.get(`/auth/resource/getAllMenus`);
    const { success, data } = res;
    resInfo("getAllMenus", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const getMenusByRole = async (params: any, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `/auth/resource/getMenusByRole?roleId=${params.roleId}`
    );
    const { success, data } = res;
    resInfo("getAllMenus", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const addRoleFn = async (params: any, cb?: () => void) => {
  try {
    const res = await axios$.post("/auth/roleInfo/addRole", params);
    cb && cb();
    resInfo("addRole", res);
    return res;
  } catch (e) {
    cb && cb();
    console.log("e", e);
  }
};

const deleteRole = async (params: any, cb?: () => void) => {
  try {
    const res = await axios$.delete(
      `/auth/roleInfo/deleteRole?roleId=${params.roleId}`
    );
    cb && cb();
    resInfo("deleteRole", res);
    return res;
  } catch (e) {
    cb && cb();
    console.log("e", e);
  }
};

const getGroupDataList = async (params: any, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `/auth/group/list?pageNo=${params.pageNo}&pageSize=${params.pageSize}`
    );
    const { success, data } = res;
    resInfo("getGroupList", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const getGroupUserListFn = async (params: any, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `/auth/group/listGroupUsers?pageNo=${params.pageNo}&pageSize=${params.pageSize}&groupId=${params.groupId}`
    );
    const { success, data } = res;
    resInfo("getGroupUserList", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const updateGroupData = async (params: any, cb?: () => void) => {
  try {
    const res = await axios$.put("/auth/group/update", params);
    cb && cb();
    resInfo("updateGroupData", res);
    return res;
  } catch (e) {
    cb && cb();
    console.log("e", e);
  }
};

const addGroupData = async (params: any, cb?: () => void) => {
  try {
    const res = await axios$.post("/auth/group/add", params);
    cb && cb();
    resInfo("addGroupData", res);
    return res;
  } catch (e) {
    cb && cb();
    console.log("e", e);
  }
};

const deleteGroupData = async (params: any, cb?: () => void) => {
  try {
    const res = await axios$.delete(`/auth/group/delete?id=${params.id}`);
    cb && cb();
    resInfo("deleteGroupData", res);
    return res;
  } catch (e) {
    cb && cb();
    console.log("e", e);
  }
};

const editGroupUsers = async (params: any, cb?: () => void) => {
  try {
    const res = await axios$.post("/auth/group/editGroupUsers", params);
    cb && cb();
    resInfo("editGroupUsers", res);
    return res;
  } catch (e) {
    cb && cb();
    console.log("e", e);
  }
};

const getUserType = async (params?: any, cb?: () => void) => {
  const userInfo: any = getLocalUserInfo();
  try {
    const res: any = await axios$.get(
      `/auth/user/getUserType?userName=${userInfo.userInfo.userName}&userId=${userInfo.userInfo.id}`
    );
    const { success, data } = res;
    resInfo("getRoleInfo", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

export {
  getUserType,
  getInfoList,
  getUserInfo,
  updateUserInfo,
  updatePassword,
  userLogout,
  updateHeaderPic,
  getByUserId,
  searchUserList,
  setRoles,
  setUserStatus,
  addUserFn,
  getRoleInfo,
  updateRole,
  getAllMenus,
  getMenusByRole,
  addRoleFn,
  deleteRole,
  getGroupDataList,
  updateGroupData,
  addGroupData,
  deleteGroupData,
  editGroupUsers,
  getGroupUserListFn,
  editUserFn,
  deleteUserFn
};
