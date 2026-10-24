import React, { ReactNode, useState, useRef, useEffect } from "react";
import { SplitLayoutProvider } from "./SplitLayoutContext";
import SplitDivider from "./SplitDivider";

interface SplitLayoutProps {
  isResize?: boolean;
  leftPanel: ReactNode;
  rightPanel: ReactNode;
  initialLeftWidth?: number | string;
  minLeftWidth?: number | string;
  maxLeftWidth?: number | string;
  className?: string;
}
const initialWidth = 332;
const minLWidth = 300;
const maxLwidth = "50%";

const enhanceReactNode = <P extends object>(
  node: ReactNode,
  additionalProps: Partial<P>
): ReactNode => {
  if (!React.isValidElement(node)) {
    return node;
  }

  return React.cloneElement(node, {
    ...node.props,
    ...additionalProps
  });
};

const SplitLayout: React.FC<SplitLayoutProps> = ({
  isResize = true,
  leftPanel,
  rightPanel,
  initialLeftWidth = initialWidth,
  minLeftWidth = minLWidth,
  maxLeftWidth = maxLwidth,
  className = ""
}) => {
  const [leftWidth, setLeftWidth] = useState<number | string>(initialLeftWidth);
  const [leftWidthNum, setLeftWidthNum] = useState<number | string>(
    initialLeftWidth
  );
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const leftPanelRef = useRef<HTMLDivElement>(null);
  const widthRef = useRef(leftWidth);
  const widthNumRef = useRef(initialLeftWidth);

  const handleMouseDown = () => {
    setIsDragging(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  const handleMouseMove = (e: any) => {
    if (!isDragging || !containerRef.current) return;

    const containerRect = containerRef.current.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const mouseX = e.clientX;
    const containerLeft = containerRect.left;

    const newLeftWidth = ((mouseX - containerLeft) / containerWidth) * 100;
    widthRef.current = newLeftWidth;
    widthNumRef.current = mouseX - containerLeft;
    if (leftPanelRef.current) {
      leftPanelRef.current.style.flex = `0 0 ${newLeftWidth}%`;
    }
  };

  const handleMouseUp = () => {
    if (isDragging) {
      setIsDragging(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";

      setLeftWidth(widthRef.current);
      setLeftWidthNum(widthNumRef.current);
    }
  };

  useEffect(() => {
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  return (
    <SplitLayoutProvider>
      <div
        ref={containerRef}
        className={`flex h-full bg-white ${className} ${isDragging ? "cursor-col-resize" : ""}`}
      >
        {/* 左 */}
        <div
          ref={leftPanelRef}
          className="h-full overflow-auto"
          style={{
            width: typeof leftWidth === "number" ? `${leftWidth}px` : leftWidth,
            minWidth:
              typeof minLeftWidth === "number"
                ? `${minLeftWidth}px`
                : minLeftWidth,
            maxWidth:
              typeof maxLeftWidth === "number"
                ? `${maxLeftWidth}px`
                : maxLeftWidth
          }}
        >
          {leftPanel}
        </div>

        {isResize ? (
          <SplitDivider
            isDragging={isDragging}
            handleMouseDown={handleMouseDown}
          />
        ) : null}

        {/* 右 */}
        <div className="flex-1 h-full ">
          {enhanceReactNode(rightPanel, {
            leftWidth: leftWidthNum
          })}
        </div>
      </div>
    </SplitLayoutProvider>
  );
};

export default SplitLayout;
