import { createPlatePlugin, PlateElement, withRef } from "@udecode/plate/react";
import { useEffect, useState } from "react";
import mermaid from "mermaid";

export const MERMAID = "mermaid";

const MermaidChart: React.FC<{ chart: string }> = ({ chart }) => {
  const [isError, setIsError] = useState(true);
  useEffect(() => {
    try {
      mermaid.parse(chart); // 检查 chart 是否有效
      setIsError(false);
    } catch (error) {
      setIsError(true);
    }
  }, [chart]);

  useEffect(() => {
    if (isError) return; // 如果 chart 无效，则不渲染图表
    mermaid.initialize({
      startOnLoad: true,
      securityLevel: "loose"
    });
    mermaid.contentLoaded();
  }, [chart, isError]);

  return (
    <>
      {isError ? (
        <div>{chart}</div>
      ) : (
        <div className="mermaid relative -left-10">{chart}</div>
      )}
    </>
  );
};

export const MermaidElement = withRef<typeof PlateElement>(
  ({ children, className, element, ...props }, ref) => {
    return (
      <PlateElement
        ref={ref}
        element={element}
        {...props}
        contentEditable={false}
      >
        <div>
          {element.data && <MermaidChart chart={element.data as string} />}
          {children}
        </div>
      </PlateElement>
    );
  }
);

export const mermaidPlugin = createPlatePlugin({
  key: MERMAID,
  node: {
    isElement: true,
    isInline: true,
    type: MERMAID
  }
});
