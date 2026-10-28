import { useLocation, useNavigate } from "react-router-dom";
import { Popover } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import Back from "../../../assets/img/back.png";
import "./style.less";
import "@mxmweb/fv/style.css";
import {
  dealMinioUrl,
  getFileName,
  getFilePath,
  getFileType,
  getInitialZoom,
  useAppPassport,
  isOfficePreviewType
} from "@root/src/core/helps";
import {
  PREVIEW_STREAM_API,
  STREAM_API,
  isSheetType
} from "@root/src/core/helps/fileAccess";
import jiantou from "../../../assets/img/jiantou.png";
import { getFileIcon } from "../FolderDetail";
import empty from "@/assets/knowledgebase/empty.png";
import loadingGif from "@/assets/knowledgebase/loading_gif.gif";
import { getFileByPageNum } from "./service";
import { GientechStreamReader } from "@root/src/core/components/StreamReader";
const KnowledgeAnalyBlock = () => {
  const { getToken } = useAppPassport();
  const [loading, setLoading] = useState<boolean>(false);
  const [list, setList]: any = useState([]);
  const scrollRef: any = useRef(null);
  const [current, setCurrent] = useState(1);
  const { state } = useLocation();
  const fileInfo = useMemo(() => {
    const info = {
      fileUrl: "",
      fileName: "",
      fileType: "pdf"
    };
    if (!state) return info;
    const { parsedFilePath } = state;
    if (!parsedFilePath) return info;
    const arr = parsedFilePath.split("/");
    info.fileUrl = parsedFilePath;
    info.fileName = arr[arr.length - 1];
    const arrs = parsedFilePath.split(".");
    info.fileType = arrs[arrs.length - 1];
    return info;
  }, [state]);

  const changePage = (page: number) => {
    setCurrent(page);
    getFileByPageNumFn(page);
  };

  const getFileByPageNumFn = async (pageNum?: number) => {
    try {
      setLoading(true);
      const res = await getFileByPageNum({
        spaceName: state.spaceName,
        fileId: state.fileId,
        pageNum: pageNum || current
      });
      setLoading(false);
      const { edgeList } = res;
      setList(edgeList || []);
    } catch (error) {
      setLoading(false);
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  useEffect(() => {
    getFileByPageNumFn(1);
  }, []);

  const curData = useMemo(() => {
    const token: any = getToken();
    if (state && token) {
      console.log("content999", state);
      const content = {
        file_source: state?.parsedFilePath || "",
        pdfPages: state?.pdfPage || 0,
        metadata: {
          source: state?.filePath || ""
        }
      };

      const filePath = dealMinioUrl(getFilePath(content));
      // R14-LIVE-10：getFileType 对 Office 一律返回 "pdf"，不能用来判分流；
      // 这里与知识库文件抽屉保持同一口径：按对象键真实后缀决定 stream / previewStream。
      const sourceType = (
        String(getFilePath(content) || "").split("?")[0].split(".").pop() || ""
      ).toLowerCase();
      return {
        filePath,
        sourceType,
        fileName: getFileName(content),
        fileType: getFileType(content, filePath),
        totalPages: content.pdfPages || 0,
        token
      };
    } else {
      return {};
    }
  }, [state]);

  const renderFileCom = useMemo(() => {
    if (!curData.filePath) return <></>;
    console.log("curData", curData);

    return (
      <GientechStreamReader
        convertedFilePath={curData.filePath}
        fileName={curData.fileName}
        fileType={
          isOfficePreviewType(curData.sourceType) || isSheetType(curData.sourceType)
            ? "pdf"
            : curData.fileType
        }
        initialPage={1}
        totalPages={curData.totalPages}
        authorization={curData.token}
        streamApiUrl={
          isOfficePreviewType(curData.sourceType) || isSheetType(curData.sourceType)
            ? PREVIEW_STREAM_API
            : STREAM_API
        }
        eventsEmit={(name: string, data: any) => {
          switch (name) {
            case "pageChange":
              changePage(data?.pageNumber);
              break;
          }
          console.log("name", data);
        }}
        tools={{
          close: false
        }}
      />
    );
  }, [curData]);

  return (
    <div className="h-full selfTimeLine">
      <Header fileInfo={fileInfo} state={state} />
      <div className="h-[calc(100%-60px)] flex px-[16px]">
        <div id="pdfBox" className="w-[65%] mr-[16px]">
          {renderFileCom}
        </div>
        <div
          className="w-[35%] bg-white px-[16px] py-[20px] h-[calc(100%-20px)] rounded-[8px]"
          style={{
            borderLeft: "1px solid #EEEEEE",
            background: "linear-gradient(#F4F5FF 0%,#FFFFFF 10%,#FFFFFF 100%)"
          }}
        >
          <div className="text-[16px] font-bold text-text-color1 pb-[20px] flex justify-between">
            <div>三元组信息</div>
            <div className="text-[14px] text-[#555555] font-normal">
              {list?.length || 0}个
            </div>
          </div>
          <div
            className="h-[calc(100%-49px)] overflow-y-auto overflow-x-hidden pr-[5px]"
            ref={scrollRef}
          >
            {loading && (
              <div className="h-full flex flex-col items-center justify-center">
                <div className=" text-sky-600 animate-pulse -mt-5 ">
                  努力加载中...
                </div>
              </div>
            )}
            {!loading && list.length === 0 && (
              <div className="h-full flexitems-center justify-center">
                <EmptyBox />
              </div>
            )}
            <div className="h-full">
              {list.length !== 0 &&
                (list || []).map((item: any) => {
                  return (
                    <div className="w-[calc(100%-0px)] h-[46px] rounded-[4px] bg-[#F7F8FA] flex px-[20px] items-center text-[14px] text-[#2A2A2A] mb-[8px] text-ellipsis line-clamp-1">
                      <Popover
                        placement="top"
                        content={item?.src?.name}
                        style={{ color: "red!important", flexShrink: 0 }}
                      >
                        <div className="text-ellipsis line-clamp-1">
                          {item?.src?.name}
                        </div>
                      </Popover>
                      <img
                        src={jiantou}
                        width={16}
                        height={8}
                        className="mx-[16px]"
                      />
                      <Popover
                        placement="top"
                        content={item?.name}
                        style={{ color: "red!important", flexShrink: 0 }}
                      >
                        <div className="shrink-0">
                          {item.name || item.edgeType}
                        </div>
                      </Popover>
                      <img
                        src={jiantou}
                        width={16}
                        height={8}
                        className="mx-[16px]"
                      />
                      <Popover
                        placement="top"
                        content={item?.dst?.name}
                        style={{ color: "red!important", flexShrink: 0 }}
                      >
                        <div className="text-ellipsis line-clamp-1">
                          {item?.dst?.name}
                        </div>
                      </Popover>
                    </div>
                  );
                })}
              <div className="w-full flex justify-center items-center h-[50px]">
                {loading && <img src={loadingGif} height={50} />}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default KnowledgeAnalyBlock;
const Header = ({ fileInfo, state }: any) => {
  const navigator = useNavigate();
  return (
    <div className="h-[60px] flex items-center ">
      <img
        src={Back}
        width={14}
        height={14}
        className="ml-[16px] cursor-pointer"
        onClick={() => navigator(-1)}
      />

      <div className="text-[16px] font-bold text-text-color1 ml-[20px] flex items-center">
        {getFileIcon(state?.fileType)}
        <div>{fileInfo?.fileName || "--"}</div>
      </div>
    </div>
  );
};

const EmptyBox = () => {
  const navigator = useNavigate();
  return (
    <div className="flex flex-col justify-center items-center">
      <img src={empty} width={106} />
      <div className="text-center mt-[25px]">
        数据为空，请
        <span
          className="text-blue-400 cursor-pointer"
          onClick={() => navigator(-1)}
        >
          返回上一级
        </span>
      </div>
    </div>
  );
};
