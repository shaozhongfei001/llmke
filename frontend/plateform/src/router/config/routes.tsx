import {
  TeamOutlined,
  SolutionOutlined,
  UserOutlined,
  UserSwitchOutlined,
  SnippetsOutlined
} from "@ant-design/icons";
import PageLoading from "@root/src/pages/others/PageLoading";
import System from "@root/src/pages/system";
import Mine from "@root/src/pages/system/mine";
import ModelsPage from "@root/src/pages/system/models";
import Organization from "@root/src/pages/system/organization";
import Departments from "@root/src/pages/system/organization/departments";
import Groups from "@root/src/pages/system/organization/groups";
import Roles from "@root/src/pages/system/organization/roles";
import { lazy, Suspense } from "react";

const AuditPage = lazy(() => import("@root/src/pages/system/userOperate"));

const getSuspenceWrap = (el: React.ReactNode) => {
  return <Suspense fallback={<PageLoading />}>{el}</Suspense>;
};

const manageMapRoute: any = {
  "/system/users": {
    icon: <UserSwitchOutlined size={24} />
  },
  "/system/roles": {
    icon: <SolutionOutlined size={24} />
  },
  "/system/group": {
    icon: <TeamOutlined size={24} />
  },
  "/system/mine": {
    icon: <UserOutlined size={24} />
  },
  "/system/userOperate": {
    icon: <SnippetsOutlined size={24} />
  },
  "/system": {
    icon: null
  }
};

const systemRoutes = [
  {
    name: "系统管理",
    path: "system",
    element: <System />,
    children: [
      {
        name: "组织管理",
        path: "organization",
        element: <Organization />,
        children: [
          {
            name: "部门管理",
            path: "departments",
            element: <Departments />
          },
          {
            name: "分组管理",
            path: "groups",
            element: <Groups />
          },
          // {
          //   name: "用户管理",
          //   path: "users",
          //   element: <Users />
          // }
          {
            name: "角色管理",
            path: "roles",
            element: <Roles />
          }
        ]
      },
      {
        name: "我的账户",
        path: "mine",
        element: <Mine />
      },
      {
        name: "模型管理",
        path: "models",
        element: <ModelsPage />
      },
      {
        name: "用户操作记录",
        path: "userOperate",
        element: getSuspenceWrap(<AuditPage />)
      }
    ]
  }
];

//输出头部导航的数据
const extractMenuData = (routes: any[]) => {
  return routes.map((route) => ({
    label: route.name,
    key: route.path,
    icon: route.menuConfig?.icon,
    path: route.path
  }));
};
// const rootNavMenu = [...extractMenuData(managerRoutes)];

//antMenu的menu.item获取
const getItem = (
  label: React.ReactNode,
  key: React.Key,
  icon?: React.ReactNode,
  children?: any,
  type?: "group",
  disabled?: boolean,
  url?: string
) => {
  return {
    key,
    icon,
    children,
    label,
    type,
    disabled
  };
};
//输出ant需要的menu格式
const generateLocalMenu = (routes: any[]): any[] => {
  const result: any[] = [];

  routes.forEach((route) => {
    // 当前路由有menuConfig
    if (route.menuConfig) {
      const children = route.children
        ? generateLocalMenu(route.children)
        : undefined;
      result.push(
        getItem(
          route.menuConfig.label,
          route.menuConfig.key,
          route.menuConfig.icon,
          children,
          route.menuConfig.type,
          route.menuConfig.disabled
        )
      );
    } else if (route.children) {
      // 当前路由没有menuConfig，但是子路由有
      const childrenWithMenuConfig = route.children.filter(
        (r: any) => r.menuConfig
      );
      if (childrenWithMenuConfig.length) {
        const subMenu = generateLocalMenu(route.children);
        if (subMenu.length) {
          result.push(...subMenu);
        }
      }
    }
  });
  return result;
};

export { getItem, systemRoutes };
