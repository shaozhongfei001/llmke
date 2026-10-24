import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import avatar_blue from "@/assets/img/avatar_blue.svg";
import { RAG_APP_NAME, RAG_AUTH_PLUGIN_PREFIX } from "@root/src/const";
import useMenus from "./hooks/useMenus";
import { traverse } from "../util";
import navLogo from "@/assets/img/nav-logo.png";
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

  const rag_styles_overlap_default = {
    token: {
      colorText: "#222222"
    },
    components: {
      Layout: {
        headerBg: "#fff"
      },
      Select: {
        optionSelectedBg: "#F3F9FF",
        optionSelectedColor: "#014DDF"
      },
      Divider: {
        colorSplit: "#014DDF"
      },
      Button: {
        defaultActiveBg: "#fff",
        defaultColor: "#014DDF",
        defaultActiveColor: "#014DDF",
        colorBgContainer: "#fff"
      }
    },
    customized: {
      appname: {
        color: "#014DDF",
        fontWeight: "400",
        fontSize: "18px"
      },
      logo: {
        objectFit: "cover",
        margin: "15px 20px",
        height: "30px"
      },
      userName: {
        display: "flex",
        alignItems: "center",
        color: "#333",
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
        borderBottom: "2px solid #014DDF"
      }
    }
  };

  const LOGO_CONFIG = {
    logoImg: navLogo,
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
