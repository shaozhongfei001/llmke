import React, { useState, useEffect, useRef } from "react";
import "./style.less";
interface ResizableLayoutProps {
  LeftComponent: React.ReactNode; // 左侧组件
  RightComponent: React.ReactNode | ((resetFn: () => void) => React.ReactNode); // 右侧组件
  minWidth?: number; // 左侧最小宽度百分比
  maxWidth?: number; // 左侧最大宽度百分比
}

const resizeCursorSVG = `url("data:image/svg+xml,%3Csvg width='38' height='28' viewBox='0 0 38 28' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cmask id='path-1-outside-1_1700_287760' maskUnits='userSpaceOnUse' x='0' y='-0.0709229' width='38' height='28' fill='black'%3E%3Crect fill='white' y='-0.0709229' width='38' height='28'/%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M25.2222 12.1898V5L34.9998 13.9639L25.2222 22.9291V15.7393H12.7763V22.9291L3 13.9652L12.7761 5V12.1898H25.2222Z'/%3E%3C/mask%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M25.2222 12.1898V5L34.9998 13.9639L25.2222 22.9291V15.7393H12.7763V22.9291L3 13.9652L12.7761 5V12.1898H25.2222Z' fill='black'/%3E%3Cpath d='M25.2222 12.1898H27.2222V14.1898H25.2222V12.1898ZM25.2222 5H23.2222V0.453165L26.5737 3.52577L25.2222 5ZM34.9998 13.9639L36.3513 12.4897L37.9593 13.9638L36.3514 15.438L34.9998 13.9639ZM25.2222 22.9291L26.5738 24.4032L23.2222 27.4764V22.9291H25.2222ZM25.2222 15.7393V13.7393H27.2222V15.7393H25.2222ZM12.7763 15.7393H10.7763V13.7393H12.7763V15.7393ZM12.7763 22.9291H14.7763V27.4763L11.4247 24.4032L12.7763 22.9291ZM3 13.9652L1.64836 15.4393L0.0407586 13.9653L1.64824 12.4912L3 13.9652ZM12.7761 5L11.4243 3.52598L14.7761 0.45223V5H12.7761ZM12.7761 12.1898V14.1898H10.7761V12.1898H12.7761ZM23.2222 12.1898V5H27.2222V12.1898H23.2222ZM26.5737 3.52577L36.3513 12.4897L33.6482 15.4381L23.8706 6.47423L26.5737 3.52577ZM36.3514 15.438L26.5738 24.4032L23.8705 21.4549L33.6481 12.4898L36.3514 15.438ZM23.2222 22.9291V15.7393H27.2222V22.9291H23.2222ZM25.2222 17.7393H12.7763V13.7393H25.2222V17.7393ZM14.7763 15.7393V22.9291H10.7763V15.7393H14.7763ZM11.4247 24.4032L1.64836 15.4393L4.35164 12.4911L14.1279 21.4549L11.4247 24.4032ZM1.64824 12.4912L11.4243 3.52598L14.1278 6.47402L4.35176 15.4392L1.64824 12.4912ZM14.7761 5V12.1898H10.7761V5H14.7761ZM12.7761 10.1898H25.2222V14.1898H12.7761V10.1898Z' fill='white' mask='url(%23path-1-outside-1_1700_287760)'/%3E%3C/svg%3E") 19 14, col-resize`;

const ResizableLayout: React.FC<ResizableLayoutProps> = ({
  LeftComponent,
  RightComponent,
  minWidth = 25, // 默认最小宽度 25%
  maxWidth = 50 // 默认最大宽度 50%
}) => {
  const [leftWidth, setLeftWidth] = useState(minWidth); // 左侧宽度百分比
  const [isDragging, setIsDragging] = useState(false);
  const containerRef: any = useRef(null);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    document.body.style.cursor = resizeCursorSVG;
    e.preventDefault();
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;

      const containerRect = containerRef.current?.getBoundingClientRect();
      const containerWidth = containerRect.width;
      const newLeftWidth =
        ((e.clientX - containerRect.left) / containerWidth) * 100;

      // 限制宽度在25%到50%之间
      const clampedWidth = Math.max(minWidth, Math.min(maxWidth, newLeftWidth));
      setLeftWidth(clampedWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.body.style.cursor = "";
    };

    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);
  // 回到最小宽度
  const resetToMinWidth = () => {
    setLeftWidth(minWidth);
  };

  const renderRightPanel = () => {
    if (typeof RightComponent === "function") {
      return RightComponent(resetToMinWidth);
    }
    return RightComponent;
  };

  return (
    <div className="flex w-full h-full" ref={containerRef}>
      {/* 左侧区域 */}
      <div
        style={{
          width: `${leftWidth}%`,
          minWidth: `${minWidth}%`,
          maxWidth: `${maxWidth}%`,
          position: "relative"
        }}
        className="h-full flex-shrink-0"
      >
        {LeftComponent}
        {/* 拖拽条 */}
        <div
          onMouseDown={handleMouseDown}
          className="resize-handle"
          style={{
            position: "absolute",
            top: 0,
            right: 0,
            width: "1px",
            height: "100%",
            backgroundColor: "#EEEEEE"
          }}
        ></div>
      </div>
      {/* 右侧区域 */}
      <div
        style={{
          width: `calc(100% - ${leftWidth}%)`
        }}
        className="h-full"
      >
        {renderRightPanel()}
      </div>
    </div>
  );
};

export default ResizableLayout;
