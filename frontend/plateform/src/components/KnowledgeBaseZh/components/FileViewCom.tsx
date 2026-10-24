/* eslint-disable no-case-declarations */
import { ConfigProvider, Modal } from "antd";
import { useEffect, useMemo, useState } from "react";
import {
  dealMinioUrl,
  FileModalSize,
  fileViewTypes,
  getFileName,
  getFilePath,
  getFileType,
  getInitialZoom,
  useAppPassport
} from "@root/src/core/helps";
import { GientechStreamReader } from "@gientech/modual/streamFilesReader";
interface ICurFileInfo {
  display_file_type?: string;
  hide_toolbar?: boolean;
  fileSuffix?: string;
  fileName?: string;
  file_source?: any;
  file_convert_source?: string;
  fullWidth?: boolean;
}

const FileViewCom = ({ data, showPreviewModal, setShowPreviewModal }: any) => {
  const { getToken } = useAppPassport();

  const [curFileInfo, setCurFileInfo] = useState<any>({});

  const handleEvent = () => {
    setCurFileInfo(data);
    setShowPreviewModal(true);
  };

  const modalStyles = {
    header: {
      padding: "20px 24px",
      borderBottom: "1px solid #F0F0F0",
      margin: 0
    },
    body: { padding: 0 },
    mask: {},
    footer: { padding: 0, margin: 0 },
    content: { padding: 0 }
  };

  useEffect(() => {
    if (!showPreviewModal) return;
    handleEvent();
  }, [showPreviewModal]);

  const curData = useMemo(() => {
    if (curFileInfo) {
      const token: any = getToken();
      console.log("content999", curFileInfo);
      const content = {
        pdfPages: curFileInfo.pdfPages || 0,
        file_source: curFileInfo.filePath,
        metadata: {
          source: curFileInfo.filePath
        }
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
    if (!curData.filePath) return <></>;
    console.log("curData", curData);

    return (
      <GientechStreamReader
        convertedFilePath={curData.filePath}
        fileName={curData.fileName}
        fileType={curData.fileType}
        initialPage={1}
        totalPages={curData.totalPages}
        authorization={curData.token}
        streamApiUrl="/proxy/index/knowledgeBase/file/stream"
        eventsEmit={(name: string) => {
          switch (name) {
            case "viewer:close":
              setShowPreviewModal(false);
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
    <ConfigProvider
      modal={{
        styles: modalStyles
      }}
    >
      <Modal
        destroyOnClose={true}
        footer={null}
        open={showPreviewModal}
        onCancel={() => setShowPreviewModal(false)}
        width={FileModalSize.width}
        height={FileModalSize.height}
        closable={false}
      >
        <div className="h-[600px] overflow-y-auto">{renderFileCom}</div>
      </Modal>
    </ConfigProvider>
  );
};

export default FileViewCom;
