/* eslint-disable import/no-unresolved */
import React, { Suspense, ReactNode, useEffect, useState } from "react";
import SystemLayout from "@/components/layouts/SystemLayout";
import SystemLoading from "./SystemLoading";
import { useSelector } from "react-redux";
import { getMenu } from "../HomePage/hooks/useMenus";
import { useNavigate, useLocation } from "react-router-dom";

// 定义导航菜单项类型
interface SystemNavItemType {
  key: string;
  label: string;
  icon?: ReactNode;
  children?: SystemNavItemType[];
  path?: string;
  url: string;
}

// 系统管理导航菜单配置
const systemNavItems: SystemNavItemType[] = [
  {
    key: "organization",
    label: "组织架构",
    path: "/system/organization",
    url: "/system/organization",
    children: [
      {
        key: "department",
        label: "部门管理",
        path: "/system/organization/departments",
        url: "/system/organization/departments"
      },
      {
        key: "group",
        label: "分组管理",
        path: "/system/organization/groups",
        url: "/system/organization/groups"
      },
      {
        key: "roles ",
        label: "角色管理",
        path: "/system/organization/roles",
        url: "/system/organization/roles"
      }
    ]
  },

  {
    key: "models",
    label: "模型管理",
    path: "/system/models",
    url: "/system/models"
  },
  {
    key: "mine",
    label: "我的账户",
    path: "/system/mine",
    url: "/system/mine"
  },
  {
    key: "userOperate",
    label: "操作记录",
    path: "/system/userOperate",
    url: "/system/userOperate"
  }
];

export default function System() {
  const globalMenu: any = useSelector((state: any) => state.global.globalMenu);
  const [filteredNavItems, setFilteredNavItems]: any = useState([]);
  const navigate = useNavigate();
  const location = useLocation();

  // 处理路由重定向
  useEffect(() => {
    if (location.pathname === '/system') {
      navigate('/system/mine', { replace: true });
    }
  }, [location.pathname, navigate]);

  useEffect(() => {
    if (globalMenu) {
      const res = getMenu(globalMenu, systemNavItems as any);
      setFilteredNavItems(res);
    }
  }, [globalMenu]);

  // 在这里进行角色路由权限的判断
  // 可以根据用户角色过滤或修改菜单项

  return (
    <Suspense fallback={<SystemLoading />}>
      <SystemLayout navItems={filteredNavItems} headerTitle="系统管理" />
    </Suspense>
  );
}
