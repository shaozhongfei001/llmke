import {
  Modal,
  Table,
  message,
  Tree,
  Spin,
  Card,
  Empty,
  Button,
  Input,
  Avatar,
  Dropdown,
  Form,
  Input as AntInput
} from "antd";
import {
  DeleteOutlined,
  UserOutlined,
  EditOutlined,
  MoreOutlined
} from "@ant-design/icons";
import { useState, useEffect, useCallback, useRef } from "react";
import systemApi from "@/apis/system";
import type { DataNode } from "antd/es/tree";
import type { DepartmentTreeDTO } from "@/apis/system/data-contracts";
import { RequestParams } from "@root/src/apis/system/http-client";
import { Building2 } from "lucide-react";
import {
  GRADIENTS,
  getAvatarProps,
  getIconProps
} from "../../config/gradients";

interface AddMemberModalProps {
  visible: boolean;
  onClose: () => void;
  groupId?: string;
  onSuccess?: () => void;
  type: "member" | "department";
  existingElements?: any[];
}

interface TreeNodeData {
  id: string | number;
  name: string | null;
  elementType: number;
  userCount: number;
  parentId: number | null;
  parentDeptName: string | null;
  userName: string | null;
  userRealname: string | null;
  url: string | null;
  userEmail: string | null;
  empNo: string | null;
  deptName: string | null;
  children?: TreeNodeData[] | null;
}

type AntTreeNode = DataNode & {
  children?: AntTreeNode[];
  checkable?: boolean;
  selectable?: boolean;
};

interface TreeNode extends Omit<TreeNodeData, "children">, AntTreeNode {
  children?: TreeNode[];
}

