import React, { useState, useEffect, useMemo } from "react";
import { uid } from "uid";
import { QuestionCircleOutlined, CloseCircleFilled } from "@ant-design/icons";
import {
  Button,
  InputNumber,
  Tooltip,
  Slider,
  Select,
  Form,
  Flex,
  Modal,
  notification
} from "antd";
import type { NotificationArgsProps } from "antd";
import IdentifyTag from "./IdentifyTag";
import NotFoundContent from "./NotFoundContent";
import "@/assets/styles/knowledgebaseNew.less";
const { useForm } = Form;
const { confirm } = Modal;
enum StrategyType {
  INTELLIGENT = "intelligent",
  NAIVE = "naive",
  FINANCIAL = "financial"
}
interface IdentifyTagItem {
  label?: string;
  value: string;
  id: string;
  pos: "before" | "after";
}

const showModelReplace =
  import.meta.env.VITE_CONFIG_SHOW_MODEL_REPLACE === "true";

const ParseConfig = ({
  btnLoading,
  save,
  disabled,
  kbInfo,
  embeddingModelsOption,
  multiModelsOption,
  modelsOption,
  platform="rag-qa"
}: any) => {
  const [form] = useForm();

  const [chunkStrategy, setChunkStrategy]: any = useState(
    StrategyType.INTELLIGENT
  );
  const [chunkSize, setChunkSize]: any = useState(500);
  const [chunkOverlap, setChunkOverlap]: any = useState(0);
  const [identifyList, setIdentifyList] = useState<IdentifyTagItem[]>([]);

  const [api, contextHolder] = notification.useNotification({
    top: 0
  });

  const openNotification = (msg: string) => {
    api.info({
      message: `保存失败`,
      description: msg,
      placement: "topRight",
      icon: <CloseCircleFilled style={{ color: "#FF4D4F" }} />
    });
  };

  useEffect(() => {
    if (kbInfo) {
      initData();
      initFormData();
      form.validateFields([
        "embeddingModelName",
        "modelName",
        "multiModelName"
      ]);
    } else {
      if (
        Array.isArray(embeddingModelsOption) &&
        embeddingModelsOption?.length == 0
      ) {
        form.validateFields(["embeddingModelName"]);
      }

      if (Array.isArray(modelsOption) && modelsOption?.length == 0) {
        form.validateFields(["modelName"]);
      }
      if (Array.isArray(multiModelsOption) && multiModelsOption?.length == 0) {
        form.validateFields(["multiModelName"]);
      }
    }
  }, [kbInfo, embeddingModelsOption, modelsOption, multiModelsOption, form]);

  useEffect(() => {}, [
    embeddingModelsOption,
    modelsOption,
    multiModelsOption,
    form
  ]);

  const initData = () => {
    const { fileType, chunkSize, chunkOverlap, splitRegex } = kbInfo;
    fileType && setChunkStrategy(fileType);

    setChunkOverlap(chunkOverlap || 0);
    setChunkSize(chunkSize || 500);

    const regex = splitRegex && JSON.parse(splitRegex);
    if (regex && Array.isArray(regex)) {
      const result = regex
        .map((str) => {
          // 匹配括号内内容
          const match = str.match(/\((\?<=|\?=)([^)]+)\)/);

          if (!match) return null;
          const [, prefix, value] = match;
          console.log(match, prefix === "?<=", value, "+++");
          return {
            value,
            pos: prefix === "?<=" ? "after" : "before",
            id: uid(4)
          };
        })
        .filter(Boolean);
      setIdentifyList(result);
    } else {
      setIdentifyList([]);
    }
  };

  const initFormData = () => {
    const { embeddingModelName, modelName, multiModelName } = kbInfo;
    form.setFieldsValue({
      embeddingModelName,
      modelName,
      multiModelName
    });
  };

  const handleRegex = () => {
    const regexs = identifyList.map((i: any) => {
      return `(${i.pos == "before" ? "?=" : "?<="}${i.value})`;
    });
    return JSON.stringify(regexs);
  };

  const selectStrategy = (type: StrategyType) => {
    initData();
    if (type !== kbInfo.fileType) {
      setChunkSize(500);
    }
    setChunkStrategy(type);
  };

  const handleSaveData = async () => {
    const formData = await form.validateFields();
    let data: any = {
      fileType: chunkStrategy,
      kbConfigType: 1,
      ...formData
    };

    if (
      showModelReplace &&
      data.embeddingModelName !== kbInfo.embeddingModelName
    ) {
      confirm({
        title: "保存确认",
        content: (
          <div style={{ marginRight: "20px" }}>
            您修改嵌入模型后，当前知识库已解析的文档将重新进入排队解析状态，未解析完成之前的文档不可用于问答，您是否确定修改?
          </div>
        ),
        okText: "确认",
        cancelText: "取消",
        async onOk() {
          saveData(data);
        }
      });
    } else {
      saveData(data);
    }
  };

  const saveData = (data: any) => {
    if (chunkStrategy == StrategyType.INTELLIGENT) {
      data = {
        ...data,
        chunkSize
      };
    }

    if (chunkStrategy == StrategyType.FINANCIAL) {
      data = {
        ...data,
        chunkSize
      };
    }

    if (chunkStrategy == StrategyType.NAIVE) {
      if (chunkOverlap >= chunkSize) {
        openNotification("分段重叠长度设置必须小于最大分段长度");
        return;
      }
      if (identifyList.length > 50) {
        openNotification("分段标识符不得超过50个");
        return;
      }
      const regex = handleRegex();

      data = {
        ...data,
        chunkOverlap,
        chunkSize,
        splitRegex: regex
      };
    }
    save({
      ...data
    });
  };
  return (
    <div className="w-[840px] h-fit bg-[#fff] px-[62px] py-[32px] mt-[32px]">
      <div
        className="w-full pb-[20px]"
        style={{
          borderBottom: "1px solid #EEEEEE"
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="embeddingModelName"
            rules={[
              {
                required: true,
                validator(_: any, value: any) {
                  const options = embeddingModelsOption || [];
                  if (!value) {
                    if (Array.isArray(options) && options.length === 0) {
                      return Promise.reject("暂无可用模型，请联系管理员");
                    } else {
                      return Promise.reject("请选择嵌入模型");
                    }
                  }
                  if (
                    (Array.isArray(options) && options.length === 0) ||
                    !options.find((m: any) => m.value == value)
                  ) {
                    return Promise.reject("模型无法使用，请联系管理员");
                  }
                  return Promise.resolve();
                }
              }
            ]}
            label={
              <Tooltip title="用于嵌入块的嵌入模型，一旦更改，整个知识库要重新构建索引。">
                <span className="mx-[4px]">嵌入模型</span>
                <QuestionCircleOutlined className="text-[#888888] hover:text-[#055AFF]" />
              </Tooltip>
            }
          >
            <Select
              style={{ width: "100%" }}
              disabled={disabled}
              notFoundContent={<NotFoundContent />}
              options={embeddingModelsOption}
            />
          </Form.Item>
          <Form.Item
            name="modelName"
            label="摘要模型"
            rules={[
              {
                required: true,
                validator(_: any, value: any) {
                  const options = modelsOption || [];
                  if (!value) {
                    if (Array.isArray(options) && options.length === 0) {
                      return Promise.reject("暂无可用模型，请联系管理员");
                    } else {
                      return Promise.reject("请选择摘要模型");
                    }
                  }
                  if (
                    (Array.isArray(options) && options.length === 0) ||
                    !options.find((m: any) => m.value == value)
                  ) {
                    return Promise.reject("模型无法使用，请联系管理员");
                  }
                  return Promise.resolve();
                }
              }
            ]}
          >
            <Select
              style={{ width: "100%" }}
              disabled={disabled}
              options={modelsOption}
              notFoundContent={<NotFoundContent />}
            />
          </Form.Item>
          <Form.Item
            name="multiModelName"
            label="多模态模型"
            rules={[
              {
                required: true,
                validator(_: any, value: any) {
                  const options = multiModelsOption || [];
                  console.log("mu=====", multiModelsOption);
                  if (!value) {
                    if (Array.isArray(options) && options.length === 0) {
                      return Promise.reject("暂无可用模型，请联系管理员");
                    } else {
                      return Promise.reject("请选择多模态模型");
                    }
                  }
                  if (
                    (Array.isArray(options) && options.length === 0) ||
                    !options.find((m: any) => m.value == value)
                  ) {
                    return Promise.reject("模型无法使用，请联系管理员");
                  }
                  return Promise.resolve();
                }
              }
            ]}
          >
            <Select
              style={{ width: "100%" }}
              disabled={disabled}
              notFoundContent={<NotFoundContent />}
              options={multiModelsOption}
            />
          </Form.Item>
        </Form>
        <div className="mb-[10px] mt-[20px]">
          <b className="text-[#f83117]">*</b>
          <span className="mx-[4px]">切片策略</span>
        </div>

        <Flex justify="space-between" className="gap-4">
          <div
            className="p-[10px] rounded-md"
            style={{
              border:
                chunkStrategy == StrategyType.INTELLIGENT
                  ? "1px solid #055AFF"
                  : "1px solid #D9D9D9",
              backgroundColor:
                chunkStrategy == StrategyType.INTELLIGENT ? "#F4F5F7" : ""
            }}
            onClick={() => selectStrategy(StrategyType.INTELLIGENT)}
          >
            <div
              className={`font-bold text-[${
                chunkStrategy == StrategyType.INTELLIGENT
                  ? "#055AFF"
                  : "#555555"
              }]`}
            >
              智能切分
            </div>
            <div className="text-[#888888] mt-[6px]">
              在通用文档上的最优chunk切分方法，经过评测可在多数文档上获得最佳的检索效果
            </div>
          </div>
          {platform !== "rag-qa" && <div
            className="p-[10px] rounded-md"
            style={{
              border:
                chunkStrategy == StrategyType.FINANCIAL
                  ? "1px solid #055AFF"
                  : "1px solid #D9D9D9",
              backgroundColor:
                chunkStrategy == StrategyType.FINANCIAL ? "#F4F5F7" : ""
            }}
            onClick={() => selectStrategy(StrategyType.FINANCIAL)}
          >
            <div
              className={`font-bold text-[${
                chunkStrategy == StrategyType.FINANCIAL
                  ? "#055AFF"
                  : "#555555"
              }]`}
            >
              金融专用切片
            </div>
            <div className="text-[#888888] mt-[6px]">
              针对企业年报、财务报告等文档进行专项优化的切分方法，更适合金融场景
            </div>
          </div>}
          <div
            className="p-[10px] rounded-md"
            style={{
              border:
                chunkStrategy == StrategyType.NAIVE
                  ? "1px solid #055AFF"
                  : "1px solid #D9D9D9",
              backgroundColor:
                chunkStrategy == StrategyType.NAIVE ? "#F4F5F7" : ""
            }}
            onClick={() => selectStrategy(StrategyType.NAIVE)}
          >
            <div
              className={`font-bold text-[${
                chunkStrategy == StrategyType.NAIVE ? "#055AFF" : "#555555"
              }]`}
            >
              自定义切片
            </div>
            <div className="text-[#888888] mt-[6px]">
              完全开放的chunk切分配置，按照实际文档情况自由配置，通过调试获得更好的检索效果
            </div>
          </div>
        </Flex>
        {chunkStrategy == StrategyType.NAIVE && (
          <div className="gap-4">
            <div className="mb-[10px] mt-[20px]">
              <span>
                分段标识符<span className="text-[#888888]">（可拖拽排序）</span>
              </span>
              <Tooltip title="支持自定义文本分隔符，提供个性化的解析结果，分段标识符前后顺序决定执行顺序，可通过拖拽调整执行顺序">
                <QuestionCircleOutlined className="text-[#888888] hover:text-[#055AFF]" />
              </Tooltip>
            </div>

            <IdentifyTag
              identifyList={identifyList}
              setIdentifyList={setIdentifyList}
              disabled={disabled}
            />
          </div>
        )}

        <Flex justify="space-between" className="gap-4 mt-[20px]">
          <div>
            <div className="mb-[10px]">
              <span className="mx-[4px]">最大分段长度</span>
            </div>
            <div className="flex">
              <Slider
                disabled={disabled}
                style={{ width: "220px", marginTop: "8px" }}
                min={1}
                max={4000}
                styles={{
                  rail: { backgroundColor: "#d9d9d9", height: 4 },
                  track: { backgroundColor: "#2468f2", height: 4 }
                }}
                onChange={(value) => {
                  setChunkSize(value);
                }}
                value={typeof chunkSize === "number" ? chunkSize : 0}
              />

              <InputNumber
                disabled={disabled}
                min={1}
                max={4000}
                precision={0}
                step={1}
                className="h-[32px] ml-[16px]"
                value={chunkSize}
                onChange={(value) => {
                  setChunkSize(value || 500);
                }}
              />
            </div>
          </div>
          {chunkStrategy == StrategyType.NAIVE && (
            <div>
              <div className="mb-[10px]">
                <span className="mx-[4px]">分段重叠长度</span>
                <Tooltip title="当前分片与上一个分片重叠的文本长度">
                  <QuestionCircleOutlined className="text-[#888888] hover:text-[#055AFF]" />
                </Tooltip>
              </div>
              <div className="flex">
                <Slider
                  disabled={disabled}
                  style={{ width: "220px" }}
                  min={0}
                  max={1000}
                  styles={{
                    rail: {
                      backgroundColor: "linear-gradient(90deg,#075BFF,#AC96FF)",
                      height: 4
                    },
                    handle: {
                      color: "red"
                    },
                    track: { backgroundColor: "#2468f2", height: 4 }
                  }}
                  onChange={(value) => {
                    setChunkOverlap(value);
                  }}
                  value={typeof chunkOverlap === "number" ? chunkOverlap : 0}
                />
                <InputNumber
                  disabled={disabled}
                  min={0}
                  max={1000}
                  precision={0}
                  step={1}
                  className="h-[32px] ml-[16px]"
                  value={chunkOverlap}
                  onChange={(value) => {
                    setChunkOverlap(value || 0);
                  }}
                />
              </div>
            </div>
          )}
        </Flex>
      </div>
      <div className="h-[72px] flex items-center justify-end">
        {/* <Context.Provider value={contextValue}> */}
        {contextHolder}
        <Button
          type="primary"
          style={{
            background: "linear-gradient(90deg,#075BFF,#AC96FF)",
            width: "76px",
            border: "none"
          }}
          disabled={disabled}
          loading={btnLoading}
          onClick={handleSaveData}
        >
          保存
        </Button>
        {/* </Context.Provider> */}
      </div>
    </div>
  );
};
export default ParseConfig;
