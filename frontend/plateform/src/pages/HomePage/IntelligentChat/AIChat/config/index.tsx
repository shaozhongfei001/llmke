import userAvatar from "../assets/questionAwartar.png";
import aiAvatar from "../assets/answerAwartar.png";
import pdf from "../assets/pdf.png";
import docx from "../assets/docx-file.png";
import image from "../assets/image.png";
import sheets from "../assets/sheets.png";
import pptx from "../assets/pptx.png";
import html from "../assets/html.png";
import json from "../assets/json.png";
import md from "../assets/md.png";
import txt from "../assets/txt.png";
import { Icon } from "@mxmweb/zui";

export const defaultStyles: any = {
  theme: {
    colors: {
      primary: "#D8BD89",
      secondary: "#91A1A3",
      success: "#A9D8BA",
      warning: "#D9AA6D",
      error: "#E28683",
      info: "#94CED2",
      background: "#090D11",
      text: "#F0F2F0",
      border: "#344044",
      disabled: "#6F7E81",
      disabledBackground: "#1A292E",
      disabledText: "#91A1A3",
      shadow: "#000000",
      appBackground: "#090D11",
      listBackground: "#0B1014",
      dashboardBackground: "#090D11",
      sidebarBg: "#0B1014",
      itemBg: "transparent",
      itemHoverBg: "#1A292E",
      activeItemBg: "rgba(216, 189, 137, 0.14)",
      activeItemText: "#D8BD89",
      itemText: "#B8C3C3",
      groupBg: "transparent",
      groupText: "#91A1A3",
      groupBorder: "#243035"
    },
    space: {
      sidebar: "md",
      size: "md",
      radius: "md",
      padding: "md",
      margin: "md",
      shadow: "md",
      lineHeight: "md"
    },
    icons: {
      aiAvatar: "/icons/sheets.png",
      userAvatar:
        "/minio/dev-rag-data/header_pic/JIABINBIN00/%E5%BE%AE%E4%BF%A1%E5%9B%BE%E7%89%87_20231212161213.jpg",
      // 使用 zui-icon 新版本图标（Files/xxx_color 格式）
      pdf: <Icon type="Files/pdf_color" size={18} />,
      docx: <Icon type="Files/docx_color" size={18} />,
      doc: <Icon type="Files/docx_color" size={18} />,
      image: <Icon type="Files/tupian_color" size={18} />,
      sheets: <Icon type="Files/xls_color" size={18} />,
      excel: <Icon type="Files/xls_color" size={18} />,
      xls: <Icon type="Files/xls_color" size={18} />,
      xlsx: <Icon type="Files/xls_color" size={18} />,
      csv: <Icon type="Files/csv_color" size={18} />,
      pptx: <Icon type="Files/ppt_color" size={18} />,
      ppt: <Icon type="Files/ppt_color" size={18} />,
      txt: <Icon type="Files/txt_color" size={18} />,
      md: <Icon type="Files/txt_color" size={18} />,
      html: <Icon type="Files/lianjie_color" size={18} />,
      htm: <Icon type="Files/lianjie_color" size={18} />,
      json: <Icon type="Files/unknow_color" size={18} />,
      // 保留其他图标配置（如果存在）
      video: "/icons/video.png",
      audio: "/icons/audio.png"
    },
    others: {
      baseFontWeight: "normal"
    }
  }
};
