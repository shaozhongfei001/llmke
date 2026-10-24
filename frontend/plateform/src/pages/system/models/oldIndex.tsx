import { useState, useEffect } from "react";
import {
  Button,
  Table,
  Drawer,
  Space,
  message,
  Spin,
  Badge,
  Tooltip,
  Modal,
  Form,
  ConfigProvider
} from "antd";
import {
  PlusOutlined,
  ExclamationCircleOutlined,
  CloseOutlined
} from "@ant-design/icons";
import SystemContainer from "../SystemContainer";
import { ModelItem, Collaborator, DrawerType } from "./types";
import ModelForm, { MODEL_TYPE_OPTIONS } from "./ModelForm";
import AuthModelForm from "./AuthModelForm";
import PermisssonConfig, {
  TypeDrawConfig
} from "../../Components/PermissionConfig";
import { api_allModelPage } from "./service";
import { set } from "lodash";
import modelApi from "@/apis/system";
import type { ModelInfoDTO } from "@/apis/system/data-contracts";
import { render } from "mermaid/dist/rendering-util/render.js";
import {
  FILE_BTN,
  getBtnDisabled,
  PERMISSION_RULES,
  PERMISSION_STATUS,
  PERMISSION_WARNING_MSG
} from "@root/src/const/permission";
import CustomTooltip from "@root/src/components/CustomTooltip";

