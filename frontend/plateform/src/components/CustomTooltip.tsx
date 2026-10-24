import React, { ReactNode } from "react";
import { Tooltip } from "antd";
import {
  InfoCircleFilled,
  WarningFilled,
  CloseCircleFilled
} from "@ant-design/icons";

export type TooltipType = "warning" | "error" | "info";
export type TooltipPosition = "left" | "right" | "top" | "bottom";

interface CustomTooltipProps {
  children: ReactNode;
  type?: TooltipType;
  content: string;
  position?: TooltipPosition;
}

const typeColorMap: Record<TooltipType, string> = {
  warning: "#faad14",
  error: "#ff4d4f",
  info: "#1890ff"
};

const typeIconMap: Record<TooltipType, ReactNode> = {
  info: <InfoCircleFilled style={{ color: typeColorMap.info }} />,
  warning: <WarningFilled style={{ color: typeColorMap.warning }} />,
  error: <CloseCircleFilled style={{ color: typeColorMap.error }} />
};

export const CustomTooltip: React.FC<CustomTooltipProps> = ({
  children,
  type = "info",
  content,
  position = "top"
}) => {
  const tooltipContent = (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      {typeIconMap[type]}
      <span>{content}</span>
    </div>
  );

  return (
    <Tooltip
      placement={position}
      title={content ? tooltipContent : undefined}
      styles={{
        body: {
          backgroundColor: "#1e1e1e", // VSCode dark theme background
          color: "#ffffff",
          fontSize: "12px",
          padding: "6px 8px",
          maxWidth: "400px",
          borderRadius: "6px"
        }
      }}
    >
      {children}
    </Tooltip>
  );
};

export default CustomTooltip;
