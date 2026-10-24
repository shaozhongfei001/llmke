import { createPlatePlugin } from "@udecode/plate/react";
import { PlateElement } from "@udecode/plate-common/react";
import { useEffect, useMemo, useState } from "react";
import { getElementInfo } from "../../utils/getElementInfo";
import { dealMinioUrl } from "@root/src/core/helps";

export const CUSTOMIMG = "img";

const handleImgUrl = (url: string) => {
  return dealMinioUrl(url);
};

export const ImgElement = (props: any) => {
  const { plugin, children, element, editor, ...rest } = props;

  const elementInfo = useMemo(() => {
    const { allStyles } = getElementInfo({
      element,
      editor,
      pluginKey: CUSTOMIMG
    });
    return {
      allStyles
    };
  }, [element, editor]);

  const [svgBase64, setSvgBase64] = useState("");

  useEffect(() => {
    const fetchSvgAndConvertToBase64 = async () => {
      if ((element.url || "").includes(".svg")) {
        try {
          // 请求 SVG 文件内容
          let url = element.url;
          if (window.location.hostname !== "localhost") {
            url = dealMinioUrl(element.url);
          }
          const response = await fetch(url);
          if (!response.ok) {
            throw new Error("Failed to fetch SVG file");
          }
          // 获取 SVG 文件内容
          const svgText = await response.text();
          // 将 SVG 转换为 Base64 编码
          const base64Svg = btoa(unescape(encodeURIComponent(svgText)));
          // 设置状态
          setSvgBase64(`data:image/svg+xml;base64,${base64Svg}`);
        } catch (error) {
          console.error("Error fetching or converting SVG:", error);
          setSvgBase64(""); // 出现错误时清空 base64 数据
        }
      } else {
        setSvgBase64(""); // 如果 URL 不包含 SVG，则清空 base64 数据
      }
    };

    // 调用函数
    fetchSvgAndConvertToBase64();
  }, [element.url]);

  return (
    <PlateElement
      style={elementInfo.allStyles || {}}
      asChild
      {...props}
      contentEditable={false}
    >
      <div className="w-full">
        <img
          alt={((element.caption || [])[0] || {}).text || ""}
          src={svgBase64 || handleImgUrl(element.url) || ""}
          style={{
            maxWidth: "569px"
          }}
          width={element.width}
          height={element.height}
        />
        {children}
      </div>
    </PlateElement>
  );
};

export const CustomImgPlugin = createPlatePlugin({
  key: CUSTOMIMG,
  node: { isElement: true, isInline: true, type: CUSTOMIMG, isVoid: true }
});