export default function ModelsPage() {
  const api = modelApi();
  const [models, setModels] = useState<ModelItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [drawerType, setDrawerType] = useState<DrawerType>("add");
  const [currentModel, setCurrentModel] = useState<ModelItem | null>(null);
  const [form] = Form.useForm(); // 创建表单引用
  const [drawConfig, setDrawConfig] = useState<TypeDrawConfig>({
    type: "create"
  });
  // 模拟协作者数据
  const [collaborators, setCollaborators] = useState<Collaborator[]>([
    { id: "all", name: "所有人", role: "可浏览", permission: "可浏览" },
    { id: "user1", name: "张一", role: "部门经理", permission: "可管理" }
  ]);

  // =================== API对接点2: 获取协作者列表 ===================
  // TODO: 添加获取协作者列表的API请求

  // GET /api/collaborators
  // 返回的数据格式应与Collaborator接口一致
  // 请求参数: 无
  // 响应格式: Collaborator[]

  // =================== API对接点1: 获取模型列表 ===================

  const fetchModelList = async () => {
    setLoading(true);

    try {
      const response = await api.getAllModelList({
        pageNum: 1,
        pageSize: 1000
      });

      if (response?.data) {
        setModels((response.data.records as any) || []);
        setLoading(false);
      }
    } catch (error) {
      setLoading(false);
    }
  };
  // 在组件加载时获取数据
  useEffect(() => {
    fetchModelList();
  }, []);

  const handleAdd = () => {
    setDrawerType("add");
    setCurrentModel(null);
    setDrawerVisible(true);
  };

  const handleEdit = (record: ModelItem) => {
    setDrawerType("edit");
    setCurrentModel(record);
    setDrawerVisible(true);
  };

  const handleAuth = async (record: ModelItem) => {
    setDrawerType("auth");
    setCurrentModel(record);
    setDrawConfig((pre: any) => {
      return { ...pre, type: "permission", data: record };
    });
    setDrawerVisible(true);
  };

  const handleDelete = (record: ModelItem) => {
    Modal.confirm({
      title: "确认删除",
      icon: <ExclamationCircleOutlined />,
      content: `确定要删除模型"${record.modelName}"吗？此操作不可恢复。`,
      okText: "确认",
      cancelText: "取消",
      onOk: async () => {
        try {
          // =================== API对接点3: 删除模型 ===================
          // TODO: 替换为实际的API请求
          // DELETE /api/models/{id}
          // 请求参数: 模型ID (record.id)
          // 响应格式: { success: boolean, message: string }

          const res: any = await api.deleteModel({ id: record.id });
          if (res?.success) {
            message.success(`已删除模型: ${record.modelName}`);
            fetchModelList();
          }
        } catch (error) {
          message.error("删除模型失败");
          console.error("删除模型失败:", error);
        }
      }
    });
  };

  const closeDrawer = () => {
    setDrawerVisible(false);
  };
  const [btnLoading, setBtnLoading] = useState(false);
  const handleSubmit = async (values?: any) => {
    console.log("提交的表单数据:", values);
    setBtnLoading(true);
    try {
      if (drawerType === "add") {
        const res: any = await api.createModel(values);
        setBtnLoading(false);
        if (res?.success) {
          fetchModelList();
        }
        // =================== API对接点4: 创建模型 ===================
        // TODO: 替换为实际的API请求
        // POST /api/models
        // 请求参数: values (包含表单中的所有字段)
        // 响应格式: { success: boolean, data: ModelItem, message: string }

        // 模拟成功创建并更新列表
        // const response = await api.post('/api/models', values);
        // 如果后端返回了完整的模型数据，应该使用它更新列表
        // setModels([...models, response.data]);
      } else if (drawerType === "edit") {
        const res: any = await api.updateModel({
          ...values,
          id: currentModel?.id
        });
        setBtnLoading(false);
        if (res?.success) {
          fetchModelList();
        }
        // =================== API对接点5: 更新模型 ===================
        // TODO: 替换为实际的API请求
        // PUT /api/models/{id}
        // 请求参数: values (包含表单中的所有字段，包括id)
        // 响应格式: { success: boolean, data: ModelItem, message: string }

        // 模拟成功更新并刷新列表
        // const response = await api.put(`/api/models/${values.id}`, values);
        // 如果后端返回了完整的模型数据，应该使用它更新列表
        // setModels(models.map(item => item.id === values.id ? response.data : item));
      } else if (drawerType === "auth") {
        setBtnLoading(false);
        // =================== API对接点6: 更新模型授权 ===================
        // TODO: 替换为实际的API请求
        // PUT /api/models/{id}/auth
        // 请求参数: { id: string, isVisibleToAll: boolean, collaborators: Collaborator[] }
        // 响应格式: { success: boolean, message: string }

        // 模拟成功更新授权
        // const modelId = currentModel?.id;
        // await api.put(`/api/models/${modelId}/auth`, {
        //   isVisibleToAll: values.isVisibleToAll,
        //   collaborators: values.collaborators
        // });

        message.success("已更新授权设置");
      }

      // 关闭抽屉
      setDrawerVisible(false);

      // =================== API对接点7: 刷新模型列表 ===================
      // TODO: 在成功提交数据后刷新列表
      // 可以选择重新调用fetchModels函数，或者根据操作类型手动更新models状态
      // 例如:
      // if(shouldRefreshList) {
      //   const response = await api.get('/api/models');
      //   setModels(response.data);
      // }
    } catch (error) {
      setBtnLoading(false);
    }
  };

  const columns = [
    {
      title: "模型名称",
      dataIndex: "modelName",
      key: "modelName",
      width: "15%"
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      width: 110,
      render: (type: string) => {
        return MODEL_TYPE_OPTIONS.find((item: any) => item.value === type)
          ?.label;
      }
    },
    {
      title: "说明",
      dataIndex: "dec",
      key: "dec",
      ellipsis: true // 文本过长时自动省略
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: "18%",
      render: (status: number, record: any) => {
        if (status === 1) {
          return (
            <Tooltip title={record.errorMsg}>
              <Badge status="success" text="可用" />
            </Tooltip>
          );
        } else {
          return (
            <Tooltip title={record.errorMsg}>
              <Badge status="error" text="不可用" />
            </Tooltip>
          );
        }
      }
    },
    {
      title: "操作",
      key: "action",
      width: "20%",
      render: (_: any, record: ModelItem) => (
        <div className="flex space-x-0">
          <CustomTooltip
            content={
              getBtnDisabled(FILE_BTN.EDIT, record.permission)
                ? PERMISSION_WARNING_MSG
                : ""
            }
            type="warning"
            position="top"
          >
            <Button
              type="link"
              className="px-1 py-0 text-blue-500 min-w-0"
              onClick={() => handleEdit(record)}
              disabled={getBtnDisabled(FILE_BTN.EDIT, record.permission)}
            >
              编辑
            </Button>
          </CustomTooltip>
          <CustomTooltip
            content={
              getBtnDisabled(FILE_BTN.AUTHORIZE, record.permission)
                ? PERMISSION_WARNING_MSG
                : ""
            }
            type="warning"
            position="top"
          >
            <Button
              type="link"
              className="px-1 py-0 text-blue-500 min-w-0"
              onClick={() => handleAuth(record)}
              disabled={getBtnDisabled(FILE_BTN.AUTHORIZE, record.permission)}
            >
              授权
            </Button>
          </CustomTooltip>{" "}
          <CustomTooltip
            content={
              getBtnDisabled(FILE_BTN.DELETE, record.permission)
                ? PERMISSION_WARNING_MSG
                : ""
            }
            type="warning"
            position="top"
          >
            <Button
              type="link"
              className="px-1 py-0 text-blue-500 min-w-0"
              onClick={() => handleDelete(record)}
              disabled={getBtnDisabled(FILE_BTN.DELETE, record.permission)}
            >
              删除
            </Button>
          </CustomTooltip>
        </div>
      )
    }
  ];

  // 根据抽屉类型渲染对应的内容
  const renderDrawerContent = (drawerVisible: boolean) => {
    switch (drawerType) {
      case "add":
        return (
          <div className="h-[calc(100vh-100px)] relative px-[20px] pt-[10px] pb-[20px]">
            <ModelForm
              model={null}
              onSubmit={handleSubmit}
              form={form}
              type="add"
              drawerVisible={drawerVisible}
            />
          </div>
        );
      case "edit":
        return (
          <div className="h-[calc(100vh-100px)] relative px-[20px] pt-[10px] pb-[20px]">
            <ModelForm
              model={currentModel}
              onSubmit={handleSubmit}
              form={form}
              type="edit"
            />
          </div>
        );
      case "auth":
        return (
          <div className="h-[calc(100vh-120px)] relative px-[20px] pt-[10px] pb-[20px]">
            <PermisssonConfig
              drawConfig={drawConfig}
              subTitle="模型公开范围"
              bizType={3}
              type="modelRight"
            />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <SystemContainer title="模型管理" description="">
      <div className="p-4">
        <div className="mb-4">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAdd}
            className="bg-gradient-to-r from-[#2B69FF] to-[#8F91FF] hover:from-[#2B69FF] hover:to-[#8F91FF] border-none shadow-md"
          >
            新建
          </Button>
        </div>

        {/* {models.length > 0 ? (
          <Table
            columns={columns}
            dataSource={models}
            rowKey="id"
            pagination={{ pageSize: 5 }}
            loading={loading}
          />
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <div className="text-6xl mb-4">📋</div>
            <p>暂无模型数据</p>
            <p className="text-sm">您可以点击"新建"按钮添加模型</p>
          </div>
        )} */}

        <Table
          columns={columns}
          dataSource={models}
          rowKey="id"
          pagination={{ pageSize: 5 }}
          loading={loading}
        />
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
              <div className="font-normal flex justify-between items-center">
                <div>
                  {drawerType === "add"
                    ? "新建"
                    : drawerType === "edit"
                      ? "编辑"
                      : "授权"}
                </div>
                <div>
                  <CloseOutlined onClick={closeDrawer} />
                </div>
              </div>
            }
            placement="right"
            onClose={closeDrawer}
            open={drawerVisible}
            width={557}
            destroyOnClose
            footer={
              drawerType === "auth" ? (
                false
              ) : (
                <div className="flex justify-end space-x-2">
                  <Button onClick={closeDrawer}>取消</Button>
                  <Button
                    type="primary"
                    className="bg-indigo-600 hover:bg-indigo-700 border-none"
                    onClick={async () => {
                      // 直接使用form引用提交表单
                      form.validateFields().then((values) => {
                        handleSubmit(values);
                      });
                    }}
                    loading={btnLoading}
                  >
                    确认
                  </Button>
                </div>
              )
            }
            closable={false}
          >
            <div className="w-full flex flex-col h-full overflow-hidden">
              <div className="overflow-y-auto pb-4 overflow-x-hidden h-full">
                {renderDrawerContent(drawerVisible)}
              </div>
            </div>
          </Drawer>
        </ConfigProvider>
      </div>
    </SystemContainer>
  );
}
