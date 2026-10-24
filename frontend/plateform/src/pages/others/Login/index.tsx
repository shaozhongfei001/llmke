import { Encrypt } from "./utils";
import { Layout, message } from "antd";
import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { RAG_APP_NAME, RAG_AUTH_PLUGIN_PREFIX } from "../../../const/index";
import { useAppPassport } from "../../../core/helps";
import Login from "@/components/Login";
import { api_getKaptchaImage, login, regist } from "./services";

function LoginPage() {
  const { update } = useAppPassport();
  const navigator = useNavigate();
  const homeBg = `/icons/login/${import.meta.env.VITE_LOGIN_HOME_BG}`;
  const leftImg = `/icons/login/${import.meta.env.VITE_LOGIN_LEFT_IMG}`;
  const logoImg = `/icons/login/${import.meta.env.VITE_LOGIN_LOGO_IMG}`;
  const [btnLoading,setBtnLoading]=useState(false)
  const handleReister = async (data: any) => {
    const res = await regist({
      ...data,
      password: Encrypt(data.password),
      passwordAffirm: Encrypt(data.passwordAffirm),
      userRealname: data.userName
    });
    if (res) {
      message.success("注册成功, 去登录吧");
      window.location.reload();
    }
  };

  const handleLogin = async (data: any) => {
    try {
      setBtnLoading(true)
      const res: any = await login({
        ...data,
        password: Encrypt(data.password)
      });
      setBtnLoading(false)
      if (res) {
        const infoMapper = {
          userInfo: {
            userName: res.userName,
            email: res.userEmail,
            avatar: res.url,
            phone: res.userPhone,
            realName: res.userRealname,
            token: res.token,
            id: res.id
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
        // localStorage.setItem(`${RAG_AUTH_PLUGIN_PREFIX}${RAG_APP_NAME}`, `${JSON.stringify(infoMapper)}`);

        navigator("/");
      }
    } catch (e) {
      console.log(e);
    }
  };

  const [kaptchaUrl, setKaptchaUrl] = useState("");
  const [registreKaptchaUrl, setRegistreKaptchaUrl] = useState("");
  const getKaptchaImageFn = async ()=>{
      try {
        const res = await api_getKaptchaImage()
        if (res) {
          const imgBlob = new Blob([res], { type: "image/jpeg" });
          const imageUrl = window.URL.createObjectURL(imgBlob);
          setKaptchaUrl(imageUrl);
          setRegistreKaptchaUrl(imageUrl);
        }
      } catch (error) {
        
      }
    }
    useEffect(() => {
      getKaptchaImageFn()
      return () => {
        window.URL.revokeObjectURL(kaptchaUrl);
      };
    }, []);

  const eventEmit = async (name: string, data: any) => {
    switch (name) {
      case "login:register":
        await handleReister(data);
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
        eventEmit={eventEmit}
      />
    </Layout>
  );
}

export default LoginPage;
