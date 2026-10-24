import {
  LoadingOutlined,
  ShoppingOutlined,
  UserOutlined
} from "@ant-design/icons";
import { Button, Flex, Form, FormInstance, Input, Typography } from "antd";
import React, { useState } from "react";
import PasswordModal, { MODAL_TYPE } from "../../PasswordModal";
const { Text } = Typography;
export enum LoginFormActionEnum {
  CANCEL = "cancel",
  SUBMIT = "submit",
  REFRESH = "refresh",
  REGISTER = "register"
}

interface Iprops {
  setIsRegister: React.Dispatch<React.SetStateAction<boolean>>;
  logoImg?: string;
  eventEmit?: (n: string, d: any) => void;
  form: FormInstance<any>;
  codeImgSrc?: string;
  loginLoading?: boolean;
}

const LoginBox: React.FC<Iprops> = (props) => {
  const {
    logoImg,
    setIsRegister,
    eventEmit,
    form,
    codeImgSrc,
    loginLoading = false
  } = props;
  const [visible, setVisible] = useState(false);
  const [codeLoading, setCodeLoading] = useState<boolean>(false);
  const handleLogin = () => {
    form.validateFields().then(async (res) => {
      eventEmit && (await eventEmit("login:login", res));
    });
  };

  const handleClickCode = async () => {
    setCodeLoading(true);
    eventEmit && (await eventEmit("login:codeClick", ""));
    setCodeLoading(false);
  };
  return (
    <Flex vertical justify="center">
      <Form.Item
        name={"userName"}
        rules={[{ required: true, message: "请输入用户名字" }]}
      >
        <Input placeholder="输入用户名字" prefix={<UserOutlined />} />
      </Form.Item>
      <Form.Item
        name={"password"}
        rules={[{ required: true, message: "请输入密码" }]}
      >
        <Input
          placeholder="输入密码"
          prefix={<ShoppingOutlined />}
          type="password"
        />
      </Form.Item>
      {codeImgSrc && (
        <Form.Item
          name={"verifyCode"}
          rules={[{ required: true, message: "请输入验证码" }]}
        >
          <Flex>
            <Input placeholder="输入验证码" className="mr-2" />

            {codeLoading ? (
              <Flex style={{ width: "96px", height: "32px" }} justify="center">
                <LoadingOutlined />
              </Flex>
            ) : (
              <img
                onClick={handleClickCode}
                src={codeImgSrc}
                style={{
                  width: "96px",
                  height: "32px",
                  background: "white",
                  border: "solid 1px #d9d9d9",
                  cursor: "pointer",
                  borderRadius: "6px"
                }}
              />
            )}
          </Flex>
        </Form.Item>
      )}
      <Form.Item>
        <Button
          style={{ width: "100%" }}
          type="primary"
          loading={loginLoading}
          onClick={handleLogin}
        >
          登录
        </Button>
      </Form.Item>
      <div className="flex justify-end">
        <Text
          style={{
            textAlign: "right",
            cursor: "pointer",
            marginRight: "8px"
          }}
          onClick={() => setIsRegister(true)}
        >
          点击注册
        </Text>
        <Text
          style={{
            textAlign: "right",
            cursor: "pointer",
            color: "#055aff"
          }}
          onClick={() => setVisible(true)}
        >
          忘记密码
        </Text>
      </div>
      <PasswordModal
        visible={visible}
        onCancel={() => setVisible(false)}
        type={MODAL_TYPE.RESET}
      />
    </Flex>
  );
};

export default LoginBox;
