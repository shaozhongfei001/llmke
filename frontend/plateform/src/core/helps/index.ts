import { AppPassportProvider, useAppPassport } from "./appPassport";
import xls from "@/assets/img/xls.png";
import txt from "@/assets/img/txt.png";
import doc from "@/assets/img/doc.png";
import pdf from "@/assets/img/pdf.png";
import ppt from "@/assets/img/ppt.png";
import img from "@/assets/img/img.png";
import dayjs from "dayjs";
import { getTokenLocal } from "@root/src/apis/token";
import axios$ from "@root/src/apis";
export const PASSWORD_REGEX =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,20}$/;
export const PASSWORD_WARN_MSG =
  "支持8-20位密码，密码内需包含大小写字母、英文格式的特殊字符!@#$%^&*、数字";
type Helps = {
  AppPassportProvider: typeof AppPassportProvider;
  useAppPassport: typeof useAppPassport;
};
const helps: Helps = { AppPassportProvider, useAppPassport };

export { AppPassportProvider, useAppPassport };
export default helps;

export const dealMinioUrl = (url: string) => {
  // | undefined | string[]
  return url || "";
  // if (!url) return "";
  // if (Array.isArray(url)) {
  //   const urlArr = url.map((item) => {
  //     const arr = item.split("/").slice(3);
  //     return `${getMinioUrlPrefix()}/` + arr.join("/");
  //   });
  //   return urlArr;
  // }

  // const arr = url.split("/").slice(3);

  // return `${getMinioUrlPrefix()}/` + arr.join("/");
};

export const uniqArr2By = (array1: any[], array2: any[], key: string) => {
  return array2.filter(
    (item2) => !array1.some((item1) => item1[key] === item2[key])
  );
};

export const fileViewTypes = [
  "txt",
  "pdf",
  // "xlsx",
  // "xls",
  // "csv",
  //"md",
  "jpeg",
  "jpg",
  "png"
];

export const getMarkExcludeType = (file_type: string) => {
  return [""].includes(file_type); //"xls", "xlsx", "csv"
};

export const isImage = (type: string) => {
  return ["png", "jpg", "jpeg"].includes(type);
};

export const TempBaseUrl = `http://${location.hostname}:9000/`;

export const getFileHost = (convertedPath: string) => {
  if (convertedPath.includes("http")) {
    const url = new URL(convertedPath);
    return `${url.origin}/`;
  }
  return TempBaseUrl;
};
export const FILEIMG: any = {
  docx: doc,
  doc: doc,
  pdf: pdf,
  xls: xls,
  xlsx: xls,
  csv: xls,
  ppt: ppt,
  pptx: ppt,
  pub: ppt,
  txt: txt,
  png: img,
  jpg: img,
  jpge: img
};

export const getFileIcon = (fileType: string) => {
  return FILEIMG[fileType] || FILEIMG["txt"];
};

export const smoothScroll = (container: any, distance?: number) => {
  const d = distance || 20;
  const { scrollTop, scrollHeight, clientHeight } = container;
  const isBottom = scrollTop + clientHeight >= scrollHeight;
  requestAnimationFrame(() => {
    if (!isBottom) {
      if (scrollTop + clientHeight + d < scrollHeight) {
        container.scrollBy({
          top: d,
          behavior: "smooth"
        });
        smoothScroll(container, d);
      } else {
        container.scrollTo({
          top: scrollHeight,
          behavior: "smooth"
        });
      }
    }
  });
};

export const judgeXlS = (item: { type?: string; fileName: string }) => {
  const validTypes = ["xlsx", "xls", "csv", "png", "jpg", "jpeg"];
  const fileExtension = item.fileName.split(".").pop()?.toLowerCase();
  return (
    validTypes.includes(item.type || "") ||
    validTypes.includes(fileExtension || "")
  );
};

export const FileModalSize = {
  width: 960,
  height: 742
};

export const formatTime = (val: string) => {
  return val ? dayjs(val).format("YY-MM-DD HH:mm") : "";
};

export const getUrlPrefix = () => {
  return import.meta.env.VITE_RAG_PREFIX;
};

export const getMinioUrlPrefix = () => {
  return import.meta.env.VITE_MINIO_PREFIX;
};

export const getCecUrlPrefix = () => {
  return import.meta.env.VITE_CEC_PREFIX;
};

export const handleDownLoad = async (url: string) => {
  if (!url) return;

  try {
    const response = await fetch(encodeURI(url)); // 处理特殊字符
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = url.split("/").pop() || "file.pdf"; // 提取文件名
    link.style.display = "none";

    document.body.appendChild(link);
    link.click();

    // 清理资源
    setTimeout(() => {
      URL.revokeObjectURL(blobUrl);
      document.body.removeChild(link);
    }, 100);
  } catch (error) {
    console.error("下载失败:", error);
  }
};

/**
 * 获取文档预览组件数据
 */

