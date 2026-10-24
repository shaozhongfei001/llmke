import {
  Input,
  Button,
  List,
  Spin,
  Modal,
  message,
  Avatar,
  Space,
  Dropdown,
  Form
} from "antd";
import {
  PlusOutlined,
  SearchOutlined,
  TeamOutlined,
  EditOutlined,
  DeleteOutlined,
  MoreOutlined
} from "@ant-design/icons";
import { Trash } from "lucide-react";
import { useState, useMemo } from "react";
import { GroupInfo } from "../types";
import { GroupModal } from "./GroupModal";
import systemApi from "@/apis/system";
import {
  GRADIENTS,
  getAvatarProps,
  getIconProps
} from "../../config/gradients";

interface GroupListProps {
  loading: boolean;
  groupList: GroupInfo[];
  selectedGroup: GroupInfo | null;
  onSelect: (group: GroupInfo) => void;
  onRefresh: () => void;
  frameElements: any[];
}

export const GroupList: React.FC<GroupListProps> = ({
  loading,
  groupList,
  selectedGroup,
  onSelect,
  onRefresh,
  frameElements
}) => {
  const [searchText, setSearchText] = useState("");
  const [modalVisible, setModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingGroup, setEditingGroup] = useState<GroupInfo | null>(null);
  const [form] = Form.useForm();
  const api = systemApi();

  const filteredGroups = useMemo(() => {
    if (!searchText) return groupList;
    return groupList.filter((group) =>
      group.name.toLowerCase().includes(searchText.toLowerCase())
    );
  }, [groupList, searchText]);

  const handleDelete = async (group: GroupInfo, e: React.MouseEvent) => {
    e.stopPropagation();

    Modal.confirm({
      title: "确认删除",
      content: `确定要删除分组"${group.name}"吗？`,
      okText: "确定",
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.deleteGroup({ id: group.id });
          message.success("删除成功");
          onRefresh();
        } catch (error: any) {
          if (error?.response.data.errorCode === "30026") {
            const userIds = frameElements
              .filter(
                (item) => item.elementType === 3 || item.elementType === null
              )
              .map((item) => item.id);
            const deptIds = frameElements
              .filter((item) => item.elementType === 1)
              .map((item) => item.id);

            Modal.confirm({
              title: "确认删除",
              content: (
                <div>
                  <p>
                    当前机构已关联用户，是否要移除组内所有部门和成员并继续删除？
                  </p>
                  <div className="mt-4 p-3 bg-gray-50 rounded">
                    <table className="w-full">
                      <tbody>
                        <tr>
                          <td className="py-1">部门数量：</td>
                          <td className="text-blue-600">{deptIds.length}</td>
                        </tr>
                        <tr>
                          <td className="py-1">成员数量：</td>
                          <td className="text-blue-600">{userIds.length}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              ),
              okText: "确定",
              cancelText: "取消",
              onOk: async () => {
                try {
                  await api.deleteGroupsByIds({
                    groupId: group.id,
                    userIds,
                    deptIds
                  });
                  await api.deleteGroup({ id: group.id });
                  message.success("删除成功");
                  onRefresh();
                } catch (error) {
                  console.error("删除分组失败:", error);
                  message.error("删除分组失败");
                }
              }
            });
          } else {
            console.error("删除分组失败:", error);
            message.error("删除分组失败");
          }
        }
      }
    });
  };

  const handleEdit = async (values: { name: string }) => {
    if (!editingGroup) return;

    try {
      await api.updateGroup({
        id: editingGroup.id,
        name: values.name,
        status: 1
      });
      message.success("更新成功");
      setEditModalVisible(false);
      onRefresh();
    } catch (error) {
      console.error("更新失败:", error);
      message.error("更新失败");
    }
  };

  const getItemActions = (group: GroupInfo) => {
    return {
      items: [
        {
          key: "edit",
          label: "编辑分组",
          icon: <EditOutlined />,
          onClick: (e: any) => {
            e.domEvent.stopPropagation();
            setEditingGroup(group);
            form.setFieldsValue({ name: group.name });
            setEditModalVisible(true);
          }
        },
        {
          key: "delete",
          label: "删除分组",
          icon: <DeleteOutlined />,
          danger: true,
          onClick: (e: any) => {
            e.domEvent.stopPropagation();
            handleDelete(group, e.domEvent);
          }
        }
      ]
    };
  };

  return (
    <>
      <div className="p-4 h-full flex flex-col">
        <Space direction="vertical" size={16} className="w-full">
          <Input
            placeholder="搜索用户组"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <Button
            type="dashed"
            block
            icon={<PlusOutlined />}
            onClick={() => setModalVisible(true)}
            style={{
              background: GRADIENTS.BUTTON,
              borderColor: "transparent",
              color: "#fff"
            }}
          >
            创建分组
          </Button>
        </Space>
        <div className="flex-1 overflow-auto mt-4">
          <Spin spinning={loading}>
            {filteredGroups.map((group) => (
              <div
                key={group.id}
                className={`h-[43px] rounded-[4px] px-[20px] flex items-center cursor-pointer group ${
                  selectedGroup?.id === group.id
                    ? "bg-[#F3F6FF] text-primary-color"
                    : "hover:bg-[#F3F6FF]"
                }`}
                onClick={() => onSelect(group)}
              >
                <Avatar
                  icon={<TeamOutlined {...getIconProps()} />}
                  {...getAvatarProps("GROUP")}
                />
                <div className="flex-1 truncate" title={group.name}>
                  {group.name}
                </div>
                <Dropdown
                  menu={getItemActions(group)}
                  placement="bottomRight"
                  trigger={["click"]}
                >
                  <Button
                    type="text"
                    size="small"
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                    icon={<MoreOutlined />}
                    onClick={(e) => e.stopPropagation()}
                  />
                </Dropdown>
              </div>
            ))}
          </Spin>
        </div>
        <GroupModal
          visible={modalVisible}
          onClose={() => setModalVisible(false)}
          onSuccess={(newGroup) => {
            onRefresh();
            setModalVisible(false);
            onSelect(newGroup);
          }}
        />
      </div>

      {/* 编辑弹窗 */}
      <Modal
        title="编辑分组"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} onFinish={handleEdit} layout="vertical">
          <Form.Item
            name="name"
            label="分组名称"
            rules={[{ required: true, message: "请输入分组名称" }]}
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};
