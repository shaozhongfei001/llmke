import { Button, Flex, Form, Input, message } from "antd";
import { ChangeEventHandler, useEffect, useState } from "react";
import {
  api_getKaptchaImage,
  api_getkaptchaSix,
  api_queryResetPassword,
  api_resetPassword,
  api_updatePasswordByQuestion
} from "../utils/services";
import { Decrypt, Encrypt } from "@root/src/pages/Login/utils";
import { PASSWORD_REGEX } from "@root/src/core/helps";
import { LoadingOutlined } from "@ant-design/icons";
import { BTN_STYLE } from "../utils/constants";
import copy from "copy-to-clipboard";
const toCopy = (content: string) => {
  if (!content) return message.warning("数据为空");
  copy(content);
  message.success("复制成功!");
};

export const SuperViewPassword = ({ emitEvent, userId }: any) => {
  const [form] = Form.useForm();
  const [codeLoading, setCodeLoading] = useState<boolean>(false);
  const [kaptchaUrl, setKaptchaUrl] = useState("");
  const [btnLoading, setBtnLoading] = useState<boolean>(false);
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [value, setValue] = useState<string>("");

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

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setBtnLoading(true);
      const res = await api_queryResetPassword({
        verifyCode: values.verifyCode,
        userId
      });
      setBtnLoading(false);
      if (res) {
        const data = Decrypt(res.data);
        form.setFieldValue("Pwd", data);
        setValue(data);
        setShowPassword(true);
      }
    } catch (error) {
      setBtnLoading(false);
    }
  };
  const handleClickCode = () => {
    getKaptchaImageFn();
  };

  useEffect(() => {
    handleClickCode();
  }, []);
  return (
    <>
      <Form form={form}>
        {showPassword ? (
          <Form.Item label="密码" name={"Pwd"}>
            <Input.Password
              value={value}
              maxLength={64}
              readOnly
              className="mr-2"
              suffix={
                <div
                  className="px-[2px] text-[#1d70f5] cursor-pointer"
                  onClick={() => toCopy(value)}
                >
                  复制
                </div>
              }
            />
          </Form.Item>
        ) : (
          <Form.Item
            name={"verifyCode"}
            label="验证码"
            rules={[{ required: true, message: "请输入验证码" }]}
            className={`mb-[20px]`}
          >
            <Flex>
              <Input placeholder="输入验证码" className="mr-2" maxLength={30} />

              {codeLoading ? (
                <Flex
                  style={{ width: "96px", height: "32px" }}
                  justify="center"
                >
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
        )}

        {showPassword ? (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 8,
              marginTop: 8
            }}
          >
            <Button
              onClick={() => {
                emitEvent("cancel");
              }}
            >
              关闭
            </Button>
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 8,
              marginTop: 8
            }}
          >
            <Button
              onClick={() => {
                emitEvent("cancel");
              }}
            >
              取消
            </Button>
            <Button
              type="primary"
              loading={btnLoading}
              onClick={handleOk}
              style={BTN_STYLE}
            >
              确定
            </Button>
          </div>
        )}
      </Form>
    </>
  );
};