export const getFilePath = (content: {
  file_type?: string;
  file_source?: string;
  metadata: { source?: string };
}) => {
  let fileType = content?.file_type;
  const source = content?.metadata?.source;
  if (source) {
    fileType = source.split(".").slice(-1)[0];
  } else {
    return content?.file_source || "";
  }
  if (fileViewTypes.includes(fileType)) {
    if (source.includes("http")) {
      return source;
    } else {
      return `${TempBaseUrl}${source}`;
    }
  } else {
    return content?.file_source || "";
  }
};

export const getTypeBySource = (source: string) => {
  if (!source) return "";
  const arrs = source.split("/");
  const len = arrs.length;
  const str = arrs[len - 3];
  if (!str) return "";
  const arr2s = str.split(".");
  return arr2s[arr2s.length - 1];
};

export const getNameBySource = (source: string) => {
  try {
    if (!source) return "";
    const arrs = source.split("/");
    const len = arrs.length;
    const str = arrs[len - 3];
    return str || "";
  } catch (error) {
    return "";
  }
};

export const getFileName = (content: {
  file_name?: string;
  file_source?: string;
  metadata: { source?: string };
}) => {
  if (!content) return "";
  // const { file_name } = content;
  // if (file_name) return file_name;
  const source = content?.metadata?.source;
  if (source) {
    // const arr = source.split("/");
    // if (!arr.length) return "";
    return getNameBySource(source); //arr[arr.length - 1];
  } else {
    return "";
  }
};

export const getFileType = (
  content: { metadata: { source?: string } },
  filePath: string
) => {
  if (!content) return "";
  const source = content?.metadata?.source;
  if (source) {
    const arr = source.split(".");
    if (!arr.length) return "";
    const type = arr[arr.length - 1];

    const _arr = (filePath || "").split(".");
    if (!_arr.length) return "";
    const _type = _arr[_arr.length - 1];
    switch (type.toLocaleLowerCase()) {
      case "ppt":
      case "pub":
      case "pptx":
        return "pdf_slides";
      case "xls":
      case "xlsx":
      case "csv":
        if (_type === "pdf") return "pdf";
        return "markdown_table";
      case "md":
        return "pdf";
      case "png":
      case "jpg":
      case "jpeg":
        return "image";
      case "html":
      case "htm":
        return "html";
      case "txt":
        return "text";
      default:
        if (_type === "ppt" || _type === "pub" || _type === "pptx")
          return "pdf_slides";
        return "pdf";
    }
  } else {
    return "";
  }
};

export const downloadByStream = async ({
  filePath,
  fileName
}: {
  filePath: string;
  fileName: string;
}) => {
  if (filePath && fileName) {
    try {
      const response: any = await axios$.post(
        "/proxy/index/knowledgeBase/file/stream",
        { convertedFilePath: filePath },
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: getTokenLocal()
          },
          responseType: "arraybuffer"
        }
      );
      //const response = await fetch(filePath);
      console.log("response", response);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const _link = document.createElement("a");
      const _body = document.body;

      _link.href = url;
      _link.download = fileName;
      _link.style.display = "none";
      _body.appendChild(_link);

      const event = new MouseEvent("click", {
        view: window,
        bubbles: true,
        cancelable: true
      });
      _link.dispatchEvent(event);

      setTimeout(() => {
        _body.removeChild(_link);
        window.URL.revokeObjectURL(url);
      }, 100);
    } catch (error) {
      console.error("下载文件失败：", error);
    }
  } else {
    console.error("缺少文件名或文件地址：");
  }
};

export const getInitialZoom = (boxWidth: number, curContent: any) => {
  try {
    if (!curContent?.metadata?.page_size?.length) {
      const filePath = dealMinioUrl(getFilePath(curContent));
      const fileType = getFileType(curContent, filePath);
      let file_type = fileType;
      const s = curContent?.file_name || curContent?.metadata?.source;
      if (s) {
        const sarr = s.split(".");
        file_type = sarr?.[sarr.length - 1];
      }
      return judgePPT(fileType) || judgePPT(file_type) ? 0.65 : 1;
    } else {
      let pageSize = curContent?.metadata?.page_size || [[0, 0]];
      if (!Array.isArray(pageSize)) {
        pageSize = JSON.parse(pageSize);
      }
      const pageWidth = pageSize[0]?.[0] || 0;
      const pageHeight = pageSize[0]?.[1] || 0;
      if (pageHeight > pageWidth) return 1;
      if (!boxWidth || !pageWidth) return 1;
      if (pageWidth <= boxWidth) return 1;
      const res = +(boxWidth / pageWidth).toFixed(4);
      return res < 0.65 ? 0.65 : res;
    }
  } catch (error) {
    console.log("error", error);
    return 1;
  }
};

export const judgePPT = (type: string) => {
  const types = ["ppt", "pptx", "pub"];
  return types.includes(type.toLocaleLowerCase());
};

export const validatePassword = (password: string) => {
  return PASSWORD_REGEX.test(password);
};

