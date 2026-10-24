import { Button, ConfigProvider, Modal } from 'antd';
import warning from '../../assets/img/warning.png';
export const DeleteModal = ({ isModalOpen, handleOk, handleCancel }) => {
  const modalStyles = {
    header: {},
    body: {},
    mask: {},
    footer: {},
    content: { padding: '12px', borderRadius: '8px' },
  };
  return (
    <ConfigProvider
      modal={{
        styles: modalStyles,
      }}
    >
      <Modal
        title={null}
        closeIcon={null}
        open={isModalOpen}
        onOk={handleOk}
        onCancel={handleCancel}
        width={224}
        centered
        className="deleteModal"
        footer={
          <div className="mt-[16px] flex justify-end">
            <Button size="small" children="取消" onClick={handleCancel} className="mr-[8px]" />
            <Button
              size="small"
              children="确认"
              onClick={handleOk}
              type="primary"
              className="border-none"
            />
          </div>
        }
      >
        <div className="flex items-center">
          <img src={warning} />
          <div className="text-[14px] text-[#000000] font-bold ml-[8px]">删除</div>
        </div>
        <div className="flex items-center">
          <div className="w-[30px]" />
          <div className="text-[14px] text-[#000000] mt-[8px]">删除后无法恢复，是否继续删除？</div>
        </div>
      </Modal>
    </ConfigProvider>
  );
};
