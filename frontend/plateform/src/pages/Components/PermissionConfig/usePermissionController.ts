import useSystemApi, { SetPermissionDTO } from "@root/src/apis/system";
import { ELEMENT_TYPE } from "@root/src/const/permission";
import { useState } from "react";

export const usePermissionController = ({
  bizType,
  targetId,
  fetchAllPrivilegeList
}: {
  bizType: number;
  targetId: string | number | undefined;
  fetchAllPrivilegeList: () => void;
}) => {
  const api = useSystemApi();
  const [btnLoading, setBtnLoading] = useState(false);

  const setAllPemission = async (
    type: "users" | "groups" | "depts",
    params: SetPermissionDTO | any[]
  ) => {
    const api_permission =
      type === "users"
        ? api.setBatchUserPermission
        : type === "groups"
        ? api.setBatchGroupPermission
        : api.setBatchDeptPermission;
    const res = await api_permission(params as any);
    console.log("setAllPemission", res);
  };

  const setPrivilegePermission = async (data: any, cb: () => void) => {
    const users: SetPermissionDTO | any[] = [],
      groups: SetPermissionDTO | any[] = [],
      depts: SetPermissionDTO | any[] = [];
    console.log("setPrivilegePermission", data);
    data.forEach((item: any) => {
      if (item.elementType === ELEMENT_TYPE.DEPARTMENT) {
        depts.push({
          deptId: item.id.split("_")[0],
          targetId,
          permission: item.permission,
          bizType
        });
      } else if (item.elementType === ELEMENT_TYPE.GROUP) {
        groups.push({
          groupId: item.id.split("_")[0],
          targetId,
          permission: item.permission,
          bizType
        });
      } else {
        users.push({
          userId: item.id.split("_")[0],
          targetId,
          permission: item.permission,
          bizType
        });
      }
    });
    try {
      setBtnLoading(true);
      users.length && (await setAllPemission("users", users));
      groups.length && (await setAllPemission("groups", groups));
      depts.length && (await setAllPemission("depts", depts));
      setBtnLoading(false);
      fetchAllPrivilegeList();
      cb && cb();
    } catch (error) {
      setBtnLoading(false);
    }
  };

  const updatePermission = async (
    type: ELEMENT_TYPE,
    params: any,
    cb?: () => void
  ) => {
    try {
      const api_permission =
        type === ELEMENT_TYPE.DEPARTMENT
          ? api.updateDeptPermission
          : type === ELEMENT_TYPE.GROUP
          ? api.updateGroupPermission
          : api.updateUserPermission;
      const res: any = await api_permission(params);
      if (res.success) {
        cb && cb();
        fetchAllPrivilegeList();
      }
    } catch (error) {
      console.log("error", error);
    }
  };
  return {
    setPrivilegePermission,
    updatePermission,
    setAllPemission,
    btnLoading
  };
};
