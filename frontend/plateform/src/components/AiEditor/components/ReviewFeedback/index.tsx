import { Flex, Modal, Select, Input, Form, Tag, message } from "antd";
import { useCallback, useEffect, useState } from "react";
import { useStateStore } from "../../core/states/useStateStore";
const { TextArea } = Input;

interface Data {
  id?: string;
  errorType: string | number | null;
  source: string;
  target?: string;
  suggestion?: string;
}

interface ConfirmData {
  originData?: Data;
  formData: {
    errorType: string | number | null;
    suggestion?: string;
  };
}

interface Iprops {
  open: boolean;
  handleOk?: (data: ConfirmData) => void;
  handleClose?: (data?: Data) => void;
  data?: Data;
}

const errorTypeOption = [
  {
    label: "错别字",
    value: "1"
  },
  {
    label: "文法错误",
    value: "2"
  },
  {
    label: "标点不当",
    value: "3"
  },
  {
    label: "字词冗余",
    value: "4"
  },
  {
    label: "缺字",
    value: "5"
  },
  {
    label: "序号错误",
    value: "6"
  },
  {
    label: "段落重复",
    value: "7"
  },
  {
    label: "口语化表达",
    value: "8"
  },
  // 与后端约定100为敏感词错误
  {
    label: "敏感词",
    value: "100"
  },
  // 0为其他
  {
    label: "其他",
    value: "0"
  }
];

const ReviewFeedback = (props: Iprops) => {
  const { open, handleOk, handleClose, data } = props;
  const [form] = Form.useForm();
  const [okLoading, setOkLoading] = useState(false);
  const [curTag, setCurTag] = useState(
    data?.errorType === null ? null : String(data?.errorType)
  );

  useEffect(() => {
    setCurTag(data?.errorType === null ? null : String(data?.errorType));
    if (!data) return;
    form.setFieldsValue({
      errorType: String(data?.errorType),
      suggestion: data?.suggestion
    });
  }, [data]);

  const onOk = () => {
    if (!curTag) {
      message.warning("请选择错误类型");
      return;
    }
    form.validateFields().then(async (res) => {
      try {
        setOkLoading(true);
        handleOk &&
          (await handleOk({
            originData: data,
            formData: { ...res, errorType: curTag }
          }));
        setOkLoading(false);
      } catch (e) {
        setOkLoading(false);
      }
    });
  };

  const onCancel = () => {
    setCurTag(null);
    handleClose && handleClose();
  };

  const handTagClick = (tagItem) => {
    setCurTag(tagItem.value);
  };

  return (
    <Modal
      open={open}
      okText="确认"
      cancelText="取消"
      centered={true}
      width={412}
      onOk={onOk}
      onCancel={onCancel}
      okButtonProps={{ loading: okLoading }}
      destroyOnClose={true}
    >
      <span className="text-[#2a2a2a] text-[16px] font-bold">
        感谢您的反馈！这将帮助我们不断优化与提升。
      </span>
      <Flex vertical className="mt-[20px] w-[364px]" gap={12}>
        {data?.errorType ? (
          <p className="bg-[#e6f4ff] h-[30px] leading-[30px] text-[14px] text-[#2a2a2a] w-full pl-[12px]">
            错误类型：
            {
              errorTypeOption.find((i) => i.value === String(data?.errorType))
                ?.label
            }
          </p>
        ) : (
          <Flex wrap gap={8}>
            {errorTypeOption.map((i) => (
              <Tag
                className="cursor-pointer"
                color={i.value === curTag ? "blue" : ""}
                onClick={() => handTagClick(i)}
                key={i.value}
              >
                {i.label}
              </Tag>
            ))}
          </Flex>
        )}
        <Form form={form}>
          {/* {!!data?.errorType ? (
            <p className="bg-[#e6f4ff] h-[30px] leading-[30px] text-[14px] text-[#2a2a2a] w-full pl-[12px]">
              错误类型：{errorTypeOption.find((i) => i.value === data?.errorType)?.label}
            </p>
          ) : (
            <Form.Item name={'errorType'} rules={[{ required: true, message: '请选择错误类型' }]}>
              <Select
                placeholder="请选择错误类型"
                options={errorTypeOption}
                disabled={!!data?.errorType}
              ></Select>
            </Form.Item>
          )} */}
          <Form.Item
            name={"suggestion"}
            rules={[
              {
                max: 151,
                message: "最多150字"
              }
            ]}
          >
            <TextArea
              placeholder="请输入产品功能问题及改进建议(150字以内)"
              autoSize={{
                minRows: 5,
                maxRows: 5
              }}
            ></TextArea>
          </Form.Item>
        </Form>
      </Flex>
    </Modal>
  );
};

export default ReviewFeedback;
