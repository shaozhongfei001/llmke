import { useEffect, useState } from "react";
import { QuestionCircleOutlined } from "@ant-design/icons";
import { Button, Form, InputNumber, Tooltip, Slider, Select } from "antd";
import NotFoundContent from "./NotFoundContent";
import "@/assets/styles/knowledgebaseNew.less";
const { useForm } = Form;

const FAQConfig = ({
  btnLoading,
  save,
  disabled,
  kbInfo,
  modelsOption
}: any) => {
  const [form] = useForm();

  const [similarQuestionMaxNums, setSimilarQuestionMaxNums]: any = useState(1);
  const [fileFaqMaxNums, setFileFaqMaxNums]: any = useState();

  useEffect(() => {
    if (kbInfo) {
      const { fileType, faqModelName } = kbInfo;
      form.setFieldsValue({
        faqModelName
      });
      if (Array.isArray(modelsOption) && modelsOption?.length == 0) {
        form.validateFields(["faqModelName"]);
      }

      if (fileType) {
        const f = !kbInfo.fileFaqMaxNums ? Infinity : kbInfo.fileFaqMaxNums;
        const s = !kbInfo.similarQuestionMaxNums
          ? 1
          : kbInfo.similarQuestionMaxNums;
        setFileFaqMaxNums(f);
        setSimilarQuestionMaxNums(s);
      } else {
        setFileFaqMaxNums(Infinity);
      }
    } else {
      setFileFaqMaxNums(Infinity);
    }
  }, [kbInfo]);
  return (
    <div className="w-[640px] h-[280px] bg-[#fff] px-[62px] py-[32px] mt-[32px]">
      <div
        className="w-full pb-[20px]"
        style={{
          borderBottom: "1px solid #EEEEEE"
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="faqModelName"
            label="抽取模型"
            rules={[
              {
                required: true,
                validator(_: any, value: any) {
                  const options = modelsOption || [];
                  if (!value) {
                    if (Array.isArray(options) && options.length === 0) {
                      return Promise.reject("暂无可用模型，请联系管理员");
                    } else {
                      return Promise.reject("请选择抽取模型");
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
        </Form>
        <div className="label-wrap">
          <span>单篇文档问答对抽取数量上限</span>
        </div>
        <div className="flex">
          <div className="l mr-[8px]">
            <Slider
              disabled={disabled}
              style={{ width: "400px" }}
              min={1}
              max={1001}
              styles={{
                rail: { backgroundColor: "#d9d9d9", height: 4 },
                track: { backgroundColor: "#2468f2", height: 4 }
              }}
              onChange={(value) => {
                setFileFaqMaxNums(value);
              }}
              value={typeof fileFaqMaxNums === "number" ? fileFaqMaxNums : 0}
              tooltip={{
                formatter: (value) => {
                  return value == 1001 ? "无限大" : value;
                }
              }}
            />
          </div>
          <div className="r">
            <InputNumber
              disabled={disabled}
              min={1}
              max={1001}
              value={fileFaqMaxNums}
              formatter={(value) => {
                return value == 1001 ||
                  value === Infinity ||
                  value === "Infinity"
                  ? "无限大"
                  : value;
              }}
              onChange={(value) => {
                setFileFaqMaxNums(value);
              }}
            />
          </div>
        </div>
        <div className="label-wrap mt-[12px]">
          <span className="mx-[4px]">生成相似问个数</span>
          <Tooltip title="使用大模型自动生成相似问">
            <QuestionCircleOutlined className="text-[#888888] hover:text-[#055AFF]" />
          </Tooltip>
        </div>
        <div className="flex">
          <div className="l mr-[8px]">
            <Slider
              disabled={disabled}
              style={{ width: "400px" }}
              min={1}
              max={3}
              styles={{
                rail: { backgroundColor: "#d9d9d9", height: 4 },
                track: { backgroundColor: "#2468f2", height: 4 }
              }}
              onChange={(value) => {
                setSimilarQuestionMaxNums(value);
              }}
              value={
                typeof similarQuestionMaxNums === "number"
                  ? similarQuestionMaxNums
                  : 0
              }
            />
          </div>
          <div className="r">
            <InputNumber
              disabled={disabled}
              min={1}
              max={3}
              value={similarQuestionMaxNums}
              onChange={(value) => {
                setSimilarQuestionMaxNums(value);
              }}
            />
          </div>
        </div>
      </div>
      <div className="h-[72px] flex items-center justify-end">
        <Button
          type="primary"
          style={{
            background: "linear-gradient(90deg,#075BFF,#AC96FF)",
            width: "76px",
            border: "none"
          }}
          disabled={disabled}
          loading={btnLoading}
          onClick={async () => {
            const formData = await form.validateFields();
            save({
              similarQuestionMaxNums,
              fileFaqMaxNums,
              kbConfigType: 2,
              ...formData
            });
          }}
        >
          保存
        </Button>
      </div>
    </div>
  );
};

export default FAQConfig;
