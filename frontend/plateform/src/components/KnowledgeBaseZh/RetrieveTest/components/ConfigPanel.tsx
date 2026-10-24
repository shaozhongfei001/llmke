import React, { useState, useEffect } from "react";
import {
  Form,
  Slider,
  Switch,
  Select,
  Input,
  Tooltip,
  Collapse,
  InputNumber
} from "antd";
import type { FormInstance, CollapseProps } from "antd";
import { QuestionCircleOutlined } from "@ant-design/icons";
import { Settings } from "lucide-react";

const { Panel } = Collapse;
import "./style.css";
interface ConfigPanelProps {
  form: FormInstance;
  visible: boolean;
  enableLLM: boolean;
  sliderValues: {
    textChunks: number;
    topP: number;
    topN: number;
    denseWeight: number;
    temperature: number;
    diversity: number;
    maxTokens: number;
  };
  onSliderChange: (
    field: keyof ConfigPanelProps["sliderValues"],
    value: number
  ) => void;
  onEnableLLMChange: (enabled: boolean) => void;
  onVisibleChange: (visible: boolean) => void;
  modelOptions?: { label: string; value: string }[];
  recallModelOptions?: { label: string; value: string }[];
}

enum RecallStrategy {
  "混合检索" = 1,
  "全文检索",
  "语义检索"
}

