import { useLayoutEffect, useState } from 'react';

export const useContianerLayout = (elementRef: React.MutableRefObject<any>) => {
  const [minHeight, setMinHeight] = useState('100vh'); // 默认使用'100vh'
  const [minWidth, setMinWidth] = useState('100%');
  useLayoutEffect(() => {
    const updateParentHeight = () => {
      if (elementRef.current && elementRef.current.parentNode) {
        // 只有当父元素的ID不是'root'时才执行
        if (elementRef.current.parentNode.id !== 'root') {
          const parentHeight = elementRef.current.parentNode.clientHeight; // 获取父元素的高度
          const parentWidth = elementRef.current.parentNode.clientWidth; // 获取父元素的高度
          const newMinHeight = parentHeight > 0 ? '100%' : '100vh';
          const newMinWidth = parentWidth > 0 ? '100%' : '1200px';
          setMinHeight(newMinHeight); // 根据父元素高度更新 minHeight
          setMinWidth(newMinWidth); //
        } else {
          const newMinHeight = '100vh';
          const newMinWidth = '1200px';
          setMinWidth(newMinWidth); //
          setMinHeight(newMinHeight); // 根据父元素高度更新 minHeight
        }
      } else {
        const newMinWidth = '1200px';
        setMinWidth(newMinWidth); //
        const newMinHeight = '100vh';
        setMinHeight(newMinHeight); // 根据父元素高度更新 minHeight
      }
    };
    updateParentHeight();
    window.addEventListener('resize', updateParentHeight); // 窗口大小改变时更新高度
    return () => {
      window.removeEventListener('resize', updateParentHeight);
    };
  }, []);

  return {
    height: minHeight,
    width: minWidth,
  };
};
