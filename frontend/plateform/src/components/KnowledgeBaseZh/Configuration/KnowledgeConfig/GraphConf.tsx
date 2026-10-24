import { useRef, useState, useEffect } from "react";
import { Button, Form, Select } from "antd";
import NotFoundContent from "./NotFoundContent";
import AutoTag from "@root/src/pages/HomePage/IntelligentChat/SensitiveWords/common/components/autoTag";
const { useForm } = Form;

const graphConfig = ({
  btnLoading,
  save,
  disabled,
  kbInfo,
  modelsOption
}: any) => {
  const [tags, setTags]: any = useState([]);
  const tagsWrapRef = useRef(null);
  const [form] = useForm();

  useEffect(() => {
    if (kbInfo) {
      const { graphPrompt, generateGraphModelName } = kbInfo;
      form.setFieldsValue({
        generateGraphModelName
      });
      if (Array.isArray(modelsOption) && modelsOption?.length == 0) {
        form.validateFields(["generateGraphModelName"]);
      }
      if (graphPrompt) {
        setTags(graphPrompt.split(","));
      }
    }
  }, [kbInfo]);
  return (
    <div className=" w-full px-[20px] pt-[20px] rounded-[8px] bg-white">
      <Form form={form} layout="vertical">
        <Form.Item
          name="generateGraphModelName"
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
      <div className=" text-[#2A2A2A]">抽取实体类型</div>
      <div
        ref={tagsWrapRef}
        className="overflow-hidden border-[1px] h-[calc(100%-120px)] border-solid border-[#D9D9D9] py-4 pl-4 pr-1 bg-[#F5F5F5] mt-4 rounded-lg"
      >
        <AutoTag
          wrapRef={tagsWrapRef}
          tags={tags}
          setTags={setTags}
          disabled={disabled}
          addLabel="添加抽取实体类型"
        />
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
              graphPrompt: tags.join(","),
              kbConfigType: 3,
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
export default graphConfig;
