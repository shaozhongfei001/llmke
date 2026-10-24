import {
  Alert,
  Button,
  ConfigProvider,
  Flex,
  Form,
  Input,
  message
} from "antd";
import { BTN_STYLE } from "../utils/constants";
import { ExclamationCircleFilled, LoadingOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import {
  PASSWORD_REGEX,
  PASSWORD_WARN_MSG,
  useAppPassport
} from "@root/src/core/helps";
import {
  api_forceUpdatePassword,
  api_getKaptchaImage,
  userLogout
} from "../utils/services";
import { Encrypt } from "@root/src/pages/Login/utils";
import { RAG_APP_NAME, RAG_AUTH_PLUGIN_PREFIX } from "@root/src/const";

export const AfterSuperReset = ({ emitEvent }: any) => {
  const { update, clear } = useAppPassport();
  const [btnLoading, setBtnLoading] = useState(false);
  const [showReset, setShowReset] = useState(1);
  const forceUpdatePassword = async (params: any) => {
    try {
      setBtnLoading(true);

      const res = await api_forceUpdatePassword({
        oldPassword: Encrypt(params.oldPassword),
        newPassword: Encrypt(params.newPassword),
        verifyCode: params.verifyCode
      });
      setBtnLoading(false);
      if (res) {
        const userInfo_str = localStorage.getItem(
          `${RAG_AUTH_PLUGIN_PREFIX}${RAG_APP_NAME}`
        );
        let info: any = {};
        if (userInfo_str) {
          info = JSON.parse(userInfo_str);
        }
        if (info.userInfo) {
          info.userInfo.hasAdminResetPassword = false;
        }
        update({ ...info });
        emitEvent && emitEvent("setTitle", "去登录");
        setShowReset(3);
        message.success("重置密码成功");
      }
    } catch (error) {
      setBtnLoading(false);
    }
  };
  const logout = async () => {
    try {
      setBtnLoading(true);
      const res = await userLogout();
      setBtnLoading(false);
      if (res) {
        clear();
        window.location.pathname = "/login";
      }
    } catch (error) {
      setBtnLoading(false);
    }
  };
  const handleEvent = (type: string, data?: any) => {
    switch (type) {
      case "toReset":
        setShowReset(2);
        break;
      case "toLoginPage":
        forceUpdatePassword(data);

        break;
      case "toLogin":
        logout();
        break;
    }
  };
  return (
    <>
      {showReset === 1 && <WarningReset eventEmit={handleEvent} />}
      {showReset === 2 && <ResetPassword eventEmit={handleEvent} />}
      {showReset === 3 && (
        <ToLogin eventEmit={handleEvent} btnLoading={btnLoading} />
      )}
    </>
  );
};

const WarningReset = ({ eventEmit }: any) => {
  return (
    <div className="flex flex-col items-center">
      <ConfigProvider
        theme={{
          components: {
            Alert: {
              defaultPadding: "0px 8px",
              colorWarningBg: "transparent",
              colorWarningBorder: "transparent"
            }
          }
        }}
      >
        <Alert
          showIcon
          message="为了您的账户安全，请重置密码！"
          type="warning"
          style={{ color: "#4E5969", fontSize: 14 }}
          icon={
            <ExclamationCircleFilled
              className="text-[14px]"
              style={{ color: "#FAAD14" }}
            />
          }
        />
      </ConfigProvider>
      <div className="pt-[20px] flex justify-center">
        <Button
          type="primary"
          onClick={async () => {
            eventEmit("toReset");
          }}
          style={BTN_STYLE}
        >
          重置密码
        </Button>
      </div>
    </div>
  );
};

const ToLogin = ({ eventEmit, btnLoading }: any) => {
  return (
    <div className="flex flex-col items-center">
      <ConfigProvider
        theme={{
          components: {
            Alert: {
              defaultPadding: "0px 8px",
              colorSuccessBg: "transparent",
              colorSuccessBorder: "transparent"
            }
          }
        }}
      >
        <Alert
          showIcon
          message="重置密码成功，请重新登录！"
          type="success"
          style={{ color: "#4E5969", fontSize: 14 }}
        />
      </ConfigProvider>
      <div className="pt-[20px] flex justify-center">
        <Button
          type="primary"
          onClick={() => {
            eventEmit("toLogin");
          }}
          style={BTN_STYLE}
          loading={btnLoading}
        >
          去登录
        </Button>
      </div>
    </div>
  );
};

const ResetPassword = ({ eventEmit }: any) => {
  const [form] = Form.useForm();
  const [codeLoading, setCodeLoading] = useState<boolean>(false);
  const [kaptchaUrl, setKaptchaUrl] = useState("");
  const getKaptchaImageFn = async () => {
    try {
      setCodeLoading(true);
      const res = await api_getKaptchaImage();
      setCodeLoading(false);
      if (res) {
        const imgBlob = new Blob([res], { type: "image/jpeg" });
        const imageUrl = window.URL.createObjectURL(imgBlob);
        setKaptchaUrl(imageUrl);
      }
    } catch (error) {
      setCodeLoading(false);
    }
  };
  const handleClickCode = () => {
    getKaptchaImageFn();
  };
  const handleOk = async () => {
    const values = await form.validateFields();
    eventEmit("toLoginPage", values);
  };
  useEffect(() => {
    handleClickCode();
  }, []);
  return (
    <Form form={form} labelCol={{ span: 4 }}>
      <Form.Item
        label="原密码"
        name={"oldPassword"}
        validateTrigger={false}
        rules={[{ required: true, message: "请输入原密码" }]}
      >
        <Input.Password placeholder={PASSWORD_WARN_MSG} maxLength={64} />
      </Form.Item>
      <Form.Item
        label="新密码"
        name={"newPassword"}
        validateTrigger={false}
        rules={[
          { required: true, message: "请输入新密码" },
          {
            message: PASSWORD_WARN_MSG,
            pattern: PASSWORD_REGEX
          }
        ]}
      >
        <Input.Password placeholder={PASSWORD_WARN_MSG} maxLength={64} />
      </Form.Item>

      <Form.Item
        label="确认密码"
        validateTrigger="onBlur"
        rules={[
          { required: true, message: "请输入新密码" },
          {
            message: PASSWORD_WARN_MSG,
            pattern: PASSWORD_REGEX
          },
          ({ getFieldValue }) => ({
            validator(_, value) {
              if (!value || getFieldValue("newPassword") === value) {
                return Promise.resolve();
              }
              return Promise.reject(new Error("密码不一致，请重新输入"));
            }
          })
        ]}
        name={"confirmPwd"}
      >
        <Input.Password
          id="confirmPwd"
          placeholder={PASSWORD_WARN_MSG}
          maxLength={64}
        />
      </Form.Item>

      <Form.Item
        name={"verifyCode"}
        label="验证码"
        rules={[{ required: true, message: "请输入验证码" }]}
        className={`mt-[20px]`}
      >
        <Flex>
          <Input placeholder="输入验证码" className="mr-2" maxLength={30} />

          {codeLoading ? (
            <Flex style={{ width: "96px", height: "32px" }} justify="center">
              <LoadingOutlined />
            </Flex>
          ) : (
            <img
              onClick={handleClickCode}
              src={kaptchaUrl}
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

      <div className="pt-[20px] flex justify-center">
        <Button type="primary" onClick={handleOk} style={BTN_STYLE}>
          重置密码
        </Button>
      </div>
    </Form>
  );
};
