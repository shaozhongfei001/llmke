import { useLocation, useNavigate, useParams } from "react-router-dom";
import { getFileChunks, updateChunk, deleteChunk } from "./service";
import { message, Timeline, Image, Space, Popconfirm } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import empty from "@/assets/knowledgebase/empty.png";
import Back from "../../../assets/img/back.png";
import DeletChunk from "../../../assets/img/deleteChunk.png";
import EditChunk from "../../../assets/img/editChunk.png";
import warning from "../../../assets/img/warning.png";
import "./style.less";

import "@mxmweb/fv/style.css";
import { createPlateEditor, Plate } from "@udecode/plate-common/react";
import { displayerEditor } from "@root/src/components/AiChat/components/editor/plugins/displayer";
import { deserializeMd } from "@udecode/plate-markdown";
import { Editor } from "@root/src/components/AiChat/components/editor";
import { uid } from "uid";
import ImageGroupView from "@root/src/components/ImageGroupView";
import loadingGif from "@/assets/knowledgebase/loading_gif.gif";
import {
  isMarkdownTableData,
  tableValue
} from "@root/src/components/CommonEditor/ui/tableValue";
import { validateAndFixNodes } from "@root/src/components/CommonEditor/ChatViewEditor";
import EditChunkModal, { ChunkType } from "./components/EditChunkModal";
import {
  dealMinioUrl,
  getFileName,
  getFilePath,
  getFileType,
  getInitialZoom,
  useAppPassport
} from "@root/src/core/helps";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import { filegetById } from "../common/faqService";
import { GientechStreamReader } from "@gientech/modual/streamFilesReader";

interface Iprops {
  isCec?: boolean;
}

