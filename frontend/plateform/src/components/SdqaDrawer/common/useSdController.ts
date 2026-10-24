import { registerPDFWorker } from "@mxmweb/fv";
registerPDFWorker("/worker/pdf.worker.min.js");
import { useState, useEffect, useMemo } from "react";
import { uid } from "uid";

interface SdController {
  setMarkData: React.Dispatch<React.SetStateAction<any>>;
  markLoading: boolean;
  setMarkLoading: (arg: boolean) => void;
  annotations: any[];
  tableAnnotations: any;
  initialPage: number;
}

interface Content {
  file_source?: string;
  file_type?: string;
  contents: any[];
  curMark: string;
  pdfPages: number;
  fileType: string;
}
const useSdController = ({ content }: { content: Content }): SdController => {
  const [markLoading, setMarkLoading] = useState(false);
  const [markData, setMarkData] = useState<any>();
  const [annotations, setAnnotations] = useState<any[]>([]);
  const [tableAnnotations, setTableAnnotations] = useState<any>([]);
  const [initialPage, setInitialPage] = useState(1);

  const fileType = useMemo(() => {
    if (!content) return;
    const { file_source } = content;
    if (!file_source) return;
    const arr = file_source.split(".");
    if (!arr.length) return "";
    return arr[arr.length - 1];
  }, [content]);

  useEffect(() => {
    if (!markData) return setMarkLoading(false);
    const { contents, curMark, pdfPages } = markData;
    const curChunk = contents.find((item: any) => item.mark === curMark);
    if (!curChunk) return setMarkLoading(false);
    const { metadata } = curChunk;
    if (!metadata) return setMarkLoading(false);
    const { page_number, page_size, position, offset, chunk_type } = metadata;
    if (fileType === "md") {
      if (offset?.length) {
        setTableAnnotations([{ id: uid(), offsets: offset }]);
      } else {
        setTableAnnotations([]);
      }
    } else {
      if (!page_size || !position) {
        console.log("%c缺少文件size或者文件坐标", "color: red");
        setMarkLoading(false);
        return;
      }
      const pageSizes = Array.isArray(page_size)
        ? page_size
        : JSON.parse(page_size);
      if (!pageSizes.length) {
        console.log("%c缺少文件size", "color: red");
        setMarkLoading(false);
        return;
      }
      const positions = Array.isArray(position)
        ? position
        : JSON.parse(position);
      if (!positions.length || !page_number) {
        console.log("%c缺少文件坐标或者文件页数", "color: red");
        setMarkLoading(false);
        return;
      }

      const anno = positions.map((item: any, index: number) => {
        return {
          id: uid(),
          pageNumber: page_number[index],
          x: +(item[0][0] / pageSizes[0][0]).toFixed(4),
          y: +(item[0][1] / pageSizes[0][1]).toFixed(4),
          width: +((item[1][0] - item[0][0]) / pageSizes[0][0]).toFixed(4),
          height: +((item[2][1] - item[0][1]) / pageSizes[0][1]).toFixed(4),
          content: "",
          color: chunk_type === "image" ? "#60f74f" : "#4FC3F7"
        };
      });
      console.log("anno", anno);
      setInitialPage(page_number[0]);
      setAnnotations(anno);
    }
  }, [markData]);

  return {
    setMarkData,
    annotations,
    initialPage,
    tableAnnotations,
    markLoading,
    setMarkLoading
  };
};

export default useSdController;
