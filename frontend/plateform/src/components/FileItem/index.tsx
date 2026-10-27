import genera from "@/assets/gif/genera.gif";
import {
  dealMinioUrl,
  FileModalSize,
  fileViewTypes,
  getFileIcon,
  getFileName,
  getFilePath,
  getFileType,
  getInitialZoom,
  useAppPassport
} from "@root/src/core/helps";
import { ConfigProvider, Image, Modal } from "antd";
import CloseCircle from "@/assets/img/CloseCircle.png";
import CloseCircleFail from "@/assets/img/CloseCircleFail.png";
import FileShow from "@/assets/img/fileShow.png";
import { useEffect, useMemo, useState } from "react";
import { GientechStreamReader } from "@root/src/core/components/StreamReader";
export const FileItem = ({
  type,
  fileList,
  handleDeleteFile,
  idx,
  className
}: {
  fileList: any[];
  handleDeleteFile?: (type: string, uid: string) => void;
  type?: string;
  idx: number;
  className?: string;
}) => {
  const [visible, setVisible] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [curFileInfo, setCurFileInfo] = useState({
    file_source: "",
    file_convert_source: "",
    fileType: "",
    pdfPages: 0,
    metadata: { page_size: [] }
  });
  const imgList = useMemo(() => {
    return fileList.filter((item: any) => {
      return item?.type?.indexOf("image") > -1;
    });
  }, [fileList]);
  const otherList = useMemo(() => {
    return fileList.filter((item: any) => {
      return item.type.indexOf("image") === -1;
    });
  }, [fileList]);
  const handleE = (type: string) => {
    switch (type) {
      case "close":
        setShowPreviewModal(false);
        break;
    }
  };

  const getType = (str: string) => {
    const arr = str.split(".");
    return arr[arr.length - 1];
  };

  const handlePreview = (item: any) => {
    if (item.status && item.status !== "done") return;
    const fileType = getType(item.filePath);
    setCurFileInfo({
      fileType,
      file_source: item.filePath,
      file_convert_source: item.convertedFilePath,
      pdfPages: item.pdfPages || 0,
      metadata: item?.metadata || item
    });
    setShowPreviewModal(true);
  };
  const { getToken } = useAppPassport();
  const getNameA = (item: any) => {
    if (!item?.name || typeof item.name !== "string") return "";
    const arrs = item.name.split(".");
    if (arrs.length <= 1) return "";
    const exName = arrs[1];
    if (!exName || typeof exName !== "string") return "";
    return exName.toLowerCase();
  };
  const curData = useMemo(() => {
    const token = getToken();
    if (curFileInfo && token) {
      console.log("content999", curFileInfo);
      const content = {
        file_source: curFileInfo.file_convert_source,
        metadata: {
          source: curFileInfo.file_source
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
    <div key={idx}>
      <div className="flex flex-wrap">
        {(otherList || []).map((item: any, index: number) => {
          return (
            <div
              className="group relative h-[48px] w-[202px] rounded-[4px] flex items-center mx-[4px] my-[4px] bg-white pl-[4px]"
              style={{ border: "1px solid #EEEEEE" }}
              key={item.uid || index}
            >
              <img src={getFileIcon(getNameA(item))} width={28} height={28} />
              <div
                className="ml-[16px] cursor-default"
                onClick={() => {
                  type !== "view" && handlePreview(item);
                }}
              >
                <div className="w-[126px] text-ellipsis line-clamp-1 text-[12px] text-[#2A2A2A]">
                  {item.name}
                </div>
                {item.status === "done" || !item.status ? (
                  <div className="mt-[3px] w-[126px] text-ellipsis line-clamp-1  text-[12px] text-[#888888]">
                    {item.size}
                  </div>
                ) : (
                  <div className="flex mt-[3px] w-[126px] text-ellipsis line-clamp-1  text-[12px] text-[#888888] items-center">
                    <img
                      src={item.status === "fail" ? CloseCircleFail : genera}
                      className="mr-[4px]"
                      width={10}
                      height={10}
                    />
                    {item.status === "loading" ? (
                      "上传中..."
                    ) : item.status === "analysis" ? (
                      "解析中..."
                    ) : (
                      <div className="text-[#FF4D4F]">解析失败</div>
                    )}
                  </div>
                )}
              </div>
              <img
                src={type === "view" ? FileShow : CloseCircle}
                width={12}
                height={12}
                className={`absolute top-[8px] right-[8px] cursor-pointer  ${
                  type === "view" ? "" : "opacity-0 group-hover:opacity-100"
                }`}
                onClick={() => {
                  if (type === "view") {
                    handlePreview(item);
                    return;
                  }
                  handleDeleteFile && handleDeleteFile("file", item.uid);
                }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap">
        <Image.PreviewGroup
          preview={{
            onChange: (current, prev) =>
              console.log(`current index: ${current}, prev index: ${prev}`)
          }}
        >
          {(imgList || []).map((item: any) => {
            //item.status === "done" || !item.status
            return item.status === "done" || !item.status ? (
              <div
                className="group mx-[4px] my-[4px] rounded-[4px] overflow-hidden relative"
                key={item.uid}
              >
                {type === "view" ? (
                  <Image
                    width={110}
                    height={110}
                    className="object-cover"
                    src={dealMinioUrl(item.filePath) as any}
                    preview={{
                      visible,
                      onVisibleChange: (value) => {
                        setVisible(value);
                      }
                    }}
                  />
                ) : (
                  <Image
                    width={72}
                    height={48}
                    className="object-cover"
                    src={dealMinioUrl(item.filePath) as any}
                    preview={{
                      visible,
                      onVisibleChange: (value) => {
                        setVisible(value);
                      },
                      mask: false
                    }}
                  />
                )}
                <img
                  src={CloseCircle}
                  width={12}
                  height={12}
                  className={`absolute top-[6px] right-[6px] ml-[8px] cursor-pointer opacity-0 group-hover:opacity-100 ${
                    type === "view" ? "hidden" : ""
                  }`}
                  onClick={() =>
                    handleDeleteFile && handleDeleteFile("img", item.uid)
                  }
                />
              </div>
            ) : (
              <div
                key={item.uid}
                className="group w-[72px] h-[48px] rounded-[4px] flex justify-center flex-col items-center relative mx-[4px] my-[4px] bg-white"
                style={{ border: "1px solid #EEEEEE" }}
              >
                <img src={genera} width={16} height={16} />
                <div className=" text-[12px] text-[#888888] mt-[4px]">
                  {item.status === "loading" ? "上传中" : "解析中"}...
                </div>
                <img
                  src={CloseCircle}
                  width={12}
                  height={12}
                  className={`absolute top-[6px] right-[6px] ml-[8px] cursor-pointer opacity-0 group-hover:opacity-100 ${
                    type === "view" ? "hidden" : ""
                  }`}
                  onClick={() =>
                    handleDeleteFile && handleDeleteFile("img", item.uid)
                  }
                />
              </div>
            );
          })}
        </Image.PreviewGroup>
      </div>
      <ConfigProvider
        modal={{
          styles: { content: { padding: 0 } }
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
    </div>
  );
};
