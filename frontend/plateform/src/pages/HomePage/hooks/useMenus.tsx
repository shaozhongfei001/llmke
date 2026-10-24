import axios$ from "@root/src/apis";
import { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import { useSystemApi } from "@/apis/system";
import { useGlobalStore } from "@/storage/state/zustand";
import xiezuo1 from "@/assets/img/xiezuo1.png";
import xiezuo2 from "@/assets/img/xiezuo2.png";
import moban1 from "@/assets/img/moban1.png";
import moban2 from "@/assets/img/moban2.png";
import duihua1 from "@/assets/svg/duihua1.svg";
import duihua2 from "@/assets/svg/duihua2.svg";
import knowlegeBase1 from "@/assets/svg/knowlegeBase1.svg";
import knowlegeBase2 from "@/assets/svg/knowlegeBase2.svg";
import database1 from "@/assets/svg/database1.svg";
import database2 from "@/assets/svg/database2.svg";
import sucai1 from "@/assets/svg/sucai1.svg";
import sucai2 from "@/assets/svg/sucai2.svg";
import assistant1 from "@/assets/img/assistant1.png";
import assistant2 from "@/assets/img/assistant2.png";
import sensitiveWords1 from "@/assets/img/sensitiveWords1.png";
import sensitiveWords2 from "@/assets/img/sensitiveWords2.png";
import comparison1 from "@/assets/img/comparison1.png";
import comparison2 from "@/assets/img/comparison2.png";
import duibi1 from "@/assets/img/duibi1.png";
import duibi2 from "@/assets/img/duibi2.png";
import IconWriting from "@/assets/svg/icon-writing.svg";
import IconDocument from "@/assets/svg/icon-document.svg";
import IconMaterial from "@/assets/svg/icon-material.svg";
import IconScene from "@/assets/svg/icon-scene.svg";
import IconWritingActive from "@/assets/svg/icon-writing-active.svg";
import IconDocumentActive from "@/assets/svg/icon-document-active.svg";
import IconMaterialActive from "@/assets/svg/icon-material-active.svg";
import IconSceneActive from "@/assets/svg/icon-scene-active.svg";
import MenuSearch from "@/assets/img/menu-search.png";
import MenuSearchActive from "@/assets/img/menu-search-active.png";
import IconComponentActive from "@/assets/svg/icon-component-active.svg";
import IconComponent from "@/assets/svg/icon-component.svg";
import IconIndicatorActive from "@/assets/svg/icon-indicator-active.svg";
import IconIndicator from "@/assets/svg/icon-indicator.svg";

interface NavBarItm {
  name: string;
  key: string;
  path: string;
  routes?: NavBarItm[];
  exact?: boolean;
  icon?: string;
  activeIcon?: string;
  id: string;
  url: string;
  hidden?: boolean;
}

const initData: NavBarItm[] = [
  {
    name: "智能问答",
    key: "/chats",
    id: "1025",
    path: "/chats",
    url: "/chats",
    routes: [
      {
        name: "智能对话",
        key: "/chats/main",
        path: "/chats/main",
        icon: duihua1,
        activeIcon: duihua2,
        id: "1025",
        url: "/chats/main"
      },
      {
        name: "知识库",
        key: "/chats/knowledgeBase",
        path: "/chats/knowledgeBase",
        icon: knowlegeBase1,
        activeIcon: knowlegeBase2,
        id: "1003",
        url: "/chats/knowledgeBase"
      },
      {
        name: "数据库",
        key: "/chats/database",
        path: "/chats/database",
        icon: database1,
        activeIcon: database2,
        id: "10813",
        url: "/chats/database"
      },
      {
        name: "助手对比",
        key: "/chats/comparison",
        path: "/chats/comparison",
        icon: duibi1,
        activeIcon: duibi2,
        id: "0",
        url: "/chats/comparison"
      },
      {
        name: "助手配置",
        key: "/chats/setting",
        path: "/chats/setting",
        icon: assistant1,
        activeIcon: assistant2,
        id: "1008",
        url: "/chats/setting"
      },
      {
        name: "敏感词配置",
        key: "/chats/sensitiveWords",
        path: "/chats/sensitiveWords",
        icon: sensitiveWords1,
        activeIcon: sensitiveWords2,
        id: "1043",
        url: "/chats/sensitiveWords"
      },
      {
        name: "用户反馈",
        key: "/chats/feedback",
        path: "/chats/feedback",
        icon: comparison1,
        activeIcon: comparison2,
        id: "1033",
        url: "/chats/feedback"
      },
      {
        name: "搜索",
        key: "/chats/knowledgeSearch",
        path: "/chats/knowledgeSearch",
        icon: MenuSearch, //缺图标
        activeIcon: MenuSearchActive,
        id: "10707",
        url: "/chats/knowledgeSearch"
      }
    ]
  },
  {
    name: "文档写作",
    key: "/docWriting",
    path: "/docWriting",
    id: "1035",
    url: "/docWriting/main",
    routes: [
      {
        name: "写作",
        key: "/docWriting/main",
        path: "/docWriting/main",
        icon: IconWriting,
        activeIcon: IconWritingActive,
        id: "1035",
        url: "/docWriting/main"
      },
      {
        name: "文档",
        key: "/docWriting/history",
        path: "/docWriting/history",
        icon: IconDocument,
        activeIcon: IconDocumentActive,
        id: "1040",
        url: "/docWriting/history"
      },
      {
        name: "素材",
        key: "/docWriting/resource",
        path: "/docWriting/resource",
        icon: IconMaterial,
        activeIcon: IconMaterialActive,
        id: "1039",
        url: "/docWriting/resource"
      },
      {
        name: "场景",
        key: "/docWriting/template",
        path: "/docWriting/template",
        icon: IconScene,
        activeIcon: IconSceneActive,
        id: "1038",
        url: "/docWriting/template"
      },
      {
        name: "组件",
        key: "/docWriting/component",
        path: "/docWriting/component",
        icon: IconComponent,
        activeIcon: IconComponentActive,
        id: "10730",
        url: "/docWriting/component"
      },
      {
        name: "指标",
        key: "/docWriting/indicator",
        path: "/docWriting/indicator",
        icon: IconIndicator,
        activeIcon: IconIndicatorActive,
        id: "11111",
        url: "/docWriting/indicator"
      },
      {
        name: "敏感词",
        key: "/docWriting/sensitiveWords",
        path: "/docWriting/sensitiveWords",
        icon: sensitiveWords1,
        activeIcon: sensitiveWords2,
        id: "10802",
        url: "/docWriting/sensitiveWords"
      }
    ]
  },
  {
    name: "系统管理",
    key: "/system",
    path: "/system",
    id: "1018",
    url: "/system",
    routes: [
      {
        name: "角色管理",
        url: "/system/roles",
        key: "/system/roles",
        path: "/system/roles",
        icon: xiezuo1,
        activeIcon: xiezuo2,
        id: "1020",
        hidden: true
      },
      {
        name: "用户管理",
        url: "/system/group",
        key: "/system/group",
        path: "/system/group",
        icon: moban1,
        activeIcon: moban2,
        id: "1019",
        hidden: true
      },
      {
        name: "机构管理",
        url: "/system/group",
        key: "/system/group",
        path: "/system/group",
        icon: sucai1,
        activeIcon: sucai2,
        id: "1028",
        hidden: true
      },
      {
        name: "我的",
        url: "/system/mine",
        key: "/system/mine",
        path: "/system/mine",
        icon: sucai1,
        activeIcon: sucai2,
        id: "1040",
        hidden: true
      }
    ]
  }
];

// 9009的情况下隐藏文档写作
const port = location.port;
const navBar = () => {
  return initData;
  let result: any = [];
  switch (port) {
    case "9009":
      result = initData.filter((i) => i.key !== "docWriting");
      break;
    case "9005":
      result = initData.filter((i) => i.key !== "chats");
      break;
    default:
      result = initData;
      break;
  }
  return result;
};

export const getMenu = (rawData: any[], configArray: NavBarItm[]) => {
  const permissionMap = new Map(
    rawData.map((item) => [
      item.url,
      {
        permission: item.permission,
        resourceType: item.resourceType
      }
    ])
  );
  return configArray.flatMap((v: any) => {
    if (
      (permissionMap.get(v.url)?.permission ||
        (v.routes || []).some((item: any) => {
          return permissionMap.get(item.url)?.permission;
        })) &&
      !v.hidden
    ) {
      if (v.routes) {
        const permissionRoutes: NavBarItm[] = getMenu(rawData, v.routes);
        return [{ ...v, routes: permissionRoutes }];
      }
      return [{ ...v, config: permissionMap.get(v.url) }];
    }

    return [];
  });
};

const useMenus = () => {
  const dispatch = useDispatch();
  const { setGlobalMenu } = useGlobalStore();
  const [navBarData, setNavBarData] = useState<NavBarItm[]>([]);
  const api = useSystemApi();

  useEffect(() => {
    api.getMenusByUser().then((result) => {
      const configData = navBar();
      const formatData = result.data;
      if (formatData) {
        dispatch.global.SET_GLOBAL_MENU(formatData);

        //替换zustand方案，rematch逐步放弃
        setGlobalMenu(formatData);

        const res = getMenu(formatData, configData);
        setNavBarData(res);
      }
    });
  }, []);

  return {
    navBarData,
    setNavBarData
  };
};

export default useMenus;
