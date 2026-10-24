import React, { useState, useEffect } from "react";
import { Drawer } from "antd";
import "@/pages/HomePage/IntelligentChat/KnowledgeSearch/components/new-style.less";
import FileViewNew from "../FileViewNew";
import { FILEIMG } from "@root/src/core/helps";

const getFileName = (url: string): any => {
  const regex = /([^/]+)\.([^/]+)$/;
  const match = url.match(regex);

  if (match) {
    return {
      fileName: match[1],
      fileExtension: match[2],
      url
    };
  }
  return {};
};

const RagReCallDrawer = ({ selectFile, clearSelect }: any) => {
  const [isShowFile, setIsShowFile] = useState<boolean>(false);

  const [total, setTotal] = useState(0);
  const [origin_paper_size, setOriginPaperSize] = useState({
    width: 1191,
    height: 1684
  });

  const [curFile, setCurFile] = useState<any>({});
  const [curChunk, setCurChunk] = useState<any>({});

  useEffect(() => {
    if (!selectFile) return;
    setIsShowFile(true);
    try {
      const { fileName, fileExtension, url } = getFileName(
        selectFile?.parsedFilePath || ""
      );
      // ===================================
      const _curFile = {
        ...selectFile,
        fileName,
        fileExtension,
        url,
        file_source: selectFile.parsedFilePath,
        fileSuffix: fileExtension
      };

      // =======================================
      let _position = (selectFile.metadata || {})["position"] || [];
      if (typeof _position === "string") {
        _position = JSON.parse(_position);
      }
      const _curChunk = {
        pageNumbers: (selectFile.metadata || {})["page_number"] || [],
        positions: _position,
        type: selectFile.type,
        metadata: {
          ...selectFile.metadata,
          type: selectFile.type
        },
        id: selectFile["order_num"]
      };
      setCurFile(_curFile);
      setCurChunk(_curChunk);

      // =========================================

      let _page_size = (selectFile?.metadata || {})["page_size"] || "[]";

      if (Object.prototype.toString.call(_page_size) === "[object String]") {
        _page_size = JSON.parse(_page_size);
      }

      if (_page_size && _page_size.length) {
        setOriginPaperSize({
          width: _page_size[0][0],
          height: _page_size[0][1]
        });
      }

      setTotal(selectFile.pdfPages);
    } catch (e) {
      console.log(e);
    }
  }, [selectFile]);

  const closeFileView = () => {
    setIsShowFile(false);
    clearSelect();
  };

  return (
    <Drawer
      title={
        <div className="file-title-wrap select-none">
          <img
            src={FILEIMG[curFile.fileExtension] || FILEIMG["doc"]}
            width={16}
            height={16}
            className="absolute -left-2 top-[3px]"
          />
          <b className="text-ellipsis break-words line-clamp-1 mr-10">
            {curFile.fileName}.{curFile.fileExtension}
          </b>
          <i onClick={closeFileView} title="关闭"></i>
        </div>
      }
      closable={false}
      onClose={closeFileView}
      open={isShowFile}
      size="large"
      // width="50%"
      styles={{
        body: { padding: "8px" }
      }}
      footer={null}
    >
      <div className="pb-10 h-[calc(100%-40px)] overflow-y-auto">
        {isShowFile && curFile ? (
          <FileViewNew
            key={curFile.file_source || ""}
            total={total}
            curFile={curFile}
            curChunk={curChunk}
            origin_paper_size={origin_paper_size}
          />
        ) : null}
      </div>
    </Drawer>
  );
};

export default RagReCallDrawer;
