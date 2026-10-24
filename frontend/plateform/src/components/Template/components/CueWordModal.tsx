import { Flex, Modal, Tag, theme, Typography } from 'antd';
import VarCom from './VarCom';
const { Text } = Typography;
const { useToken } = theme;
const CueWordModal = ({ isModalOpen, handlerEvent, setIsModalOpen, modalList }: any) => {
  const { token } = useToken();
  return (
    <Modal
      title={
        <Flex align="center">
          <VarCom fontSize="40px" />
          <Text style={{ marginLeft: token.margin }}>
            提示词中引用了未定义的变量，是否自动添加到用户输入表单中？
          </Text>
        </Flex>
      }
      okText="确定"
      cancelText="取消"
      open={isModalOpen}
      onOk={() => handlerEvent('addTableList')}
      closable={false}
      onCancel={() => setIsModalOpen(false)}
    >
      <div style={{ marginLeft: '80px' }}>
        {modalList.map((item: any, index: number) => (
          <Tag key={index} bordered={false} color="blue">
            {`{{${item}}}`}
          </Tag>
        ))}
      </div>
    </Modal>
  );
};

export default CueWordModal;
