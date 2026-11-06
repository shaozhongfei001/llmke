import { ConfigProvider, Divider, Dropdown, Flex, Layout, Tooltip } from "antd";
import React, { ReactNode, useEffect, useMemo, useState } from "react";
import { ProLayout } from "@ant-design/pro-components";
import "./style.less";
import navbarBg from "../../assets/navbarBg_spectra.svg";
import { merge } from "lodash";
import AiRobit from "@/assets/img/aiRobit.png";
import SiderOpt from "@/assets/svg/siderOpt.svg";
import PackUp from "@/assets/svg/packUp.svg";
import Unfold from "@/assets/svg/unfoId.svg";
import { eventBus, EventBusList } from "@root/src/core/helps/editorEventBus";
import { hide } from "@udecode/plate-floating";
import { version } from "@/const";
import {
  SafetyCertificateOutlined,
  LogoutOutlined,
  InfoCircleOutlined
} from "@ant-design/icons";

interface IDashboardProps {
  children?: ReactNode;
  appInfo?: {
    name: string;
    version?: string;
  };
  navBarOpt?: {
    type?: "select" | "button" | "dropdown";
    navBarData?: NavBarItemType[];
    defaultKey?: string | number;
  };
  sideBarData?: SideBarItemType[];
  avatar?: {
    userName: string;
    url: string;
    dropDownList: DropDownItemType[];
    realName?: string;
    email?: string;
  };
  noticeData?: DropDownItemType[];
  style?: any;
  logo?: {
    logoImg: any;
    hasLogo: boolean;
  };
  event_emitter?: (eventName: string, data: any) => void;
}

interface NavBarItemType {
  key: string | number;
  name: string;
  disabled?: boolean;
  children?: NavBarItemType[];
  routes?: NavBarItemType[];
  icon?: string;
  activeIcon?: string;
  path?: string;
}

interface SideBarItemType {
  key: string | number;
  name: string;
  disabled?: boolean;
  icon?: ReactNode;
  children?: SideBarItemType[];
}

interface DropDownItemType {
  key: string | number;
  label: string;
  icon?: ReactNode;
  disabled?: boolean;
}

const noPaddingUrl = [
  "chats/main",
  "/docWriting/docs",
  "/system",
  "/chats/knowledgeBase/",
  "/docWriting/resource/"
];

