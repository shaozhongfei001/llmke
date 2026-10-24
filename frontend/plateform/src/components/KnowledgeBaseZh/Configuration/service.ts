import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";

const prefix = "/auth";
const prefix2 = `${getUrlPrefix()}/index`;

const updateConf = async (params: any) => {
  try {
    const res: any = await axios$.put(
      `${prefix2}/knowledgeBase/updateConf`,
      params
    );
    resInfo("updateConf", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const getGroupUserList = async (params: any, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/group/listGroupUsers?pageNo=${params.pageNo}&pageSize=${params.pageSize}&groupId=${params.groupId}`
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

const getGroups = async (id: any) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/privilege/getGroups?targetId=${id}`
    );
    resInfo("getGroups", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const getUsers = async (id: any) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/privilege/getUsers?targetId=${id}`
    );
    resInfo("getUsers", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const deleteGroupPermission = async (id: string) => {
  try {
    const res: any = await axios$.delete(
      `${prefix}/privilege/deleteGroupPermission?id=${id}`
    );
    resInfo("deleteGroupPermission", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const deleteUserPermission = async (id: string) => {
  try {
    const res: any = await axios$.delete(
      `${prefix}/privilege/deleteUserPermission?id=${id}`
    );
    resInfo("deleteUserPermissions", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const updateGroupPermission = async (params: any) => {
  try {
    const res: any = await axios$.put(
      `${prefix}/privilege/updateGroupPermission`,
      params
    );
    resInfo("setGroupPermission", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const updateUserPermission = async (params: any) => {
  try {
    const res: any = await axios$.put(
      `${prefix}/privilege/updateUserPermission`,
      params
    );
    resInfo("setGroupPermission", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const setGroupPermission = async (params: any) => {
  try {
    const res: any = await axios$.post(
      `${prefix}/privilege/setGroupPermission`,
      params
    );
    resInfo("setGroupPermission", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const setUserPermission = async (params: any) => {
  try {
    const res: any = await axios$.post(
      `${prefix}/privilege/setUserPermission`,
      params
    );
    resInfo("setGroupPermission", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const getGroupList = async (params: any) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/group/list?pageNo=${params.pageNo}&pageSize=${params.pageSize}`
    );
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const getUserList = async (params: any) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/user/searchUserList?pageNo=${params.pageNo}&pageSize=${params.pageSize}`
    );
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

export {
  getGroups,
  getGroupList,
  getUserList,
  setGroupPermission,
  setUserPermission,
  getUsers,
  getGroupUserList,
  updateGroupPermission,
  updateUserPermission,
  deleteUserPermission,
  deleteGroupPermission,
  updateConf
};

const resInfo = (name: string, res: any) => {
  console.log(`${name}---------->`, res);
};
