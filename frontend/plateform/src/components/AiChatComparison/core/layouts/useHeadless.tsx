import { Layout } from 'antd';
import { ReactNode, useLayoutEffect, useRef, useState } from 'react';
const { Content } = Layout;
export interface IHeadLessContainer {
  children?: ReactNode;
  className?: string;
  defaultMinheight?: string;
  defaultWidth?: string;
  isContent?: boolean;
}
export const HeadLessContainer = (props: IHeadLessContainer) => {
  const elementRef = useRef<any>(null);
  const [minHeight, setMinHeight] = useState(props.defaultMinheight || '100vh'); // 默认使用'100vh'
  const [minWidth, setMinWidth] = useState(props.defaultWidth || '100%');
  useLayoutEffect(() => {
    const updateParentHeight = () => {
      if (elementRef.current && elementRef.current.parentNode) {
        // 只有当父元素的ID不是'root'时才执行
        if (elementRef.current.parentNode.id !== 'root') {
          const parentHeight = elementRef.current.parentNode.clientHeight; // 获取父元素的高度
          const parentWidth = elementRef.current.parentNode.clientWidth; // 获取父元素的高度
          const newMinHeight = parentHeight > 0 ? '100%' : props.defaultMinheight || '100vh';
          const newMinWidth = parentWidth > 0 ? '100%' : props.defaultWidth || '1200px';
          setMinHeight(newMinHeight); // 根据父元素高度更新 minHeight
          setMinWidth(newMinWidth); //
        } else {
          const newMinHeight = props.defaultMinheight || '100vh';
          const newMinWidth = props.defaultWidth || props.isContent ? '100%' : '1200px';
          setMinWidth(newMinWidth); //
          setMinHeight(newMinHeight); // 根据父元素高度更新 minHeight
        }
      } else {
        const newMinWidth = props.defaultWidth || '1200px';
        setMinWidth(newMinWidth); //
        const newMinHeight = props.defaultMinheight || '100vh';
        setMinHeight(newMinHeight); // 根据父元素高度更新 minHeight
      }
    };
    updateParentHeight();
    window.addEventListener('resize', updateParentHeight); // 窗口大小改变时更新高度
    return () => {
      window.removeEventListener('resize', updateParentHeight);
    };
  }, []);

  if (props.isContent) {
    return (
      <Content
        ref={elementRef}
        className=""
        style={{ minHeight: minHeight, minWidth: minWidth, height: '100%', width: '100%' }}
      >
        {props.children}
      </Content>
    );
  } else {
    return (
      <Layout
        ref={elementRef}
        className=""
        style={{ minHeight: minHeight, minWidth: minWidth, height: '100%' }}
      >
        {props.children}
      </Layout>
    );
  }
};
