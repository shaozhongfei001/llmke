export const GRADIENTS = {
  // 部门图标渐变色
  DEPARTMENT: 'linear-gradient(135deg, #A98D62 0%, #D8BD89 100%)',
  
  // 分组图标渐变色
  GROUP: 'linear-gradient(135deg, #6FA9AE 0%, #94CED2 100%)',
  
  // 成员图标渐变色
  MEMBER: 'linear-gradient(135deg, #8FBF9F 0%, #A9D8BA 100%)',
  
  // 按钮渐变色
  BUTTON: '#D8BD89',
} as const;

// 图标样式配置
export const ICON_STYLES = {
  // Avatar 配置
  AVATAR: {
    size: 28,
    className: 'flex items-center justify-center mr-[8px]',
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }
  },
  
  // 图标配置
  ICON: {
    size: 14,
    style: {
      fontSize: '12px'
    }
  },

  // 圆角图标容器配置
  ROUNDED_CONTAINER: {
    className: 'w-8 h-8 rounded-lg flex items-center justify-center',
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }
  }
} as const;

// 类型定义
export type GradientType = keyof typeof GRADIENTS;

// 获取渐变色的辅助函数
export const getGradient = (type: GradientType): string => {
  return GRADIENTS[type];
};

// 获取完整的Avatar样式
export const getAvatarProps = (type: keyof typeof GRADIENTS) => {
  return {
    size: ICON_STYLES.AVATAR.size,
    className: ICON_STYLES.AVATAR.className,
    style: {
      ...ICON_STYLES.AVATAR.style,
      background: GRADIENTS[type]
    }
  };
};

// 获取图标样式
export const getIconProps = () => {
  return {
    size: ICON_STYLES.ICON.size,
    style: ICON_STYLES.ICON.style
  };
};

// 获取圆角容器样式
export const getRoundedContainerProps = (type: keyof typeof GRADIENTS) => {
  return {
    className: ICON_STYLES.ROUNDED_CONTAINER.className,
    style: {
      ...ICON_STYLES.ROUNDED_CONTAINER.style,
      background: GRADIENTS[type]
    }
  };
}; 