const Dashborad: React.FC<IDashboardProps> = (props: IDashboardProps) => {
  const {
    appInfo,
    navBarOpt = {},
    sideBarData,
    avatar,
    noticeData,
    style = {},
    logo,
    event_emitter
  } = props;
  const { type = "select", navBarData = [], defaultKey = "/" } = navBarOpt;
  const getPath = (data: any) => {
    return data.flatMap((item: any) => {
      if (item.routes) {
        return [item.path, ...item.routes.map((route: any) => route.path)];
      } else {
        return item.path;
      }
    });
  };

  const paths = useMemo(() => {
    // console.log("getPath(navBarData)", getPath(navBarData));

    return getPath(navBarData);
  }, [navBarData]);

  const handleNavButtonClick = (key: any) => {
    console.log("点击函数", key);
    event_emitter && event_emitter("dashboard:user_item_click", key);
  };

  const noSiderBar = ["/docWriting"];
  const [pathname, setPathname]: any = useState(defaultKey);
  const excludesUrl = ["chats", "/chats", "/docWriting", "/system"];

  useEffect(() => {
    // console.log("defaultKey", defaultKey);
    if (location.pathname !== "/") {
      setPathname(location.pathname);
    } else {
      setPathname(defaultKey);
    }
  }, [location, defaultKey]);

  // 文档界面二级导航栏状态
  const [docNavState, setDocNavState] = useState<{
    state: "open" | "close";
    isHover: boolean;
  }>({
    state: "open",
    isHover: false
  });

  const hideLayout = () => {
    return import.meta.env.VITE_HEADLESS === "true";
  };

  const getPadding = (noPaddingUrl: string[]) => {
    if (pathname.includes("/docWriting/resource/")) {
      return "16px 0 0 16px";
    }
    return noPaddingUrl.some((i) => pathname.includes(i)) ? "0" : "16px";
  };

  return (
    <ConfigProvider
      theme={merge(
        {
          token: {
            // colorTextPlaceholder: '#eee',
            // colorBgContainer: 'rgb(250, 251, 255)',
            // colorBgBase: 'rgb(250, 251, 255)',
            // heightLayoutHeader: 60,
          },
          components: {
            ProLayout: { heightLayoutHeader: 60 },
            Layout: {
              paddingInlinePageContainerContent: 0,
              paddingBlockPageContainerContent: 0,
              // SPECTRA：近黑画布 + 深色 shell（几何尺寸保持原值）
              bgLayout: "#090D11",
              headerBg: "#0B1014",
              colorMenuBackground: "#0B1014",
              footerPadding: "0",
              headerHeight: 60,
              headerPadding: "0px 16px"
            },
            Select: {
              // selectorBg: '#00004d',
              // optionSelectedBg: '#00004d',
              // optionSelectedColor: '#fff',
            },
            Divider: {
              colorSplit: "#243035"
            },
            Button: {
              defaultColor: "#B8C3C3",
              defaultBg: "#10181C",
              defaultHoverBg: "#1A292E",
              defaultHoverColor: "#E8D4A7",
              borderRadius: 4
            },
            Menu: {
              itemMarginBlock: "8px",
              colorTextMenu: "#91A1A3",
              colorTextMenuSelected: "#D8BD89"
            }
          }
        },
        style
      )}
    >
      {hideLayout() ? (
        <div className="noLayout">
          <MainContent
            event_emitter={event_emitter}
            children={props.children}
            pathname={pathname}
            docNavState={docNavState}
            setDocNavState={setDocNavState}
            navBarData={navBarData}
            setPathname={setPathname}
          />
        </div>
      ) : (
        <ProLayout
          route={{ path: defaultKey, routes: navBarData }}
          layout="mix"
          fixSiderbar={true}
          splitMenus={true}
          disableMobile={true}
          location={{ pathname }}
          style={{ padding: 0, minWidth: "1200px" }}
          collapsed={false}
          siderWidth={84}
          collapsedButtonRender={() => false}
          avatarProps={{
            src: avatar?.url,
            size: 32,
            className: "border border-gray-200",
            title: avatar?.userName,
            render: (props, dom) => {
              return (
                <Dropdown
                  menu={{
                    items: [
                      {
                        key: "user-info",
                        label: (
                          <div className="p-4 cursor-pointer hover:bg-gray-50">
                            <div>
                              <div className="font-medium text-base">
                                {avatar?.realName || "未设置"}
                              </div>
                              <div className="text-gray-600 text-sm mb-1">
                                {avatar?.userName}
                              </div>
                              <div className="text-gray-500 text-sm">
                                {avatar?.email || "暂无邮箱"}
                              </div>
                            </div>
                          </div>
                        ),
                        disabled: true
                      },
                      { type: "divider" },
                      {
                        key: "legal",
                        label: (
                          <div className="flex items-center px-4 py-2">
                            <SafetyCertificateOutlined className="mr-2" />
                            <span>隐私政策</span>
                          </div>
                        ),
                        onClick: () => handleNavButtonClick("legal")
                      },
                      {
                        key: "logout",
                        label: (
                          <div className="flex items-center px-4 py-2 text-red-500">
                            <LogoutOutlined className="mr-2" />
                            <span>退出登录</span>
                          </div>
                        ),
                        onClick: () => handleNavButtonClick("logout")
                      },
                      { type: "divider" } as any,
                      {
                        key: "version",
                        label: (
                          <div className="flex items-center px-4 py-2 text-gray-400 text-xs justify-center">
                            <InfoCircleOutlined className="mr-1" />
                            <span>
                              版本 {import.meta.env.VITE_PLATEFORM_VERSION}
                            </span>
                          </div>
                        ),
                        disabled: true
                      } as const
                    ]
                  }}
                  placement="bottomRight"
                  dropdownRender={(menu) => (
                    <div className="spectra-dropdown-panel rounded-lg shadow-lg border border-gray-100 min-w-[200px]">
                      {menu}
                    </div>
                  )}
                >
                  <div className="flex items-center cursor-pointer hover:bg-gray-50 rounded-full px-2 py-1">
                    {dom}
                  </div>
                </Dropdown>
              );
            }
          }}
          logo={logo && logo.logoImg}
          // logo={<span className="font-bold">V1.1</span>}
          title={false}
          hasSiderMenu={noSiderBar.some((item) => pathname.indexOf(item) > -1)}
          menuItemRender={(item: any, dom) => {
            return (
              <div
                onClick={() => {
                  setPathname(item.path);
                  event_emitter &&
                    event_emitter("dashboard:navbar_item_click", item);
                }}
                className="flex flex-col items-center relative h-full justify-center"
              >
                {item.icon && (
                  <img
                    src={
                      pathname.startsWith(item.path)
                        ? item.activeIcon
                        : item.icon
                    }
                    className="w-6 h-6 mb-[10px]"
                  />
                )}
                <div
                  style={{
                    textAlign: "center",
                    width: "100%",
                    whiteSpace: "break-spaces",
                    lineHeight: 1,
                    // SPECTRA：当前项暖金，其他项冷灰（字号/行高沿用全局继承）
                    color: pathname.startsWith(item.path) ? "#D8BD89" : "#91A1A3"
                  }}
                >
                  {item.name}
                </div>
                {!item.icon && pathname.startsWith(item.path) && (
                  <img className="w-full absolute bottom-0" src={navbarBg} />
                )}
              </div>
            );
          }}
          menuRender={(props, defaultDom) => {
            return !noSiderBar.some((item) => pathname.indexOf(item) > -1) ? (
              defaultDom
            ) : (
              <></>
            );
          }}
        >
          <div
            className="noContainer relative"
            style={{
              height: "calc(100vh - 55px)",
              overflow: "hidden",
              padding: getPadding(noPaddingUrl),
              // SPECTRA：主工作区近黑画布（替换原蓝紫渐变）
              background: "#090D11"
            }}
          >
            <MainContent
              event_emitter={event_emitter}
              children={props.children}
              pathname={pathname}
              docNavState={docNavState}
              setDocNavState={setDocNavState}
              navBarData={navBarData}
              setPathname={setPathname}
            />
          </div>
        </ProLayout>
      )}
    </ConfigProvider>
  );
};

