import React from 'react';
import { Modal, Button } from 'antd';

interface LogoutModalProps {
  visible: boolean;
  onCancel: () => void;
  onLogout: () => void;
}

const LogoutModal: React.FC<LogoutModalProps> = ({
  visible,
  onCancel,
  onLogout
}) => {
  return (
    <Modal
      title="确认退出"
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button 
          key="logout" 
          danger 
          type="primary" 
          onClick={onLogout} 
          style={{ background: 'linear-gradient(to right, #ff4d4f, #ff7875)', borderColor: 'transparent' }}
        >
          确认退出
        </Button>,
      ]}
      className="rounded-lg"
    >
      <p>您确定要退出系统吗？</p>
    </Modal>
  );
};

export default LogoutModal; 