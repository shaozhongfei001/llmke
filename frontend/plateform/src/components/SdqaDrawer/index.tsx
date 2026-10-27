/* eslint-disable no-case-declarations */
import { Drawer, Flex, message } from "antd";
import { DrawerStyles } from "antd/es/drawer/DrawerPanel";
import { CloseOutlined } from "@ant-design/icons";
import "./common/style.less";
import { useSize } from "ahooks";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ChatDisplayer from "../SdAiChat/components/ChatDisplayer/index";
import { QAChatItem, StatusType } from "../SdAiChat/@types/props";
import { api_sd_startChat_re } from "../SdAiChat/core/services/servers";
import { useStateStore } from "../SdAiChat/core/useStateStore";
import { useDataTransformer } from "../SdAiChat/core/useDataTransformer";
import {
  dealMinioUrl,
  downloadByStream,
  getFileName,
  getFilePath,
  getFileType,
  getInitialZoom,
  getUrlPrefix,
  useAppPassport,
  judgePPT
} from "@root/src/core/helps";
import { Node } from "slate";
import { uid } from "uid";
import AiInputer from "../AiInputer";
import { useAiChatCore } from "../AiInputer/common/useAiChatCore";
import { FileDown } from "lucide-react";
import CustomTooltip from "../CustomTooltip";
import { GientechStreamReader } from "@root/src/core/components/StreamReader";
export interface SdContentData {
  file_source: string;
  file_type: string;
  file_name: string;
  pdfPages: number;
}

interface ISdProps {
  is_download?: boolean;
  showDownload?: boolean;
  open: boolean;
  setContent: (arg: any) => void;
  content: SdContentData;
  title: string;
  close: (arg: boolean) => void;
  hideQA?: boolean;
}

const SdqaDrawer = (props: ISdProps) => {
  const { open, setContent, hideQA = false } = props;
  const size = useSize(document.body);
  const drawerStyles: DrawerStyles = {
    mask: { boxShadow: "none", border: "none" },
    content: {
      backgroundColor: "#fff",
      minWidth: "1200px",
      //background: `url(${BG}) no-repeat`,
      backgroundSize: "cover",
      zIndex: -1
    },
    header: {},
    body: {
      height: "100%",
      padding: "20px",
      overflowY: "hidden"
    },
    footer: { padding: 0, border: "none" }
  };

  return (
    <Drawer
      placement={"bottom"}
      closable={false}
      mask={false}
      width={"100%"}
      height={size?.height ? size.height - 65 : "100%"}
      open={open}
      push={false}
      title={false}
      styles={drawerStyles}
      motion={undefined}
      afterOpenChange={(open) => {
        if (!open) {
          setContent({});
        }
      }}
    >
      {open && <SdqaContent {...props} />}
    </Drawer>
  );
};

export default SdqaDrawer;

let streamData: any = undefined;
let toAbortSdpa = false;

