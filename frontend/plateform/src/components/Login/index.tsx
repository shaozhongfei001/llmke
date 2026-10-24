import { ConfigProvider, Flex, Form } from "antd";
import { useState } from "react";
import LoginBox from "./LoginBox";
import RegisterBox from "./RegisterBox";

const defaultStyle = {
  colorPrimary: "#1677ff",
  defaultBg: "#ffffff"
};

interface LoginStyle {
  defaultBg?: string;
  colorPrimary?: string;
}
interface LoginProps {
  homeBg?: string;
  leftImg?: string;
  logoImg?: string;
  eventEmit?: (n: string, d: any) => void;
  loginLoading?: boolean;
  registerLoading?: boolean;
  codeImgSrc?: string;
  loginStyle?: LoginStyle;
  registreKaptchaUrl?: string;
  isRegister: boolean;
  setIsRegister: any;
}
const Login = (props: LoginProps) => {
  const {
    homeBg,
    leftImg,
    logoImg,
    eventEmit,
    codeImgSrc = "",
    loginStyle,
    loginLoading,
    registerLoading,
    registreKaptchaUrl,
    isRegister,
    setIsRegister
  } = props;

  const [form] = Form.useForm();

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: loginStyle?.colorPrimary || defaultStyle.colorPrimary
        },
        components: {
          Button: {
            defaultBg: loginStyle?.defaultBg || defaultStyle.defaultBg
          }
        }
      }}
    >
      <Flex
        style={{
          width: "100%",
          height: "100%",
          background: `url('${homeBg}') no-repeat center/cover`
        }}
        justify="center"
        align="center"
      >
        <Flex
          style={{
            background: "white",
            height: "505px",
            minHeight: "393px",
            width: "calc(505px * 2)",
            minWidth: "840px",
            borderRadius: "10px",
            overflow: "hidden"
          }}
        >
          {leftImg && (
            <img
              style={{
                objectFit: "cover",
                width: "50%"
              }}
              src={leftImg}
            />
          )}
          <Flex flex={1} justify="center" align="center">
            <Form form={form} labelCol={{ span: 6 }} className="w-[367px]">
              {isRegister ? (
                <RegisterBox
                  form={form}
                  setIsRegister={setIsRegister}
                  eventEmit={eventEmit}
                  registerLoading={registerLoading}
                  registreKaptchaUrl={registreKaptchaUrl}
                />
              ) : (
                <LoginBox
                  loginLoading={loginLoading}
                  form={form}
                  logoImg={logoImg}
                  setIsRegister={setIsRegister}
                  codeImgSrc={codeImgSrc}
                  eventEmit={eventEmit}
                />
              )}
            </Form>
          </Flex>
        </Flex>
      </Flex>
    </ConfigProvider>
  );
};

export default Login;
