import {
  CaretDownOutlined,
  CloseOutlined,
  EllipsisOutlined,
  PlusCircleOutlined,
  PlusOutlined,
  SearchOutlined,
  UserOutlined
} from "@ant-design/icons";
import { Building2 } from "lucide-react";
import {
  Button,
  ConfigProvider,
  Drawer,
  Dropdown,
  Input,
  message,
  Pagination,
  Spin,
  Table,
  Tree,
  TreeDataNode,
  Avatar,
  Tooltip
} from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import "../style.less";
import { uid } from "uid";
import {
  AddOrEditDepartment,
  AddOrEditMembers,
  BatchExport,
  BatchImport,
  ChangeDepartment,
  Resignation
} from "./drawerContent";
import DeleteConfirm from "@root/src/components/DeletModal";
import useSystemApi from "@root/src/apis/system";
import {
  BTN_NAME,
  getEditPermission,
  PERMISSION_WARNING_MSG,
  USER_STATUS
} from "@root/src/const/permission";
import { getUrlPrefix, useAppPassport } from "@root/src/core/helps";
import axios$ from "@root/src/apis";
import TreeListItem from "./components/treeListItem";
import RightIcon from "./components/rightIcon";
import LinkItemsBtn from "./components/listItemsBtn";
import type { ColumnType } from "antd/es/table";
import {
  getAvatarProps,
  getIconProps,
  GRADIENTS
} from "../../config/gradients";
import CustomTooltip from "@root/src/components/CustomTooltip";
import { BatchAddModal } from "./components/BatchAddModal";
import PasswordModal, { MODAL_TYPE } from "@root/src/components/PasswordModal";
type TCallback = (res?: any) => void;
const DRAWER_WIDTH = 557;

