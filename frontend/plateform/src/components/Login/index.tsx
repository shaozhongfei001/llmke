import { ConfigProvider, Flex, Form } from "antd";
import LoginBox from "./LoginBox";
import RegisterBox from "./RegisterBox";
import brandOctopus from "@/assets/brand/octopus-white.png";
import { spectraColors } from "@/styles/spectraTheme";

/**
 * 登录页视觉：SPECTRA
 * - 左侧为深色视觉区，承载**纯白章鱼**（唯一形状源 assets/brand/octopus-source.jpg 的透明使用版），
 *   不使用会议室照片、人物剧照，也不使用环形/镜头光圈构图。
 * - 右侧表单保持原 Ant Design Input / Button 尺寸与校验逻辑（含验证码、注册、忘记密码、错误提示）。
 * - 卡片宽高、最小宽度沿用改造前的 505*2 / 840 / 10px 圆角，避免改变控件密度。
 */
const defaultStyle = {
  colorPrimary: spectraColors.gold,
  defaultBg: spectraColors.surface
};

interface LoginStyle {
  defaultBg?: string;
  colorPrimary?: string;
}
interface LoginProps {
  /** 兼容旧调用方：传入后作为页面背景（SPECTRA 默认使用 CSS 暗色渐层，不启用图片背景） */
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
          colorPrimary: loginStyle?.colorPrimary || defaultStyle.colorPrimary,
          colorBgContainer: spectraColors.surface,
          colorBorder: spectraColors.line,
          colorText: spectraColors.text,
          colorTextPlaceholder: spectraColors.textMuted,
          colorError: spectraColors.danger
        },
        components: {
          Button: {
            defaultBg: loginStyle?.defaultBg || defaultStyle.defaultBg,
            primaryColor: spectraColors.onGold
          }
        }
      }}
    >
      <div className="spectra-login">
        <Flex
          className="spectra-login-card"
          style={{
            height: "505px",
            minHeight: "393px",
            width: "calc(505px * 2)",
            minWidth: "840px",
            borderRadius: "10px"
          }}
        >
          <Flex className="spectra-login-visual" style={{ width: "50%" }}>
            <img
              className="spectra-login-octopus"
              src={brandOctopus}
              alt="品牌标志"
            />
            <div className="spectra-login-brand">
              <div className="spectra-login-brand-name">客户经营数字化</div>
              <div className="spectra-login-brand-line" />
              <div className="spectra-login-brand-sub">
                让客户经营变得更简单
              </div>
            </div>
          </Flex>
          <Flex
            flex={1}
            justify="center"
            align="center"
            className="spectra-login-form"
          >
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
                  setIsRegister={setIsRegister}
                  codeImgSrc={codeImgSrc}
                  eventEmit={eventEmit}
                />
              )}
            </Form>
          </Flex>
        </Flex>
      </div>
    </ConfigProvider>
  );
};

export default Login;
