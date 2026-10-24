import React, { useState } from "react";
import { Avatar, Button, Space, Tag } from "antd";
import { UserOutlined } from "@ant-design/icons";
import { UserData } from "./types";
import { dealMinioUrl } from "@root/src/core/helps";
import PasswordModal, { MODAL_TYPE } from "@root/src/components/PasswordModal";
import mineEdit from "@/assets/img/mineEdit.png";
import loginout from "@/assets/img/loginout.png";
import mineReset from "@/assets/img/mineReset.png";

interface UserInfoCardProps {
  userData: UserData | null;
  onEditProfile: () => void;
  onResetPassword: () => void;
  onLogout: () => void;
  primaryButtonStyle: React.CSSProperties;
}

const UserInfoCard: React.FC<UserInfoCardProps> = ({
  userData,
  onEditProfile,
  onResetPassword,
  onLogout,
  primaryButtonStyle
}) => {
  const [visible, setVisible] = useState(false);
  return (
    <div className="overflow-y-auto">
      <div className="flex flex-col items-center mt-[40px]">
        <Avatar
          size={120}
          icon={<UserOutlined />}
          src={dealMinioUrl(userData?.url ? userData.url : "")}
          className="mb-[20px]"
        />
        <div className="flex justify-center items-center ">
          <div className="w-[30px] h-[30px]"></div>
          <div className="text-[20px] font-bold text-[#1D2129] mr-[15px]">
            {userData?.userRealname}
          </div>
          <img
            src={mineEdit}
            className="text-[#4E6EF2] w-[15px] h-[15px] cursor-pointer"
            onClick={onEditProfile}
          />
        </div>

        <div className="w-full flex justify-center mt-[30px]">
          <div className="text-[14px] text-[#4E5969]">
            <div className="flex  items-center mb-[24px]">
              <span className="w-[73px]">部门：</span>
              <span>{userData?.deptName || "暂无"}</span>
            </div>
            <div className="flex items-center mb-[24px]">
              <span className="w-[73px]">用户名：</span>
              <span>{userData?.userName || "暂无"}</span>
            </div>
            <div className="flex items-center mb-[24px]">
              <span className="w-[73px]">电子邮箱：</span>
              <span>{userData?.userEmail || "暂无"}</span>
            </div>
            <div className="flex items-center mb-[24px]">
              <span className="w-[73px]">手机号码：</span>
              <span>{userData?.userPhone || "暂无"}</span>
            </div>
            <div className="flex items-center mb-[24px]">
              <span className="w-[73px]">用户角色：</span>
              <div className="mt-1">
                {(userData?.roles || []).map((role: any) => (
                  <Tag
                    bordered={false}
                    key={role.id}
                    className="text-[#4E6EF2] text-[12px] bg-[#F1F8FF]"
                  >
                    {role.name}
                  </Tag>
                ))}
              </div>
            </div>
          </div>
        </div>

        <Space direction="horizontal" align="center" className="mt-[16px]">
          <Button
            block
            icon={<img src={mineReset} className="w-[16px] h-[16px]" />}
            onClick={onResetPassword}
          >
            重置密码
          </Button>
          <Button
            block
            onClick={() => {
              setVisible(true);
            }}
          >
            密保问题设置
          </Button>
          <Button
            block
            danger
            icon={<img src={loginout} className="w-[16px] h-[16px]" />}
            onClick={onLogout}
          >
            退出登录
          </Button>
        </Space>
      </div>
      <PasswordModal
        visible={visible}
        onCancel={() => setVisible(false)}
        type={MODAL_TYPE.SECURITYUPDATE}
      />
    </div>
  );
};

export default UserInfoCard;
