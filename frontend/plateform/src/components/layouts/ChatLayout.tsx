import React, { ReactNode, useState, useEffect } from "react";
import { Flex, Tooltip, Badge } from "antd";
import { useNavigate, useLocation, Outlet } from "react-router-dom";
import AiRobit from "@/assets/img/aiRobit.png";
import SiderOpt from "@/assets/svg/siderOpt.svg";
import PackUp from "@/assets/svg/packUp.svg";
import Unfold from "@/assets/svg/unfoId.svg";

// 添加自定义样式钩子
const useNavIconStyles = () => {
  useEffect(() => {
    // 确保样式只添加一次
    const styleId = 'nav-icon-styles';
    if (!document.getElementById(styleId)) {
      const styleEl = document.createElement('style');
      styleEl.id = styleId;
      styleEl.innerHTML = `
        /* 定义颜色变量 */
        :root {
          --color-gray: #64748b;
          --color-purple: #8b5cf6;
          --color-blue: #3b82f6;
        }
        
        /* 导航项通用样式 */
        .nav-item {
          position: relative;
          transition: all 0.3s ease;
          border-radius: 8px;
        }
        
        /* 图标容器 */
        .nav-icon-container {
          position: relative;
          z-index: 1;
        }
        
        /* 图标基本样式 */
        .nav-icon-container img {
          transition: all 0.3s ease;
          /* 灰色滤镜，不产生模糊 */
          filter: grayscale(100%) brightness(100%) opacity(0.7);
        }
        
        /* 文字样式 */
        .nav-text {
          color: var(--color-gray);
          transition: color 0.3s ease;
        }
        
        /* 点击效果 */
        .nav-icon-container img:active {
          transform: scale(0.92);
          transition-duration: 0.1s;
        }
        
        /* 悬停效果 - 统一图标和文字 */
        .nav-item:not(.active):hover .nav-icon-container img {
          /* 蓝色滤镜，不产生模糊 */
          filter: sepia(100%) saturate(1000%) hue-rotate(200deg) brightness(80%) opacity(1);
          transform: scale(1.05);
        }
        
        .nav-item:not(.active):hover .nav-text {
          color: var(--color-blue);
          font-weight: 500;
        }
        
        /* 底部边框效果 */
        .nav-item:not(.active)::after {
          content: '';
          position: absolute;
          bottom: 0;
          left: 25%;
          right: 25%;
          height: 2px;
          background: var(--color-blue);
          opacity: 0;
          transform: scaleX(0);
          transition: transform 0.3s ease, opacity 0.3s ease;
        }
        
        .nav-item:not(.active):hover::after {
          opacity: 1;
          transform: scaleX(1);
        }
        
        /* 激活状态 */
        .nav-item.active {
          background-color: rgba(219, 234, 254, 0.6);
        }
        
        /* 激活状态图标 */
        .nav-item.active .nav-icon-container img {
          /* 蓝色滤镜，不产生模糊 */
          filter: sepia(100%) saturate(1000%) hue-rotate(200deg) brightness(100%) opacity(1);
          transform: scale(1.05);
        }
        
        /* 激活状态文本 */
        .nav-item.active .nav-text {
          color: var(--color-blue);
          opacity: .8;
          font-weight: 500;
        }
        
        /* 激活状态左侧指示条 */
        .nav-item.active::before {
          content: '';
          position: absolute;
          left: 0;
          top: 30%;
          bottom: 30%;
          width: 3px;
          background: var(--color-blue);
          border-radius: 0 2px 2px 0;
        }
      `;
      document.head.appendChild(styleEl);
    }
  }, []);
};

// 波浪背景组件接口
interface WaveBackgroundProps {
  enableAnimation?: boolean; // 控制是否启用动画
  gradientColors?: {
    color1: string;
    color2: string;
    color3: string;
    color4: string;
  };
  waveColors?: {
    wave1: string;
    wave2: string;
    wave3: string;
    opacity1: number;
    opacity2: number;
    opacity3: number;
  };
  glowEffect?: {
    intensity: number;
    size: number;
  };
}

// 波浪背景组件
const WaveBackground: React.FC<WaveBackgroundProps> = ({ 
  enableAnimation = true,
  gradientColors = {
    color1: '#FFFFFF',
    color2: '#F9F9F9',
    color3: '#F7F0F6',
    color4: '#BBBBBB'
  },
  waveColors = {
    wave1: '#ffffff',
    wave2: '#f9f9f9',
    wave3: '#bbbbbb',
    opacity1: 0.6,
    opacity2: 0.7,
    opacity3: 0.3
  },
  glowEffect = {
    intensity: 0.4,
    size: 40
  }
}) => {
  // 使用提供的值或默认值
  const {
    color1 = '#FFFFFF', 
    color2 = '#F9F9F9', 
    color3 = '#F7F0F6', 
    color4 = '#BBBBBB'
  } = gradientColors || {};
  
 
  return (
    <div className="wave-bg">
      <div className={`wave wave-1 ${enableAnimation ? 'animated' : ''}`}></div>
      <div className={`wave wave-2 ${enableAnimation ? 'animated' : ''}`}></div>
      <div className={`wave wave-3 ${enableAnimation ? 'animated' : ''}`}></div>
    </div>
  );
};

