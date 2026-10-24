import { Layout } from 'antd';
import { useLayoutEffect, useRef, useState } from 'react';
const { Content } = Layout;
export const HeadLessContainer = ({
  defaultMinWidth = '1200px',
  defaultMinHeight = '100vh',
  children,
}: any) => {
  const elementRef = useRef<any>(null);
  const [minHeight, setMinHeight] = useState(defaultMinHeight); // 默认使用'100vh'
  const [minWidth, setMinWidth] = useState('100%');
  useLayoutEffect(() => {
    const updateParentHeight = () => {
      if (elementRef.current && elementRef.current.parentNode) {
        // 只有当父元素的ID不是'root'时才执行
        if (elementRef.current.parentNode.id !== 'root') {
          const parentHeight = elementRef.current.parentNode.clientHeight; // 获取父元素的高度
          const parentWidth = elementRef.current.parentNode.clientWidth; // 获取父元素的高度
          const newMinHeight = parentHeight > 0 ? '100%' : defaultMinHeight;
          const newMinWidth = parentWidth > 0 ? '100%' : defaultMinWidth;
          setMinHeight(newMinHeight); // 根据父元素高度更新 minHeight
          setMinWidth(newMinWidth); //
        } else {
          const newMinHeight = defaultMinHeight;
          const newMinWidth = defaultMinWidth;
          setMinWidth(newMinWidth); //
          setMinHeight(newMinHeight); // 根据父元素高度更新 minHeight
        }
      } else {
        const newMinWidth = defaultMinWidth;
        setMinWidth(newMinWidth); //
        const newMinHeight = defaultMinHeight;
        setMinHeight(newMinHeight); // 根据父元素高度更新 minHeight
      }
    };
    updateParentHeight();
    window.addEventListener('resize', updateParentHeight); // 窗口大小改变时更新高度
    return () => {
      window.removeEventListener('resize', updateParentHeight);
    };
  }, []);

  return (
    <Layout ref={elementRef} style={{ minHeight: minHeight, minWidth: minWidth, height: '100%' }}>
      {children}
    </Layout>
  );
};
