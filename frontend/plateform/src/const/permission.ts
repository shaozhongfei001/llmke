export enum USER_STATUS {
  SUPER_ADMIN = 1,
  ADMIN = 2
}

export enum PERMISSION_STATUS {
  NO_PERMISSION = 0,
  READ_ONLY,
  READ_AND_WRITE,
  ALL_PERMISSION
}

export enum BIZETYPE_TYPE {
  KNOWLEDGE_BASE = 1,
  CONFIG = 2,
  MODEL = 3
}

export enum ELEMENT_TYPE {
  DEPARTMENT = 1,
  GROUP = 2,
  USER = 3,
  ALLUSER = -1,
  COLLABORATORS_READONLY = 8,
  COLLABORATORS_ALL_PERMISSION = 9,
  COLLABORATORS_READ_AND_WRITE = 10
}

export enum FILE_BTN {
  DATE = 0,
  VIEW,
  ERROR,
  AUTHORIZE,
  DELETE,
  ANALYSIS_OR_EXTRACT,
  DOWNLOAD,
  EDIT,
  ADD,
  ANALYSIS_CONFIG,
  AUTHORIZE_CONFIG
}

export enum BASE_USER_TYPE {
  READ_ONLY = "可阅读成员",
  EDIT = "可编辑成员",
  MANAGE = "可管理成员"
}

export const PERMISSION_RULES = {
  // 适用于 DATE 和 DELETE 按钮
  [FILE_BTN.DATE]: {
    [PERMISSION_STATUS.NO_PERMISSION]: true,
    [PERMISSION_STATUS.READ_ONLY]: true,
    [PERMISSION_STATUS.READ_AND_WRITE]: false,
    [PERMISSION_STATUS.ALL_PERMISSION]: false
  },
  [FILE_BTN.DELETE]: {
    // 与 DATE 相同规则
    [PERMISSION_STATUS.NO_PERMISSION]: true,
    [PERMISSION_STATUS.READ_ONLY]: true,
    [PERMISSION_STATUS.READ_AND_WRITE]: true,
    [PERMISSION_STATUS.ALL_PERMISSION]: false
  },

  // 适用于 VIEW 和 ERROR 按钮
  [FILE_BTN.VIEW]: {
    [PERMISSION_STATUS.NO_PERMISSION]: true,
    [PERMISSION_STATUS.READ_ONLY]: false,
    [PERMISSION_STATUS.READ_AND_WRITE]: false,
    [PERMISSION_STATUS.ALL_PERMISSION]: false
  },
  [FILE_BTN.ERROR]: {
    // 与 VIEW 相同规则
    [PERMISSION_STATUS.NO_PERMISSION]: true,
    [PERMISSION_STATUS.READ_ONLY]: false,
    [PERMISSION_STATUS.READ_AND_WRITE]: false,
    [PERMISSION_STATUS.ALL_PERMISSION]: false
  },

  // 单独处理的 AUTHORIZE 按钮
  [FILE_BTN.AUTHORIZE]: {
    [PERMISSION_STATUS.NO_PERMISSION]: true,
    [PERMISSION_STATUS.READ_ONLY]: true,
    [PERMISSION_STATUS.READ_AND_WRITE]: true,
    [PERMISSION_STATUS.ALL_PERMISSION]: false
  },
  [FILE_BTN.ANALYSIS_OR_EXTRACT]: {
    [PERMISSION_STATUS.NO_PERMISSION]: true,
    [PERMISSION_STATUS.READ_ONLY]: true,
    [PERMISSION_STATUS.READ_AND_WRITE]: false,
    [PERMISSION_STATUS.ALL_PERMISSION]: false
  },
  [FILE_BTN.DOWNLOAD]: {
    [PERMISSION_STATUS.NO_PERMISSION]: true,
    [PERMISSION_STATUS.READ_ONLY]: true,
    [PERMISSION_STATUS.READ_AND_WRITE]: false,
    [PERMISSION_STATUS.ALL_PERMISSION]: false
  },
  [FILE_BTN.EDIT]: {
    [PERMISSION_STATUS.NO_PERMISSION]: true,
    [PERMISSION_STATUS.READ_ONLY]: true,
    [PERMISSION_STATUS.READ_AND_WRITE]: false,
    [PERMISSION_STATUS.ALL_PERMISSION]: false
  },
  [FILE_BTN.ADD]: {
    [PERMISSION_STATUS.NO_PERMISSION]: true,
    [PERMISSION_STATUS.READ_ONLY]: true,
    [PERMISSION_STATUS.READ_AND_WRITE]: false,
    [PERMISSION_STATUS.ALL_PERMISSION]: false
  },
  [FILE_BTN.ANALYSIS_CONFIG]: {
    [PERMISSION_STATUS.NO_PERMISSION]: true,
    [PERMISSION_STATUS.READ_ONLY]: true,
    [PERMISSION_STATUS.READ_AND_WRITE]: false,
    [PERMISSION_STATUS.ALL_PERMISSION]: false
  },
  [FILE_BTN.AUTHORIZE_CONFIG]: {
    [PERMISSION_STATUS.NO_PERMISSION]: true,
    [PERMISSION_STATUS.READ_ONLY]: true,
    [PERMISSION_STATUS.READ_AND_WRITE]: true,
    [PERMISSION_STATUS.ALL_PERMISSION]: false
  }
};

export const getBtnDisabled = (
  btn: FILE_BTN,
  permission: PERMISSION_STATUS
): boolean => {
  return PERMISSION_RULES[btn]?.[permission] ?? true;
};

export enum BTN_NAME {
  VIEW,
  ADD,
  AUTHORIZE
}

export const getEditPermission = (
  userType: USER_STATUS,
  btnName: BTN_NAME,
  rowUserType?: number | null
) => {
  const isSuperAdmin = userType === USER_STATUS.SUPER_ADMIN;
  const isAdmin = userType === USER_STATUS.ADMIN;

  if (!isSuperAdmin && rowUserType === USER_STATUS.SUPER_ADMIN) return true;
  
  switch (btnName) {
    case BTN_NAME.VIEW:
      return !(isSuperAdmin || isAdmin);
    case BTN_NAME.ADD:
      return !isSuperAdmin;
    default:
      return true;
  }
};

export const PERMISSION_WARNING_MSG = "角色无权限操作";