const Members = ({ userType }: { userType: USER_STATUS }) => {
  const api = useSystemApi();
  const { getToken, getUserInfo }: any = useAppPassport();
  const [selected, setSelected] = useState<any>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [visible, setVisible] = useState(false);
  const [openDraw, setOpenDraw] = useState(false);
  const [saveBtnLoading, setSaveBtnLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [userId, setUserId] = useState("");
  const [passwordType, setPasswordType] = useState<any>(MODAL_TYPE.SUPER_RESET);
  const [drawConfig, setDrawConfig] = useState<{
    type: string;
    data: any;
    extraData?: any;
  }>({
    type: "add",
    data: null,
    extraData: null
  });

  const [deptTreeData, setDeptTreeData] = useState<any>([]);
  const [deptMap, setDeptMap] = useState<any>(new Map());
  const [treeLoading, setTreeLoading] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [tempData, setTempData]: any = useState(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [drawWidth, setDrawWidth] = useState<number | string>(DRAWER_WIDTH);
  const [searchInput, setSearchInput] = useState("");
  const [searchUserInput, setSearchUserInput] = useState("");
  const tableBoxRef = useRef<HTMLDivElement | null>(null);
  const [tableHeight, setTableHeight] = useState(500);
  const [pageNo, setPageNo] = useState(1);
  const [total, setTotal] = useState(0);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      setSelected(null);
      searchUserListFn(1, true);
    }
  };
  useEffect(() => {
    if (tableBoxRef.current) {
      const tableBoxHeight = tableBoxRef.current.offsetHeight;
      setTableHeight(tableBoxHeight);
    }
  }, []);
  const filteredDept = useMemo(() => {
    if (!deptTreeData) return deptTreeData;

    const filterTree = (nodes: any[], search: string): any[] => {
      return nodes
        .map((node) => {
          const match = node.name.toLowerCase().includes(search.toLowerCase());
          if (node.children) {
            const filteredChildren = filterTree(node.children, search);
            if (filteredChildren.length > 0 || match) {
              return { ...node, children: filteredChildren };
            }
          }
          return match ? { ...node, children: [] } : null;
        })
        .filter((node) => node !== null);
    };

    return filterTree(deptTreeData[0]?.children || [], searchInput);
  }, [deptTreeData, searchInput]);

  const [userList, setUserList] = useState([]);

  const editMembersFn = async (item: any) => {
    try {
      setSaveBtnLoading(true);
      const res: any = await api.updateUser({
        ...item,
        id: drawConfig.data.id,
        status: drawConfig.data.status,
        deptName: deptMap.get(item.deptId).name
      });
      setSaveBtnLoading(false);
      if (res.success) {
        if (item.deptId === selected) {
          searchUserListFn();
        } else {
          setSelected(item.deptId);
        }
        setOpenDraw(false);
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };

  const addMembersFn = async (item: any, cb?: (arg?: any) => void) => {
    try {
      setSaveBtnLoading(true);
      const res: any = await api.addUser({
        ...item,
        deptName: deptMap.get(item.deptId).name
      });
      setSaveBtnLoading(false);
      if (res.success) {
        cb && cb(res.data);
        if (item.deptId === selected) {
          searchUserListFn();
        } else {
          setSelected(item.deptId);
        }

        //setOpenDraw(false);
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };

  const uploadFilesOrUrls = (
    formData: FormData,
    sucFn?: TCallback,
    failFn?: TCallback,
    finFn?: TCallback
  ) => {
    const _url = `${getUrlPrefix()}/auth/user/import`;

    setSaveBtnLoading(true);
    axios$
      .post(_url, formData, {
        headers: {
          Authorization: getToken() || ""
        }
      })
      .then((res: any) => {
        if (res) {
          const { success, data } = res;
          searchUserListFn();
          if (res.data.length) {
            failFn && failFn(res.data);
          } else {
            sucFn && sucFn(data);
          }
        } else {
          failFn && failFn(res);
        }
      })
      .finally(() => {
        if (finFn) {
          finFn();
        } else {
          setSaveBtnLoading(false);
        }
      })
      .catch((e) => {
        finFn && finFn();
        console.log(e);
      });
  };

  const handleTriggerUpload = (fList: any[], cb?: (arg?: any) => void) => {
    if (!fList.length) return;
    const _formData = new FormData();
    _formData.append("file", fList[0]);
    uploadFilesOrUrls(
      _formData,
      () => {
        setOpenDraw(false);
        setDrawWidth(DRAWER_WIDTH);
        cb && cb([]);
      },
      (data) => {
        if (data?.length) {
          setDrawWidth("100%");
        }

        cb && cb(data);
      }
    );
  };

  const changeDepartmentFn = async (item: any) => {
    try {
      setSaveBtnLoading(true);
      const res: any = await api.updateUserInfoBatch({
        userIds: Array.isArray(drawConfig.data)
          ? drawConfig.data.map((v) => v.id)
          : [drawConfig.data.id],
        deptId: item.deptId,
        deptName: deptMap.get(item.deptId).name
      });
      setSaveBtnLoading(false);
      if (res.success) {
        if (item.deptId === selected) {
          searchUserListFn();
        } else {
          setSelected(item.deptId);
        }
        setOpenDraw(false);
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };

  const userExportFn = async (params: any) => {
    const queryParams = new URLSearchParams(params);
    setSaveBtnLoading(true);
    fetch(`${getUrlPrefix()}/auth/user/export?${queryParams.toString()}`, {
      method: "GET",
      headers: {
        Authorization: getToken() || ""
      }
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.blob(); // 获取Blob对象
      })
      .then((blob) => {
        setSaveBtnLoading(false);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        a.download = "用户信息模板";
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url); // 释放URL对象
        document.body.removeChild(a);
        setSaveBtnLoading(false);
      })
      .catch((error) => {
        setSaveBtnLoading(false);
        console.error(
          "There has been a problem with your fetch operation:",
          error
        );
      });
  };

  const transferPropertyFn = async (data: any) => {
    try {
      setSaveBtnLoading(true);
      const res: any = await api.transferProperty(data);
      setSaveBtnLoading(false);
      if (res.success) {
        searchUserListFn();
        setOpenDraw(false);
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };

  const transferTypeFn = async (data: any, successCb: any) => {
    try {
      message.info({
        key: "transferLoading",
        content: "资源加载中……"
      });
      const res: any = await api.getTransferType({ userId: data.id });
      message.destroy("transferLoading");
      if (res.success) {
        successCb && successCb(res.data);
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  const updateUserStatusBatchFn = async (data: any, cb?: any) => {
    try {
      setSaveBtnLoading(true);
      const res: any = await api.updateUserStatusBatch({ userIds: data });
      setSaveBtnLoading(false);
      if (res.success) {
        cb && cb();
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };
  const handleEvent = (type: string, data?: any, cb?: (arg?: any) => void) => {
    switch (type) {
      case "save:resignation":
        updateUserStatusBatchFn(
          Array.isArray(data) ? selectedRowKeys : [data.id],
          cb
        );
        break;
      case "save:transferPropertyFn":
        transferPropertyFn(data);
        break;
      case "save:batchExport":
        userExportFn(data ? { deptIds: data } : {});
        break;
      case "save:changeDepartment":
        changeDepartmentFn(data);
        break;
      case "save:importUser":
        handleTriggerUpload(data, cb);
        break;
      case "save:addMembers":
        addMembersFn(data, cb);
        break;
      case "save:viewMembers":
        editMembersFn(data);
        break;
      case "save:editDepartment":
        editDepartmentFn(data);
        break;
      case "save:addDepartment":
        createDepartmentFn(data);
        break;
      case "batchExport":
        setDrawConfig({ type, data });
        setOpenDraw(true);
        break;
      case "reImport":
        setDrawWidth(DRAWER_WIDTH);
        break;
      case "closeDrawerAndFresh":
        setOpenDraw(false);
        searchUserListFn();
        break;
      case "closeDrawer":
        setOpenDraw(false);
        break;
      case "addMembers":
        setDrawConfig({ type, data });
        setOpenDraw(true);
        break;
      case "batchImport":
        setDrawConfig({ type, data });
        setOpenDraw(true);
        break;
    }
  };
  const getRightItems: any = (record: any) => {
    const btns = [
      {
        key: "1",
        label: (
          <LinkItemsBtn
            item={{ name: "变更部门", key: "changeDepartment" }}
            handleEvent={() => rightEvent("changeDepartment", record)}
            disabled={getEditPermission(
              userType,
              BTN_NAME.VIEW,
              record.userType
            )}
            tip={
              getEditPermission(userType, BTN_NAME.VIEW, record.userType)
                ? PERMISSION_WARNING_MSG
                : ""
            }
          />
        )
      },
      {
        key: "2",
        label: (
          <LinkItemsBtn
            item={{ name: "操作离职", key: "resignation" }}
            handleEvent={() => rightEvent("resignation", record)}
            disabled={getEditPermission(
              userType,
              BTN_NAME.ADD,
              record.userType
            )}
            tip={
              getEditPermission(userType, BTN_NAME.ADD, record.userType)
                ? PERMISSION_WARNING_MSG
                : ""
            }
          />
        )
      },
      {
        key: "3",
        label: (
          <LinkItemsBtn
            item={{
              name: `${record.status === 1 ? "暂停账号" : "恢复账号"}`,
              key: "suspend"
            }}
            handleEvent={() => rightEvent("suspend", record)}
            disabled={getEditPermission(
              userType,
              BTN_NAME.VIEW,
              record.userType
            )}
            tip={
              getEditPermission(userType, BTN_NAME.VIEW, record.userType)
                ? PERMISSION_WARNING_MSG
                : ""
            }
          />
        )
      },
      {
        key: "4",
        label: (
          <LinkItemsBtn
            item={{ name: "转移资源", key: "transfer" }}
            handleEvent={() => rightEvent("transfer", record)}
            disabled={getEditPermission(
              userType,
              BTN_NAME.ADD,
              record.userType
            )}
            tip={
              getEditPermission(userType, BTN_NAME.ADD, record.userType)
                ? PERMISSION_WARNING_MSG
                : ""
            }
          />
        )
      }

      // {
      //   key: "5",
      //   label: (
      //     <LinkItemsBtn
      //       item={{ name: "置顶", key: "topUp" }}
      //       handleEvent={() => rightEvent("topUp")}
      //     />
      //   )
      // }
    ];
    if (!getEditPermission(userType, BTN_NAME.ADD, record.userType)) {
      btns.push({
        key: "5",
        label: (
          <LinkItemsBtn
            item={{ name: "重置密码", key: "resetPassword" }}
            handleEvent={() => rightEvent("resetPassword", record)}
            disabled={getEditPermission(
              userType,
              BTN_NAME.ADD,
              record.userType
            )}
            tip={
              getEditPermission(userType, BTN_NAME.ADD, record.userType)
                ? PERMISSION_WARNING_MSG
                : ""
            }
          />
        )
      });
    }
    if (
      record.hasAdminResetPassword &&
      !getEditPermission(userType, BTN_NAME.ADD, record.userType)
    ) {
      btns.push({
        key: "6",
        label: (
          <LinkItemsBtn
            item={{ name: "查看密码", key: "viewPassword" }}
            handleEvent={() => rightEvent("viewPassword", record)}
            disabled={getEditPermission(
              userType,
              BTN_NAME.ADD,
              record.userType
            )}
            tip={
              getEditPermission(userType, BTN_NAME.ADD, record.userType)
                ? PERMISSION_WARNING_MSG
                : ""
            }
          />
        )
      });
    }
    return btns;
  };

  const columns: ColumnType<any>[] = [
    {
      title: "姓名",
      dataIndex: "userRealname",
      key: "userRealname",
      render: (text: string, record: any) => (
        <div className="flex items-center">
          <Avatar
            icon={<UserOutlined {...getIconProps()} />}
            {...getAvatarProps("MEMBER")}
            className="mr-[8px]"
          />
          <span className="ml-2">{text || "匿名"}</span>
        </div>
      )
    },
    {
      title: "账号状态",
      dataIndex: "status",
      minWidth: 100,
      key: "status",
      render: (_: any, record: any) => {
        return (
          <div className="flex items-center">
            <div
              className={`w-2 h-2  rounded-full mr-[4px] ${
                _ === 1 ? "bg-green-500" : "bg-[#BCBCBC]"
              }`}
            ></div>
            <div>{_ === 1 ? "正常" : "已暂停"}</div>
          </div>
        );
      }
    },
    {
      title: "联系邮箱",
      dataIndex: "userEmail",
      key: "userEmail",
      width: 200
    },
    {
      title: "部门",
      dataIndex: "deptName",
      key: "deptName",
      minWidth: 100,
      render: (text: string) => (
        <div className="flex items-center">
          <Avatar
            icon={<Building2 {...getIconProps()} />}
            {...getAvatarProps("DEPARTMENT")}
            className="mr-[8px]"
          />
          <span>{text}</span>
        </div>
      )
    },
    {
      title: "角色",
      dataIndex: "roleName",
      key: "roleName",
      minWidth: 100,
      render: (_: any, record: any) => {
        return (record.roles || [])
          .map((item: any) => {
            return item.name;
          })
          .join(";");
      }
    },
    {
      title: "特征",
      dataIndex: "feature",
      key: "feature",
      render: (_: any, record: any) => {
        return (
          <Tooltip
            title={_}
            styles={{
              body: {
                backgroundColor: "#1e1e1e",
                color: "#ffffff",
                fontSize: "12px",
                padding: "6px 8px",
                maxWidth: "400px",
                borderRadius: "6px",
                width: "300px",
                maxHeight: "40vh",
                overflowY: "auto"
              }
            }}
          >
            <span>{_ ? (_.length > 10 ? `${_.slice(0, 10)}...` : _) : _}</span>
          </Tooltip>
        );
      }
    },
    {
      title: "操作",
      key: "action",
      width: 200,
      render: (_: any, record: any) => {
        return (
          <div className="flex items-center gap-2">
            <CustomTooltip
              content={
                getEditPermission(userType, BTN_NAME.VIEW, record.userType)
                  ? PERMISSION_WARNING_MSG
                  : ""
              }
              type="warning"
              position="top"
            >
              <Button
                type="link"
                onClick={() => rightEvent("viewMembers", record)}
                disabled={getEditPermission(
                  userType,
                  BTN_NAME.VIEW,
                  record.userType
                )}
              >
                详情
              </Button>
            </CustomTooltip>
            <Dropdown menu={{ items: getRightItems(record) }}>
              <a onClick={(e) => e.preventDefault()}>
                <EllipsisOutlined />
              </a>
            </Dropdown>
          </div>
        );
      }
    }
  ];

  const setUserStatusFn = async (params: any) => {
    try {
      setSaveBtnLoading(true);
      const res: any = await api.setUserStatus(params);
      setSaveBtnLoading(false);
      if (res.success) {
        searchUserListFn();
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };

  const rightEvent = (type: string, data?: any) => {
    console.log("====================================");
    console.log("t->", type, "d->", data);
    console.log("====================================");
    switch (type) {
      case "viewPassword":
        setPasswordType(MODAL_TYPE.SUPER_VIEW);
        setUserId(data.id);
        setVisible(true);
        break;
        break;
      case "resetPassword":
        setPasswordType(MODAL_TYPE.SUPER_RESET);
        setUserId(data.id);
        setVisible(true);
        break;
      case "batchFeature":
        setModalVisible(true);
        break;
      case "suspend":
        setUserStatusFn({
          userIds: data.id,
          status: data.status === 1 ? 0 : 1
        });
        break;
      case "transfer":
        transferTypeFn(data, (res: any[]) => {
          if (res.length) {
            setDrawConfig({
              type,
              data: { ...data },
              extraData: { transferType: res }
            });
            setOpenDraw(true);
          } else {
            message.info("该用户无资源可转移");
          }
        });
        break;
      case "changeDepartment":
        setDrawConfig({
          type,
          data:
            data ||
            userList.filter((item: any) => {
              return selectedRowKeys.includes(item.id);
            })
        });
        setOpenDraw(true);
        break;
      case "resignation":
        const userInfo = getUserInfo();
        if (data) {
          if (data.id === userInfo.id) {
            return message.warning("不可将自己操作为离职");
          }
          transferTypeFn(data, (res: any[]) => {
            setDrawConfig({
              type,
              data,
              extraData: { transferType: res }
            });
            setOpenDraw(true);
          });
        } else {
          if (selectedRowKeys.some((user: any) => user === userInfo.id)) {
            return message.warning("不可将自己操作为离职");
          }
          setDrawConfig({
            type,
            data: userList.filter((item: any) => {
              return selectedRowKeys.includes(item.id);
            })
          });
          setOpenDraw(true);
        }

        break;
      case "viewMembers":
        setDrawConfig({ type, data });
        setOpenDraw(true);
        break;

      case "add":
        setDrawConfig({ type, data });
        setOpenDraw(true);
        break;
      case "edit":
        setDrawConfig({ type, data });
        setOpenDraw(true);
        break;
      case "delete":
        setTempData(data);
        setShowDeleteModal(true);
        break;
      case "prev":
        break;
      case "next":
        break;
    }
  };

  const deleteDepartmentFn = async (item: any) => {
    try {
      setSaveBtnLoading(true);
      const res: any = await api.deleteDepartment({
        id: item.id
      });
      setSaveBtnLoading(false);
      if (res.success) {
        setShowDeleteModal(false);
        getDepartmentInfo();
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };

  const createDepartmentFn = async (item: any) => {
    try {
      setSaveBtnLoading(true);
      const res: any = await api.createDepartment({
        name: item.name,
        parentId: item.parentId
      });
      setSaveBtnLoading(false);
      if (res.success) {
        setOpenDraw(false);
        getDepartmentInfo();
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };

  const editDepartmentFn = async (item: any) => {
    try {
      setSaveBtnLoading(true);
      const res: any = await api.editDepartment({
        name: item.name,
        parentId: item.parentId,
        id: drawConfig.data.id
      });
      setSaveBtnLoading(false);
      if (res.success) {
        setOpenDraw(false);
        getDepartmentInfo();
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };

  useEffect(() => {
    if (openDraw && drawWidth !== DRAWER_WIDTH) {
      setDrawWidth(DRAWER_WIDTH);
    }
  }, [openDraw]);

  const handleListItem = (type: string, data?: any) => {
    switch (type) {
      case "clickItem":
        setSelected(data.id);
        break;
      case "clickRightIcon":
        rightEvent(data.type, data.item);
        break;
    }
  };

  const setTreeConfig = (data: any) => {
    const map = new Map();
    const recursionFn = (data: any, layer: number) => {
      data.forEach((item: any) => {
        item.layer = layer;
        map.set(item.id, item);
        if (item?.children?.length) {
          recursionFn(item.children, layer + 1);
        }
      });
    };
    recursionFn(data, 0);
    return { data, map };
  };

  const getDepartmentInfo = async () => {
    setTreeLoading(true);
    try {
      const res: any = await api.getTreeDeptById({}, {});
      setTreeLoading(false);
      if (res.success) {
        const { data, map } = setTreeConfig(res.data);
        setDeptMap(map);
        setDeptTreeData(data);
        setSelected(data[0].id);
      }
    } catch (error) {
      setTreeLoading(false);
      console.log("error", error);
    }
  };

  const searchUserListFn = async (p?: number, noDept?: boolean) => {
    try {
      setTableLoading(true);
      const params: any = {
        pageSize: 5,
        pageNo: p || 1,
        fuzzy: searchUserInput
      };
      if (!noDept) {
        params.deptId = selected;
      }
      const res: any = await api.searchUserList(params);
      setTableLoading(false);
      if (res.success) {
        setUserList(res.data.records);
        setTotal(res.data.total);
      }
    } catch (error) {
      setTableLoading(false);
      console.log("error", error);
    }
  };

  useEffect(() => {
    getDepartmentInfo();
  }, []);

  useEffect(() => {
    if (selected) {
      searchUserListFn();
    }
  }, [selected]);
  useEffect(() => {
    setDrawWidth(DRAWER_WIDTH);
  }, [openDraw]);
  return (
    <div className="w-full h-full flex">
      <div
        className="h-full w-[260px] p-[20px]"
        style={{ borderRight: "1px solid #E8E8E8" }}
      >
        <Input
          placeholder="搜索部门名"
          suffix={
            <SearchOutlined
              onClick={() => {
                setSelected(null);
                searchUserListFn();
              }}
            />
          }
          value={searchInput}
          onChange={(e) => setSearchInput(e?.target?.value || "")}
          className="mb-[10px]"
        />
        <CustomTooltip
          content={
            getEditPermission(userType, BTN_NAME.ADD)
              ? PERMISSION_WARNING_MSG
              : ""
          }
          type="warning"
          position="top"
        >
          <Button
            className="w-[219px] text-text-color2 border-[#EBEBEB] mb-[16px]"
            type="dashed"
            block
            icon={<PlusOutlined />}
            style={{
              border: getEditPermission(userType, BTN_NAME.ADD)
                ? "1px solid rgb(235, 235, 235)"
                : "none",
              color: getEditPermission(userType, BTN_NAME.ADD)
                ? "rgb(85, 85, 85)"
                : "#fff",
              background: getEditPermission(userType, BTN_NAME.ADD)
                ? "rgba(0,0,0,.04)"
                : "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
            }}
            onClick={() => {
              setDrawConfig({ type: "add", data: { id: deptTreeData[0]?.id } });
              setOpenDraw(true);
            }}
            disabled={getEditPermission(userType, BTN_NAME.ADD)}
          >
            新建部门
          </Button>
        </CustomTooltip>
        <TreeListItem
          handleEvent={handleListItem}
          item={{
            name: deptTreeData[0]?.name,
            id: deptTreeData[0]?.id,
            type: "company"
          }}
          selected={selected}
        />
        <div className="h-[calc(100%-150px)] overflow-y-auto">
          <Spin spinning={treeLoading}>
            <div className="mt-[8px] userTree">
              <div className="max-h-[calc(100%-63px)] hideScroll">
                <Tree
                  treeData={filteredDept}
                  showIcon
                  blockNode
                  scrollWidth={100}
                  titleRender={(nodeData: any) => {
                    const storey = nodeData.layer - 1;
                    let w = 115 - storey * 24;
                    w = w < 30 ? 30 : w;
                    const curList = nodeData.parentId
                      ? (deptMap.get(nodeData.parentId) as any).children
                      : [];
                    const index = (curList || []).findIndex(
                      (item: any) => item.id === nodeData.id
                    );
                    return (
                      <div className="flex items-center">
                        <Avatar
                          icon={<Building2 {...getIconProps()} />}
                          {...getAvatarProps("DEPARTMENT")}
                          className="mr-[8px]"
                        />
                        <div
                          style={{ width: `${w}px` }}
                          className="text-ellipsis line-clamp-1 block"
                        >
                          {nodeData.name}
                        </div>
                        <RightIcon
                          type={
                            curList?.length === 1
                              ? 4
                              : index === 0
                              ? 1
                              : index === curList?.length - 1
                              ? 3
                              : 2
                          }
                          className={`${
                            selected === nodeData.key
                              ? "text-primary-color"
                              : "text-text-color1"
                          }`}
                          handleEvent={(type) => rightEvent(type, nodeData)}
                          disabled={getEditPermission(userType, BTN_NAME.ADD)}
                        />
                      </div>
                    );
                  }}
                  fieldNames={{ key: "id", title: "name" }}
                  switcherIcon={
                    <CaretDownOutlined className="text-[#888888]" />
                  }
                  selectedKeys={[selected]}
                  onSelect={(
                    selectedKeys: any,
                    e: {
                      selected: boolean;
                      selectedNodes: any;
                      node: any;
                      event: any;
                    }
                  ) => {
                    if (e.selected) {
                      setSelected(selectedKeys[0]);
                    } else {
                      setSelected("000");
                    }
                  }}
                />
              </div>
            </div>
          </Spin>
        </div>
      </div>
      <div className="w-[calc(100%-260px)] p-[16px] h-full">
        <div className="flex">
          <div className="text-text-color1 font-[600] text-[16px] mr-[20px]">
            {deptMap.get(selected)?.name}
          </div>
          <div className="text-text-color2 text-[14px]">
            总人数{" "}
            <span className="text-text-color1 font-[600] text-[16px]">
              {total}
            </span>
          </div>
        </div>
        <div className="flex mt-[20px]">
          <CustomTooltip
            content={
              getEditPermission(userType, BTN_NAME.ADD)
                ? PERMISSION_WARNING_MSG
                : ""
            }
            type="warning"
            position="top"
          >
            <Button
              icon={<PlusCircleOutlined />}
              style={{
                border: getEditPermission(userType, BTN_NAME.ADD)
                  ? "1px solid rgb(235, 235, 235)"
                  : "none",
                color: getEditPermission(userType, BTN_NAME.ADD)
                  ? "rgb(85, 85, 85)"
                  : "#fff",
                background: getEditPermission(userType, BTN_NAME.ADD)
                  ? "rgba(0, 0, 0, 0.04)"
                  : "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)",
                marginRight: "16px"
              }}
              onClick={() => handleEvent("addMembers")}
              disabled={getEditPermission(userType, BTN_NAME.ADD)}
            >
              添加成员
            </Button>
          </CustomTooltip>
          <CustomTooltip
            content={
              getEditPermission(userType, BTN_NAME.ADD)
                ? PERMISSION_WARNING_MSG
                : ""
            }
            type="warning"
            position="top"
          >
            <Button
              style={{
                border: "1px solid #EBEBEB",
                color: "#555555",
                marginRight: "16px"
              }}
              onClick={() => handleEvent("batchImport")}
              disabled={getEditPermission(userType, BTN_NAME.ADD)}
            >
              批量导入
            </Button>
          </CustomTooltip>
          <CustomTooltip
            content={
              getEditPermission(userType, BTN_NAME.ADD)
                ? PERMISSION_WARNING_MSG
                : ""
            }
            type="warning"
            position="top"
          >
            <Button
              style={{
                border: "1px solid #EBEBEB",
                color: "#555555",
                marginRight: "16px"
              }}
              onClick={() => handleEvent("batchExport")}
              disabled={getEditPermission(userType, BTN_NAME.ADD)}
            >
              批量导出
            </Button>
          </CustomTooltip>
          <CustomTooltip
            content={
              getEditPermission(userType, BTN_NAME.VIEW)
                ? PERMISSION_WARNING_MSG
                : !selectedRowKeys.length
                ? "请至少选择一条数据"
                : ""
            }
            type="warning"
            position="top"
          >
            <Button
              style={{
                border: "1px solid #EBEBEB",
                color: "#555555",
                marginRight: "16px"
              }}
              onClick={() => rightEvent("changeDepartment")}
              disabled={
                getEditPermission(userType, BTN_NAME.VIEW) ||
                !selectedRowKeys.length
              }
            >
              变更部门
            </Button>
          </CustomTooltip>
          <CustomTooltip
            content={
              getEditPermission(userType, BTN_NAME.ADD)
                ? PERMISSION_WARNING_MSG
                : !selectedRowKeys.length
                ? "请至少选择一条数据"
                : ""
            }
            type="warning"
            position="top"
          >
            <Button
              style={{
                border: "1px solid #EBEBEB",
                color: "#555555",
                marginRight: "16px"
              }}
              onClick={() => rightEvent("resignation")}
              disabled={
                getEditPermission(userType, BTN_NAME.ADD) ||
                !selectedRowKeys.length
              }
            >
              操作离职
            </Button>
          </CustomTooltip>
          {/* <CustomTooltip
            content={
              getEditPermission(userType, BTN_NAME.VIEW)
                ? PERMISSION_WARNING_MSG
                : ""
            }
            type="warning"
            position="top"
          >
            <Button
              style={{
                border: getEditPermission(userType, BTN_NAME.VIEW)
                  ? "1px solid rgb(235, 235, 235)"
                  : "none",
                color: getEditPermission(userType, BTN_NAME.VIEW)
                  ? "rgb(85, 85, 85)"
                  : "#fff",
                background: getEditPermission(userType, BTN_NAME.VIEW)
                  ? "rgba(0, 0, 0, 0.04)"
                  : "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)",
                marginRight: "16px"
              }}
              onClick={() => rightEvent("batchFeature")}
              disabled={getEditPermission(userType, BTN_NAME.VIEW)}
            >
              批量新增特征
            </Button>
          </CustomTooltip> */}
          <Input
            placeholder="搜索姓名、邮箱、手机号"
            suffix={
              <SearchOutlined
                onClick={() => {
                  setSelected(null);
                  searchUserListFn(1, true);
                }}
              />
            }
            value={searchUserInput}
            onChange={(e) => setSearchUserInput(e?.target?.value || "")}
            className="mb-[10px] mr-[16px] w-[200px]"
            onPressEnter={handleKeyDown}
          />
        </div>
        <div ref={tableBoxRef} className="h-[calc(100%-150px)]">
          <Table
            columns={columns}
            dataSource={userList}
            className="mt-[20px]"
            rowKey="id"
            loading={tableLoading}
            scroll={{
              x: "max-content",
              y: tableHeight - 60 > 380 ? undefined : tableHeight - 60
            }}
            rowSelection={{
              type: "checkbox",
              onChange: (selectedRowKeys: any, selectedRows: any[]) => {
                setSelectedRowKeys(selectedRowKeys);
              }
            }}
            pagination={false}
          />
          <Pagination
            align="end"
            className="mt-[10px]"
            current={pageNo}
            total={total}
            pageSize={5}
            size="small"
            hideOnSinglePage
            showSizeChanger={false}
            onChange={(page: number, pageSize: number) => {
              setPageNo(page);
              searchUserListFn(page);
            }}
          />
        </div>
      </div>
      <ConfigProvider
        drawer={{
          styles: {
            body: { padding: 0 },
            header: { padding: "20px 20px 16px 20px" }
          }
        }}
      >
        <Drawer
          title={
            <div className="flex justify-between items-center">
              <div className="text-[16px] font-bold">
                {drawConfig.type === "add"
                  ? "新建部门"
                  : drawConfig.type === "edit"
                  ? "编辑部门"
                  : drawConfig.type === "addMembers"
                  ? "添加成员"
                  : drawConfig.type === "viewMembers"
                  ? "详情"
                  : drawConfig.type === "batchImport"
                  ? "批量导入"
                  : drawConfig.type === "resignation"
                  ? "操作离职"
                  : drawConfig.type === "batchExport"
                  ? "批量导出"
                  : drawConfig.type === "changeDepartment"
                  ? "变更部门"
                  : drawConfig.type === "transfer"
                  ? "转移资源"
                  : ""}
              </div>
              <CloseOutlined
                className="cursor-pointer"
                onClick={() => setOpenDraw(false)}
              />
            </div>
          }
          closable={false}
          width={drawWidth}
          onClose={() => setOpenDraw(false)}
          open={openDraw}
          destroyOnClose
        >
          <div className="h-[calc(100vh-62px)] relative px-[20px] pt-[10px] pb-[20px]">
            {(drawConfig.type === "add" || drawConfig.type === "edit") && (
              <AddOrEditDepartment
                drawConfig={drawConfig}
                deptTreeData={deptTreeData}
                handleEvent={handleEvent}
                btnLoading={saveBtnLoading}
              />
            )}
            {(drawConfig.type === "addMembers" ||
              drawConfig.type === "viewMembers") && (
              <AddOrEditMembers
                drawConfig={drawConfig}
                deptTreeData={deptTreeData}
                handleEvent={handleEvent}
                btnLoading={saveBtnLoading}
              />
            )}
            {drawConfig.type === "batchImport" && (
              <BatchImport
                drawConfig={drawConfig}
                handleEvent={handleEvent}
                btnLoading={saveBtnLoading}
              />
            )}
            {drawConfig.type === "resignation" && (
              <Resignation
                drawConfig={drawConfig}
                handleEvent={handleEvent}
                btnLoading={saveBtnLoading}
              />
            )}
            {drawConfig.type === "batchExport" && (
              <BatchExport
                drawConfig={drawConfig}
                deptTreeData={deptTreeData}
                handleEvent={handleEvent}
                btnLoading={saveBtnLoading}
              />
            )}
            {drawConfig.type === "changeDepartment" && (
              <ChangeDepartment
                drawConfig={drawConfig}
                handleEvent={handleEvent}
                deptTreeData={deptTreeData}
                btnLoading={saveBtnLoading}
              />
            )}
            {drawConfig.type === "transfer" && (
              <Resignation
                drawConfig={drawConfig}
                type="transfer"
                handleEvent={handleEvent}
                btnLoading={saveBtnLoading}
              />
            )}
          </div>
        </Drawer>
      </ConfigProvider>
      <PasswordModal
        visible={visible}
        onCancel={() => setVisible(false)}
        type={passwordType}
        userId={userId}
        eventEmit={(type: string) => {
          if (type === "superReset:afterReset") {
            searchUserListFn();
          }
        }}
      />
      <BatchAddModal
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        onSave={() => {
          searchUserListFn();
        }}
      />
      <DeleteConfirm
        isShowDeleteModal={showDeleteModal}
        loading={saveBtnLoading}
        confirmModal={() => {
          deleteDepartmentFn(tempData);
        }}
        closeModal={() => {
          setShowDeleteModal(false);
        }}
      />
    </div>
  );
};

export default Members;

const createKeyMap = (
  data: any[],
  map: Map<string, TreeDataNode> = new Map()
): Map<string, TreeDataNode> => {
  data.forEach((node) => {
    map.set(node.key, node);
    if (node.children) {
      createKeyMap(node.children, map);
    }
  });
  return map;
};
