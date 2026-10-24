import React, { useEffect, useState } from "react";
import { Form, Input, Select, Typography, Switch } from "antd";
import { ModelItem } from "./types";

const { TextArea } = Input;
const { Text } = Typography;

interface ModelFormProps {
  model: ModelItem | null;
  onSubmit?: (values: any) => void;
  form?: any;
  type?: "add" | "edit";
  drawerVisible?: boolean;
}

export const MODEL_TYPE_OPTIONS = [
  { value: 1, label: "Baichuan" },
  { value: 2, label: "Qwen" },
  { value: 3, label: "GLM" },
  { value: 4, label: "Xinference" }
];

const ModelForm: React.FC<ModelFormProps> = ({
  model,
  onSubmit,
  form: externalForm,
  type = "edit",
  drawerVisible
}) => {
  const [form] = Form.useForm(externalForm);
  const [value, setValue]: any = useState("");
  // 当model变化时重置表单
  useEffect(() => {
    if (model && type === "edit") {
      setValue(model.type);
      form.setFieldsValue({
        modelName: model.modelName,
        modelIde: model.modelIde,
        apiKey: model.apiKey,
        url: model.url,
        type: model.type,
        dec: model.dec,
        thinking: model.thinking,
        trace: model.trace
      });
    }
  }, [model, form, type]);

  // 处理表单提交
  const handleFinish = (values: any) => {
    if (onSubmit) {
      onSubmit(values);
    }
  };

  // 如果是编辑模式但没有模型数据，显示错误信息
  if (type === "edit" && !model) {
    return <div className="p-4 text-red-500">无效的模型数据</div>;
  }

  useEffect(() => {
    if (drawerVisible && !model) {
      form.resetFields();
    }
  }, [drawerVisible]);

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleFinish}
      className="w-full pr-1"
    >
      <Form.Item
        label={
          <>
            <Text className="text-sm">模型名称</Text>
            {/* <Text className="text-red-500"> *</Text> */}
          </>
        }
        name="modelName"
        rules={[{ required: true, message: "请输入模型名称" }]}
      >
        <Input
          placeholder="请输入模型名称"
          className="hover:border-gray-300 focus:border-blue-400 focus:outline-none transition-colors"
        />
      </Form.Item>

      <Form.Item
        label={
          <>
            <Text className="text-sm">模型ID</Text>
            {/* <Text className="text-red-500"> *</Text> */}
          </>
        }
        name="modelIde"
        rules={[{ required: true, message: "请输入模型ID" }]}
      >
        <Input
          placeholder="请输入模型ID"
          className="hover:border-gray-300 focus:border-blue-400 focus:outline-none transition-colors"
        />
      </Form.Item>

      <Form.Item
        label={
          <>
            <Text className="text-sm">APIKey</Text>
            {/* <Text className="text-red-500"> *</Text> */}
          </>
        }
        name="apiKey"
        // rules={value === 4 ? [] : [{ required: true, message: "请输入APIKey" }]}
      >
        <Input
          placeholder="请输入APIKey"
          className="hover:border-gray-300 focus:border-blue-400 focus:outline-none transition-colors"
        />
      </Form.Item>

      <Form.Item
        label={
          <>
            <Text className="text-sm">请求URL</Text>
            {/* <Text className="text-red-500"> *</Text> */}
          </>
        }
        name="url"
        rules={[{ required: true, message: "请输入请求URL" }]}
      >
        <Input
          placeholder="请输入URL"
          className="hover:border-gray-300 focus:border-blue-400 focus:outline-none transition-colors"
        />
      </Form.Item>

      <Form.Item
        label={
          <>
            <Text className="text-sm">类型</Text>
            {/* <Text className="text-red-500"> *</Text> */}
          </>
        }
        name="type"
        rules={[{ required: true, message: "请选择类型" }]}
      >
        <Select
          placeholder="请选择类型"
          className="hover:border-gray-300 focus:border-blue-400 focus:outline-none transition-colors"
          options={MODEL_TYPE_OPTIONS}
          value={value}
          onChange={(v) => {
            setValue(v);
          }}
        />
      </Form.Item>

      {/* 新增：推理思考和溯源策略 */}
      <div style={{ display: "flex", gap: 64 }}>
        <Form.Item
          name="thinking"
          valuePropName="checked"
          // getValueFromEvent={(checked) => (checked ? 1 : 0)}
          initialValue={false}
          layout="horizontal"
          label={<Text className="text-sm"> 是否支持推理思考</Text>}
        >
          <Switch />
        </Form.Item>
        <Form.Item
          name="trace"
          valuePropName="checked"
          // getValueFromEvent={(checked) => (checked ? 1 : 0)}
          layout="horizontal"
          initialValue={false}
          label={<Text className="text-sm"> 是否支持溯源策略</Text>}
        >
          <Switch />
        </Form.Item>
      </div>

      <Form.Item label={<Text className="text-sm">说明</Text>} name="dec">
        <TextArea
          placeholder="请输入说明"
          rows={4}
          className="hover:border-gray-300 focus:border-blue-400 focus:outline-none transition-colors"
        />
      </Form.Item>
    </Form>
  );
};

export default ModelForm;