export function ConfigPanel({
  form,
  visible,
  enableLLM,
  sliderValues,
  onSliderChange,
  onEnableLLMChange,
  onVisibleChange,
  modelOptions = [],
  recallModelOptions = []
}: ConfigPanelProps) {
  const [activeKey, setActiveKey] = useState<string[]>(
    enableLLM ? ["1", "2"] : ["1"]
  );

  useEffect(() => {
    setActiveKey(enableLLM ? ["1", "2"] : ["1"]);
  }, [enableLLM]);

  const handleLLMSwitch = (checked: boolean) => {
    onEnableLLMChange(checked);
    // activeKey 会由 useEffect 自动同步
  };

  const SettingButton = ({
    visible,
    onClick
  }: {
    visible: boolean;
    onClick: () => void;
  }) => (
    <Tooltip title={visible ? "收起测试配置" : "展开测试配置"}>
      <div
        onClick={onClick}
        className={`w-8 h-8 rounded-lg hover:bg-gray-50 transition-colors flex items-center justify-center cursor-pointer
          ${!visible ? "bg-gray-50 ml-[8.5px] rounded-full shadow" : ""}`}
      >
        <Settings className="w-5 h-5 text-gray-600" />
      </div>
    </Tooltip>
  );

  const retrievalPanel = {
    key: "1",
    label: "检索召回",
    children: (
      <div className="space-y-6">
        <div className="mb-6">
          <Form.Item name="plan_model_name" label="规划模型">
            <Select
              // value={sliderValues.textChunks}
              // onChange={(value) =>
              //   onSliderChange("plan_model_name", value == null ? 1 : value)
              // }
              options={modelOptions}
            />
          </Form.Item>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center text-sm">
              返回文本片数量（top_k）
              <Tooltip title="控制最终检索返回的文本片数量。top_k代表模型最终取信的文本块数，例如门槛top_p = 0.8，top_k = 3，意味着模型会依据相似度高低取前3个大于0.8的文本块，即使当前可能有大于3个文本块的相似度大于0.8；">
                <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
              </Tooltip>
            </div>
            <InputNumber
              min={1}
              max={200}
              value={sliderValues.textChunks}
              onChange={(value) =>
                onSliderChange(
                  "textChunks",
                  value == null ? 1 : (value as number)
                )
              }
              size="small"
              style={{ width: 70, marginLeft: 8 }}
            />
          </div>
          <Form.Item name="textChunks" noStyle>
            <Slider
              min={1}
              max={200}
              value={sliderValues.textChunks}
              onChange={(value) =>
                onSliderChange("textChunks", value == null ? 1 : value)
              }
              styles={{
                track: { backgroundColor: "#1890ff" },
                rail: { backgroundColor: "#e0e0e0" }
              }}
            />
          </Form.Item>
        </div>

        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center text-sm">
              相似度阈值 (score_threshold)
              <Tooltip title="对文本片进行排序时，对于文本块取舍的门槛值">
                <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
              </Tooltip>
            </div>
            <InputNumber
              min={0}
              max={1}
              step={0.01}
              value={sliderValues.topP}
              onChange={(value) =>
                onSliderChange("topP", value == null ? 0.1 : value)
              }
              size="small"
              style={{ width: 70, marginLeft: 8 }}
            />
          </div>
          <Form.Item name="topP" noStyle>
            <Slider
              styles={{
                track: { backgroundColor: "#1890ff" },
                rail: { backgroundColor: "#e0e0e0" }
              }}
              step={0.01}
              min={0}
              max={1}
              value={sliderValues.topP}
              onChange={(value) => onSliderChange("topP", value)}
            />
          </Form.Item>
        </div>

        <div className="flex items-center justify-between py-1">
          <div className="flex items-center text-sm">
            启用图谱增强
            <Tooltip title="是否使用图谱增强召回通路（只有使用了图谱增强解析才能生效)">
              <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
            </Tooltip>
          </div>
          <Form.Item name="enableKG" noStyle>
            <Switch />
          </Form.Item>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center text-sm">
              检索策略
              <Tooltip title="选择系统配置的检索策略">
                <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
              </Tooltip>
            </div>
          </div>
          <Form.Item name="search_policy" noStyle>
            <Select
              placeholder="请选择"
              className="w-full"
              options={Object.entries(RecallStrategy)
                .filter(([k, v]) => !Number.isNaN(Number(v)))
                .map(([label, value]) => ({ label, value }))}
            />
          </Form.Item>
        </div>
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center text-sm">
              Dense Weight
              <Tooltip title="Dense Weight 参数用于控制检索时语义相似程度的重要性权重，越偏向 1 表示越倾向于语义检索，越偏向 0 则表示越偏向于关键词匹配检索。">
                <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
              </Tooltip>
            </div>
            <InputNumber
              min={0}
              max={1}
              step={0.01}
              value={sliderValues.denseWeight}
              onChange={(value) =>
                onSliderChange("denseWeight", value == null ? 0.5 : value)
              }
              size="small"
              style={{ width: 70, marginLeft: 8 }}
            />
          </div>
          <Form.Item name="denseWeight" noStyle>
            <Slider
              styles={{
                track: { backgroundColor: "#1890ff" },
                rail: { backgroundColor: "#e0e0e0" }
              }}
              step={0.01}
              min={0}
              max={1}
              value={sliderValues.denseWeight}
              onChange={(value) => onSliderChange("denseWeight", value)}
            />
          </Form.Item>
        </div>
        {/* <div className="flex items-center justify-between py-1">
          <div className="flex items-center text-sm">
            启用重排模型
            <Tooltip title="控制是否使用reranker模型对检索到的文本片进行重新排序。">
              <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
            </Tooltip>
          </div>
          <Form.Item name="enableRerank" noStyle>
            <Switch />
          </Form.Item>
        </div> */}

        <Form.Item
          shouldUpdate={(prev, curr) => prev.enableRerank !== curr.enableRerank}
        >
          {() =>
            form.getFieldValue("enableRerank") ? (
              <Form.Item
                label={
                  <div className="flex items-center text-sm">
                    选择排序模型
                    <Tooltip title="选择系统配置的reranker模型">
                      <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
                    </Tooltip>
                  </div>
                }
                name="recallModel"
              >
                <Select
                  placeholder="请选择"
                  className="w-full"
                  options={recallModelOptions}
                />
              </Form.Item>
            ) : null
          }
        </Form.Item>

        <Form.Item
          shouldUpdate={(prev, curr) => prev.enableRerank !== curr.enableRerank}
        >
          {() =>
            form.getFieldValue("enableRerank") ? (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center text-sm">
                    召回数量 (top_n)
                    <Tooltip title="召回是指从海量的候选文本片中找出与问题最相关的 K 个文本片的过程。仅在打开了重排模型的时候可设置此项。建议设置召回数量略大于返回文本片数量，可提高检索性能">
                      <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
                    </Tooltip>
                  </div>
                  <InputNumber
                    min={1}
                    max={1000}
                    value={sliderValues.topN}
                    onChange={(value) =>
                      onSliderChange("topN", value == null ? 10 : value)
                    }
                    size="small"
                    style={{ width: 70, marginLeft: 8 }}
                  />
                </div>
                <Form.Item name="topN" noStyle>
                  <Slider
                    styles={{
                      track: { backgroundColor: "#1890ff" },
                      rail: { backgroundColor: "#e0e0e0" }
                    }}
                    min={1}
                    max={1000}
                    value={sliderValues.topN}
                    onChange={(value) => onSliderChange("topN", value)}
                  />
                </Form.Item>
              </div>
            ) : null
          }
        </Form.Item>
      </div>
    )
  };

  const llmPanel = {
    key: "2",
    label: (
      <div
        className="w-full flex items-center"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex-1">大模型问答</div>
        <Switch checked={enableLLM} onChange={handleLLMSwitch} />
      </div>
    ),
    collapsible: enableLLM ? ("header" as const) : ("disabled" as const),
    className: !enableLLM ? "opacity-60" : "",
    children: (
      <div className="space-y-6">
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center text-sm">
              选择问答模型
              <Tooltip title="选择系统配置的大模型">
                <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
              </Tooltip>
            </div>
          </div>
          <Form.Item name="llmModel" noStyle>
            <Select
              placeholder="请选择"
              className="w-full"
              options={modelOptions}
            />
          </Form.Item>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center text-sm">
              温度
              <Tooltip title="温度是模型回答的倾向性，取值范围一般是0～1; 取值趋近0代表着模型回答会更严谨，适合回答检索类问题; 取值趋近1则代表回答更发散，适合回答创新性的问题">
                <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
              </Tooltip>
            </div>
            <InputNumber
              min={0}
              max={1}
              step={0.01}
              value={sliderValues.temperature}
              onChange={(value) =>
                onSliderChange("temperature", value == null ? 0.3 : value)
              }
              size="small"
              style={{ width: 70, marginLeft: 8 }}
            />
          </div>
          <Form.Item name="temperature" noStyle>
            <Slider
              railStyle={{ backgroundColor: "#e0e0e0" }}
              trackStyle={{ backgroundColor: "#1890ff" }}
              step={0.01}
              min={0}
              max={1}
              value={sliderValues.temperature}
              onChange={(value) => onSliderChange("temperature", value)}
            />
          </Form.Item>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center text-sm">
              多样性
              <Tooltip title="限制模型从累计概率大于或等于该值的最小token集合中进行选择。如果设定较低的值，模型将只考虑最有可能的选项，有助于保持生成的确定性；如果设定较高的值，模型将考虑更广泛的选项，有可能产生更有创意的内容。">
                <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
              </Tooltip>
            </div>
            <InputNumber
              min={0}
              max={1}
              step={0.01}
              value={sliderValues.diversity}
              onChange={(value) =>
                onSliderChange("diversity", value == null ? 0.8 : value)
              }
              size="small"
              style={{ width: 70, marginLeft: 8 }}
            />
          </div>
          <Form.Item name="diversity" noStyle>
            <Slider
              railStyle={{ backgroundColor: "#e0e0e0" }}
              trackStyle={{ backgroundColor: "#1890ff" }}
              step={0.01}
              min={0}
              max={1}
              value={sliderValues.diversity}
              onChange={(value) => onSliderChange("diversity", value)}
            />
          </Form.Item>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center text-sm">
              最大令牌数
              <Tooltip title="代表模型窗口大小，即一次问答大模型一次能够接受的token最大长度，包括用户的提问和模型的回答；多轮对话中历史对话内容也包括在内；最大值取决于大模型本身是否支持">
                <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
              </Tooltip>
            </div>
            <InputNumber
              min={0}
              max={16000}
              value={sliderValues.maxTokens}
              onChange={(value) =>
                onSliderChange("maxTokens", value == null ? 4096 : value)
              }
              size="small"
              style={{ width: 90, marginLeft: 8 }}
            />
          </div>
          <Form.Item name="maxTokens" noStyle>
            <Slider
              style={{}}
              railStyle={{ backgroundColor: "#e0e0e0" }}
              trackStyle={{ backgroundColor: "#1890ff" }}
              min={0}
              max={16000}
              value={sliderValues.maxTokens}
              onChange={(value) => onSliderChange("maxTokens", value)}
            />
          </Form.Item>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center text-sm">
              编写 prompt
              <Tooltip title="提示词用于指定聊天的背景和上下文，或者让助手采取某个人格来回答你的问题">
                <QuestionCircleOutlined className="ml-1.5 text-gray-400" />
              </Tooltip>
            </div>
          </div>
          <Form.Item name="prompt" noStyle>
            <Input.TextArea
              rows={4}
              placeholder="XXXXXXX"
              className="resize-none text-sm"
            />
          </Form.Item>
        </div>
      </div>
    )
  };

  // 默认参数
  const defaultValues = {
    textChunks: 10,
    topP: 0.1,
    topN: 10,
    denseWeight: 0.5,
    temperature: 0.3,
    diversity: 0.8,
    maxTokens: 4096,
    enableKG: false,
    enableRerank: true,
    recallModel: recallModelOptions[0]?.value,
    llmModel: modelOptions[0]?.value,
    prompt: "",
    search_policy: RecallStrategy["混合检索"]
  };

  // 恢复默认按钮点击事件
  const handleResetDefault = () => {
    form.setFieldsValue(defaultValues);
    // 只对 sliderValues 字段触发 onSliderChange
    if (onSliderChange) {
      [
        "textChunks",
        "topP",
        "topN",
        "denseWeight",
        "temperature",
        "diversity",
        "maxTokens"
      ].forEach((key) => {
        onSliderChange(
          key as keyof typeof sliderValues,
          (defaultValues as any)[key]
        );
      });
    }
    if (onEnableLLMChange) onEnableLLMChange(false);
  };

  // 保证表单初始值同步 defaultValues
  useEffect(() => {
    form.setFieldsValue(defaultValues);
  }, [form, recallModelOptions, modelOptions]);

  return (
    <div
      className={`group h-full bg-white setting-panel relative overflow-hidden transition-[width] duration-200 ease-in-out ${
        visible
          ? "w-4/12 border-r border-solid border-t-0 border-b-0 border-l-0 border-gray-200 delay-[50ms]"
          : "w-[65px] border-none"
      }`}
    >
      <div
        className={`w-full h-full flex flex-col transition-transform duration-200 ease-in-out ${
          visible ? "translate-x-0 delay-[50ms]" : "-translate-x-[295px]"
        }`}
      >
        <div className="flex-none   px-4 pt-4">
          <div
            className={`text-lg  pb-2  font-bold flex justify-between items-center ${
              visible
                ? "border-b border-t-0 border-l-0 border-r-0 border-solid border-gray-200 "
                : ""
            }`}
          >
            <div className="flex items-center">
              <div className="w-8 flex justify-center">
                <SettingButton
                  visible={visible}
                  onClick={() => onVisibleChange(!visible)}
                />
              </div>
              <span
                className={`ml-2 whitespace-nowrap transition-opacity duration-75 ${
                  visible ? "opacity-100 delay-150 " : "opacity-0"
                }`}
              >
                测试配置
              </span>
            </div>
            <button
              type="button"
              className="ml-4 px-3 py-1 rounded border border-gray-300 cursor-pointer text-xs text-gray-400 hover:text-gray-800 hover:bg-gray-100 transition"
              onClick={handleResetDefault}
            >
              恢复默认
            </button>
          </div>
        </div>

        <div
          className={`flex-1 px-4 pb-4 overflow-y-auto transition-opacity duration-75 ${
            visible ? "opacity-100 delay-150" : "opacity-0"
          }`}
        >
          <div className={visible ? "" : "invisible pointer-events-none"}>
            <Form form={form} layout="vertical">
              <Collapse
                activeKey={activeKey}
                onChange={(key) =>
                  setActiveKey(Array.isArray(key) ? key : [key])
                }
                bordered={false}
                items={[retrievalPanel, llmPanel]}
                className="bg-white [&_.ant-collapse-header]:!flex [&_.ant-collapse-header]:!items-center [&_.ant-collapse-header]:!pr-4 [&_.ant-collapse-header-text]:!flex-1"
              />
            </Form>
          </div>
        </div>
      </div>

      {!visible && (
        <div className="absolute top-4 left-2 transition-opacity duration-75">
          <SettingButton
            visible={visible}
            onClick={() => onVisibleChange(true)}
          />
        </div>
      )}
    </div>
  );
}
