import { Button, Flex, Form, FormInstance, Input, Typography } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import React, { useState } from "react";
import { SecurityCom } from "../../PasswordModal/components/SecurityCom";
import { MODAL_TYPE } from "../../PasswordModal";
import { PASSWORD_REGEX, PASSWORD_WARN_MSG } from "@root/src/core/helps";
const { Title } = Typography;

export enum RegisterFormActionEnum {
  CANCEL = "cancel",
  SUBMIT = "submit"
}

//不能用数字开头，长度不超过25，无特殊符号，无空格
const REG_NAME = /^[\u4e00-\u9fa5A-Za-z_][\u4e00-\u9fa5A-Za-z0-9_]{0,24}$/;
const REG_NAME_MSG = "不能用数字开头，长度不超过25，无特殊符号，无空格";

const REG_PHONE =
  /^(((13[0-9]{1})|(15[0-9]{1})|(18[0-9]{1})|(16[0-9]{1})|(17[0-9]{1})|(19[0-9]{1}))+\d{8})$/;
const REF_PHONE_MSG = "手机号格式不正确";

const REG_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const REF_EMAIL_MSG = "邮箱格式不正确";

const REG_PASSWORD = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$/;

interface Iprops {
  eventEmit?: (name: string, data: any, failCb?: () => void) => void;
  setIsRegister: React.Dispatch<React.SetStateAction<boolean>>;
  form: FormInstance<any>;
  registerLoading?: boolean;
  registreKaptchaUrl?: string;
}

const RegisterBox: React.FC<Iprops> = (props) => {
  const {
    eventEmit,
    setIsRegister,
    form,
    registreKaptchaUrl,
    registerLoading = false
  } = props;
  const [page, setPage] = useState(1);
  const [btnLoading, setBtnLoading] = useState<boolean>(false);

  const handleRegister = async () => {
    form.validateFields().then(async (res) => {
      console.log("校验1", res);

      setPage(2);
    });
  };

  const handleEvent = (type: string, data: any, failCb?: () => void) => {
    console.log("type,data", type, data);

    switch (type) {
      case "register:securitySet":
        eventEmit &&
          eventEmit(
            "login:register",
            { ...form.getFieldsValue(), ...data },
            failCb
          );
        break;
    }
  };

  return (
    <>
      <Flex
        style={{
          paddingTop: "35px",
          display: page === 1 ? "" : "none"
        }}
        vertical
      >
        <Form.Item
          label="用户名"
          name={"userName"}
          rules={[
            { required: true, message: "请输入名称" },
            {
              pattern: new RegExp(REG_NAME),
              message: `名称${REG_NAME_MSG}`
            }
          ]}
        >
          <Input placeholder="输入用户名字" />
        </Form.Item>
        <Form.Item
          label="手机号"
          name={"userIphone"}
          rules={[
            { required: true, message: "请输入手机号" },
            {
              pattern: new RegExp(REG_PHONE),
              message: `${REF_PHONE_MSG}`
            }
          ]}
        >
          <Input placeholder="请输入手机号" />
        </Form.Item>
        <Form.Item
          label="邮箱"
          name={"userEmail"}
          rules={[
            { required: true, message: "请输入邮箱" },
            {
              pattern: new RegExp(REG_EMAIL),
              message: `${REF_EMAIL_MSG}`
            }
          ]}
        >
          <Input placeholder="输入邮箱" />
        </Form.Item>
        <Form.Item
          label="密码"
          name={"password"}
          validateTrigger={false}
          rules={[
            { required: true, message: "请输入密码" },
            {
              message: PASSWORD_WARN_MSG,
              pattern: PASSWORD_REGEX
            }
          ]}
        >
          <Input placeholder="请输入密码" type="password" />
        </Form.Item>
        <Form.Item
          label="确认密码"
          name={"passwordAffirm"}
          validateTrigger="onBlur"
          dependencies={["password"]}
          rules={[
            {
              required: true,
              message: "请确认新密码"
            },
            {
              message: PASSWORD_WARN_MSG,
              pattern: PASSWORD_REGEX
            },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue("password") === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error("两次密码不一致!"));
              }
            })
          ]}
        >
          <Input placeholder="请确认新密码" type="password" />
        </Form.Item>
        <Form.Item>
          <Flex justify="space-between" className="mt-[32px]">
            <Button
              style={{ width: "48%" }}
              onClick={() => setIsRegister(false)}
            >
              取消
            </Button>
            <Button
              style={{ width: "48%" }}
              onClick={handleRegister}
              type="primary"
              loading={registerLoading}
            >
              下一步
            </Button>
          </Flex>
        </Form.Item>
      </Flex>
      <div style={{ display: page === 2 ? "" : "none", width: "367px" }}>
        <SecurityCom
          onCancel={() => setPage(1)}
          type={MODAL_TYPE.REGISTER}
          emitEvent={handleEvent}
          confirmLoading={btnLoading}
        />
      </div>
    </>
  );
};

export default RegisterBox;
