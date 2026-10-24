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
      primary: "#4E6EF2",
      secondary: "#6c757d",
      success: "#008000",
      warning: "#FFA500",
      error: "#FF0000",
      info: "#0000FF",
      background: "#ffff",
      text: "#000000",
      border: "#dee2e6",
      disabled: "#808080",
      disabledBackground: "#F5F5F5",
      disabledText: "#808080",
      shadow: "#000000",
      appBackground: "#fff",
      listBackground: "#f9f9f9",
      dashboardBackground: "#ffffff",
      sidebarBg: "#FBFBFF",
      itemBg: "transparent",
      itemHoverBg: "#f0f4ff",
      activeItemBg: "linear-gradient(to right, #E3ECFF, #EEEBFF)",
      activeItemText: "#1D2129",
      itemText: "#333",
      groupBg: "transparent",
      groupText: "#333",
      groupBorder: "#dee2e6"
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
