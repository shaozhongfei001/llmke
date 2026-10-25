import { useFileViewer, registerPDFWorker } from "@mxmweb/fv";
import { useMemo, useEffect } from "react";
registerPDFWorker("/worker/pdf.worker.min.js");
import "./style.less";
import "@mxmweb/fv/style.css";
import {
  dealMinioUrl,
  getPreviewConvertUrl,
  isOfficePreviewType
} from "@root/src/core/helps";
export interface ICurFileInfo {
  display_file_type?: string;
  hide_toolbar?: boolean;
  fileSuffix?: string;
  fileName?: string;
  file_source?: any;
  file_convert_source?: string;
  fullWidth?: boolean;
  metadata: any;
}
interface IFile {
  curFileInfo: ICurFileInfo;
  handleEvent: (type: string, data?: any) => void;
}
//.ppt,.pptx,.pdf,.docx,.txt,.xlsx,.jpeg,.jpg,.png,.doc
const types = ["txt", "xlsx", "jpeg", "jpg", "png", "pdf", "docx", "xls"];
const FilePreview = ({ curFileInfo, handleEvent }: IFile) => {
  console.log("FilePreview updated:", curFileInfo);

  // R13：office 一律走 /preview/convert 转出的 PDF
  const isOffice = isOfficePreviewType(curFileInfo?.display_file_type);

  const viewerOptions = useMemo(
    () => ({
      fileUrl: isOffice
        ? getPreviewConvertUrl(curFileInfo?.file_source)
        : !curFileInfo?.display_file_type ||
          types.includes(curFileInfo.display_file_type)
        ? dealMinioUrl(curFileInfo?.file_source)
        : dealMinioUrl(curFileInfo?.file_convert_source),
      actionOnEmmit: handleEvent,
      bgColor: "#ffffff",
      hide_toolbar: curFileInfo?.hide_toolbar,
      display_file_type: isOffice ? "pdf" : curFileInfo?.display_file_type
    }),
    [
      curFileInfo?.file_source,
      curFileInfo?.file_convert_source,
      curFileInfo?.display_file_type,
      curFileInfo?.hide_toolbar,
      handleEvent
    ]
  );

  const { Element } = useFileViewer(viewerOptions);

  useEffect(() => {
    console.log("file_source changed:", curFileInfo?.file_source);
  }, [curFileInfo?.file_source]);

  return (
    <div
      style={{ width: curFileInfo?.fullWidth ? "100%" : "auto" }}
      className="overflow-y-auto  h-full fileView3"
    >
      {Element}
    </div>
  );
};

export default FilePreview;
