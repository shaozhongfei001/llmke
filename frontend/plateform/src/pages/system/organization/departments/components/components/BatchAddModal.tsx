import {
  Modal,
  message,
  Tree,
  Spin,
  Card,
  Input,
  Avatar,
  Form,
  Input as AntInput
} from "antd";
import {
  DeleteOutlined,
  UserOutlined,
  EditOutlined,
} from "@ant-design/icons";
import { useState, useEffect, useCallback, useRef } from "react";
import systemApi from "@/apis/system";
import type { DataNode } from "antd/es/tree";
import { Building2 } from "lucide-react";
import {
  GRADIENTS,
  getAvatarProps,
  getIconProps
} from "../../../config/gradients";
const { TextArea } = Input;
interface AddMemberModalProps {
  visible: boolean;
  onClose: () => void;
  onSave: any;
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

export const BatchAddModal: React.FC<AddMemberModalProps> = ({
  visible,
  onClose,
  onSave
}) => {
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [treeData, setTreeData] = useState<any[]>([]);
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [searchValue, setSearchValue] = useState("");
  const [feature, setFeaturee] = useState('');
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
          {
            item.elementType === 3 ? (
              <Avatar
                icon={<UserOutlined {...getIconProps()} />}
                {...getAvatarProps("MEMBER")}
              />
            ) : (
              <Avatar
                icon={<Building2 {...getIconProps()} />}
                {...getAvatarProps("DEPARTMENT")}
              />
            )
          }
          <span>{item.elementType === 3? (item.userRealname || item.userName) :item.name}</span>
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
      const response:any = await api.getTreeFrame({},{});
        if (response.data) {
          const treeData = transformDepartmentData(response.data);
          setTreeData(treeData);
          if (expandedKeys.length === 0) {
            setExpandedKeys(getAllKeys(treeData));
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
      setFeaturee('');
      setLoading(false);
      setConfirmLoading(false);
      isFirstRender.current = true;
    }
  }, [visible]);
  
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

      setSelectedKeys(checkedKeys);
      updateSelectedItems(checkedKeys);
    },
    [treeData, updateSelectedItems]
  );

  // 搜索过滤函数
  const filterTreeNode = useCallback(
    (node: any) => {
      if (!searchValue) return false;
      const nodeTitle =
        node.elementType === 1 ? node.name : (node.userRealname || node.userName);


      return nodeTitle.toLowerCase().includes(searchValue.toLowerCase())
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

  useEffect(()=>{
    console.log('selectedKeys',selectedKeys);
    console.log('selectedItems',selectedItems);
  },[selectedKeys])

  const handleOk = async () => {
    if (!feature) {
      message.warning(`请输入用户特征`);
      return;
    }

    const userIds = selectedItems.filter((item) => item.elementType === 3).map((item) => item.id);
    if (userIds.length === 0) {
      message.warning(`请选择用户`);
      return;
    }

    try {
      setConfirmLoading(true)
      const res:any = await api.batchUpdateUserFeature({
        userIds,
        feature
      },{})
      setConfirmLoading(false)
      if(res.success){
        onSave()
        message.success("保存成功");
        onClose();
      }
    } catch (error) {
      setConfirmLoading(false)
      console.error("保存失败:", error);
      message.error("保存失败");
    }
  };

  return (
    <>
      <Modal
        title='批量新增特征'
        open={visible}
        onCancel={onClose}
        onOk={handleOk}
        width={800}
        destroyOnClose
        confirmLoading={confirmLoading}
        okButtonProps={{
          style: {
            background: GRADIENTS.BUTTON,
            borderColor: "transparent",
            border: "none",
          }
        }}
        cancelButtonProps={{
          style: {
            background: "transparent",
            borderColor: "#d9d9d9",
            color: "#555",
          }
        }}
      >
        <div className="flex gap-4">
          <Card
            className="flex-1 h-[500px]"
            bodyStyle={{ padding: "12px", height: "100%" }}
          >
            <div className="h-full overflow-auto flex flex-col">
              <div className="mb-3">
                <Input.Search
                  placeholder={`搜索名称`}
                  allowClear
                  onChange={(e) => handleSearch(e.target.value)}
                  className="w-full"
                />
              </div>
              <div className="flex-1 overflow-auto py-[16px]">
                <Spin spinning={loading}>
                  <Tree
                    checkable
                    expandedKeys={expandedKeys}
                    onExpand={handleExpand}
                    treeData={treeData}
                    checkedKeys={selectedKeys}
                    onCheck={handleCheck}
                    showLine
                    filterTreeNode={filterTreeNode}
                    selectable={false}
                  />
                </Spin>
              </div>
            </div>
          </Card>

          <Card
            title={
              <div className="flex items-center justify-between">
                <span>输入特征：</span>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500">
                    共{" "}
                    <span className="text-[#2B69FF]">
                      {selectedItems.length}
                    </span>{" "}
                    项
                  </span>
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
              <TextArea showCount value={feature} maxLength={1000} onChange={(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>)=>{setFeaturee(e.target.value)}} style={{height: 'calc(100% - 30px)', resize: 'none'}}/>
            </div>
          </Card>
        </div>
      </Modal>
    </>
  );
};
