import { createContext, useEffect, useState } from "react";
import {
  Form,
  Select,
  Input,
  Button,
  Alert,
  ConfigProvider,
  Flex,
  message,
  Modal
} from "antd";
import { ExclamationCircleFilled, LoadingOutlined } from "@ant-design/icons";
import {
  api_findByUserName,
  api_getKaptchaImage,
  api_getkaptchaSix,
  api_saveUserSecurityQuestion,
  api_updateUserSecurityQuestion,
  api_validateSecurityQuestion,
  userLogout
} from "../utils/services";
import { BTN_STYLE, QUESTION_POOL } from "../utils/constants";
import { MODAL_TYPE, typeTYPE } from "..";
import { useAppPassport } from "@root/src/core/helps";
import { RAG_APP_NAME, RAG_AUTH_PLUGIN_PREFIX } from "@root/src/const";
import { set } from "lodash";
const { Option } = Select;

export interface SecurityComProps {
  setShowReset?: (show: boolean) => void;
  setSecurityKey?: (key: string) => void;
  emitEvent?: (type: string, data?: any, failCb?: () => void) => void;
  onCancel: () => void;
  confirmLoading?: boolean;
  type?: typeTYPE;
}

const MB = "mb-[20px]";
const config = {
  content: (
    <>
      您还未设置过密保问题，无法进行忘记密码操作，请联系管理员重置您的密码，并在登录后设置密保问题及重置密码！
    </>
  )
};
export const SecurityCom = ({
  onCancel,
  type,
  emitEvent,
  confirmLoading,
  setShowReset,
  setSecurityKey
}: SecurityComProps) => {
  const { update, clear } = useAppPassport();
  const [modal, contextHolder] = Modal.useModal();
  const [form] = Form.useForm();
  const [options, setOptions] = useState<any[]>([]);
  const [codeLoading, setCodeLoading] = useState<boolean>(false);
  const [btnLoading, setBtnLoading] = useState<boolean>(false);
  const [btnOutLoading, setBtnOutLoading] = useState<boolean>(false);
  const [btnUserLoading, setBtnUserLoading] = useState<boolean>(false);
  const [kaptchaUrl, setKaptchaUrl] = useState("");
  const [selected, setSelected] = useState<(string | undefined)[]>([
    "",
    "",
    ""
  ]);
  const [verifyCode, setVerifyCode] = useState("");

  const getKaptchaImageFn = async () => {
    try {
      setCodeLoading(true);
      const res = await (type === MODAL_TYPE.RESET
        ? api_getkaptchaSix
        : api_getKaptchaImage)();
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

  const saveUserSecurityQuestions = async (params: any) => {
    console.log("params", params);

    try {
      setBtnLoading(true);
      const res = await api_saveUserSecurityQuestion(params);
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
          info.userInfo.hasSetSecurityQuestion = true;
        }
        update({ ...info });

        form.resetFields();
        setSelected([undefined, undefined, undefined]);
        onCancel();
      } else {
        form.setFieldValue("verifyCode", "");
        setVerifyCode("");
        handleClickCode();
      }
    } catch (error) {
      setBtnLoading(false);
    }
  };

  const updateUserSecurityQuestions = async (params: any) => {
    try {
      setBtnLoading(true);
      const res = await api_updateUserSecurityQuestion(params);
      setBtnLoading(false);
      if (res) {
        message.success("密保问题更新成功");
        form.resetFields();
        setSelected([undefined, undefined, undefined]);
        onCancel();
      }
    } catch (error) {
      setBtnLoading(false);
    }
  };

  const validateSecurityQuestion = async (params: any) => {
    try {
      setBtnLoading(true);
      const res = await api_validateSecurityQuestion(params);
      setBtnLoading(false);
      if (res?.data) {
        setSecurityKey && setSecurityKey(res.data);
        setShowReset && setShowReset(true);
        form.resetFields();
        setSelected([undefined, undefined, undefined]);
      } else {
        form.setFieldValue("verifyCode", "");
        setVerifyCode("");
        handleClickCode();
      }
    } catch (error) {
      setBtnLoading(false);
    }
  };

  const handleClickCode = () => {
    getKaptchaImageFn();
  };

  const onValuesChange = (_: any, allValues: any) => {
    setSelected([
      allValues.question1,
      allValues.question2,
      allValues.question3
    ]);
  };

  const getDatas = async () => {
    const values = await form.validateFields();

    if (type === MODAL_TYPE.RESET && options.length !== 3) {
      return {};
    }
    const payload =
      type === MODAL_TYPE.RESET
        ? [
            {
              question: values.question1,
              ...options[0],
              answer: values.answer1
            },
            {
              question: values.question2,
              ...options[1],
              answer: values.answer2
            },
            {
              question: values.question3,
              ...options[2],
              answer: values.answer3
            }
          ]
        : [
            { question: values.question1, answer: values.answer1 },
            { question: values.question2, answer: values.answer2 },
            { question: values.question3, answer: values.answer3 }
          ];
    const data: any = {
      userSecurityQuestionList: payload,
      verifyCode: values.verifyCode
    };
    if (type === MODAL_TYPE.RESET) {
      data["username"] = values.username;
    }
    return data;
  };

  const handleOk = async () => {
    try {
      const params = await getDatas();
      saveUserSecurityQuestions(params);
    } catch (err) {
      console.log("err", err);
    }
  };

  const makeUniqueValidator = (fieldKey: string, otherKeys: string[]) => ({
    validator(_: any, value: string) {
      if (!value) return Promise.resolve();
      for (const key of otherKeys) {
        const other = form.getFieldValue(key);
        if (other && other === value) {
          return Promise.reject(new Error("三个问题不能选择相同的问题"));
        }
      }
      return Promise.resolve();
    }
  });

  const handleGetSecurity = async (user: string) => {
    try {
      setBtnUserLoading(true);
      const res = await api_findByUserName(user);
      setBtnUserLoading(false);
      if (res?.data?.length === 3) {
        setOptions(res.data);
        setSelected([
          res.data[0].question,
          res.data[1].question,
          res.data[2].question
        ]);
        form.setFieldsValue({
          question1: res.data[0].question,
          question2: res.data[1].question,
          question3: res.data[2].question
        });
      } else {
        modal.warning(config);
      }
    } catch (error) {
      setBtnUserLoading(false);
      setCodeLoading(false);
    }
  };

  const renderSelect = (fieldName: string, index: number) => {
    const otherSelected = selected.filter((_, i) => i !== index);
    return (
      <Form.Item
        name={fieldName}
        label={`问题 ${index + 1}`}
        rules={
          type === MODAL_TYPE.RESET
            ? []
            : [
                { required: true, message: "请选择密保问题" },
                makeUniqueValidator(
                  fieldName,
                  ["question1", "question2", "question3"].filter(
                    (k) => k !== fieldName
                  )
                )
              ]
        }
        style={{ marginBottom: "16px" }}
      >
        {type === MODAL_TYPE.RESET ? (
          <span>{selected[index]}</span>
        ) : (
          <Select
            placeholder="请选择问题"
            showSearch
            optionFilterProp="children"
            allowClear
          >
            {QUESTION_POOL.map((q) => (
              <Option key={q} value={q} disabled={otherSelected.includes(q)}>
                {q}
              </Option>
            ))}
          </Select>
        )}
      </Form.Item>
    );
  };

  const logout = async () => {
    try {
      setBtnOutLoading(true);
      const res = await userLogout();
      setBtnOutLoading(false);
      if (res) {
        clear();
        window.location.pathname = "/login";
      }
    } catch (error) {
      setBtnOutLoading(false);
    }
  };

  useEffect(() => {
    handleClickCode();
  }, []);
  return (
    <>
      {(type === MODAL_TYPE.SECURITYSET ||
        type === MODAL_TYPE.REGISTER ||
        type === MODAL_TYPE.SECURITYUPDATE) && (
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
            message="请您设置密保问题用于忘记密码时重置密码！"
            type="warning"
            style={{ color: "#4E5969", fontSize: 12 }}
            icon={
              <ExclamationCircleFilled
                className="text-[14px]"
                style={{ color: "#FAAD14" }}
              />
            }
          />
        </ConfigProvider>
      )}
      <Form
        form={form}
        onValuesChange={onValuesChange}
        labelCol={{ span: 6 }}
        labelAlign="left"
        className="mt-4 px-2 h-[356px] overflow-y-auto"
      >
        {type === MODAL_TYPE.RESET && (
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <div className="flex">
              <Input placeholder="请输入用户名" className="mr-2" />
              <Button
                type="primary"
                onClick={async () => {
                  const user = await form.validateFields(["username"]);
                  if (!user?.username) {
                    return;
                  }
                  handleGetSecurity(user.username);
                }}
                loading={btnUserLoading}
                style={BTN_STYLE}
              >
                获取用户密保
              </Button>
            </div>
          </Form.Item>
        )}

        {renderSelect("question1", 0)}
        <Form.Item
          name="answer1"
          label="答案"
          rules={[{ required: true, message: "请输入答案" }]}
          className={`${MB}`}
        >
          <Input placeholder="请输入答案" maxLength={30} />
        </Form.Item>

        {renderSelect("question2", 1)}
        <Form.Item
          name="answer2"
          label="答案"
          rules={[{ required: true, message: "请输入答案" }]}
          className={`${MB}`}
        >
          <Input placeholder="请输入答案" maxLength={30} />
        </Form.Item>

        {renderSelect("question3", 2)}
        <Form.Item
          name="answer3"
          label="答案"
          rules={[{ required: true, message: "请输入答案" }]}
          className={`${MB}`}
        >
          <Input placeholder="请输入答案" maxLength={30} />
        </Form.Item>
        {(type === MODAL_TYPE.REGISTER ||
          type === MODAL_TYPE.SECURITYSET ||
          type === MODAL_TYPE.RESET) && (
          <Form.Item
            name={"verifyCode"}
            label="验证码"
            rules={[{ required: true, message: "请输入验证码" }]}
            className={`${MB}`}
          >
            <Flex>
              <Input
                placeholder="输入验证码"
                value={verifyCode}
                className="mr-2"
                maxLength={30}
                onChange={(e) => setVerifyCode(e.target.value)}
              />

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
      </Form>

      {type === MODAL_TYPE.REGISTER && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 8,
            marginTop: type === MODAL_TYPE.REGISTER ? 8 : 16
          }}
        >
          <Button
            style={{ width: "48%" }}
            onClick={() => {
              setSelected([undefined, undefined, undefined]);
              onCancel();
            }}
          >
            上一步
          </Button>
          <Button
            style={{ width: "48%" }}
            onClick={async () =>
              emitEvent &&
              emitEvent("register:securitySet", await getDatas(), () => {
                form.setFieldValue("verifyCode", "");
                setVerifyCode("");
                handleClickCode();
              })
            }
            type="primary"
            loading={confirmLoading}
          >
            注册
          </Button>
        </div>
      )}
      {type === MODAL_TYPE.RESET && (
        <div className="flex justify-center">
          <Button
            onClick={() => {
              form.resetFields();
              setSelected([undefined, undefined, undefined]);
              onCancel();
            }}
            className="mr-4"
          >
            取消
          </Button>
          <Button
            type="primary"
            onClick={async () => {
              try {
                const params = await getDatas();
                validateSecurityQuestion(params);
                //setShowReset && setShowReset(true);
              } catch (err) {
                console.log("err", err);
              }
            }}
            loading={btnLoading}
            style={BTN_STYLE}
          >
            确定
          </Button>
        </div>
      )}
      {type === MODAL_TYPE.SECURITYSET && (
        <div className="flex justify-center">
          <Button
            type="primary"
            onClick={handleOk}
            loading={btnLoading}
            style={BTN_STYLE}
          >
            确定
          </Button>
          <Button
            type="link"
            onClick={logout}
            loading={btnOutLoading}
            className="!text-slate-400"
          >
            退出登录
          </Button>
        </div>
      )}
      {type === MODAL_TYPE.SECURITYUPDATE && (
        <div className="flex justify-center">
          <Button
            onClick={() => {
              form.resetFields();
              setSelected([undefined, undefined, undefined]);
              onCancel();
            }}
            className="mr-4"
          >
            取消
          </Button>
          <Button
            type="primary"
            onClick={async () => {
              try {
                const params = await getDatas();
                updateUserSecurityQuestions(params.userSecurityQuestionList);
              } catch (err) {
                console.log("err", err);
              }
            }}
            loading={btnLoading}
            style={BTN_STYLE}
          >
            确定
          </Button>
        </div>
      )}
      {contextHolder}
    </>
  );
};
