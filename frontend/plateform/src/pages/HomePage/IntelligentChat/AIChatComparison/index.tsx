/* eslint-disable no-case-declarations */
import { GientechStreamReader } from "@gientech/modual/streamFilesReader";
import { useAiChatComparison } from "@root/src/components/AiChatComparison";
import FileView3, { ICurFileInfo } from "@root/src/components/FileView3";
import {
  dealMinioUrl,
  FileModalSize,
  fileViewTypes,
  getFileName,
  getFilePath,
  getFileType,
  getInitialZoom,
  getUrlPrefix,
  useAppPassport
} from "@root/src/core/helps";
import { ConfigProvider, Modal } from "antd";
import { useMemo, useState } from "react";

const getFileSource = (
  file_type: string,
  file_source: string,
  source: string
) => {
  //case "csv":
  //case "xls":
  if (fileViewTypes.includes(file_type)) {
    const arr: any = file_source.split("/");
    return {
      url: dealMinioUrl(`http://${arr[2]}/${source}`),
      fileType: file_type
    };
  } else {
    return { url: dealMinioUrl(file_source) };
  }
};

const AIChatComparisonPage = () => {
  const { getToken } = useAppPassport();
  const token: any = getToken();
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [curFileInfo, setCurFileInfo] = useState<any>({});
  const { AppElement } = useAiChatComparison({
    url: getUrlPrefix(),
    token,
    mockMode: false,
    handleEvent: (type, data: any) => {
      switch (type) {
        case "fileView":
          const { file_source, file_type, title, metadata } = data;
          const o = getFileSource(file_type, file_source, metadata.source);

          setCurFileInfo({
            fileSuffix: o.fileType,
            fileName: title,
            file_source: o.url,
            metadata,
            pdfPages: data.pdfPages || 0
          });
          setShowPreviewModal(true);
          break;
      }
    }
  });
  const handleE = (type: string) => {
    switch (type) {
      case "close":
        setShowPreviewModal(false);
        break;
    }
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

  const curData = useMemo(() => {
    const token = getToken();
    if (curFileInfo && token) {
      console.log("content999", curFileInfo);
      const content = {
        file_source: curFileInfo.file_source,
        metadata: curFileInfo.metadata,
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
        eventsEmit={(name) => {
          switch (name) {
            case "viewer:close":
              handleE("close");
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
    <>
      <div className="h-full">{AppElement}</div>
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
    </>
  );
};

export default AIChatComparisonPage;
//