const KnowledgeAnalyBlock = ({ isCec = false }: Iprops) => {
  const { getToken } = useAppPassport();
  const { id: knowledgeBaseId, fileId }: any = useParams();
  const { state } = useLocation();
  const [curChunk, setCurChunk]: any = useState();
  const [annotations, setAnnotations] = useState<any[]>([]);
  const [initialPage, setInitialPage] = useState(1);

  const pagination = useRef({
    pageNo: 1,
    pageSize: 10,
    total: 0,
    pages: 0
  });

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

  const scrollRef: any = useRef(null);
  const [chunks, setChunks] = useState<any[]>([]);
  const [chunksLoading, setChunksLoading] = useState<boolean>(false);
  const [editChunkLoading, setEditChunkLoading] = useState<boolean>(false);
  const [fileUrl, setFileUrl] = useState<string>("");
  const [fInfo, setFInfo] = useState<any>({});
  const tableFilePaths: any = useRef(null);
  const [curFileInfo, setCurFileInfo] = useState<any>({});
  const [pdfPages, setPdfPages] = useState<any>(0);

  const getFileById = async () => {
    if (knowledgeBaseId) {
      const res = await filegetById(fileId);
      if (res) {
        setPdfPages(res.pdfPage);
        setFInfo(res);
        const { convertedFilePath, tableFilePaths: resTableFilePaths } = res;
        setCurFileInfo(res);
        const arrs = convertedFilePath?.split(".") || [];
        const fileType = arrs[arrs.length - 1];
        if (fileType === "md") {
          const tablePaths = JSON.parse(resTableFilePaths);
          tableFilePaths.current = tablePaths || [];
          setFileUrl(tablePaths[0]);
        } else {
          setFileUrl(res.convertedFilePath || "");
        }
      }
    }
  };

  useEffect(() => {
    if (!fileId) return;
    getFileById();
  }, [fileId]);

  const clearAnnotations = () => {
    setAnnotations([]);
    setInitialPage(1);
  };

  const clearChunk = () => {
    setCurChunk();
    clearAnnotations();
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  };
  const queryFileChunks = async (
    { pageNo, pageSize }: any,
    cb?: () => void
  ) => {
    const { docId } = state;
    if (!knowledgeBaseId || !docId) return;
    setChunksLoading(true);

    try {
      const res = await getFileChunks({
        docId,
        kbId: knowledgeBaseId,
        pageNo,
        pageSize
      });
      loadMore.current = false;
      res.records && setChunksLoading(false);
      pagination.current = {
        pageNo,
        pageSize,
        total: res.total,
        pages: res.pages
      };
      cb && cb();
      if (pageNo === 1) {
        setChunks(res?.records || []);
      } else {
        setChunks((pre) => {
          return [
            ...(pre || []),
            ...(res?.records || []).map((item: any) => ({
              ...item
            }))
          ];
        });
      }
      setPdfPages(res.pdfPages);
      setChunksLoading(false);
    } catch (err) {
      loadMore.current = false;
      console.error(err);
    }
  };

  useEffect(() => {
    queryFileChunks({
      pageNo: pagination.current.pageNo,
      pageSize: pagination.current.pageSize
    });
  }, [state, knowledgeBaseId]);

  const clickItem = (data: any) => {
    setCurChunk(data);
    if (fileInfo.fileType === "md") {
      if (data?.offsets?.length) {
        if (tableFilePaths.current) {
          console.log("tableFilePaths.current", tableFilePaths.current, data);
          tableFilePaths.current.forEach((item: any) => {
            const match = item.match(/\/([^\/]+)\.md$/);
            const result2 = match ? match[1] : "";
            if (result2 == data.table) {
              setFileUrl(item);
            }
          });
        }
        setAnnotations([{ id: uid(), offsets: data.offsets }]);
        console.log("anno", [{ id: uid(), offsets: data.offsets }]);
      } else {
        setAnnotations([]);
      }
    } else {
      if (!data?.pageNumbers?.length) {
        console.log("%c缺少文件页数", "color: red");
        return;
      }
      if (!data?.pageSizes?.length) {
        console.log("%c缺少文件尺寸", "color: red");
        return;
      }
      if (data.positions?.length) {
        const [sizeW, sizeH] = data.pageSizes[0];
        const anno = data.positions.map((item: any, index: number) => {
          return {
            id: uid(),
            pageNumber: data.pageNumbers[index],
            x: +(item[0][0] / sizeW).toFixed(4),
            y: +(item[0][1] / sizeH).toFixed(4),
            width: +((item[1][0] - item[0][0]) / sizeW).toFixed(4),
            height: +((item[2][1] - item[0][1]) / sizeH).toFixed(4),
            content: "",
            color: data.chunk_type === "image" ? "#60f74f" : "#4FC3F7"
          };
        });
        console.log("anno", anno);
        setInitialPage(data.pageNumbers[0]);
        setAnnotations(anno);
      } else {
        clearAnnotations();
      }
    }
  };

  const [showModal, setShowModal] = useState(false);
  const handleEvent = (type: string, data: any) => {
    switch (type) {
      case ChunkType.CONFIRM:
        if (!knowledgeBaseId) {
          message.error("知识库ID不存在");
          return;
        }
        setEditChunkLoading(true);

        updateChunk(
          {
            content: data.content,
            chunkId: data.chunkId,
            kbId: +knowledgeBaseId
          },
          (data) => {
            if (data) {
              pagination.current.pageNo = 1;
              queryFileChunks(
                {
                  pageNo: pagination.current.pageNo,
                  pageSize: pagination.current.pageSize
                },
                clearChunk
              );
              setShowModal(false);
              message.success("编辑成功");
            }

            setEditChunkLoading(false);
          }
        );
        break;
      case "deleteChunk":
        if (getBtnDisabled(FILE_BTN.DELETE, fInfo.permission)) {
          return;
        }
        deleteChunk(
          {
            tableName: data.tableName,
            chunkIds: [data.id]
          },
          (data) => {
            if (data) {
              setTimeout(() => {
                pagination.current.pageNo = 1;
                queryFileChunks(
                  {
                    pageNo: pagination.current.pageNo,
                    pageSize: pagination.current.pageSize
                  },
                  clearAnnotations
                );
              }, 800);
              setShowModal(false);
              message.success("删除成功");
            }

            setEditChunkLoading(false);
          }
        );
        break;
      case "editChunk":
        setShowModal(true);
        break;
      case "clickChunk":
        clickItem(data);
        break;
    }
  };
  const items = useMemo(() => {
    return chunks.map((item: any, index: number) => {
      return {
        color: "#888888",
        label: item.pageNumbers?.length
          ? `第${item.pageNumbers?.[0]}页`
          : `第${index + 1}块`,
        position: "left",
        children: (
          <TimeItem
            data={item}
            curChunk={curChunk}
            handleEvent={handleEvent}
            fInfo={fInfo}
          />
        )
      };
    });
  }, [chunks, curChunk]);

  const loadMore = useRef(false);

  const pullingUpHandler = () => {
    if (
      pagination.current.pageNo === pagination.current.pages ||
      loadMore.current
    )
      return;
    setChunksLoading(true);
    loadMore.current = true;
    pagination.current.pageNo = pagination.current.pageNo + 1;
    queryFileChunks({
      pageNo: pagination.current.pageNo,
      pageSize: pagination.current.pageSize
    });
  };

  const handleScroll = (e: any) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    // 当滚动到底部时加载更多数据
    if (scrollTop + clientHeight >= scrollHeight - 10) {
      pullingUpHandler();
    }
  };
  useEffect(() => {
    const scrollWrapper: any = scrollRef.current;

    if (scrollWrapper) {
      scrollWrapper.addEventListener("scroll", handleScroll);

      // 清理函数，组件卸载时移除事件监听器
      return () => {
        scrollWrapper.removeEventListener("scroll", handleScroll);
      };
    }
  }, [handleScroll]);

  const curData = useMemo(() => {
    console.log("content88888888888", curFileInfo);
    console.log("fileUrl88888888888", fileUrl);
    const token = getToken();
    if (curFileInfo && token) {
      const content: any = {
        file_source: curFileInfo.convertedFilePath,
        metadata: {
          source: curFileInfo.filePath
        }
      };
      const fileType = getFileType(content, curFileInfo.filePath);
      return {
        filePath:
          fileType === "markdown_table"
            ? ""
            : dealMinioUrl(getFilePath(content)),
        fileName: getFileName(content),
        fileType,
        totalPages: pdfPages || 0,
        token
      };
    } else {
      return {};
    }
  }, [curFileInfo, pdfPages]);

  const renderFileCom = useMemo(() => {
    if (
      (curData.fileType !== "markdown_table" && !curData.filePath) ||
      (curData.fileType === "markdown_table" && !fileUrl)
    ) {
      return <></>;
    }

    if (curData.fileType === "pdf" && !curData.totalPages) return <></>;
    console.log("curData", curData);
    console.log("annotations", annotations);
    return (
      <GientechStreamReader
        convertedFilePath={curData.filePath || dealMinioUrl(fileUrl)}
        fileName={curData.fileName}
        fileType={curData.fileType}
        initialPage={initialPage}
        totalPages={curData.totalPages}
        authorization={curData.token}
        annotations={annotations}
        streamApiUrl="/proxy/index/knowledgeBase/file/stream"
        eventsEmit={() => {}}
        key={fileUrl}
        tools={{
          close: false
        }}
      />
    );
  }, [curData, annotations, fileUrl]);

  return (
    <div className="h-full selfTimeLine">
      <Header fileInfo={curData} />
      <div className="h-[calc(100%-60px)] flex">
        <div id="setRenderWidth" className="w-[50%] flex flex-col">
          <div id="box" className="h-full px-[16px] pt-[16px]">
            <div
              id="pdfBox"
              className="bg-white h-full shadow-lg overflow-auto"
            >
              {renderFileCom}
            </div>
          </div>
        </div>
        <div
          className="w-[50%] bg-white px-[16px] pt-[20px] h-full"
          style={{ borderLeft: "1px solid #EEEEEE" }}
        >
          <div className="text-[16px] font-bold text-text-color1 pb-[20px]">
            文档解析
          </div>
          <div
            className="h-[calc(100%-49px)] overflow-y-auto overflow-x-hidden"
            ref={scrollRef}
          >
            {chunksLoading && (
              <div className="h-full flex flex-col items-center justify-center">
                <div className=" text-sky-600 animate-pulse -mt-5 ">
                  努力加载中...
                </div>
              </div>
            )}
            {!chunksLoading && chunks.length === 0 && (
              <div className="h-full flexitems-center justify-center">
                <EmptyBox />
              </div>
            )}
            <div
              className="h-full max-w-[calc(100%-70px)]"
              style={{
                maxWidth: isCec ? "calc(100% - 70px)" : ""
              }}
            >
              {chunks.length !== 0 && <Timeline items={items} mode="left" />}
              <div className="w-full flex justify-center items-center h-[50px]">
                {chunksLoading && (
                  <img
                    src={loadingGif}
                    height={50}
                    style={{ height: "50px", marginLeft: "110px" }}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      <EditChunkModal
        showModal={showModal}
        setShowModal={setShowModal}
        data={curChunk}
        handleEvent={handleEvent}
        loading={editChunkLoading}
      />
    </div>
  );
};
export default KnowledgeAnalyBlock;

const traverseTree = (text: any) => {
  if (isMarkdownTableData(text)) {
    return tableValue(text)[0];
  }
  // function traverseTreeNode(node: any) {
  //   if (node.children && node.children.length > 0) {
  //     node.children.forEach((child: any, index: any) => {
  //       if (child.text) {
  //         if (isMarkdownTableData(child.text)) {
  //           node.children[index] = tableValue(node.children[0].text)[0];
  //         }
  //       }
  //       traverseTreeNode(child); // 递归遍历子节点
  //     });
  //   }
  // }
  // // 从根节点开始遍历整个树
  // tree.forEach((node, index) => {
  //   traverseTreeNode(node);
  // });
};

function WithPlate({ id, data, className = "", type }: any) {
  const tempEditor = createPlateEditor({
    plugins: [...displayerEditor({}).plugins]
  });

  let deserializedData: any = [{ children: [{ text: "" }], type: "p" }];
  if (type === "table") {
    const r = traverseTree(data);
    if (r?.type === "table") {
      deserializedData = [
        {
          children: [traverseTree(data)],
          type: "p"
        }
      ];
    } else {
      deserializedData = deserializeMd(tempEditor, data || "");
      deserializedData = validateAndFixNodes(deserializedData);
    }
  } else {
    deserializedData = deserializeMd(tempEditor, data || "");
    deserializedData = validateAndFixNodes(deserializedData);
  }
  console.log("deserializedData", deserializedData);

  const editor = createPlateEditor({
    ...displayerEditor({}),
    id: id,
    shouldNormalizeEditor: true,
    value: deserializedData
  });

  return (
    <Plate editor={editor}>
      <Editor readOnly className={className} />
    </Plate>
  );
}

const TimeItem = ({ data, curChunk, handleEvent, fInfo }: any) => {
  const plateCom = useMemo(() => {
    return (
      <WithPlate
        id={uid(32)}
        className="px-0 py-0 text-[14px] text-[#2a2a2a] overflow-x-hidden bg-transparent"
        data={data.content}
        type={data.type}
        readOnly={true}
      />
    );
  }, [data]);
  return (
    <>
      <div
        id={`chunk${data.id}`}
        className="knowledgeBlock bg-[#F3F6FF] px-[16px] pt-[20px] pb-[16px] w-[calc(100%-0px)] rounded-[8px] cursor-pointer overflow-hidden chatView relative"
        style={{
          border:
            curChunk?.id == data.id ? "1px solid #C1D2FF" : "1px solid #F3F6FF"
        }}
        onClick={() => handleEvent("clickChunk", data)}
      >
        {curChunk?.id == data.id && (
          <div className="btnGroup absolute flex right-[4px] top-[4px]">
            <img
              src={EditChunk}
              height={20}
              width={20}
              className={`mr-[4px] ${
                getBtnDisabled(FILE_BTN.ADD, fInfo.permission)
                  ? "cursor-not-allowed"
                  : "cursor-pointer"
              }`}
              onClick={(e) => {
                if (getBtnDisabled(FILE_BTN.ADD, fInfo.permission)) return;
                e.stopPropagation();
                handleEvent("editChunk", data);
              }}
            />
            <Popconfirm
              placement="topRight"
              icon={null}
              style={{ width: "224px", borderRadius: "8px" }}
              title={
                <>
                  <div className="flex items-center">
                    <img src={warning} />
                    <div className="text-[14px] text-[#000000] font-bold ml-[8px]">
                      删除
                    </div>
                  </div>
                  <div className="flex items-center">
                    <div className="w-[24px]" />
                    <div className="text-[14px] text-[#000000] mt-[8px]">
                      <span>删除后无法查看相关内</span>
                      <br />
                      <span>容，是否确认操作？</span>
                    </div>
                  </div>
                </>
              }
              onConfirm={() => handleEvent("deleteChunk", data)}
              okText="确认"
              okButtonProps={{ type: "primary", className: "gradientPopBtn" }}
              cancelButtonProps={{ className: "popBtn" }}
              cancelText="取消"
              disabled={getBtnDisabled(FILE_BTN.DELETE, fInfo.permission)}
            >
              <img
                src={DeletChunk}
                height={20}
                width={20}
                onClick={(e) => {
                  e.stopPropagation();
                }}
                className={`${
                  getBtnDisabled(FILE_BTN.DELETE, fInfo.permission)
                    ? "cursor-not-allowed"
                    : "cursor-pointer"
                }`}
              />
            </Popconfirm>
          </div>
        )}
        {data.imagePath ? (
          <div className="flex">
            <Image
              src={dealMinioUrl(data.imagePath) as any}
              className="object-contain max-w-[126px] max-h-[126px]"
            />
            <div className="text-[12px] w-[calc(100%-150px)] ml-[10px]">
              {plateCom}
            </div>
          </div>
        ) : (
          <div>
            <div className="text-[12px]">{plateCom}</div>
            <div className="flex flex-wrap mt-[10px]">
              <ImageGroupView
                imageList={data.picUrlList.filter((item: any) => item)}
              />
            </div>
          </div>
        )}
      </div>
    </>
  );
};

const Header = ({ fileInfo }: any) => {
  const navigator = useNavigate();
  return (
    <div
      className="h-[60px] bg-white flex items-center "
      style={{ borderBottom: "1px solid #EEEEEE" }}
    >
      <img
        src={Back}
        width={14}
        height={14}
        className="ml-[16px] cursor-pointer"
        onClick={() => navigator(-1)}
      />
      <div className="text-[16px] font-bold text-text-color1 ml-[35px]">
        {fileInfo?.fileName || "--"}
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
        未完成解析，请
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
