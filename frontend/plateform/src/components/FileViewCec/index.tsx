import { useFileViewer, registerPDFWorker } from "@mxmweb/fv";
import "@mxmweb/fv/style.css";
import React, { useMemo } from "react";
import {
  dealMinioUrl,
  getPreviewConvertUrl,
  isOfficePreviewType
} from "@root/src/core/helps";
registerPDFWorker("/worker/pdf.worker.min.js");
export interface ICurFileInfo {
  fileSuffix: string;
  fileName?: string;
  file_source?: string;
}
interface IFile {
  curFileInfo: ICurFileInfo;
  handleEvent: () => void;
}
const FilePreview = ({ curFileInfo, handleEvent }: IFile) => {
  // 勿删 start
  // const useFileViewer = (props: any) => {
  //   return {
  //     Element: <div>勿删！</div>,
  //   };
  // };
  // 勿删 end

  // R13：office 由 /preview/convert 转出 PDF，按 pdf 渲染
  const isOffice = isOfficePreviewType(curFileInfo?.fileSuffix);
  const form = isOffice
    ? "pdf"
    : ["pdf", "txt", "html", "csv", "img"].includes(curFileInfo?.fileSuffix)
    ? curFileInfo?.fileSuffix
    : "html";

  const handlethat = (type: string) => {
    if (type == "close") {
      handleEvent();
    }
  };
  const { Element } = useFileViewer({
    fileUrl: isOffice
      ? getPreviewConvertUrl(curFileInfo?.file_source)
      : dealMinioUrl(curFileInfo?.file_source),
    form: form,
    display_file_type: isOffice ? "pdf" : curFileInfo?.fileSuffix,
    actionOnEmmit: handlethat
  });

  return <div className="overflow-y-auto h-full">{Element}</div>;
};

export default FilePreview;
