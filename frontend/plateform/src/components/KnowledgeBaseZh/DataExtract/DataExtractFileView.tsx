import FileViewer, { Annotation, registerPDFWorker } from "@mxmweb/file-viewer";
registerPDFWorker("/worker/pdf.worker1.min.js");
import { dealMinioUrl } from "@root/src/core/helps";
import { useEffect, useMemo, useState } from "react";
import { uid } from "uid";
export const DataExtractFileView = ({ fileViewInfo, onClose }: any) => {
  const [annotations, setAnnotations] = useState<any[]>([]);
  const [tableAnnotations, setTableAnnotations] = useState<any>([]);
  const [initialPage, setInitialPage] = useState(1);

  const fileType = useMemo(() => {
    if (!fileViewInfo) return;
    const { parsedFileUrl, sourceFileUrl } = fileViewInfo;
    const arr = (parsedFileUrl || sourceFileUrl || "").split(".");
    if (!arr.length) return "";
    return arr[arr.length - 1];
  }, [fileViewInfo]);

  useEffect(() => {
    if (!fileViewInfo) return;
    let { pageNum, pageSize, position, offset } = fileViewInfo;

    if (fileType === "md") {
      if (offset?.length) {
        offset = JSON.parse(offset);
        setTableAnnotations([{ id: uid(), offsets: offset }]);
      } else {
        setTableAnnotations([]);
      }
    } else {
      if (!pageSize || !position) {
        console.log("%c缺少文件size或者文件坐标", "color: red");
        return;
      }
      pageSize = JSON.parse(pageSize);
      position = JSON.parse(position);
      const pageSizes = Array.isArray(pageSize)
        ? pageSize
        : JSON.parse(pageSize);
      if (!pageSizes.length) {
        console.log("%c缺少文件size", "color: red");
        return;
      }
      const positions = Array.isArray(position)
        ? position
        : JSON.parse(position);
      if (!positions.length || !pageNum) {
        console.log("%c缺少文件坐标或者文件页数", "color: red");
        return;
      }
      pageNum = JSON.parse(pageNum);
      const anno = positions.map((item: any, index: number) => {
        return {
          id: uid(),
          pageNumber: pageNum[index],
          x: +(item[0][0] / pageSizes[0][0]).toFixed(4),
          y: +(item[0][1] / pageSizes[0][1]).toFixed(4),
          width: +((item[1][0] - item[0][0]) / pageSizes[0][0]).toFixed(4),
          height: +((item[2][1] - item[0][1]) / pageSizes[0][1]).toFixed(4),
          content: "",
          color: "#4FC3F7"
        };
      });
      console.log("anno", anno);
      setInitialPage(pageNum[0]);
      setAnnotations(anno);
    }
  }, [fileViewInfo]);

  const url = useMemo(() => {
    return fileViewInfo?.parsedFileUrl || "";
  }, [fileViewInfo]);

  return (
    <div
      style={{
        fontFamily: "Source Han Sans CN",
        fontSize: "12px"
      }}
      className="h-full w-full"
    >
      <FileViewer
        content={dealMinioUrl(url) as any}
        onClose={onClose}
        annotations={annotations}
        tableAnnotations={tableAnnotations as any}
        tools={{
          annotation: true,
          download: true,
          close: true
        }}
        initialPage={initialPage}
        headerClass="bg-white"
        contentClass="bg-white p-[12px] md:p-[12px]"
      />
    </div>
  );
};
