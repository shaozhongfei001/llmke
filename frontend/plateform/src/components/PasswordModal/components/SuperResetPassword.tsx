import { Button, Flex, Form, Input, message } from "antd";
import { ChangeEventHandler, useEffect, useState } from "react";
import {
  api_getKaptchaImage,
  api_getkaptchaSix,
  api_resetPassword,
  api_updatePasswordByQuestion
} from "../utils/services";
import { Encrypt } from "@root/src/pages/Login/utils";
import { PASSWORD_REGEX } from "@root/src/core/helps";
import { LoadingOutlined } from "@ant-design/icons";
import { BTN_STYLE } from "../utils/constants";
import copy from "copy-to-clipboard";
const toCopy = (content: string) => {
  if (!content) return message.warning("数据为空");
  copy(content);
  message.success("复制成功!");
};
async function generateSecurePasswordCrypto(length = 12) {
  const lowercase = "abcdefghijklmnopqrstuvwxyz";
  const uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const numbers = "0123456789";
  const specialChars = "!@#$%^&*";
  const allChars = lowercase + uppercase + numbers + specialChars;
  // 创建Uint32数组用于更安全的随机数
  const randomValues = new Uint32Array(length);
  crypto.getRandomValues(randomValues);

  let password = "";

  // 确保每种类型至少有一个字符
  password += lowercase[randomValues[0] % lowercase.length];
  password += uppercase[randomValues[1] % uppercase.length];
  password += numbers[randomValues[2] % numbers.length];
  password += specialChars[randomValues[3] % specialChars.length];
  password += numbers[randomValues[4] % numbers.length];

  // 生成剩余字符
  for (let i = 5; i < length; i++) {
    password += allChars[randomValues[i] % allChars.length];
  }

  // 打乱顺序
  const passwordArray = password.split("");
  for (let i = passwordArray.length - 1; i > 0; i--) {
    const j = randomValues[i] % (i + 1);
    [passwordArray[i], passwordArray[j]] = [passwordArray[j], passwordArray[i]];
  }

  return passwordArray.join("");
}

export const SuperResetPassword = ({ emitEvent, userId }: any) => {
  const [form] = Form.useForm();
  const [codeLoading, setCodeLoading] = useState<boolean>(false);
  const [kaptchaUrl, setKaptchaUrl] = useState("");
  const [btnLoading, setBtnLoading] = useState<boolean>(false);
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
      const res = await api_resetPassword({
        password: Encrypt(values.Pwd),
        verifyCode: values.verifyCode,
        userId
      });
      setBtnLoading(false);
      if (res) {
        message.success("密码重置成功");
        emitEvent("superReset:cancel");
      }
    } catch (error) {
      setBtnLoading(false);
    }
  };
  const handleClickCode = () => {
    getKaptchaImageFn();
  };
  const handleGetPassword = async () => {
    try {
      const res = await generateSecurePasswordCrypto(8);
      setValue(res);
      form.setFieldValue("Pwd", res);
    } catch (error) {}
  };
  useEffect(() => {
    handleClickCode();
  }, []);
  return (
    <>
      <Form form={form}>
        <Form.Item
          label="新密码"
          name={"Pwd"}
          validateTrigger={false}
          rules={[{ required: true, message: "请输入新密码" }]}
        >
          <div className="flex">
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
            <Button
              type="primary"
              onClick={async () => {
                handleGetPassword();
              }}
              style={BTN_STYLE}
            >
              生成新密码
            </Button>
          </div>
        </Form.Item>
        <Form.Item
          name={"verifyCode"}
          label="验证码"
          rules={[{ required: true, message: "请输入验证码" }]}
          className={`mb-[20px]`}
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
      </Form>
    </>
  );
};
