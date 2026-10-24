import {
  Table,
  Button,
  Dropdown,
  Input,
  Select,
  Space,
  Popconfirm,
  Modal,
  Avatar,
  Drawer,
  Descriptions,
  Tooltip
} from "antd";
import {
  PlusOutlined,
  TeamOutlined,
  UserOutlined,
  SearchOutlined,
  DeleteOutlined,
  InfoCircleOutlined
} from "@ant-design/icons";
import { useState, useEffect } from "react";
import { GroupInfo, GroupMember } from "../types";
import { AddMemberModal } from "./AddMemberModal";
import { Building2, Users, User, CalendarClock } from "lucide-react";
import { message } from "antd";
import { useSystemApi } from "@/apis/system";
import Apartment from "@/assets/img/Apartment.png";
import dayjs from "dayjs";
import {
  GRADIENTS,
  getAvatarProps,
  getIconProps,
  getRoundedContainerProps
} from "../../config/gradients";

interface MemberTableProps {
  group: GroupInfo | null;
  frameElements: any[];
  loading: boolean;
  onRefresh?: (groupId: string) => void;
}

export const MemberTable: React.FC<MemberTableProps> = ({
  group,
  frameElements,
  loading,
  onRefresh
}) => {
  const [modalVisible, setModalVisible] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [modalType, setModalType] = useState<"member" | "department">("member");
  const [tableHeight, setTableHeight] = useState<string | undefined>(undefined);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const systemApi = useSystemApi();

  // 计算成员和部门数量
  const memberCount = frameElements.filter(
    (item) => item.elementType !== 1
  ).length;
  const deptCount = frameElements.filter(
    (item) => item.elementType === 1
  ).length;

  console.log("当前选中的分组:", group);

  // 过滤数据
  const filteredData = frameElements.filter((item) => {
    const matchSearch = searchText
      ? (item.elementType === 1
          ? item.name
          : (item.userRealname || "匿名") + (item.userEmail || "")
        )
          ?.toLowerCase()
          .includes(searchText.toLowerCase())
      : true;

    const matchType =
      filterType === "all"
        ? true
        : filterType === "member"
        ? item.elementType !== 1
        : filterType === "department"
        ? item.elementType === 1
        : true;

    return matchSearch && matchType;
  });

  // 计算表格高度
  useEffect(() => {
    // 当数据变化时重新计算高度
    setTableHeight(filteredData.length > 0 ? "calc(100vh - 400px)" : undefined);
  }, [filteredData]);

  // 处理移除操作
  const handleRemove = async (record: any) => {
    if (!group?.id) return;

    try {
      await systemApi.deleteGroupsByIds({
        groupId: group.id,
        userIds:
          record.elementType === 3 || record.elementType === null
            ? [record.id]
            : [], // 如果是成员则传 userIds
        deptIds: record.elementType === 1 ? [record.id] : [] // 如果是部门则传 deptIds
      });

      message.success("移除成功");
      onRefresh?.(group.id);
    } catch (error) {
      console.error("移除失败:", error);
      message.error("移除失败");
    }
  };

  // 处理批量移除
  const handleBatchRemove = async () => {
    if (!group?.id || selectedRowKeys.length === 0) return;

    // 直接从 frameElements 中获取选中的项目
    const selectedItems = frameElements.filter((item) =>
      selectedRowKeys.includes(item.id)
    );
    console.log("选中的项目:", selectedItems);

    const userIds = selectedItems
      .filter((item) => item.elementType === 3 || item.elementType === null)
      .map((item) => item.id); // 成员的 elementType 可能是 3 或 null
    const deptIds = selectedItems
      .filter((item) => item.elementType === 1)
      .map((item) => item.id); // 部门的 elementType 是 1

    console.log("准备发送的数据:", {
      groupId: group.id,
      userIds,
      deptIds
    });

    try {
      await systemApi.deleteGroupsByIds({
        groupId: group.id,
        userIds,
        deptIds
      });

      message.success("批量移除成功");
      setSelectedRowKeys([]);
      onRefresh?.(group.id);
    } catch (error) {
      console.error("批量移除失败:", error);
      message.error("批量移除失败");
    }
  };

  const columns = [
    {
      title: "组内成员或部门",
      dataIndex: "userRealname",
      render: (_: any, record: any) => (
        <div className="flex items-center">
          {record.elementType === 1 ? (
            <Avatar
              icon={<Building2 {...getIconProps()} />}
              {...getAvatarProps("DEPARTMENT")}
            />
          ) : (
            <Avatar
              icon={<UserOutlined {...getIconProps()} />}
              {...getAvatarProps("MEMBER")}
            />
          )}
          <span className="ml-2">
            {record.elementType === 1
              ? record.name
              : record.userRealname || "匿名"}
          </span>
        </div>
      )
    },
    {
      title: "联系邮箱",
      dataIndex: "userEmail",
      render: (_: any, record: any) =>
        record.elementType === 1 ? "_" : record.userEmail || "无"
    },
    {
      title: "所属部门",
      dataIndex: "deptName",
      render: (_: any, record: any) =>
        record.elementType === 1 ? record.name || "_" : record.deptName || "_"
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      // fixed: 'right' as const,
      render: (_: any, record: any) => (
        <div className="flex justify-center items-center gap-x-1">
          <Popconfirm
            title={`确定要移除该${
              record.elementType === 1 ? "部门" : "成员"
            }吗？`}
            onConfirm={() => handleRemove(record)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              移除
            </Button>
          </Popconfirm>
        </div>
      )
    }
  ];

  const addMenuItems = {
    items: [
      {
        key: "member",
        label: "添加成员",
        onClick: () => {
          if (!group?.id) {
            message.warning("请先选择分组");
            return;
          }
          setModalType("member");
          setModalVisible(true);
        }
      },
      {
        key: "department",
        label: "添加部门",
        onClick: () => {
          if (!group?.id) {
            message.warning("请先选择分组");
            return;
          }
          setModalType("department");
          setModalVisible(true);
        }
      }
    ]
  };

  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      console.log("选中的行:", newSelectedRowKeys);
      console.log("当前数据:", filteredData);
      setSelectedRowKeys(newSelectedRowKeys);
    }
  };

  return (
    <>
      <div className="flex justify-between mb-4">
        <div className="flex items-center gap-x-3">
          <h2 className="text-lg font-medium">{group?.name || "未命名分组"}</h2>
          <Tooltip title="成员数包括已添加部门内的成员，当部门发生变化时更新会略有延迟">
            <InfoCircleOutlined className="text-gray-800 cursor-help" />
          </Tooltip>
          <span className="text-gray-500">
            成员人数：{memberCount}，
            <span className="text-primary">部门数量：{deptCount}</span>
          </span>
        </div>
        <div
          className="text-primary cursor-pointer text-primary-color"
          onClick={() => setDrawerVisible(true)}
        >
          显示分组详情
        </div>
      </div>
      <div className="flex justify-between items-center toolbar py-3">
        <Space size="middle">
          <Dropdown menu={addMenuItems} placement="bottomRight">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              style={{
                background: GRADIENTS.BUTTON,
                borderColor: "transparent"
              }}
            >
              添加
            </Button>
          </Dropdown>
          <Input
            placeholder="请输入成员姓名或邮箱"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 200 }}
          />
          <Select
            value={filterType}
            onChange={setFilterType}
            style={{ width: 120 }}
            options={[
              { value: "all", label: "显示所有" },
              { value: "member", label: "只显示成员" },
              { value: "department", label: "只显示部门" }
            ]}
          />
        </Space>
        {selectedRowKeys.length > 0 && (
          <Popconfirm
            title="确定要批量移除选中的项目吗？"
            onConfirm={handleBatchRemove}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="primary"
              danger
              icon={<DeleteOutlined />}
              style={{
                background: GRADIENTS.BUTTON,
                borderColor: "transparent"
              }}
            >
              批量移除 ({selectedRowKeys.length})
            </Button>
          </Popconfirm>
        )}
      </div>
      <Table
        rowSelection={rowSelection}
        columns={columns}
        dataSource={filteredData}
        rowKey="id"
        loading={loading}
        pagination={{
          size: "small",
          pageSize: 7,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
          position: ["bottomRight"]
        }}
        expandable={{ expandIcon: () => null }}
        scroll={{
          y: tableHeight,
          x: "100%"
        }}
      />
      <AddMemberModal
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        groupId={group?.id}
        type={modalType}
        onSuccess={() => {
          onRefresh?.(group?.id as any);
          setModalVisible(false);
        }}
        existingElements={frameElements}
      />
      <Drawer
        title={
          <div className="flex items-center gap-2">
            <div {...getRoundedContainerProps("GROUP")}>
              <Users {...getIconProps()} className="text-white" />
            </div>
            <div>
              <div className="text-base font-medium">{group?.name}</div>
              <div className="text-gray-400 text-xs">分组详情</div>
            </div>
          </div>
        }
        placement="right"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        width={400}
      >
        {group && (
          <div className="space-y-6">
            <div className="flex items-center p-3 rounded-lg bg-gray-50">
              <div className="flex-1">
                <div className="text-gray-400 text-sm">成员数量</div>
                <div className="text-xl font-medium text-[#2B69FF]">
                  {memberCount}
                </div>
              </div>
              <div {...getRoundedContainerProps("MEMBER")}>
                <TeamOutlined {...getIconProps()} className="text-white" />
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div {...getRoundedContainerProps("MEMBER")}>
                  <User {...getIconProps()} className="text-white" />
                </div>
                <div className="flex-1">
                  <div className="text-gray-400 text-sm">创建人</div>
                  <div className="text-sm mt-0.5">{group.createBy || "-"}</div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div {...getRoundedContainerProps("MEMBER")}>
                  <CalendarClock {...getIconProps()} className="text-white" />
                </div>
                <div className="flex-1">
                  <div className="text-gray-400 text-sm">创建时间</div>
                  <div className="text-sm mt-0.5">
                    {group.gmtCreate
                      ? dayjs(group.gmtCreate).format("YYYY-MM-DD HH:mm:ss")
                      : "-"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </>
  );
};