const SdqaContent = ({
  content,
  title,
  close,
  hideQA = false,
  showDownload,
  is_download
}: any) => {
  const { getToken } = useAppPassport();
  const token: any = getToken();
  const { serverInfo, setServerInfo } = useStateStore();

  const {
    conversationData,
    setConversationData,
    inputer,
    sseController,
    appData,
    setAppData
  } = useStateStore();

  const { stremDataToQAdata } = useDataTransformer();

  const { clearInputer, uploadAudio } = useAiChatCore({
    inputer,
    appData,
    setAppData,
    serverInfo,
    conversationData
  });

  const [currentChat, setCurrentChat] = useState<QAChatItem[]>();
  const initMessageData = useRef<QAChatItem | undefined>(undefined);
  const faqAnswerRef = useRef<string>("");
  const faqAnswerDisplayRef = useRef<string>("");
  const faqDisplayIntervalRef = useRef<any>(undefined);
  const isFaqStopRef = useRef<boolean>(false);

  const faqAnswerDisplay = (answer: string, lastData: any) => {
    faqAnswerRef.current = answer;
    const _data = { ...lastData };
    faqDisplayIntervalRef.current = setInterval(() => {
      typewriterEffect(_data);
    }, 50);
  };

  const typewriterEffect = (d: any) => {
    if (isFaqStopRef.current) {
      isFaqStopRef.current = false;
      faqAnswerRef.current = "";
    }
    const [max, min] = [10, 3];
    const _answer = faqAnswerRef.current;
    const list = _answer.split("");
    const num = Math.floor(Math.random() * (max - min + 1)) + min;
    const displayList = list.slice(0, num);
    faqAnswerDisplayRef.current =
      faqAnswerDisplayRef.current + displayList.join("");
    list.splice(0, num);
    if (sessionIdRef.current === d.sessionId) {
      setCurrentChat((prevChat) => {
        streamData = streamData || initMessageData.current;
        const p = prevChat?.length ? prevChat : [];
        const i = prevChat?.length ? prevChat?.length - 1 : 0;
        const lastData = { ...d };
        lastData.reply.content = faqAnswerDisplayRef.current;
        const data = stremDataToQAdata(lastData);
        p[i] = {
          ...streamData,
          answer: {
            ...streamData.answer,
            id: data?.qaData?.id || "",
            reference: data?.qaData?.answer?.reference || [],
            content: lastData.reply.content,
            type: "text"
          },
          status: list.length ? StatusType.Process : StatusType.Done
        };
        !list.length && clearFaqInterval();
        return [...p];
      });
    }
    faqAnswerRef.current = list.join("");
  };

  const clearFaqInterval = () => {
    clearInterval(faqDisplayIntervalRef.current);
    faqDisplayIntervalRef.current = undefined;
    faqAnswerRef.current = "";
    faqAnswerDisplayRef.current = "";
    streamData = null;
  };
  /****** typewriterEffect end ******/

  const onMessageCallback = useCallback((event: any) => {
    const curData = JSON.parse(event.data);
    const { resultType } = curData;
    //const data = stremDataToQAdata(curData);
    if (curData.status === StatusType.Done) {
      setConversationData((pre) => ({
        ...pre,
        status: curData.status
      }));

      // 推到currentChat数据里面
      if (sessionIdRef.current === curData.sessionId) {
        setCurrentChat((prevChat) => {
          streamData = streamData || initMessageData.current;
          if (streamData) {
            //获取当前对话
            const p = prevChat?.length ? prevChat : [];
            const i = prevChat?.length ? prevChat?.length - 1 : 0;
            const lastData = { ...curData };
            // 获取最终回答内容
            lastData.reply.content =
              streamData?.answer?.content + curData.reply.content || "";
            const data = stremDataToQAdata(lastData);
            console.log("最新对话的最终处理数据", data);
            p[i] = {
              ...streamData,
              answer: {
                ...streamData.answer,
                id: data?.qaData?.id || "",
                reference: data?.qaData?.answer?.reference || [],
                content: resultType === 2 ? "" : lastData.reply.content,
                type: "text" // 修正类型
              },
              status: resultType === 2 ? StatusType.Process : StatusType.Done
            };
            console.log("最新对话的最终数据", p[i]);
            streamData = undefined;
            if (resultType === 2) {
              faqAnswerDisplay(lastData.reply.content, curData);
            }
            return [...p];
          }
          return prevChat;
        });
      }
    } else {
      if (toAbortSdpa) {
        sseController.current.abort();
        setConversationData((pre) => ({
          ...pre,
          status: StatusType.Done
        }));
      } else {
        setConversationData((pre) => ({
          ...pre,
          status: curData.status
        }));
      }

      if (!streamData) {
        streamData = initMessageData.current;
      } else {
        streamData = {
          ...streamData,
          answer: {
            content: streamData.answer.content + (curData.reply.content || ""),
            type: "text" // 修正类型
          }
        };
      }
      try {
        if (sessionIdRef.current === curData.sessionId) {
          setCurrentChat((prevChat) => {
            if (streamData) {
              const p = prevChat?.length ? prevChat : [];
              const i = prevChat?.length ? prevChat?.length - 1 : 0;
              const lastData = { ...curData };
              lastData.reply.content = streamData?.answer?.content || "";
              const data = stremDataToQAdata(lastData);
              if (streamData?.answer) {
                streamData.answer.reference =
                  data?.qaData?.answer?.reference || [];
                streamData.answer.id = data?.qaData?.id || "";
              }
              p[i] = {
                ...streamData,
                status: toAbortSdpa ? StatusType.Done : curData.status
              };
              return [...p];
            }
            return prevChat;
          });
        }
      } catch (e) {
        console.error(e);
      }
    }
  }, []);

  const onErrorCallback = (e: any) => {
    setConversationData((pre) => ({
      ...pre,
      status: StatusType.Done
    }));

    setCurrentChat((prevChat) => {
      const p = prevChat?.length ? prevChat : [];
      const i = prevChat?.length ? prevChat?.length - 1 : 0;
      p[i] = {
        ...(streamData || initMessageData.current),
        status: StatusType.Done
      };
      streamData = undefined;
      return [...p];
    });

    message.error("请求失败!");
    throw e;
  };

  const onCloseCallback = () => {
    sseController.current.abort();
    console.log("onCloseCallback sse");
  };

  const sessionIdRef = useRef<string>();

  const handleQuestionSend = async (
    type?: any,
    audioText?: any,
    audioConfig?: any
  ) => {
    if (!sessionIdRef.current) {
      sessionIdRef.current = uid();
    }
    let data = Node.string(inputer.current as any);
    if (audioText && audioConfig?.audioUrl) data = audioText;

    const newQueryId = `query-${uid(32)}`;
    toAbortSdpa = false;
    streamData = undefined;
    let params: any = null;

    if (type === "reGenerate") {
      if (!currentChat?.length) return;
      const curChat = currentChat[currentChat.length - 1];
      const p: QAChatItem = {
        ...curChat,
        answer: {
          content: ""
        },
        status: 0,
        configId: conversationData.assist_id
      };
      initMessageData.current = p;
      setCurrentChat((prevChat) => {
        const cur = prevChat || [];
        const i = prevChat?.length ? prevChat.length - 1 : 0;
        cur[i] = { ...p };
        return [...cur];
      });
      sseController.current = new AbortController();

      params = {
        queryId: curChat.query.queryId || "",
        name: conversationData.name!,
        lastDate: new Date().getTime().toString(),
        type: curChat.query?.audioUrl ? "audio" : "text",
        content: curChat?.query?.content,
        audioUrl: curChat.query?.audioUrl || ""
      };
    } else {
      //拿到当前对话信息
      const p: QAChatItem = {
        id: newQueryId,
        query: {
          content: data,
          type: audioConfig?.audioUrl ? "audio" : "text",
          audioUrl: audioConfig?.audioUrl,
          queryId: newQueryId
        },
        answer: {
          content: ""
        },
        status: StatusType.Pending,
        configId: conversationData.assist_id
      };
      initMessageData.current = p;
      setCurrentChat((prevChat) => {
        return [...(prevChat || []), { ...p }];
      });
      sseController.current = new AbortController();
      setConversationData((pre: any) => ({
        ...pre,
        status: StatusType.Pending
      }));
      params = {
        queryId: newQueryId,
        name: conversationData.name!,
        lastDate: new Date().getTime().toString(),
        type: audioConfig?.audioUrl ? "audio" : "text",
        content: data,
        audioUrl: audioConfig?.audioUrl || ""
      };
    }
    api_sd_startChat_re({
      data: {
        sessionId: sessionIdRef.current,
        onMessage: onMessageCallback,
        onError: onErrorCallback,
        onClose: onCloseCallback,
        signal: sseController.current.signal,
        documentTitle: content.file_name,
        qaHistory: currentChat
          ? currentChat.slice(-5).map((item: any) => {
              return {
                answer: item?.answer?.content || "",
                query: item?.query?.content || ""
              };
            })
          : [],
        configId: content.assist_id,
        newConfigId: conversationData.assist_id!,
        fileUrl:
          content.metadata.source.indexOf("http") > -1
            ? content.metadata.source.split("/").slice(3).join("/")
            : content.metadata.source,
        ...params
      },
      config: {
        url: serverInfo.baseURL,
        token: serverInfo.token,
        enableMock: serverInfo.mockMode
      }
    });
    clearInputer(inputer.current);
  };

  const stopStream = () => {
    toAbortSdpa = true;
    isFaqStopRef.current = true;
  };

  const reGenerate = () => {
    handleQuestionSend("reGenerate");
  };

  const handleEvent = (type: string, data: any) => {
    switch (type) {
      case "fileView":
        break;
    }
  };

  const btnLoading = useMemo(() => {
    return conversationData.status == StatusType.Process;
  }, [conversationData.status]);

  useEffect(() => {
    setServerInfo({
      token: token, // 如果props.token存在则使用，否则使用空字符串
      baseURL: getUrlPrefix(), // 如果props.url存在则使用，否则使用空字符串
      mockMode: false
    });
    return () => {
      clearFaqInterval();
    };
  }, []);

  const handleDownLoad = () => {
    if (!content) return;
    const { metadata } = content;
    const url = new URL(content.file_source);
    const baseUrl = url.origin;
    const path = metadata.source;
    const fileName = path.split("/").slice(-1)[0];
    const filePath: any = dealMinioUrl(`${baseUrl}/${path}`);
    downloadByStream({ filePath, fileName });
  };

  const curData = useMemo(() => {
    if (content && token) {
      console.log("content999", content);
      const filePath = dealMinioUrl(getFilePath(content));
      const fileType = getFileType(content, filePath);
      return {
        filePath,
        fileName: getFileName(content),
        fileType,
        totalPages: content.pdfPages || 0,
        token
      };
    } else {
      return {};
    }
  }, [content, token]);

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
        eventsEmit={() => {}}
        tools={{
          close: false
        }}
      />
    );
  }, [curData]);

  return (
    <>
      <Flex align="center" className="h-[40px]" vertical>
        <Flex justify="space-between" className="w-full">
          <div className="flex items-center">
            {/* <DownloadOutlined className="mr-[5px] cursor-pointer" /> */}

            <div className="text-[#2A2A2A] font-bold max-w-[1000px] text-ellipsis overflow-hidden whitespace-nowrap mr-[5px]">
              {title}
            </div>
            {showDownload && (
              <CustomTooltip
                content={!is_download ? "无权限操作" : ""}
                type="warning"
                position="top"
              >
                <button
                  disabled={!is_download}
                  onClick={handleDownLoad}
                  className={`${
                    is_download
                      ? " bg-blue-600 hover:bg-blue-700 text-white"
                      : "bg-white text-[#555555] cursor-not-allowed"
                  } flex items-center gap-1.5 px-1 py-1 rounded-lg shadow-sm hover:shadow-md transition-all duration-200 ease-in-out text-sm font-medium`}
                >
                  <FileDown
                    className={`${
                      is_download ? "text-white/90" : "text-[#555555]"
                    } h-4 w-4 `}
                  />
                  <span>下载源文件</span>
                </button>
              </CustomTooltip>
            )}
          </div>
          <CloseOutlined onClick={() => close()} />
        </Flex>
      </Flex>
      <div
        className="bg-[rgba(255,255,255,.5)] rounded-t-[8px] h-[calc(100%-42px)] overflow-y-hidden overflow-x-hidden flex"
        style={
          hideQA
            ? {
                display: "flex",
                justifyContent: "center"
              }
            : {}
        }
      >
        <div
          id="pdfBox"
          className="w-1/2 h-full"
          style={{ borderRight: "1px solid #EEEEEE" }}
        >
          {renderFileCom}
        </div>
        {!hideQA && (
          <div className="w-1/2 h-full relative overflow-y-hidden">
            <ChatDisplayer
              currentChat={currentChat}
              setCurrentChat={setCurrentChat}
              stopStream={stopStream}
              reGenerate={reGenerate}
              handleEvent={handleEvent}
            />
            <div className=" absolute bottom-0 w-full">
              <AiInputer
                onSend={(editor: any, audioText: any, audioConfig: any) =>
                  handleQuestionSend(editor, audioText, audioConfig)
                }
                btnLoading={btnLoading}
                inputer={inputer}
                conversationData={conversationData}
                clearInputer={clearInputer}
                uploadAudio={uploadAudio}
                className="px-[20px] w-[calc(100%-40px)] pb-[40px]"
                handleEvent={() => {
                  setCurrentChat([]);
                }}
              />
            </div>
          </div>
        )}
      </div>
    </>
  );
};
