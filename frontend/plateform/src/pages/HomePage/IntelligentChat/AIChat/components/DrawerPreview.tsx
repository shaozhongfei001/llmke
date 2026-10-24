import { useMemo } from "react";
import {
  dealMinioUrl,
  getFileName,
  getFilePath,
  getFileType,
  getInitialZoom,
  useAppPassport
} from "@root/src/core/helps";
import { GientechStreamReader } from "@gientech/modual/streamFilesReader";

const DrawerPreview = ({
  curFileInfo,
  onClose
}: {
  curFileInfo: any;
  onClose: any;
}) => {
  const { getToken } = useAppPassport();
  const curData = useMemo(() => {
    const token = getToken();
    if (curFileInfo && token) {
      console.log("content999", curFileInfo);
      const content = {
        file_source:
          curFileInfo.parse_url ||
          curFileInfo.parsedFilePath ||
          curFileInfo.url,
        file_type: curFileInfo.file_type,
        metadata: {
          source:
            curFileInfo?.metadata?.source ||
            curFileInfo.filePath ||
            curFileInfo.url ||
            ""
        },
        pdfPages: curFileInfo.pdfPages
      };
      const filePath = dealMinioUrl(getFilePath(content));
      return {
        filePath,
        fileName: getFileName(content),
        fileType: getFileType(content, filePath),
        totalPages: content.pdfPages || 0,
        token
      };
    } else {
      return {};
    }
  }, [curFileInfo]);

  const renderFileCom = useMemo(() => {
    console.log("curData", curData);
    if (!curData.filePath) return <></>;
    return (
      <GientechStreamReader
        convertedFilePath={curData.filePath}
        fileName={curData.fileName}
        fileType={curData.fileType}
        initialPage={1}
        totalPages={curData.totalPages}
        authorization={curData.token}
        streamApiUrl="/proxy/index/knowledgeBase/file/stream"
        eventsEmit={(type) => {
          switch (type) {
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
    <div id="pdfBox" className="h-full overflow-y-auto">
      {renderFileCom}
    </div>
  );
};

export default DrawerPreview;
