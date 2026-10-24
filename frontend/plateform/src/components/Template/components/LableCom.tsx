import { QuestionCircleOutlined } from "@ant-design/icons";
import { Flex, Popover, Typography } from "antd";
import "./style.less";
const { Text } = Typography;
const LableCom = ({
  title,
  required = true,
  popContent = (
    <Text>
      <span>变量将以表单形式让用户在对话前</span>
      <br />
      <span>埴写，用户填写的表单内容将自动</span>
      <br />
      <span>替换提示词中的变量。</span>
    </Text>
  ),
}: any) => {
  return (
    <Flex className="mb-2 addTemplateForm">
      <label className={`${required ? "selfLabel" : ""} text-sm mr-1`}>
        {title}
      </label>
      <Popover content={popContent}>
        <QuestionCircleOutlined
          style={{
            fontSize: "16px",
            color: "#888",
          }}
        />
      </Popover>
    </Flex>
  );
};

export default LableCom;
