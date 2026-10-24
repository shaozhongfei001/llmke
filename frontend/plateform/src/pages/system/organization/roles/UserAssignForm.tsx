import React, { useState, useEffect, useMemo } from "react";
import { Modal, Table, Input, Empty, Button, message, Tag } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { RoleData } from "./types";
import { useSystemApi } from "@/apis/system";
import type { UserInfo } from "@/apis/system/data-contracts";

interface UserAssignFormProps {
  visible: boolean;
  onCancel: () => void;
  currentRole: RoleData;
  onAssignUsers: (userIds: string[]) => void;
}

const UserAssignForm: React.FC<UserAssignFormProps> = ({
  visible,
  onCancel,
  currentRole,
  onAssignUsers
}) => {
  const [allUsers, setAllUsers] = useState<UserInfo[]>([]);
  const [selectedUserKeys, setSelectedUserKeys] = useState<string[]>([]);
  const [searchText, setSearchText] = useState("");
  const [loading, setLoading] = useState(false);
  const systemApi = useSystemApi();

  // 获取用户列表
  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await systemApi.searchUserList({
        pageSize: 10000,
        pageNo: 1
      });
      // 过滤掉已经拥有当前角色的用户
      const filteredUsers = response.data.records.filter((user) => {
        return !user.roles?.some((role) => role.id === currentRole.id);
      });

      setAllUsers(filteredUsers);
    } catch (error) {
      message.error("获取用户列表失败");
      console.error("获取用户列表失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 只在弹窗打开时获取一次数据
  useEffect(() => {
    if (visible) {
      fetchUsers();
    }
  }, [visible]);

  // 前端搜索过滤
  const filteredUsers = useMemo(() => {
    if (!searchText) return allUsers;

    const searchLower = searchText.toLowerCase();
    return allUsers.filter(
      (user) =>
        user.userName?.toLowerCase().includes(searchLower) ||
        user.userEmail?.toLowerCase().includes(searchLower) ||
        user.userRealname?.toLowerCase().includes(searchLower)
    );
  }, [allUsers, searchText]);

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const handleAssignUsers = async () => {
    if (selectedUserKeys.length === 0) return;

    try {
      onAssignUsers(selectedUserKeys);
      setSelectedUserKeys([]);
      onCancel();
    } catch (error) {
      console.error("分配用户失败:", error);
      message.error("分配用户失败");
    }
  };

  const columns = [
    {
      title: "用户ID",
      dataIndex: "id",
      key: "id",
      width: 80
    },
    {
      title: "用户名",
      dataIndex: "userRealname",
      key: "userName",
      render: (text: string) => text || "-"
    },
    {
      title: "电子邮箱",
      dataIndex: "userEmail",
      key: "userEmail",
      render: (text: string) => text || "-"
    },
    {
      title: "已有角色",
      dataIndex: "roles",
      key: "roles",
      render: (roles: UserInfo["roles"]) => (
        <div className="flex flex-wrap gap-1">
          {roles?.map((role) => (
            <Tag
              key={role.id}
              color={"blue"}
              // color={role.status === 1 ? 'blue' : 'default'}
            >
              {role.name}
            </Tag>
          )) || "-"}
        </div>
      )
    }
  ];

  const rowSelection = {
    selectedRowKeys: selectedUserKeys,
    onChange: (keys: React.Key[]) => {
      setSelectedUserKeys(keys as string[]);
    }
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          添加用户到 <Tag color="blue">{currentRole?.name}</Tag>
        </div>
      }
      open={visible}
      onCancel={onCancel}
      width={800}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button
          key="submit"
          type="primary"
          disabled={selectedUserKeys.length === 0}
          onClick={handleAssignUsers}
          className="bg-gradient-to-r mt-3 from-indigo-500 to-blue-500 hover:from-indigo-600 hover:to-blue-600 border-none shadow-md"
        >
          确认添加
        </Button>
      ]}
      className="rounded-lg"
    >
      <div className="mb-4">
        <Input
          placeholder="搜索用户（用户名/邮箱）"
          prefix={<SearchOutlined />}
          onChange={(e) => handleSearch(e.target.value)}
          allowClear
          value={searchText}
        />
      </div>

      <Table
        rowSelection={rowSelection}
        columns={columns}
        dataSource={filteredUsers}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: 10,
          showQuickJumper: true,
          size: "small",
          showTotal: (total) => `共 ${total} 条`,
          showSizeChanger: false
        }}
        size="small"
        scroll={{ y: 400 }}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="暂无可分配用户"
            />
          )
        }}
      />
    </Modal>
  );
};

export default UserAssignForm;
