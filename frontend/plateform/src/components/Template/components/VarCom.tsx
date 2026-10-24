import { XOutlined } from '@ant-design/icons';
import { Flex, theme, Typography } from 'antd';
const { useToken } = theme;
const { Text } = Typography;
const VarCom = ({ fontSize = '12px' }: any) => {
  const { token } = useToken();
  return (
    <Flex
      align="center"
      style={{ color: token.colorPrimary, fontSize: fontSize || token.fontSizeSM }}
    >
      <Text style={{ color: token.colorPrimary, fontSize: fontSize || token.fontSizeSM }}>
        {'{'}
      </Text>
      <XOutlined />
      <Text style={{ color: token.colorPrimary, fontSize: fontSize || token.fontSizeSM }}>
        {'}'}
      </Text>
    </Flex>
  );
};

export default VarCom;
