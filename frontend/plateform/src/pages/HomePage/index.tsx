import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import avatar_blue from "@/assets/img/avatar_blue.svg";
import { RAG_APP_NAME, RAG_AUTH_PLUGIN_PREFIX } from "@root/src/const";
import useMenus from "./hooks/useMenus";
import { traverse } from "../util";
// 应用品牌标识：白色章鱼（唯一形状源 assets/brand/octopus-source.jpg，透明版为其使用适配）
import brandOctopus from "@/assets/brand/octopus-white.png";
import { useAppPassport } from "@root/src/core/helps";
import Dashborad from "@root/src/components/Dashboard";
import { userLogout } from "./hooks/managerServices";
import PasswordModal, { MODAL_TYPE } from "@root/src/components/PasswordModal";
import { set } from "lodash";

function HomePage() {
  const { userInfo, clear } = useAppPassport();
  const [visible, setVisible] = useState(false);
  const [modalType, setModalType] = useState<any>("");
  const [defaultKey, setDefaultKey] = useState<string>();
  const navigator = useNavigate();
  const location = useLocation();
  const [userInfoLocal, setUserInfoLocal] = useState<any>({});
  const { navBarData } = useMenus();
  useEffect(() => {
    const userInfo_str = localStorage.getItem(
      `${RAG_AUTH_PLUGIN_PREFIX}${RAG_APP_NAME}`
    );
    let userInfo: any = {};
    if (userInfo_str) {
      userInfo = JSON.parse(userInfo_str);
    }
    setUserInfoLocal(userInfo);
    // 判断是否弹出来密保问题弹窗
    const info = userInfo?.userInfo || {};
    const curToken = info?.token || "";
    const hasSetSecurityQuestion = info?.hasSetSecurityQuestion;
    const hasAdminResetPassword = info?.hasAdminResetPassword;
    if (curToken) {
      if (typeof hasAdminResetPassword === "boolean" && hasAdminResetPassword) {
        setModalType(MODAL_TYPE.AfterSuperReset);
        setVisible(true);
      } else if (
        typeof hasSetSecurityQuestion === "boolean" &&
        !hasSetSecurityQuestion
      ) {
        setModalType(MODAL_TYPE.SECURITYSET);
        setVisible(true);
      }
    }
  }, []);

  useEffect(() => {
    let curMenu = "chats";
    traverse(navBarData, (node: { key: string }) => {
      if (location.pathname.includes(node.key)) {
        curMenu = location.pathname;
      }
    });
    setDefaultKey(curMenu);
    if (navBarData?.length) {
      const { pathname } = location;
      let _menu = {} as any;
      const rootPath = "/";
      switch (pathname) {
        case rootPath:
          _menu = navBarData[0];
          break;
        default:
          _menu =
            navBarData.find(
              (n: any) =>
                n.key === pathname ||
                (n.key !== pathname && pathname.includes(n.key))
            ) || undefined;
          break;
      }
      const { routes } = _menu;
      if (_menu && _menu.key && routes && routes.length) {
        const _route =
          _menu.key === pathname || pathname === rootPath
            ? routes[0]
            : routes.find((r: any) => r.key === pathname);

        if (_route && _route.key) {
          navigator(_route.key + location.search);
        }
      }
    }
    // if (location.pathname === "/") {
    //   if (navBarData?.length) {
    //     navigator(navBarData[0].key);
    //   }
    // }
  }, [navBarData, location.pathname]);

  const handleNavClick = (key: string) => {
    navigator(key);
  };
  const logout = async () => {
    const res = await userLogout();
    if (res) {
      clear();
      window.location.pathname = "/login";
    }
  };

  const handleUserMenuClick = (key: string) => {
    switch (key) {
      case "legal":
        window.open("/legal", "_blank");
        break;
      case "logout":
        // reset cookie
        logout();
        break;
      default:
        break;
    }
  };

  const handleEvent = (n: string, d: any) => {
    // console.log('dashboard click', n, d)
    switch (n) {
      case "dashboard:navbar_item_click":
        handleNavClick(d.path);
        break;
      case "dashboard:user_item_click":
        handleUserMenuClick(d);
        break;
      default:
        break;
    }
  };

  const userItems: any[] = [
    {
      key: "logout",
      label: "登出"
    }
  ];

  /**
   * SPECTRA 主题：仅替换颜色/表面/品牌标志。
   * 字号（appname 18px、userName 14px）与导航高度 60px 保持改造前原值。
   */
  const rag_styles_overlap_default = {
    token: {
      colorText: "#F0F2F0"
    },
    components: {
      Layout: {
        headerBg: "#0B1014"
      },
      Select: {
        optionSelectedBg: "rgba(216, 189, 137, 0.14)",
        optionSelectedColor: "#D8BD89"
      },
      Divider: {
        colorSplit: "#243035"
      },
      Button: {
        defaultActiveBg: "#1A292E",
        defaultColor: "#B8C3C3",
        defaultActiveColor: "#E8D4A7",
        colorBgContainer: "#10181C"
      }
    },
    customized: {
      appname: {
        color: "#F0F2F0",
        fontWeight: "400",
        fontSize: "18px"
      },
      logo: {
        // 纯白章鱼等比例显示，不压扁/拉长/旋转
        objectFit: "contain",
        margin: "15px 20px",
        height: "30px"
      },
      userName: {
        display: "flex",
        alignItems: "center",
        color: "#B8C3C3",
        fontSize: "14px",
        fontWeight: "400px"
      },
      navBtn: {
        border: "none",
        boxShadow: "none",
        height: "60px",
        display: "block",
        borderRadius: "0",
        borderBottom: "2px solid transparent"
      },
      navBtnActive: {
        border: "none",
        boxShadow: "none",
        height: "60px",
        display: "block",
        borderRadius: "0",
        borderBottom: "2px solid #D8BD89"
      }
    }
  };

  const LOGO_CONFIG = {
    logoImg: brandOctopus,
    hasLogo: true
  };

  return (
    <>
      <Dashborad
        navBarOpt={{
          type: "dropdown",
          navBarData,
          defaultKey
        }}
        event_emitter={handleEvent}
        avatar={{
          userName: (userInfoLocal && userInfoLocal?.userInfo?.userName) || "",
          realName: (userInfoLocal && userInfoLocal?.userInfo?.realName) || "",
          email: (userInfoLocal && userInfoLocal?.userInfo?.email) || "",
          url: (userInfoLocal && userInfoLocal?.userInfo?.avatar) || "",
          dropDownList: userItems || []
        }}
        style={rag_styles_overlap_default}
        logo={LOGO_CONFIG}
      >
        <Outlet />
      </Dashborad>
      <PasswordModal
        visible={visible}
        onCancel={() => setVisible(false)}
        type={modalType}
      />
    </>
  );
}

export default HomePage;
