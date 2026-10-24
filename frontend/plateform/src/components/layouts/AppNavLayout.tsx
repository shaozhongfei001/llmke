import React, { ReactNode, useState, useEffect } from "react";
import { Dropdown, Flex, Tooltip } from "antd";
import { useNavigate, useLocation } from "react-router-dom";

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

interface DropDownItemType {
  key: string | number;
  label: string;
  icon?: ReactNode;
  disabled?: boolean;
}

interface AppNavLayoutProps {
  children: ReactNode;
  navBarData: NavBarItemType[];
  defaultKey?: string;
  avatar?: { 
    userName: string; 
    url: string; 
    dropDownList: DropDownItemType[] 
  };
  logo?: {
    logoImg: any;
    title?: string;
  };
  onNavItemClick?: (item: any) => void;
  onUserItemClick?: (key: string) => void;
}

const AppNavLayout: React.FC<AppNavLayoutProps> = ({
  children,
  navBarData = [],
  defaultKey = "/",
  avatar,
  onNavItemClick,
  onUserItemClick
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [pathname, setPathname] = useState<string>(defaultKey);

  // 从环境变量获取logo路径，如果未设置则使用默认路径
  const logoPath =  '/logo/' + import.meta.env.VITE_LOGO_PATH || '/logos/default-logo.png';

  useEffect(() => {
    if (location.pathname !== "/") {
      setPathname(location.pathname);
    } else {
      setPathname(defaultKey);
    }
  }, [location, defaultKey]);

  const handleNavClick = (item: NavBarItemType) => {
    setPathname(item.path || "");
    if (onNavItemClick) {
      onNavItemClick(item);
    } else if (item.path) {
      navigate(item.path);
    }
  };

  const handleUserMenuClick = (key: string) => {
    if (onUserItemClick) {
      onUserItemClick(key);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* 顶部导航栏 */}
      <header className="h-[60px] bg-white border-b border-gray-200 flex items-center justify-between px-4 shadow-sm">
        <div className="flex items-center">
          <div className="flex items-center mr-8">
            <div className="w-[220px] h-[52px] flex items-center">
              <img 
                src={logoPath} 
                alt="Logo" 
                className="max-h-[52px] max-w-[220px] object-contain"
              />
            </div>
            {import.meta.env.VITE_APP_VERSION && (
              <span className="ml-2 text-xs text-gray-500">
                v{import.meta.env.VITE_APP_VERSION}
              </span>
            )}
          </div>
          
          <nav className="flex h-full">
            {navBarData.map((item) => (
              <div
                key={item.key}
                className={`group flex flex-col items-center justify-center px-4 h-full cursor-pointer relative ${
                  pathname.startsWith(item.path || "") 
                  ? "text-blue-600 font-medium" 
                  : "text-gray-600 hover:text-blue-500"
                } before:content-[''] before:absolute before:rounded-full before:bottom-[-20px] before:left-[50%] before:w-0 before:h-[3px] before:bg-blue-500 before:transition-all before:duration-300 before:-translate-x-1/2 hover:before:w-[70%] ${
                  !pathname.startsWith(item.path || "") ? "before:opacity-100" : "before:opacity-0"
                }`}
                onClick={() => handleNavClick(item)}
              >
                {item.icon && (
                  <img
                    src={pathname.startsWith(item.path || "") ? item.activeIcon : item.icon}
                    className="w-6 h-6 mb-1"
                    alt={item.name}
                  />
                )}
                <div className="text-center text-sm font-medium whitespace-break-spaces leading-tight">
                  {item.name}
                </div>
              </div>
            ))}
          </nav>
        </div>
        
        {/* 用户头像菜单 */}
        {avatar && (
          <div className="flex items-center">
            <Dropdown
              menu={{
                items: (avatar.dropDownList || []).map((menu) => ({
                  ...menu,
                  label: <div className="px-2 py-1">{menu.label}</div>,
                  onClick: () => handleUserMenuClick(menu.key as string)
                }))
              }}
            >
              <div className="flex items-center cursor-pointer">
                <img src={avatar.url} alt="avatar" className="w-8 h-8 rounded-full" />
                <span className="ml-2 text-sm">{avatar.userName}</span>
              </div>
            </Dropdown>
          </div>
        )}
      </header>
      
      {/* 内容区域 */}
      <main 
        style={{
          backgroundImage: 'linear-gradient(to left top, #e4e6ff, #dfe6ff, #dbe7fe, #d6e7fd, #d2e7fc, #d6e9fc, #daeafc, #deecfc, #e9f0fd, #f2f5fe, #f9fafe, #ffffff)',
          backgroundSize: 'cover',
          backgroundRepeat: 'no-repeat',
          backgroundAttachment: 'fixed',
          width: '100%',
          height: '100%'
        }}
        className="flex-1 overflow-auto relative"
      >
        {children}
      </main>
    </div>
  );
};

export default AppNavLayout; 