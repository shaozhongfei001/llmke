import React, { useState, useMemo, useEffect } from "react";
import { WithPlate } from "@root/src/components/CommonEditor/ChatViewEditor";
import { FILEIMG } from "./FileListNew";
import { StatusType } from "@/components/AiChatComparison/@types/sys";
import { uid } from "uid";
import IconRobot from "@/assets/svg/icon-robot.svg";
import IconSubTitle from "@/assets/svg/icon-sub-title.svg";
import Genera from "@/components/AiChatComparison/assets/img/genera.gif";
import { CaretRightOutlined, CaretDownOutlined } from "@ant-design/icons";
import { ConfigProvider, Drawer } from "antd";
import "./new-style.less";
import {
  dealMinioUrl,
  getFileName,
  getFilePath,
  getFileType,
  getInitialZoom,
  useAppPassport
} from "@root/src/core/helps";
import { GientechStreamReader } from "@gientech/modual/streamFilesReader";
interface ResultContentProps {
  answer: any;
  status: StatusType;
  selectFile: string;
  selectBlock: string;
  isHistoryHide: boolean;
  fileList: Array<any>;
  historyHideHandler: (sta: boolean) => void;
  clearSelect: () => void;
}

const ResultContentNew: React.FC<ResultContentProps> = ({
  answer = {},
  status,
  selectFile,
  selectBlock,
  isHistoryHide,
  fileList,
  historyHideHandler,
  clearSelect
}) => {
  const [isShowFile, setIsShowFile] = useState<boolean>(false);
  const [isOpenAnswer, setIsOpenAnswer] = useState<boolean>(false);
  const curFile = useMemo(() => {
    const _item =
      selectFile && fileList.length
        ? fileList.find((f: any) => f.url === selectFile)
        : {};
    const { list, fileName, fileExtension, url } = _item;
    return fileName
      ? Object.assign({}, _item, {
          hide_toolbar: true,
          fileSuffix: fileExtension,
          fileName: fileName,
          file_source: url,
          fullWidth: true,
          pdfPages:
            list && list.length && list[0].pdfPages ? list[0].pdfPages : 0
        })
      : {};
  }, [fileList, selectFile]);

  const fileName = useMemo(() => {
    if (!curFile) {
      return "";
    }
    if (curFile.fileName) return curFile.fileName;
    const source = curFile?.file_source;
    if (source) {
      const arr = source.split("/");
      if (!arr.length) return "";
      return arr[arr.length - 1];
    } else {
      return "";
    }
  }, [curFile]);

  const curChunk = useMemo(() => {
    const { list } = curFile;
    if (list && list.length) {
      const item = curFile.list.find((i: any) => i.id === selectBlock);
      return item || {};
    }
    return {};
  }, [selectBlock, curFile]);

  const [total, setTotal] = useState(0);
  const [origin_paper_size, setOriginPaperSize] = useState({
    width: 1191,
    height: 1684
  });

  const hideHistoryHandler = () => {
    if (!isHistoryHide) {
      historyHideHandler(true);
    }
  };

  const closeFileView = () => {
    setIsShowFile(false);
  };

  const fixFileViewData = () => {
    // console.log(curFile)
    const { list, pdfPages } = curFile;
    setTotal(pdfPages);
    if (list && list.length) {
      const item = list[0].metadata || {};
      const { page_size } = item;
      let _page_size = page_size as any;
      if (Object.prototype.toString.call(_page_size) === "[object String]") {
        _page_size = JSON.parse(_page_size);
      }
      if (_page_size && _page_size.length) {
        setOriginPaperSize({
          width: _page_size[0][0],
          height: _page_size[0][1]
        });
      }
    }
  };

  const changeOpenSta = () => {
    setIsOpenAnswer(!isOpenAnswer);
  };

  useEffect(() => {
    if (selectFile || selectBlock) {
      setIsShowFile(true);
      if (curFile.fileName) {
        fixFileViewData();
      }
    }
  }, [selectFile, selectBlock, curFile]);

  const { getToken } = useAppPassport();
  const curData = useMemo(() => {
    const token = getToken();
    if (curFile && token) {
      console.log("content999", curFile);
      const content = {
        file_source: curFile.file_source,
        file_type: curFile.fileSuffix,
        metadata: {
          source: curFile.url
        },
        pdfPages: curFile.pdfPages
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
  }, [curFile]);

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
        eventsEmit={(name) => {
          switch (name) {
            case "viewer:close":
              closeFileView();
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
    <div className={`result-content-wrap`} onClick={hideHistoryHandler}>
      <div className={`content-wrap`}>
        <div className="assist-name-wrap relative flex h-5">
          <img src={IconRobot} className="icon-robot" />
          <img src={IconSubTitle} className="icon-title" />
        </div>
        <div
          className={`${isOpenAnswer ? "open-btn" : "close-btn"} opener-btn`}
        >
          <span onClick={changeOpenSta}>
            {isOpenAnswer ? "收起" : "展开更多"}
            {isOpenAnswer ? <CaretDownOutlined /> : <CaretRightOutlined />}
          </span>
        </div>
        {status === StatusType.Process ? (
          <div className="flex bg-[#F2F6FF] rounded-1 h-8 items-center px-2 text-xs text-[#555] mb-1">
            <img src={Genera} width={20} height={20} className="mx-2" />
            <div className="text-[#0C5FFF]">生成中</div>
          </div>
        ) : null}
        <div
          style={{
            height: isOpenAnswer ? "auto" : "96px",
            overflow: "hidden",
            minHeight: "90px"
          }}
        >
          <WithPlate
            id={uid(32)}
            className="px-0 py-0 text-[14px] text-[#2a2a2a] bg-transparent overflow-x-hidden"
            data={answer}
            status={status}
            imgClassName="!w-[472px] mt-[10px]"
          />
        </div>
      </div>
      <ConfigProvider
        drawer={{
          styles: {
            body: { padding: 0 },
            header: { display: "none" }
          }
        }}
      >
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
          afterOpenChange={(open: boolean) => {
            if (!open) {
              console.log("clearSelect();");

              clearSelect();
            }
          }}
          closable={false}
          onClose={closeFileView}
          open={isShowFile}
          width={600}
          footer={null}
        >
          <div className="pb-10 overflow-y-auto">{renderFileCom}</div>
        </Drawer>
      </ConfigProvider>
    </div>
  );
};

export default ResultContentNew;
