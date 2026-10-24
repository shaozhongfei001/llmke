import {
  mainEditorDefaultComponents,
  mainEditorDefaultPlugins
} from "@root/src/components/AiEditor/components/editor/plugins/mainEditorSet";
import { customDeserializeMd } from "@root/src/components/AiEditor/core/operators/help/index";
import { createPlateEditor, Plate } from "@udecode/plate-common/react";
import { MarkdownPlugin } from "@udecode/plate-markdown";
import { Input } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Editor } from "./Editor";
import { injectStyle } from "@root/src/components/AiEditor/components/MainEditor";
import { defaultStyle } from "@root/src/components/AiEditor/components/MainEditor/default_style";
import mermaid from "mermaid";
const { TextArea } = Input;

// 将 SVG 转换为 PNG 图片
const convertSvgToPng = async (svg: string) => {
  // const canvas = document.createElement("canvas");
  // canvas.width = width;
  // canvas.height = height;

  // const ctx = canvas.getContext("2d");
  // canvas.width = 500;
  // canvas.height = 500;
  // const v = await Canvg.from(ctx, svg, {
  //   ignoreDimensions: true,
  //   enableRedraw: true, // 允许动态重绘
  //   ignoreAnimation: true, // 忽略动画
  // });

  // // 渲染 SVG 到 Canvas
  // await v.render();
  // return new Promise((resolve) => {
  //   canvas.toBlob((blob) => {
  //     resolve(blob); // 返回 PNG Blob
  //   }, "image/png");
  // });

  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.width;
      canvas.height = img.height;

      const ctx = canvas.getContext("2d");
      ctx && ctx.drawImage(img, 0, 0);

      canvas.toBlob(
        (blob) => {
          resolve(blob);
        },
        "image/png",
        1
      );
    };
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(svg, "image/svg+xml");
    const svgElement = svgDoc.documentElement;

    svgElement.setAttribute("width", "1000"); // 设置宽度
    // svgElement.setAttribute("height", "2500"); // 设置高度

    const updatedSvg = new XMLSerializer().serializeToString(svgElement);
    img.src =
      "data:image/svg+xml;charset=utf-8," + encodeURIComponent(updatedSvg);
  });
};

const MdTestDemo = () => {
  const [data, setData] = useState<string>("");
  const handleValueChange = (e: { target: { value: string } }) => {
    console.log(e.target.value);
    setData(e.target.value);
  };
  const editor = useMemo(() => {
    const curEditor = createPlateEditor({
      plugins: [MarkdownPlugin],
      value: [{ type: "p", children: [{ text: "" }] }]
    });
    const _data = customDeserializeMd(curEditor, data);
    const adjustedPlugins = mainEditorDefaultPlugins.map((plugin) => {
      return injectStyle(plugin, defaultStyle);
    });
    return createPlateEditor({
      plugins: adjustedPlugins,
      override: {
        components: { ...mainEditorDefaultComponents }
      },
      value: data ? _data : [{ type: "p", children: [{ text: "" }] }]
    });
  }, [data]);

  useEffect(() => {
    // 将流程图转化为img,并且将图片上传至服务器
    const mermaidStrToImg = async (mermaidStr: string, name?: string) => {
      // return new Promise((resolve, reject) => {
      //   // 渲染 Mermaid 图表为 SVG
      //   const svg = await mermaid.render("graphDiv", mermaidCode);
      //   return svg;
      // });
      // 渲染 Mermaid 图表为 SVG
      mermaid.initialize({
        startOnLoad: true,
        securityLevel: "loose"
      });
      const { svg } = await mermaid.render("graphDiv", mermaidStr);
      const blob = await convertSvgToPng(svg);
      // const blob = new Blob([svg], { type: "image/svg+xml" });
      const file = new File([blob as BlobPart], name || `股权结构图.png`, {
        type: "image/png"
      });
      const url = URL.createObjectURL(file);
      const a = document.createElement("a");
      a.href = url;
      a.download = file.name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };
    //     mermaidStrToImg(
    //       `flowchart RL
    // subgraph 一级股东
    // SH11[四川睿杰鑫电子股份有限公司10790万元]
    // end
    // subgraph 二级股东
    // SH21[夏东 6,539.40万元]
    // SH22[胡艳萍 3,126.60万元]
    // SH23[李建辉 1,134万元]
    // end
    // subgraph 目标公司
    // MAIN[天康生物股份有限公司]
    // end
    // SH11 -->|持股100%| MAIN
    // SH21 -->|持股61%| SH11
    // SH22 -->|持股29%| SH11
    // SH23 -->|持股11%| SH11
    // style MAIN font-size:18px,stroke-width:4px,fill:#f9f,stroke:#333
    // style SH11 font-size:16px,stroke-width:3px,fill:#f9f,stroke:#333
    // style SH21 font-size:14px,stroke-width:2px,fill:#f9f,stroke:#333
    // style SH22 font-size:14px,stroke-width:2px,fill:#f9f,stroke:#333
    // style SH23 font-size:14px,stroke-width:2px,fill:#f9f,stroke:#333`,
    //       "aaa"
    //     );
  }, []);

  return (
    <div className="flex">
      <TextArea
        value={data}
        onChange={handleValueChange}
        placeholder="请在此输入md字符串"
        autoSize={{ minRows: 50 }}
      ></TextArea>
      <div>
        <Plate editor={editor}>
          <div className="relative">
            <div className=" h-[700px] relative overflow-y-auto">
              <Editor className="cec-editor h-fit min-h-[1160px]" />
            </div>
          </div>
        </Plate>
      </div>
    </div>
  );
};

export default MdTestDemo;
