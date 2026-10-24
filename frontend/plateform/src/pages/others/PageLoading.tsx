import React from 'react';

interface PageLoadingProps {
  tip?: string;
}

const PageLoading: React.FC<PageLoadingProps> = ({ tip = '加载中...' }) => {
  return (
    <div className="fixed inset-0 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm z-50">
      {/* 主要动画容器 */}
      <div className="relative w-24 h-24 mb-8">
        {/* 外圈动画 */}
        <div className="absolute inset-0 rounded-full border-4 border-blue-100"></div>
        
        {/* 旋转圆环 */}
        <div className="absolute inset-0 rounded-full border-t-4 border-blue-500 animate-spin"></div>
        
        {/* 中间脉冲点 */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-4 h-4 bg-blue-500 rounded-full animate-pulse"></div>
        </div>
        
        {/* 装饰性元素 - 小点 */}
        <div className="absolute w-2 h-2 bg-blue-300 rounded-full top-0 left-1/2 -translate-x-1/2 transform animate-bounce"></div>
        <div className="absolute w-2 h-2 bg-blue-300 rounded-full bottom-0 left-1/2 -translate-x-1/2 transform animate-bounce animation-delay-300"></div>
        <div className="absolute w-2 h-2 bg-blue-300 rounded-full left-0 top-1/2 -translate-y-1/2 transform animate-bounce animation-delay-150"></div>
        <div className="absolute w-2 h-2 bg-blue-300 rounded-full right-0 top-1/2 -translate-y-1/2 transform animate-bounce animation-delay-450"></div>
      </div>
      
      {/* 加载文字 */}
      <div className="text-center">
        <p className="text-lg font-medium text-gray-700 mb-2">{tip}</p>
        <div className="flex space-x-1 justify-center">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce animation-delay-150"></div>
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce animation-delay-300"></div>
        </div>
      </div>
      
      {/* 小提示 */}
      <p className="mt-8 text-sm text-gray-500 max-w-md text-center">
        精彩内容正在准备中，请稍候片刻...
      </p>
    </div>
  );
};

// 使用此组件包装需要Suspense的组件
export const withPageLoading = (Component: React.ComponentType<any>, loadingTip?: string) => {
  return (props: any) => (
    <React.Suspense fallback={<PageLoading tip={loadingTip} />}>
      <Component {...props} />
    </React.Suspense>
  );
};

export default PageLoading;