export default Dashborad;

const MainContent = ({
  pathname,
  docNavState,
  setDocNavState,
  navBarData,
  setPathname,
  children,
  event_emitter
}: {
  event_emitter: any;
  children: any;
  pathname: any;
  docNavState: any;
  setDocNavState: any;
  navBarData: any;
  setPathname: any;
}) => {
  return (
    <Flex className="w-full h-full">
      {pathname.includes("/docWriting") &&
        !pathname.includes("/docWriting/docs") && (
          <Flex
            vertical
            align="center"
            gap={16}
            style={{
              width: docNavState.state === "close" ? "0" : "60px",
              transition: "0.3s"
            }}
            className="relative bg-[rgba(255,255,255,0.4)] mb-[20px] h-[calc(100%-20px)] shadow rounded-lg py-[16px] mr-[20px]"
          >
            <div
              onMouseEnter={() =>
                setDocNavState((p: any) => ({ ...p, isHover: true }))
              }
              onMouseLeave={() =>
                setDocNavState((p: any) => ({ ...p, isHover: false }))
              }
              className="absolute right-[-13px] top-[calc(50%-8px)] cursor-pointer"
            >
              <Tooltip
                placement="right"
                title={docNavState.state === "close" ? "展开" : "收起"}
              >
                <img
                  src={
                    docNavState.isHover
                      ? docNavState.state === "close"
                        ? Unfold
                        : PackUp
                      : SiderOpt
                  }
                  alt=""
                  onClick={() =>
                    setDocNavState((p: any) => ({
                      ...p,
                      state: p.state === "close" ? "open" : "close"
                    }))
                  }
                />
              </Tooltip>
            </div>
            {docNavState.state === "open" && (
              <>
                <img src={AiRobit} width={32} alt="" />
                <div className="border-[#eee] border-[1px] border-solid my-0 mx-[16px] w-[32px]" />
                <>
                  {(
                    (navBarData.find((i: any) => i.key === "/docWriting") || {})
                      .routes || []
                  ).map((item: any) => {
                    return (
                      <Flex
                        key={item.path}
                        vertical
                        align="center"
                        className="cursor-pointer rounded-lg w-[50px] py-[6px]"
                        style={{
                          background: pathname.startsWith(item.path)
                            ? "rgba(216, 189, 137, 0.10)"
                            : "none"
                        }}
                        onClick={() => {
                          setPathname(item.path);
                          event_emitter &&
                            event_emitter("dashboard:navbar_item_click", item);
                        }}
                      >
                        <img
                          src={
                            pathname.startsWith(item.path)
                              ? item.activeIcon
                              : item.icon
                          }
                          width={20}
                          alt=""
                        />
                        <div
                          style={{
                            color: pathname.startsWith(item.path)
                              ? "#D8BD89"
                              : "#91A1A3"
                          }}
                          className="text-[14px] mt-[4px] cursor-pointer"
                        >
                          {item.name}
                        </div>
                      </Flex>
                    );
                  })}
                </>
              </>
            )}
          </Flex>
        )}
      <div className="h-full w-full">{children}</div>
    </Flex>
  );
};
