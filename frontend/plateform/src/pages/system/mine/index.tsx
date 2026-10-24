import React, { useState, useEffect } from "react";
import { Card, Row, Col, Form, message, Tabs } from "antd";
import SystemContainer from "../SystemContainer";
import { UserData, EditProfileFormData, ResetPasswordFormData } from "./types";
import UserInfoCard from "./UserInfoCard";
import LogoutModal from "./LogoutModal";
import ResetPasswordModal from "./ResetPasswordModal";
import EditProfileModal from "./EditProfileModal";
import UserSecuritySettings from "./UserSecuritySettings";
import UserBasicInfo from "./UserBasicInfo";
import systemApi from "@/apis/system";
import { Encrypt } from "../../others/Login/utils";
import { useAppPassport } from "@root/src/core/helps";
import { useNavigate } from "react-router-dom";

// 主要按钮的渐变样式
const primaryButtonStyle = {
  background: "linear-gradient(to right, #2B69FF, #8F91FF)",
  borderColor: "transparent",
  border: "none"
};

const UserProfilePage: React.FC = () => {
  const { userInfo, clear, update: updatePassport } = useAppPassport();
  const navigate = useNavigate();
  const api = systemApi();
  const [userData, setUserData] = useState<UserData | null>(null);
  const [activeTab, setActiveTab] = useState("1");
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [resetPasswordVisible, setResetPasswordVisible] = useState(false);
  const [logoutModalVisible, setLogoutModalVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [editForm] = Form.useForm();
  const [resetPasswordForm] = Form.useForm();

  const unitInfo = async () => {
    try {
      const response = await api.getCurrentUserInfo();
      if (response.data) {
        setUserData(response.data);
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  useEffect(() => {
    unitInfo();
  }, []);

  const handleOpenEditModal = () => {
    editForm.setFieldsValue(userData);
    setEditModalVisible(true);
  };

  const handleOpenResetPasswordModal = () => {
    resetPasswordForm.resetFields();
    setResetPasswordVisible(true);
  };

  const handleUpdateProfile = async (values: EditProfileFormData) => {
    try {
      if (!userData?.id) {
        message.error("用户ID不存在");
        return;
      }
      const param: any = { ...values, userId: userData.id };
      const response = await api.updateUserInfo(param);
      if (response.data) {
        unitInfo();
        message.success("保存成功");
        setEditModalVisible(false);
      } else {
        message.error("保存失败，请联系管理员");
      }
    } catch (error) {
      message.error("更新个人信息失败");
      console.error("更新个人信息失败:", error);
    }
  };

  const handleResetPassword = async (values: ResetPasswordFormData) => {
    try {
      if (values.oldPassword === "" || values.oldPassword === undefined) {
        return message.warning("原密码不能为空");
      } else if (
        values.newPassword === "" ||
        values.newPassword === undefined
      ) {
        return message.warning("新密码不能为空");
      } else if (
        values.confirmPassword === "" ||
        values.confirmPassword === undefined
      ) {
        return message.warning("确认密码不能为空");
      } else if (values.newPassword !== values.confirmPassword) {
        return message.warning("新密码与确认密码不一致");
      }

      const param = {
        newPassword: Encrypt(values.newPassword),
        oldPassword: Encrypt(values.oldPassword)
      };

      setLoading(true);
      try {
        const response = await api.updatePassword(param);
        if (response.data) {
          setLoading(false);
          message.success("修改密码成功");
          setResetPasswordVisible(false);
        } else {
          setLoading(false);
        }
      } catch (error: any) {
        message.error(error?.response?.data?.errorMsg);
        setLoading(false);
      }
    } catch (error) {
      message.error("重置密码失败");
      console.error("重置密码失败:", error);
    }
  };

  const handleLogout = async () => {
    try {
      const response = await api.userLogout();
      if (response.data) {
        clear();
        navigate("/login");
        message.success("已安全退出系统");
        setLogoutModalVisible(false);
      }
    } catch (error) {
      message.error("退出系统失败");
      console.error("退出系统失败:", error);
    }
  };

  return (
    <SystemContainer
      title="账户信息"
      description="个人账户信息以及账户操作相关"
    >
      <div className="min-h-full p-6">
        <UserInfoCard
          userData={userData}
          onEditProfile={handleOpenEditModal}
          onResetPassword={handleOpenResetPasswordModal}
          onLogout={() => setLogoutModalVisible(true)}
          primaryButtonStyle={primaryButtonStyle}
        />
      </div>

      {/* 各种弹窗组件 */}
      <EditProfileModal
        visible={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onSubmit={handleUpdateProfile}
        userData={userData}
        form={editForm}
        unitInfo={unitInfo}
        primaryButtonStyle={primaryButtonStyle}
      />

      <ResetPasswordModal
        visible={resetPasswordVisible}
        onCancel={() => setResetPasswordVisible(false)}
        onSubmit={handleResetPassword}
        form={resetPasswordForm}
        primaryButtonStyle={primaryButtonStyle}
      />

      <LogoutModal
        visible={logoutModalVisible}
        onCancel={() => setLogoutModalVisible(false)}
        onLogout={handleLogout}
      />
    </SystemContainer>
  );
};

export default UserProfilePage;
