import React from "react";
import { Card, Row, Col, Typography, Button, Tag } from "antd";
import { EditOutlined, TeamOutlined } from "@ant-design/icons";
import { UserData } from "./types";

const { Text } = Typography;

interface UserBasicInfoProps {
  userData: UserData | null;
  onEditProfile: () => void;
}

const UserBasicInfo: React.FC<UserBasicInfoProps> = ({
  userData,
  onEditProfile
}) => {
  return (
    <div className="p-4">
      <Row gutter={[24, 24]} className="mb-4">
        <Col span={24}>
          <Card
            title="账户详细信息"
            bordered={false}
            className="shadow-sm"
            extra={
              <Button
                type="link"
                icon={<EditOutlined />}
                onClick={onEditProfile}
              >
                编辑
              </Button>
            }
          >
            <Row gutter={[32, 16]}>
              <Col xs={24} sm={12}>
                <div className="mb-4">
                  <Text type="secondary" className="block">
                    用户名
                  </Text>
                  <Text strong>{userData?.userName}</Text>
                </div>
              </Col>
              <Col xs={24} sm={12}>
                <div className="mb-4">
                  <Text type="secondary" className="block">
                    真实姓名
                  </Text>
                  <Text strong>{userData?.userRealname}</Text>
                </div>
              </Col>
              <Col xs={24} sm={12}>
                <div className="mb-4">
                  <Text type="secondary" className="block">
                    手机号码
                  </Text>
                  <Text strong>{userData?.userPhone}</Text>
                </div>
              </Col>
              <Col xs={24} sm={12}>
                <div className="mb-4">
                  <Text type="secondary" className="block">
                    电子邮箱
                  </Text>
                  <Text strong>{userData?.userEmail}</Text>
                </div>
              </Col>
              <Col span={24}>
                <div className="mb-4">
                  <Text type="secondary" className="block">
                    用户角色
                  </Text>
                  <div className="mt-1">
                    {(userData?.roles || []).map((role: any) => (
                      <Tag color="blue" key={role.id} icon={<TeamOutlined />}>
                        {role.name}
                      </Tag>
                    ))}
                  </div>
                </div>
              </Col>
              {/* <Col span={24}>
                <div>
                  <Text type="secondary" className="block">
                    上次登录时间
                  </Text>
                  <Text strong>{userData?.lastLogin}</Text>
                </div>
              </Col> */}
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default UserBasicInfo;
