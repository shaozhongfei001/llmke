import { Button, ConfigProvider, Modal, Popconfirm, Switch, Table } from "antd";
import { useEffect, useMemo, useState } from "react";
import addSearch from "@/assets/img/addSearch.png";
import { CloseOutlined } from "@ant-design/icons";
import { ColumnsType } from "antd/es/table";
import SelectCom from "../SelectRight";
import SelectOrganization from "../SelectOrganization";
import IconHeader from "../IconHeader";
import {
  BASE_USER_TYPE,
  ELEMENT_TYPE,
  FILE_BTN,
  getBtnDisabled,
  PERMISSION_STATUS
} from "@root/src/const/permission";
import { usePermissionController } from "./usePermissionController";
import useSystemApi, { SetPermissionUserDTO } from "@root/src/apis/system";
import { useLocation, useParams } from "react-router-dom";

export interface TypeDrawConfig {
  type?:
    | "create"
    | "edit"
    | "permission"
    | "view"
    | "transfer"
    | "addFile"
    | "tag"
    | "publish";
  data?: any;
  permissionList?: any;
  bizType?: number;
}

const PermisssonConfig = ({
  type,
  drawConfig,
  subTitle,
  bizType,
  kbInfo
}: {
  type: string;
  subTitle: string;
  drawConfig: TypeDrawConfig;
  bizType: number;
  kbInfo?: any;
}) => {
  const disabled = useMemo(() => {
    if (!kbInfo) return false;
    return bizType === 1 || bizType === 12
      ? getBtnDisabled(FILE_BTN.AUTHORIZE_CONFIG, kbInfo.permission)
      : false;
  }, [kbInfo]);

  const api = useSystemApi();
  const [allUser, setAllUser] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [hoveredRowKey, setHoveredRowKey]: any = useState(null);
  const [checkedData, setCheckedData]: any = useState([]);
  const [dataSource, setDataSource]: any[] = useState([]);
  const [loading, setLoading] = useState(false);
  const paramsQuery = useParams();
  const fetchAllPrivilegeList = async () => {
    try {
      const api_queryList =
        type === "docuRight" ? api.getCollaborators : api.getAllPrivilegeList;
      setLoading(true);
      const p: any = {
        bizType,
        targetId: drawConfig?.data?.id
      };
      if (type === "docuRight") {
        p.kbId = paramsQuery.id;
      }
      const res: any = await api_queryList(p);
      setLoading(false);
      setDataSource(
        res.data
          .filter((item: any) => item.permission)
          .map((item: any) => {
            if (
              item.userType === BASE_USER_TYPE.READ_ONLY ||
              item.userType === BASE_USER_TYPE.EDIT ||
              item.userType === BASE_USER_TYPE.MANAGE
            ) {
              return {
                ...item,
                id:
                  item.userType === BASE_USER_TYPE.READ_ONLY
                    ? -2
                    : item.userType === BASE_USER_TYPE.EDIT
                    ? -3
                    : -4
              };
            }
            return item;
          })
      );
      if (res.data.length) {
        setAllUser(res.data[0].userId == -1);
      }
    } catch (error) {
      setLoading(false);
      console.log("error", error);
    }
  };

  const {
    setPrivilegePermission,
    updatePermission,
    setAllPemission,
    btnLoading
  } = usePermissionController({
    bizType,
    targetId: drawConfig?.data?.id,
    fetchAllPrivilegeList
  });

  const deletePermissionFn = async (item: {
    elementType: ELEMENT_TYPE;
    id: number;
  }) => {
    const curApi =
      item.elementType === ELEMENT_TYPE.DEPARTMENT
        ? api.deleteDeptPermission
        : item.elementType === ELEMENT_TYPE.GROUP
        ? api.deleteGroupPermission
        : api.deleteUserPermission;
    try {
      const res: any = await curApi({
        id: item.id
      });
      if (res.success) {
        fetchAllPrivilegeList();
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  const setUserPemission = async (checked: boolean) => {
    try {
      if (checked) {
        const res: any = await api.setUserPermission({
          userIds: [-1],
          targetId: drawConfig?.data?.id,
          permission: PERMISSION_STATUS.READ_ONLY,
          bizType
        });
        if (res.success) {
          fetchAllPrivilegeList();
        }
      } else {
        deletePermissionFn(dataSource[0]);
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  const getText = (item: any) => {
    if (item.userType === BASE_USER_TYPE.READ_ONLY) {
      return "当前知识库可阅读成员";
    } else if (item.userType === BASE_USER_TYPE.EDIT) {
      return "当前知识库可编辑成员";
    } else if (item.userType === BASE_USER_TYPE.MANAGE) {
      return "当前知识库管理员";
    }
    return (
      item.userRealname ||
      item.userName ||
      item.deptName ||
      item.groupName ||
      item.name
    );
  };

  const getType = (item: any) => {
    if (item.userType === BASE_USER_TYPE.READ_ONLY) {
      return ELEMENT_TYPE.COLLABORATORS_READONLY;
    } else if (item.userType === BASE_USER_TYPE.EDIT) {
      return ELEMENT_TYPE.COLLABORATORS_READ_AND_WRITE;
    } else if (item.userType === BASE_USER_TYPE.MANAGE) {
      return ELEMENT_TYPE.COLLABORATORS_ALL_PERMISSION;
    }
    return item.userId == -1 ? ELEMENT_TYPE.ALLUSER : item.elementType;
  };

  const showClose = (data: any) => {
    if (
      data.userType === BASE_USER_TYPE.READ_ONLY ||
      data.userType === BASE_USER_TYPE.EDIT ||
      data.userType === BASE_USER_TYPE.MANAGE
    ) {
      return false;
    }
    return data.userId !== -1;
  };

  const getDisabled = (record: any) => {
    const { userType } = record;
    if (
      (userType === BASE_USER_TYPE.READ_ONLY ||
        userType === BASE_USER_TYPE.EDIT ||
        userType === BASE_USER_TYPE.MANAGE) &&
      !record?.users?.length
    ) {
      return true;
    }
    return false;
  };

  const columns: ColumnsType<any> = [
    {
      title: "用户",
      dataIndex: "name",
      width: "45%",
      ellipsis: true,
      key: "name",
      render: (text: string, r: any) => (
        <div className="flex items-center">
          <IconHeader
            text={r.userRealname || r.userName || r.deptName || r.groupName}
            type={getType(r)}
            rounded="rounded-full"
            size={32}
          />
          <div>
            <div className="text-[16px] flex">
              <div className="mr-[3px]">
                {r.userId == -1 ? "所有人" : getText(r)}
              </div>
              {r.creator && (
                <div className="text-primary-color bg-[#DEE7FF] text-[12px] rounded-[2px] h-[20px] px-[4px]">
                  创建者
                </div>
              )}
            </div>
            <div className="text-[#888888] text-[14px]">
              {r.department || r.deptName}
            </div>
            {typeof r.userCount === "number" && (
              <div className="text-[#888888] text-[12px]">
                ({r.userCount}人)
              </div>
            )}
          </div>
        </div>
      )
    },
    {
      title: "所有",
      dataIndex: "permission",
      key: "permission",
      width: "40%",
      ellipsis: true,
      render: (text: string, record: any) => {
        return record.creator ? (
          <div className="ml-[16px]">可管理</div>
        ) : (
          <SelectCom
            onChange={(value: number) => {
              handleSelectChange(record, value);
            }}
            value={record.permission}
            userType={record.userType}
            disabled={getDisabled(record) || disabled || record.creator}
            type={type}
          />
        );
      }
    },
    {
      title: "操作",
      dataIndex: "action",
      key: "action",
      width: "15%",
      align: "right",
      render: (_: any, record: any) =>
        hoveredRowKey === record.id &&
        showClose(record) &&
        !disabled &&
        !record.creator ? (
          <Popconfirm
            title={
              <>
                <div className="flex items-center">
                  <div className="text-[14px] text-[#000000] font-bold ml-[8px]">
                    删除
                  </div>
                </div>
                <div className="flex items-center">
                  <div className="text-[14px] text-[#000000] mt-[8px]">
                    <span>删除后无法恢复，是否继续</span>
                    <br />
                    <span>删除？</span>
                  </div>
                </div>
              </>
            }
            onConfirm={() => {
              deletePermissionFn(record);
            }}
            okText="确定"
            cancelText="取消"
          >
            <CloseOutlined className="text-[#666666] cursor-pointer" />
          </Popconfirm>
        ) : (
          <></>
        )
    }
  ];

  const allUserChange = (checked: boolean) => {
    setAllUser(checked);
    setUserPemission(checked);
  };

  const updateCurrentPermissionByBizTypeFn = async (params: any, cb?: any) => {
    try {
      const res: any = await api.updateCurrentPermissionByBizType(params);
      if (res.success) {
        cb && cb();
        fetchAllPrivilegeList();
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  const handleSelectChange = async (data: any, value: number) => {
    const params: any = {
      bizType,
      targetId: drawConfig?.data?.id,
      permission: value
    };
    if (
      data.userType === BASE_USER_TYPE.READ_ONLY ||
      data.userType === BASE_USER_TYPE.EDIT ||
      data.userType === BASE_USER_TYPE.MANAGE
    ) {
      try {
        updateCurrentPermissionByBizTypeFn(
          {
            currentPermission: data.permission,
            targetId: paramsQuery.id,
            targetPermission: value,
            bizType: 1
          },
          () => {
            data.permission = value;
          }
        );
      } catch (error) {
        console.log("error", error);
      }
      return;
    }
    if (data.elementType === ELEMENT_TYPE.DEPARTMENT) {
      params.deptId = data.deptId;
    } else if (data.elementType === ELEMENT_TYPE.GROUP) {
      params.groupId = data.groupId;
    } else {
      params.userId = data.userId;
    }
    updatePermission(data.elementType, params, () => {
      data.permission = value;
    });
  };

  useEffect(() => {
    setDataSource(drawConfig.permissionList);
    fetchAllPrivilegeList();
  }, [drawConfig]);

  return (
    <>
      <div className="border-[1px] border-[#EEEEEE] border-solid h-[50px] box-border rounded-[4px] px-[20px] py-[16px] flex justify-between">
        <div className="text-[14px] font-bold">{subTitle}</div>
        <div className="flex items-center">
          <div className="mr-[16px]">所有人可访问</div>
          <Switch
            size="small"
            value={allUser}
            disabled={!!disabled}
            onChange={allUserChange}
          />
        </div>
      </div>
      <div className="flex justify-between mt-[20px]">
        <div className="text-[16px] font-bold text-text-color1">协作者</div>
        <Button
          icon={
            <img
              src={addSearch}
              width={14}
              height={14}
              className="mt-[4px] mr-[-2px] shrink-0"
            />
          }
          size="small"
          className="text-text-color2 border-[#EEEEEE]"
          onClick={() => {
            setShowModal(true);
          }}
          disabled={!!disabled}
        >
          添加
        </Button>
      </div>
      <div className="mt-[20px] h-[calc(100%-150px)] overflow-x-hidden overflow-y-auto">
        <Table
          columns={columns}
          dataSource={dataSource}
          pagination={false}
          rowKey={(record, index) => {
            return record.id || record.userId || -(index || 0 + 2);
          }}
          onRow={(record) => ({
            onMouseEnter: () => setHoveredRowKey(record.id),
            onMouseLeave: () => setHoveredRowKey(null)
          })}
          loading={loading}
          components={{
            body: {
              cell: ({ children, ...props }: any) => (
                <td {...props} style={{ padding: "10px 12px 10px 10px" }}>
                  {children}
                </td>
              )
            },
            header: {
              cell: ({ children, ...props }: any) => (
                <th
                  {...props}
                  style={{
                    height: "40px",
                    padding: "0 0 5px 10px",
                    background: "#fff",
                    fontSize: "14px",
                    fontWeight: 700,
                    color: "#888888"
                  }}
                >
                  {children}
                </th>
              )
            }
          }}
        />
      </div>
      <ConfigProvider
        modal={{
          styles: {
            header: { margin: 0 },
            body: {},
            mask: {},
            footer: {},
            content: { padding: "20px" }
          }
        }}
      >
        <Modal
          destroyOnClose={true}
          footer={
            <div className="text-right">
              <Button
                type="text"
                onClick={() => setShowModal(false)}
                style={{ border: "1px solid #EBEBEB", marginRight: "16px" }}
                className="text-text-color2"
              >
                取消
              </Button>
              <Button
                type="text"
                onClick={() => {
                  setPrivilegePermission(checkedData, () => {
                    setShowModal(false);
                  });
                }}
                style={{
                  border: "none",
                  color: "#ffffff",
                  background:
                    "linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)"
                }}
                className="text-text-color2"
                loading={btnLoading}
              >
                确定
              </Button>
            </div>
          }
          title={<div className="text-[16px] text-[#000000]">添加用户</div>}
          open={showModal}
          onCancel={() => setShowModal(false)}
          width={700}
          height={520}
          className="viewModal"
        >
          <div className="mt-[20px] border-solid border-[1px] border-[#D9D9D9] h-[338px] rounded-[4px] flex">
            <SelectOrganization
              checkedData={checkedData}
              setCheckedData={setCheckedData}
              open={showModal}
              type={type}
            />
          </div>
        </Modal>
      </ConfigProvider>
    </>
  );
};

export default PermisssonConfig;