export const AddMemberModal: React.FC<AddMemberModalProps> = ({
  visible,
  onClose,
  groupId,
  onSuccess,
  type,
  existingElements = []
}) => {
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [treeData, setTreeData] = useState<any[]>([]);
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [searchValue, setSearchValue] = useState("");
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<TreeNode | null>(null);
  const [form] = Form.useForm();
  const api = systemApi();
  const isFirstRender = useRef(true);

  const getAllKeys = useCallback((nodes: TreeNode[]): string[] => {
    let keys: string[] = [];
    nodes.forEach((node) => {
      keys.push(String(node.key));
      if (node.children) {
        keys = keys.concat(getAllKeys(node.children));
      }
    });
    return keys;
  }, []);

  const transformMemberData = useCallback((data: any[]): any[] => {
    return data.map((item) => {
      const memberTitle =
        item.elementType === 3 ? (
          <div className="flex items-center gap-2">
            <Avatar
              icon={<UserOutlined {...getIconProps()} />}
              {...getAvatarProps("MEMBER")}
            />
            {item.userRealname ? (
              <span>
                {item.userRealname} (
                <span style={{ fontSize: "0.875em", opacity: 0.7 }}>
                  账号: {item.userName}
                </span>
                )
              </span>
            ) : (
              <span>
                匿名 (
                <span style={{ fontSize: "0.875em", opacity: 0.7 }}>
                  账号: {item.userName}
                </span>
                )
              </span>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Avatar
              icon={<Building2 {...getIconProps()} />}
              {...getAvatarProps("DEPARTMENT")}
            />
            <span>{item.name}</span>
          </div>
        );

      return {
        ...item,
        title: memberTitle,
        key: String(item.id),
        children: item.children
          ? transformMemberData(item.children)
          : undefined,
        isLeaf: item.elementType === 3,
        checkable: item.elementType === 3,
        selectable: false
      };
    });
  }, []);

  const transformDepartmentData = useCallback((data: any[]): any[] => {
    return data.map((item) => ({
      ...item,
      title: (
        <div className="flex items-center gap-2">
          <Avatar
            icon={<Building2 {...getIconProps()} />}
            {...getAvatarProps("DEPARTMENT")}
          />
          <span>{item.name}</span>
        </div>
      ),
      key: String(item.id),
      children:
        item.children && item.children.length > 0
          ? transformDepartmentData(item.children)
          : undefined,
      checkable: true,
      selectable: false
    }));
  }, []);

  // 获取树形数据
  const fetchTreeData = async () => {
    try {
      setLoading(true);
      if (type === "department") {
        const response = await api.getDepartmentTree();
        if (response.data) {
          const treeData = transformDepartmentData(response.data);
          setTreeData(treeData);
          if (expandedKeys.length === 0) {
            setExpandedKeys(getAllKeys(treeData));
          }
        }
      } else {
        const response = await api.getTreeFrame({}, {});
        if (response.data) {
          const data = Array.isArray(response.data)
            ? response.data
            : [response.data];
          const treeData = transformMemberData(data);
          console.log("获取到的树形数据:", treeData);
          setTreeData(treeData);
          if (expandedKeys.length === 0) {
            setExpandedKeys(getAllKeys(treeData));
          }
        }
      }
    } catch (error) {
      console.error("获取树形数据失败:", error);
      message.error("获取树形数据失败");
    } finally {
      setLoading(false);
    }
  };

  // 更新选中的项目列表
  const updateSelectedItems = useCallback(
    (keys: string[]) => {
      if (!treeData.length) return;

      const findItem = (tree: any[], key: string): any | undefined => {
        for (const node of tree) {
          if (String(node.key) === key) return node;
          if (node.children) {
            const found = findItem(node.children, key);
            if (found) return found;
          }
        }
        return undefined;
      };

      const selected = keys
        .map((key) => {
          const item = findItem(treeData, key);
          return item;
        })
        .filter(Boolean);

      setSelectedItems(selected);
    },
    [treeData]
  );

  // 获取所有匹配节点的父节点 keys
  const getMatchedParentKeys = useCallback(
    (
      nodes: TreeNode[],
      searchText: string,
      targetKeys: string[] = []
    ): string[] => {
      let keys: string[] = [];
      nodes.forEach((node) => {
        const nodeTitle =
          node.elementType === 3 ? node.userName || "" : node.name || "";
        const nodeRealname =
          node.elementType === 3 ? node.userRealname || "" : node.name || "";
        if (
          searchText &&
          (nodeTitle.toLowerCase().includes(searchText.toLowerCase()) ||
            nodeRealname.toLowerCase().includes(searchText.toLowerCase()))
        ) {
          keys = keys.concat(String(node.key));
        }
        if (targetKeys.length > 0 && targetKeys.includes(String(node.key))) {
          keys = keys.concat(String(node.key));
        }
        if (node.children) {
          const childKeys = getMatchedParentKeys(
            node.children,
            searchText,
            targetKeys
          );
          if (childKeys.length > 0) {
            keys = keys.concat(String(node.key), childKeys);
          }
        }
      });
      return Array.from(new Set(keys));
    },
    []
  );

  // 初始化已选数据
  useEffect(() => {
    if (!visible) return;

    // 当树形数据加载完成后，初始化已选成员
    if (treeData.length > 0 && existingElements?.length > 0) {
      console.log("初始化已选数据:", {
        existingElements,
        type,
        treeData
      });

      const newSelectedKeys = existingElements
        .filter((item) => {
          if (type === "member") {
            // 兼容 elementType 为 null 或 3 的情况
            return item.elementType === 3 || item.elementType === null;
          }
          return item.elementType === 1;
        })
        .map((item) => String(item.id));

      console.log("选中的 keys:", newSelectedKeys);

      // 设置选中的节点
      setSelectedKeys(newSelectedKeys);

      // 找到并设置选中项的详细信息
      const findSelectedItems = (
        tree: TreeNode[],
        keys: string[]
      ): TreeNode[] => {
        const items: TreeNode[] = [];
        const findItem = (nodes: TreeNode[]) => {
          nodes.forEach((node) => {
            if (keys.includes(String(node.key))) {
              items.push(node);
            }
            if (node.children) {
              findItem(node.children);
            }
          });
        };
        findItem(tree);
        return items;
      };

      const selectedNodes = findSelectedItems(treeData, newSelectedKeys);
      console.log("选中的节点:", selectedNodes);
      setSelectedItems(selectedNodes);

      // 展开包含已选节点的父节点
      const parentKeys = getMatchedParentKeys(treeData, "", newSelectedKeys);
      console.log("展开的父节点:", parentKeys);
      setExpandedKeys(parentKeys);
    }
  }, [visible, treeData, existingElements, type, getMatchedParentKeys]);

  // Modal 显示/隐藏处理
  useEffect(() => {
    if (visible && isFirstRender.current) {
      isFirstRender.current = false;
      fetchTreeData();
    }
    if (!visible) {
      // Modal 关闭时重置状态
      setTreeData([]);
      setSelectedKeys([]);
      setSelectedItems([]);
      setExpandedKeys([]);
      setSearchValue("");
      isFirstRender.current = true;
    }
  }, [visible]);

  const handleRemoveItem = useCallback(
    (key: string) => {
      setSelectedKeys((prev) => {
        const newKeys = prev.filter((k) => k !== key);
        updateSelectedItems(newKeys);
        return newKeys;
      });
    },
    [updateSelectedItems]
  );

  const handleExpand = useCallback((keys: any[]) => {
    setExpandedKeys(keys.map(String));
  }, []);

  const handleCheck = useCallback(
    (checked: any) => {
      const checkedKeys = Array.isArray(checked)
        ? checked
        : checked.checked || [];

      const findNodeInTree = (
        key: string,
        tree: TreeNode[]
      ): TreeNode | null => {
        for (const node of tree) {
          if (node.key === key) {
            return node;
          }
          if (node.children) {
            const found = findNodeInTree(key, node.children);
            if (found) {
              return found;
            }
          }
        }
        return null;
      };

      // 根据类型使用不同的选择逻辑
      const validKeys =
        type === "member"
          ? checkedKeys.filter((key: string) => {
              const node = findNodeInTree(key, treeData);
              return node?.elementType === 3 || node?.elementType === null;
            })
          : checkedKeys; // 部门模式下不需要过滤

      setSelectedKeys(validKeys);
      updateSelectedItems(validKeys);
    },
    [treeData, updateSelectedItems, type]
  );

  // 搜索过滤函数
  const filterTreeNode = useCallback(
    (node: any) => {
      if (!searchValue) return false;
      const nodeTitle =
        node.elementType === 3 ? node.userName || "" : node.name || "";

      const nodeRealname =
        node.elementType === 3 ? node.userRealname || "" : node.name || "";

      return (
        nodeTitle.toLowerCase().includes(searchValue.toLowerCase()) ||
        nodeRealname.toLowerCase().includes(searchValue.toLowerCase())
      );
    },
    [searchValue]
  );

  // 处理搜索
  const handleSearch = useCallback(
    (value: string) => {
      const searchText = value.trim();
      setSearchValue(searchText);

      if (searchText) {
        // 获取匹配节点的父节点 keys
        const matchedParentKeys = getMatchedParentKeys(treeData, searchText);
        setExpandedKeys(matchedParentKeys);
      } else {
        // 清空搜索时恢复原始展开状态
        setExpandedKeys([]);
      }
    },
    [treeData, getMatchedParentKeys]
  );

  const handleOk = async () => {
    if (!groupId || selectedKeys.length === 0) {
      message.warning(`请选择需要添加的${type === "member" ? "成员" : "部门"}`);
      return;
    }

    try {
      if (type === "department") {
        await api.editGroupDepartments([
          {
            groupId: groupId,
            deptIds: selectedKeys
          }
        ]);
        message.success("添加部门成功");
      } else {
        await api.editGroupUsers([
          {
            groupId: groupId,
            userIds: selectedKeys
          }
        ]);
        message.success("添加成员成功");
      }

      onSuccess?.();
      onClose();
    } catch (error) {
      console.error("添加失败:", error);
      message.error("添加失败");
    }
  };

  const handleEdit = async (values: { name: string }) => {
    if (!editingItem) return;

    try {
      await api.updateGroup({
        id: String(editingItem.key),
        name: values.name,
        status: 1 // 1表示正常状态
      });
      message.success("更新成功");
      setEditModalVisible(false);
      onSuccess?.();
    } catch (error) {
      console.error("更新失败:", error);
      message.error("更新失败");
    }
  };

  const getItemActions = (item: TreeNode) => {
    return {
      items: [
        {
          key: "edit",
          label: "编辑",
          icon: <EditOutlined />,
          onClick: () => {
            setEditingItem(item);
            form.setFieldsValue({ name: item.name });
            setEditModalVisible(true);
          }
        },
        {
          key: "delete",
          label: "删除",
          icon: <DeleteOutlined />,
          danger: true,
          onClick: () => handleRemoveItem(item.key as string)
        }
      ]
    };
  };

  return (
    <>
      <Modal
        title={type === "member" ? "添加成员" : "添加部门"}
        open={visible}
        onCancel={onClose}
        onOk={handleOk}
        width={800}
        destroyOnClose
        okButtonProps={{
          style: {
            background: GRADIENTS.BUTTON,
            borderColor: "transparent"
          }
        }}
      >
        <div className="flex gap-4">
          {/* 左侧树 */}
          <Card
            className="flex-1 h-[500px]"
            bodyStyle={{ padding: "12px", height: "100%" }}
          >
            <div className="h-full overflow-auto flex flex-col">
              <div className="mb-3">
                <Input.Search
                  placeholder={`搜索${type === "member" ? "成员" : "部门"}名称`}
                  allowClear
                  onChange={(e) => handleSearch(e.target.value)}
                  className="w-full"
                />
              </div>
              <div className="flex-1 overflow-auto">
                <Spin spinning={loading} className="min-h-[100px]">
                  <Tree
                    checkable
                    expandedKeys={expandedKeys}
                    onExpand={handleExpand}
                    treeData={treeData}
                    checkedKeys={selectedKeys}
                    onCheck={handleCheck}
                    showLine
                    checkStrictly={type === "member"}
                    filterTreeNode={filterTreeNode}
                    selectable={false}
                  />
                </Spin>
              </div>
            </div>
          </Card>

          {/* 右侧已选列表 */}
          <Card
            title={
              <div className="flex items-center justify-between">
                <span>已选{type === "member" ? "成员" : "部门"}</span>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500">
                    共{" "}
                    <span className="text-[#2B69FF]">
                      {selectedItems.length}
                    </span>{" "}
                    项
                  </span>
                  {selectedItems.length > 0 && (
                    <Button
                      type="link"
                      size="small"
                      className="!px-0"
                      onClick={() => {
                        setSelectedKeys([]);
                        setSelectedItems([]);
                      }}
                    >
                      清空
                    </Button>
                  )}
                </div>
              </div>
            }
            className="w-[300px] h-[500px]"
            bodyStyle={{
              padding: "12px",
              height: "calc(100% - 57px)",
              display: "flex",
              flexDirection: "column"
            }}
          >
            <div className="flex-1 overflow-y-auto pr-1">
              {selectedItems.length > 0 ? (
                <div className="flex flex-col gap-2">
                  {selectedItems.map((item) => (
                    <div
                      key={item.key}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
                    >
                      <div className="flex items-center gap-2">
                        {type === "member" ? (
                          <Avatar
                            icon={<UserOutlined {...getIconProps()} />}
                            {...getAvatarProps("MEMBER")}
                          />
                        ) : (
                          <Avatar
                            icon={<Building2 {...getIconProps()} />}
                            {...getAvatarProps("DEPARTMENT")}
                          />
                        )}
                        <span className="text-sm">
                          {type === "member" ? (
                            <span>
                              {item.userRealname ? (
                                <span>
                                  {item.userRealname} (
                                  <span
                                    style={{
                                      fontSize: "0.875em",
                                      opacity: 0.7
                                    }}
                                  >
                                    账号: {item.userName}
                                  </span>
                                  )
                                </span>
                              ) : (
                                <span>
                                  匿名 (
                                  <span
                                    style={{
                                      fontSize: "0.875em",
                                      opacity: 0.7
                                    }}
                                  >
                                    账号: {item.userName}
                                  </span>
                                  )
                                </span>
                              )}
                            </span>
                          ) : (
                            item.name
                          )}
                        </span>
                      </div>
                      <Dropdown
                        menu={getItemActions(item)}
                        placement="bottomRight"
                        trigger={["click"]}
                      >
                        <Button
                          type="text"
                          size="small"
                          className="opacity-0 group-hover:opacity-100 transition-opacity"
                          icon={<MoreOutlined />}
                        />
                      </Dropdown>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty
                  description={`暂未选择${type === "member" ? "成员" : "部门"}`}
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  className="mt-8"
                />
              )}
            </div>
          </Card>
        </div>
      </Modal>

      {/* 编辑弹窗 */}
      <Modal
        title="编辑信息"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} onFinish={handleEdit} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: "请输入名称" }]}
          >
            <AntInput />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};
