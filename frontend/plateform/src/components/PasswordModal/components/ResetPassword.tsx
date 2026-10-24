import { Button, Form, Input } from "antd";
import { useEffect, useState } from "react";
import { api_updatePasswordByQuestion } from "../utils/services";
import { Encrypt } from "@root/src/pages/Login/utils";
import { PASSWORD_REGEX, PASSWORD_WARN_MSG } from "@root/src/core/helps";
import { BTN_STYLE } from "../utils/constants";

export const ResetPassword = ({ securityKey, emitEvent }: any) => {
  const [form] = Form.useForm();
  const [btnLoading, setBtnLoading] = useState<boolean>(false);
  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setBtnLoading(true);
      const res = await api_updatePasswordByQuestion({
        validateKey: securityKey,
        password: Encrypt(values.newPwd)
      });
      setBtnLoading(false);
      if (res) {
        emitEvent("resetPassword:cancel");
      }
    } catch (error) {
      setBtnLoading(false);
    }
  };
  return (
    <>
      <Form layout="vertical" form={form}>
        <Form.Item
          label="新密码"
          name={"newPwd"}
          validateTrigger={false}
          rules={[
            { required: true, message: "请输入新密码" },
            {
              message: PASSWORD_WARN_MSG,
              pattern: PASSWORD_REGEX
            }
          ]}
        >
          <Input.Password
            id="newPwd"
            placeholder={PASSWORD_WARN_MSG}
            maxLength={64}
          />
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
                if (!value || getFieldValue("newPwd") === value) {
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
              emitEvent("resetPassword:cancel");
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
