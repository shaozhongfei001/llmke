import React, { ReactNode, useState, useEffect } from "react";
import { Flex, Tooltip, Menu } from "antd";
import { useNavigate, useLocation, Outlet } from "react-router-dom";
import SiderOpt from "@/assets/svg/siderOpt.svg";
import PackUp from "@/assets/svg/packUp.svg";
import Unfold from "@/assets/svg/unfoId.svg";

interface SystemNavItemType {
  key: string;
  label: string;
  icon?: ReactNode;
  children?: SystemNavItemType[];
  path?: string;
}

interface SystemLayoutProps {
  navItems: SystemNavItemType[]; // 现在必须提供navItems
  headerTitle?: string;
}

// 移除默认菜单项配置

const SystemLayout: React.FC<SystemLayoutProps> = ({
  navItems,  // 不再提供默认值，必须从props传入
  headerTitle = '系统管理'
}) => {
  // 打印当前菜单配置
  useEffect(() => {
    console.log('系统布局菜单项:', navItems);
  }, [navItems]);

  const navigate = useNavigate();
  const location = useLocation();
  const pathname = location.pathname;
  
  // 打印当前路径
  useEffect(() => {
    console.log('当前路径:', pathname);
  }, [pathname]);

  // 侧边栏状态
  const [sidebarState, setSidebarState] = useState<{
    state: "open" | "close";
    isHover: boolean;
  }>({
    state: "open",
    isHover: false
  });
  
  // 控制内容显示的延迟状态
  const [showContent, setShowContent] = useState(true);
  
  // 监听侧边栏状态变化，添加内容显示的延迟
  useEffect(() => {
    if (sidebarState.state === "open") {
      // 延迟显示内容，等待侧边栏展开完成
      const timer = setTimeout(() => {
        setShowContent(true);
      }, 150); // 动画时间的一半
      return () => clearTimeout(timer);
    } else {
      // 立即隐藏内容，避免收起时内容变形
      setShowContent(false);
    }
  }, [sidebarState.state]);

  // 添加选中的菜单项状态
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [openKeys, setOpenKeys] = useState<string[]>([]);

  // 更新选中的菜单项
  useEffect(() => {
    const newSelectedKeys = findSelectedKeys();
    setSelectedKeys(newSelectedKeys);
  }, [pathname, navItems]);

  // 初始化展开的菜单项
  useEffect(() => {
    const newOpenKeys = findOpenKeys();
    setOpenKeys(newOpenKeys);
  }, [navItems]);

  // 找出当前打开的菜单项和子菜单项
  const findOpenKeys = () => {
    // 默认展开所有有子级的路由
    const keysWithChildren = navItems
      .filter(item => item.children && item.children.length > 0)
      .map(item => item.key);
    
    return keysWithChildren;
  };

  // 找出当前选中的菜单项
  const findSelectedKeys = () => {
    for (const item of navItems) {
      if (item.children) {
        for (const child of item.children) {
          if (pathname === child.path || pathname.startsWith(child.path + '/')) {
            return [child.key];
          }
        }
      }
      if (pathname === item.path || pathname.startsWith(item.path + '/')) {
        return [item.key];
      }
    }
    return [];
  };

  // 处理菜单点击
  const handleMenuClick = (info: { key: string }) => {
    const { key } = info;
    console.log('点击菜单项:', key);
    
    // 查找点击的菜单项
    const findPath = (items: SystemNavItemType[]): string | undefined => {
      for (const item of items) {
        if (item.key === key) {
          console.log('找到对应项:', item.key, item.path);
          return item.path;
        }
        if (item.children) {
          const childPath = findPath(item.children);
          if (childPath) return childPath;
        }
      }
      return undefined;
    };
    
    const path = findPath(navItems);
    console.log('跳转路径:', path);
    
    if (path) {
      console.log('执行导航到:', path);
      navigate(path);
    } else {
      console.warn('未找到路径, key:', key);
    }
  };

  // 处理菜单展开/收起
  const handleOpenChange = (keys: string[]) => {
    setOpenKeys(keys);
  };

  // 渲染主内容区域
  const renderMain = (
    <div className="flex-1 h-full overflow-auto p-4">
      <Outlet />
    </div>
  );

  return (
    <div className="flex w-full h-full relative">
            {/* 折叠按钮 - 相对于侧边栏定位 */}
      <div 
        className="absolute z-20"
        style={{
          left: sidebarState.state === "close" ? "15px" : "220px",
          top: "50%",
          transform: "translateY(-50%) translateX(-50%)",
          transition: "left 0.3s ease-in-out"
        }}
      >
        <Tooltip
          placement="right"
          title={sidebarState.state === "close" ? "展开" : "收起"}
        >
          <div className="flex items-center justify-center w-6 h-6  rounded-full  cursor-pointer">
            <img
              src={
                sidebarState.isHover
                  ? sidebarState.state === "close"
                    ? Unfold
                    : PackUp
                  : SiderOpt
              }
              alt=""
              className="w-4 h-4"
              onClick={() =>
                setSidebarState(p => ({
                  ...p,
                  state: p.state === "close" ? "open" : "close"
                }))
              }
              onMouseEnter={() => setSidebarState(p => ({ ...p, isHover: true }))}
              onMouseLeave={() => setSidebarState(p => ({ ...p, isHover: false }))}
            />
          </div>
        </Tooltip>
      </div>

      {/* 侧边栏 */}
      <div 
        style={{
          width: sidebarState.state === "close" ? "0" : "200px",
          transition: "width 0.3s ease-in-out"
        }}
        className="bg-white h-full border-r border-gray-200 overflow-hidden"
      >
        {/* 侧边栏内容，仅在打开状态且内容需要显示时渲染 */}
        <div 
          className="h-full"
          style={{
            opacity: sidebarState.state === "open" && showContent ? 1 : 0,
            transition: "opacity 0.15s ease-in-out",
            visibility: sidebarState.state === "open" ? "visible" : "hidden"
          }}
        >
          <Flex vertical className="h-full">
            {/* 侧边栏头部 */}
            {/* <div className="h-12 flex items-center px-4 font-medium border-b border-gray-200">
              {headerTitle}
            </div> */}
            
            {/* 菜单 */}
            <Menu
              mode="inline"
              openKeys={openKeys}
              selectedKeys={selectedKeys}
              onOpenChange={handleOpenChange}
              onClick={handleMenuClick}
              style={{ borderRight: 0, height: '100%' }}
              items={navItems}
            />
          </Flex>
        </div>
      </div>

  
      {/* 主内容区域 */}
      <div className="flex-1 flex flex-col overflow-hidden transition-all duration-300">
        {renderMain}
      </div>
    </div>
  );
};

export default SystemLayout;