interface ChatNavItemType {
  key: string | number;
  name: string;
  disabled?: boolean;
  icon?: string;
  activeIcon?: string;
  path?: string;
  badge?: number; // 添加徽标数字，可用于显示未读消息数
}

interface ChatLayoutProps {
  children?: ReactNode;
  navItems: ChatNavItemType[];
  onNavItemClick?: (item: ChatNavItemType) => void;
  headerContent?: ReactNode; // 聊天区域顶部内容
  enableWaveAnimation?: boolean; // 控制是否启用波浪动画
  // 添加背景渐变配置参数
  gradientColors?: {
    color1: string;
    color2: string;
    color3: string;
    color4: string;
  };
  waveColors?: {
    wave1: string;
    wave2: string;
    wave3: string;
    opacity1: number;
    opacity2: number;
    opacity3: number;
  };
  glowEffect?: {
    intensity: number;
    size: number;
  };
}

const ChatLayout: React.FC<ChatLayoutProps> = ({
  children,
  navItems = [],
  onNavItemClick,
  headerContent,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const pathname = location.pathname;

  // 应用图标动画样式
  useNavIconStyles();

  // 侧边栏状态
  const [sidebarState, setSidebarState] = useState<{
    state: "open" | "close";
    isHover: boolean;
  }>({
    state: "open",
    isHover: false
  });

  const handleNavClick = (item: ChatNavItemType) => {
    if (onNavItemClick) {
      onNavItemClick(item);
    } else if (item.path) {
      navigate(item.path);
    }
  };

  // 主要内容区域
  const renderMain = (
    <div className="w-full h-full relative">
      {/* 波浪背景
      <WaveBackground 
        enableAnimation={enableWaveAnimation} 
        gradientColors={gradientColors}
        waveColors={waveColors}
        glowEffect={glowEffect}
      /> */}
        
      <div 
        className={`flex-1 flex flex-col h-full overflow-hidden transition-all duration-300 ${sidebarState.state === "close" ? 'ml-[20px]' : 'ml-[84px]'} relative z-10`}
      >
        {/* 头部区域 */}
        {headerContent && (
          <div className="flex items-center h-14 px-4 bg-white border-b border-gray-200">
            {headerContent}
          </div>
        )}
        
        {/* 内容区域 */}
        <div className="flex-1 overflow-auto p-4">
          <Outlet />
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex w-full h-full">
      {/* 折叠按钮 */}
      <div
        style={{ 
          left: sidebarState.state === "close" ? "15px" : "80px",
          transition: "all 0.3s"
        }}
        onMouseEnter={() => setSidebarState(p => ({ ...p, isHover: true }))}
        onMouseLeave={() => setSidebarState(p => ({ ...p, isHover: false }))}
        className="absolute top-1/2 transform -translate-y-1/2 w-6 h-6 cursor-pointer z-20"
      >
        <Tooltip
          placement="right"
          title={sidebarState.state === "close" ? "展开" : "收起"}
        >
          <div className="flex items-center justify-center w-6 h-6 rounded-full ">
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
            />
          </div>
        </Tooltip>
      </div>

      {/* 侧边栏 */}
      <div 
        style={{
          width: sidebarState.state === "close" ? "0" : "60px",
          minWidth: sidebarState.state === "close" ? "0" : "60px",
          transition: "all 0.3s"
        }}
        className="absolute h-[88vh] rounded-lg left-[15px] top-[15px] bg-white shadow-md overflow-hidden z-10"
      >
   
        {/* 侧边栏内容 */}
        {sidebarState.state === "open" && (
          <Flex vertical align="center" className="h-full  py-6 px-[2px]">
            {/* 头像或Logo */}
            <div className="mb-6">
              <img src={AiRobit} className="w-7 h-7" alt="AI助手" />
            </div>

            {/* 导航项 */}
            <Flex 
              vertical 
              gap="middle" 
              align="center" 
              className="w-full gap-y-[2px] mb-10 flex-1 overflow-x-hidden overflow-y-auto no-scrollbar"
            >
              {navItems.map((item) => (
                <div 
                  key={item.key}
                  onClick={() => handleNavClick(item)}
                  className={`nav-item  relative w-full flex flex-col items-center justify-center py-3 px-2 rounded-lg cursor-pointer ${
                    pathname.startsWith(item.path || "")
                      ? "active bg-blue-50"
                      : "text-gray-500 hover:bg-gray-50"
                  }`}
                >
                  {/* 图标 */}
                  <div className="relative nav-icon-container ">
                    <img
                      src={pathname.startsWith(item.path || "") && item.activeIcon 
                        ? item.activeIcon  // 使用activeIcon（如果存在）
                        : item.icon}
                      className="w-6 h-6"
                      alt={item.name}
                      onError={(e) => {
                        console.warn(`图标 ${item.name} 加载失败`);
                        e.currentTarget.src = AiRobit;
                      }}
                    />
                    
                    {/* 徽标 */}
                    {item.badge && item.badge > 0 && (
                      <Badge 
                        count={item.badge} 
                        overflowCount={99}
                        className="absolute -top-1 -right-1"
                      />
                    )}
                  </div>
                  
                  {/* 名称 */}
                  <div className="mt-1 text-xs text-center nav-text">
                    {item.name}
                  </div>
                </div>
              ))}
            </Flex>
          </Flex>
        )}
      </div>

      {renderMain}
    </div>
  );
};

export default ChatLayout; 