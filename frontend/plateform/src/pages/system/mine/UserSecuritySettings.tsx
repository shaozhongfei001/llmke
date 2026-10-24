import React from 'react';
import { Card, Typography, Button } from 'antd';
import { KeyOutlined, SafetyOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

interface UserSecuritySettingsProps {
  onResetPassword: () => void;
}

const UserSecuritySettings: React.FC<UserSecuritySettingsProps> = ({ onResetPassword }) => {
  return (
    <div className="p-4">
      <Card
        bordered={false}
        className="shadow-sm"
      >
        <div className="flex flex-col items-center justify-center py-8">
          <SafetyOutlined style={{ fontSize: 64, color: '#1890ff', marginBottom: 16 }} />
          <Title level={4}>账户安全</Title>
          <Text className="text-center max-w-md mb-6">
            管理您的账户安全设置，定期更改密码可以有效保护您的账户安全
          </Text>
          <Button 
            type="dashed" 
            icon={<KeyOutlined />}
            onClick={onResetPassword}
          >
            重置密码
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default UserSecuritySettings; 