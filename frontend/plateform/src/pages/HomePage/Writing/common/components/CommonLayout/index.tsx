// CommonLayout
import { Flex } from "antd";
import React from "react";

interface Iprops {
  name?: string | React.ReactNode; // 组件名称
  operationArea?: React.ReactNode;
  children: React.ReactNode; // 组件内容
  background?: string; // 背景色
  widthReset?: boolean;
}
// 写作通用布局组件，此组件不处理滚动，滚动页面中自行处理
export const CommonLayout = ({
  name,
  operationArea,
  background,
  children,
  widthReset = false
}: Iprops) => {
  return (
    <div className="h-full w-full overflow-hidden">
      <Flex
        justify="space-between"
        align="center"
        className="mb-[16px] ml-[12px]"
      >
        {typeof name === "string" ? (
          <div className="text-[16px] text-text-color1 font-bold">{name}</div>
        ) : (
          name
        )}
        {operationArea}
      </Flex>
      <div
        className="h-[calc(100%-56px)] rounded-[8px]"
        style={{
          background: background ? background : "white",
          width: widthReset ? "calc(100% - 20px)" : ""
        }}
      >
        {children}
      </div>
    </div>
  );
};
