import { uid } from "uid";
import { useEffect, useMemo, useState } from "react";
import {
  dealMinioUrl,
  getFileName,
  getFilePath,
  getFileType,
  getInitialZoom,
  useAppPassport
} from "@root/src/core/helps";
import { GientechStreamReader } from "@gientech/modual/streamFilesReader";
export const DrawerContent = ({
  content,
  onClose
}: {
  content: {
    file_source: string;
    contents: any[];
    curMark: string;
    file_type: string;
    title: string;
    metadata: any;
    pdfPages: number | undefined;
    url: string;
    parse_url: string;
  } | null;
  onClose: any;
}) => {
  const { getToken } = useAppPassport();

  const getAnnotations: any = (content: any) => {
    if (!content?.metadata) return;
    const fileType = getFileType(content, "");
    const { page_number, page_size, position, offset, chunk_type } =
      content.metadata;
    if (fileType === "markdown_table") {
      if (offset?.length) {
        return {
          annotations: [{ id: uid(), offsets: offset }],
          initialPage: 1
        };
      } else {
        return {};
      }
    } else {
      if (!page_size || !position) {
        console.log("%c缺少文件size或者文件坐标", "color: red");
        return {};
      }
      const pageSizes = Array.isArray(page_size)
        ? page_size
        : JSON.parse(page_size);
      if (!pageSizes.length) {
        console.log("%c缺少文件size", "color: red");
        return {};
      }
      const positions = Array.isArray(position)
        ? position
        : JSON.parse(position);
      if (!positions.length || !page_number) {
        console.log("%c缺少文件坐标或者文件页数", "color: red");
        return {};
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
      return { annotations: anno, initialPage: page_number[0] };
    }
  };

  const curData = useMemo(() => {
    console.log("content88888888888", content);
    const token = getToken();
    if (content && token) {
      console.log("content999", content);
      const { annotations, initialPage } = getAnnotations(content);
      const curContent = {
        ...content,
        metadata: {
          source: content?.metadata?.source || content.parse_url || content.url
        }
      };

      const filePath = dealMinioUrl(getFilePath(curContent));
      return {
        filePath,
        fileName: getFileName(curContent),
        fileType: getFileType(curContent, filePath),
        totalPages: curContent.pdfPages || 0,
        token,
        annotations,
        initialPage
      };
    } else {
      return {};
    }
  }, [content]);

  const renderFileCom = useMemo(() => {
    if (!curData.filePath) return <></>;
    console.log("curData", curData);
    return (
      <GientechStreamReader
        convertedFilePath={curData.filePath}
        fileName={curData.fileName}
        fileType={curData.fileType}
        initialPage={curData.initialPage}
        totalPages={curData.totalPages}
        authorization={curData.token}
        annotations={curData.annotations}
        streamApiUrl="/proxy/index/knowledgeBase/file/stream"
        eventsEmit={(name) => {
          switch (name) {
            case "viewer:close":
              onClose();
              break;
          }
        }}
        tools={{
          close: true
        }}
      />
    );
  }, [curData]);

  return (
    <div
      style={{
        fontFamily: "Source Han Sans CN",
        fontSize: "12px"
      }}
      className="h-full w-full"
    >
      {renderFileCom}
    </div>
  );
};
