import homeBg from "@/assets/login/homeBg.png";
import leftImg from "@/assets/login/left.jpg";
import logoImg from "@/assets/login/logoImg.png";
import { Layout, message } from "antd";
import { Encrypt } from "./utils";
import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { RAG_APP_NAME, RAG_AUTH_PLUGIN_PREFIX } from "../../const";
import { useAppPassport } from "@root/src/core/helps";
import Login from "@root/src/components/Login";
import { api_getKaptchaImage, login, regist } from "./services";

function LoginPage() {
  const { update } = useAppPassport();
  const navigator = useNavigate();
  const [btnLoading, setBtnLoading] = useState(false);
  const [isRegister, setIsRegister] = useState<boolean>(false);
  const handleReister = async (data: any, failCb?: () => void) => {
    const params = {
      ...data,
      password: Encrypt(data.password),
      passwordAffirm: Encrypt(data.passwordAffirm),
      userRealname: data.userName
    };
    console.log("regist->params", params);

    const res = await regist(params);
    if (res) {
      setIsRegister(false);
      message.success("注册成功, 去登录吧");
      eventEmit("login:registerCodeClick", null);
    } else {
      failCb && failCb();
    }
  };

  const handleLogin = async (data: any) => {
    try {
      setBtnLoading(true);
      const res: any = await login({
        ...data,
        password: Encrypt(data.password)
      });
      setBtnLoading(false);
      if (res) {
        const infoMapper = {
          userInfo: {
            userName: res.userName,
            email: res.userEmail,
            avatar: res.url,
            phone: res.userPhone,
            realName: res.userRealname,
            token: res.token,
            id: res.id,
            hasSetSecurityQuestion: res.hasSetSecurityQuestion,
            hasAdminResetPassword: res.hasAdminResetPassword
          },
          appInfo: {
            name: RAG_APP_NAME,
            authors: "",
            version: "0.0.1",
            theme: "light",
            lang: "cn_zh"
          }
        };
        update(infoMapper);

        navigator("/");
      }
    } catch (e) {
      console.log(e);
    }
  };

  const [kaptchaUrl, setKaptchaUrl] = useState("");
  const [registreKaptchaUrl, setRegistreKaptchaUrl] = useState("");
  const getKaptchaImageFn = async () => {
    try {
      const res = await api_getKaptchaImage();
      if (res) {
        const imgBlob = new Blob([res], { type: "image/jpeg" });
        const imageUrl = window.URL.createObjectURL(imgBlob);
        setKaptchaUrl(imageUrl);
        setRegistreKaptchaUrl(imageUrl);
      }
    } catch (error) {}
  };
  useEffect(() => {
    getKaptchaImageFn();
    return () => {
      window.URL.revokeObjectURL(kaptchaUrl);
    };
  }, []);

  const eventEmit = async (name: string, data: any, failCb?: () => void) => {
    switch (name) {
      case "login:register":
        await handleReister(data, failCb);
        break;
      case "login:login":
        await handleLogin(data);
        break;
      case "login:codeClick":
        await getKaptchaImageFn();
        break;
      case "login:registerCodeClick":
        await getKaptchaImageFn();
        break;
      default:
        break;
    }
  };
  return (
    <Layout style={{ height: "100vh" }}>
      <Login
        loginLoading={btnLoading}
        registerLoading={btnLoading}
        homeBg={homeBg}
        leftImg={leftImg}
        logoImg={logoImg}
        codeImgSrc={kaptchaUrl}
        registreKaptchaUrl={registreKaptchaUrl}
        eventEmit={eventEmit}
        isRegister={isRegister}
        setIsRegister={setIsRegister}
      />
    </Layout>
  );
}

export default LoginPage;
