import "@/assets/styles/knowledgebase.less";
import {
  message,
  Popconfirm,
  Switch,
  Table,
  TableColumnsType,
  Select,
  Button,
} from "antd";
import { useState, useMemo } from "react";
import {
  deleteUserPermission,
  updateUserPermission,
  setUserPermission,
} from "./service";

interface DataType {
  key: React.Key;
  userName: string;
  edit?: boolean;
}

interface ExpandTableI {
  className: string;
  loading: boolean;
  [key: string]: any;
}

const UserTable = (props: ExpandTableI) => {
  const {
    className,
    loading,
    users,
    fetchUsers,
    setUsers,
    userList,
    targetId,
  } = props;
  const [switchLoading, setSwitchLoading] = useState(-1);
  const [userId, setUserId] = useState("");
  const [permission, setPermission] = useState(false);

  const userListOptions = useMemo(() => {
    return (userList || []).filter(
      (item: any) =>
        !users.map((g: any) => g.userId).includes(Number(item.value))
    );
  }, [users]);

  const deleteUserPermissionById = async (id: string) => {
    try {
      const res = await deleteUserPermission(id);
      if (res) {
        message.success("删除成功");
        fetchUsers();
      } else {
        message.error("删除失败");
      }
    } catch (e) {
      console.log("e", e);
    }
  };

  const columns: TableColumnsType<DataType> = [
    {
      title: "用户",
      dataIndex: "userName",
      key: "userName",
      render: (_, record) => {
        return record.edit ? (
          getEditRowRender("userName")
        ) : (
          <>{record.userName}</>
        );
      },
    },
    {
      title: "编辑权限",
      width: 120,
      key: "permission",
      render: (_, record: any, index) => {
        return record.edit ? (
          getEditRowRender("permission")
        ) : (
          <Switch
            checked={record.permission === 2}
            loading={index === switchLoading}
            onChange={async (checked: boolean) => {
              try {
                setSwitchLoading(index);
                const res = await updateUserPermission({
                  userId: _.userId,
                  permission: checked ? 2 : 1,
                  bizType: 1,
                  targetId,
                });
                setSwitchLoading(-1);
                if (res) {
                  record.permission = checked ? 2 : 1;
                  setUsers([...users]);
                  message.success("修改权限成功!");
                }
              } catch (e) {
                setSwitchLoading(-1);
                console.log("e---------->", e);
              }
            }}
          />
        );
      },
    },
    {
      title: "操作",
      key: "action",
      width: 80,
      render: (_, record: any) =>
        record.edit ? (
          getEditRowRender("action")
        ) : (
          <Popconfirm
            title="删除权限"
            description="确认删除该用户权限吗？"
            okText="确认"
            cancelText="取消"
            onConfirm={() => deleteUserPermissionById(record.id)}
          >
            <span className="del-btn">删除</span>
          </Popconfirm>
        ),
    },
  ];

  const permissionOnChange = (checked: boolean) => {
    setPermission(checked);
  };

  const userIdOnChange = (value: string) => {
    setUserId(value);
  };

  const cancleCreate = () => {
    setUsers(users.slice(1, users.length));
  };

  const addUser = async () => {
    const res = await setUserPermission({
      userIds: [userId],
      permission: permission === true ? 2 : 1,
      bizType: 1,
      targetId,
    });
    if (res) {
      message.success("添加权限成功!");
      fetchUsers();
    }
  };

  const getEditRowRender = (key: string) => {
    switch (key) {
      case "userName":
        return (
          <Select
            style={{ width: "250px" }}
            showSearch
            placeholder="请选择"
            optionFilterProp="label"
            // mode="multiple"
            options={userListOptions}
            onChange={userIdOnChange}
          />
        );
      case "permission":
        return <Switch onChange={permissionOnChange} />;
      case "action":
        return (
          <div className="create-action-cell">
            <Button type="link" onClick={cancleCreate}>
              取消
            </Button>
            <Button type="link" disabled={!userId} onClick={addUser}>
              保存
            </Button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <Table
      className={`${className}`}
      columns={columns}
      dataSource={users}
      pagination={false}
      loading={loading}
      rowKey={(record: any) => record.id || record.key}
    />
  );
};

export default UserTable;
