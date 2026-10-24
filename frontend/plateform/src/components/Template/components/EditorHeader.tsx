import { QuestionCircleOutlined, ThunderboltFilled } from "@ant-design/icons";
import { Flex, Popover, theme, Typography } from "antd";
const { Text } = Typography;
const { useToken } = theme;
const EditorHeader = () => {
  const { token } = useToken();
  return (
    <Flex
      justify="space-between"
      align="center"
      style={{ height: "44px", marginLeft: token.margin }}
    >
      <Flex>
        <Text>提示词</Text>
        <Popover
          content={
            <Text>
              <span>提示词用于对 AI 的回复做出一系</span>
              <br />
              <span>列指令和约束。可插入表单变量，</span>
              <br />
              <span>{"例如 {{ input }}。这段提示词不会"}</span>
              <br />
              <span>被最终用户所看到。</span>
            </Text>
          }
        >
          <QuestionCircleOutlined
            style={{
              marginLeft: token.marginXS,
              fontSize: token.fontSizeSM,
              color: token.colorBgMask
            }}
          />
        </Popover>
      </Flex>
      {/* <Flex style={{ marginRight: token.margin, color: token.colorPrimary }}>
        <ThunderboltFilled style={{ marginRight: token.marginXS }} />
        <Text>生成</Text>
      </Flex> */}
    </Flex>
  );
};

export default EditorHeader;
