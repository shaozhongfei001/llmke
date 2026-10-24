import { ConfigProvider, Drawer, Layout, message } from "antd";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { IuseAiChat, QAChatItem, StatusType } from "./@types/props";
import { useLayouts } from "./core/layouts/useLayouts";
import TopicListBar from "./components/TopiclistBar";
import { Node } from "slate";
import ChatDisplayer from "./components/ChatDisplayer";
import { useDataTransformer } from "./core/useDataTransformer";
import {
  api_createDialogue,
  api_getChatHistory,
  api_startChat_re
} from "./core/services/servers";
import { useStateStore } from "./core/useStateStore";
import { uid } from "uid";
import SdqaDrawer from "../SdqaDrawer";
import { useAiChatCore } from "../AiInputer/common/useAiChatCore";
import AiInputer from "../AiInputer";
import axios$ from "@root/src/apis";
import { FILEIMG, getUrlPrefix } from "@root/src/core/helps";
import { DrawerContent } from "./components/ChatDisplayer/components/DrawerContent";
let streamData: any = undefined;
let toAbort = false;
let sessionId: string | undefined = uid(32);
const { Content } = Layout;

export const useAiChat = (props: IuseAiChat) => {
  const {
    serverInfo,
    setServerInfo,
    appData,
    conversationData,
    setConversationData,
    inputer,
    sseController,
    setAppData,
    dialogData,
    setDialogData,
    isNew,
    setIsNew
  } = useStateStore();
  const { HeadLessContainer } = useLayouts();
  const { stremDataToQAdata, createDialog_to_conversationData } =
    useDataTransformer();
  const [currentChat, setCurrentChat] = useState<QAChatItem[]>();
  const [sdDrawerOpen, setSdDrawerOpen] = useState(false);
  const [drawerData, setDrawerData]: any = useState({});
  const [open, setOpen] = useState(false);
  const initMessageData = useRef<QAChatItem | undefined>(undefined);
  /****** typewriterEffect begin ******/
  const faqAnswerRef = useRef<string>("");
  const faqAnswerDisplayRef = useRef<string>("");
  const faqDisplayIntervalRef = useRef<any>(undefined);
  const isFaqStopRef = useRef<boolean>(false);
  const [newLoading, setNewLoading] = useState(false);
  const [recommendData, setRecommendData] = useState<any>([]);
  const [content, setContent] = useState<{
    title: "";
    file_type: "";
    metadata: { offset: [] };
  } | null>(null);
  useEffect(() => {
    console.log("content999", content);
  }, [content]);
  const is_download = useMemo(() => {
    if (conversationData?.assist_id && appData?.assist_list?.length) {
      const curAssist = appData.assist_list.find(
        (item: any) => item.value === conversationData.assist_id
      );
      
      return curAssist?.details.is_download;
    } else {
      return false;
    }
  }, [conversationData?.assist_id, appData?.assist_list]);
  const { clearInputer, uploadAudio, setChatList, setActiveChat } =
    useAiChatCore({
      inputer,
      appData,
      setAppData,
      serverInfo,
      conversationData
    });
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
    if (sessionId === d.sessionId) {
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
            type: "text",
            respTime: d.respTime
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

  const recommendQuestion_api = async (params: { questionId: string }) => {
    try {
      const res = await axios$.get(
        `${getUrlPrefix()}/qa/ai/recommendQuestion?queryId=${params.questionId}`
      );
      if (res) {
        setRecommendData(res.data);
      }
    } catch (error) {
      console.log(error);
    }
  };

  const getRecommendQuestion = (curData: any) => {
    if (curData?.queryId && curData?.resultType !== 3) {
      recommendQuestion_api({
        questionId: curData.queryId
      });
    } else {
      setRecommendData([]);
    }
  };

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
      if (sessionId === curData.sessionId) {
        getRecommendQuestion(curData);
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
                respTime: curData.respTime,
                type: "text" // 修正类型
              },
              status: resultType === 2 ? StatusType.Process : StatusType.Done
            };
            if (!p[i].query.filePaths?.length) {
              p[i].query.filePaths = data.qaData.query.filePaths;
            }
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
      if (toAbort) {
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
            respTime: curData.respTime,
            content: streamData.answer.content + (curData.reply.content || ""),
            type: "text" // 修正类型
          }
        };
      }
      try {
        if (sessionId === curData.sessionId) {
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
                status: toAbort ? StatusType.Done : curData.status
              };
              if (!p[i].query.filePaths?.length) {
                p[i].query.filePaths = data.qaData.query.filePaths;
              }
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

    // 推到currentChat数据里面

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

  //应用初始化
  useEffect(() => {
    appInital();
    console.log("应用网络配置：", props.url, props.token);
  }, [props.url, props.token, props.mockMode]);

  //应用初始化
  const appInital = () => {
    setServerInfo({
      token: props.token || "/", // 如果props.token存在则使用，否则使用空字符串
      baseURL: props.url, // 如果props.url存在则使用，否则使用空字符串
      mockMode: props.mockMode
    });
  };

  const handleQuestionSend = async (
    type?: any,
    audioText?: any,
    audioConfig?: any,
    filePaths?: any
  ) => {
    let data = Node.string(inputer.current as any);
    if (audioText && audioConfig?.audioUrl) data = audioText;
    const _fileUids = (filePaths || []).map((item: any) => item.uid);
    const getLabel = (content: string): string => {
      if (!content) {
        message.info("输入点什么吧！");
        throw new Error("输入内容不能为空");
      }
      // return content.length > 12 ? content.slice(0, 12) : content;
      return content;
    };
    const newQueryId = `query-${uid(32)}`;
    toAbort = false;
    streamData = undefined;
    setRecommendData([]);
    if (type === "reGenerate") {
      if (!currentChat?.length) return;
      const curChat = currentChat[currentChat.length - 1];
      const p: QAChatItem = {
        ...curChat,
        answer: {
          content: ""
        },
        status: 0
      };
      initMessageData.current = p;
      setCurrentChat((prevChat) => {
        const cur = prevChat || [];
        const i = prevChat?.length ? prevChat.length - 1 : 0;
        cur[i] = { ...p };
        return [...cur];
      });
      sseController.current = new AbortController();
      const _fileUids = (curChat.query.filePaths || []).map(
        (item: any) => item.uid
      );
      api_startChat_re({
        data: {
          sessionId: appData.activedConversation!,
          queryId: curChat.query.queryId || "",
          fileUids: _fileUids,
          name: conversationData.name!,
          lastDate: new Date().getTime().toString(),
          type: curChat.query?.audioUrl ? "audio" : "text",
          content: curChat?.query?.content,
          configId: conversationData.assist_id!,
          audioUrl: curChat.query?.audioUrl || "",
          onMessage: onMessageCallback,
          onError: onErrorCallback,
          onClose: onCloseCallback,
          signal: sseController.current.signal
        },
        config: {
          url: serverInfo.baseURL,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      });
      setConversationData((pre) => ({
        ...pre,
        status: StatusType.Process
      }));
    } else if (isNew) {
      if (!sessionId) return;
      try {
        const label = getLabel(data);
        setNewLoading(true);
        const createDialogueResponse = await api_createDialogue({
          data: {
            label,
            sessionId,
            assist_id: conversationData.assist_id!
          },
          config: {
            url: serverInfo.baseURL,
            token: serverInfo.token,
            enableMock: serverInfo.mockMode
          }
        });
        setIsNew(false);
        setActiveChat(sessionId);
        //拿到createDialogueResponse的返回，确认ID, set appdata,conversationdata初始化
        const newConversation = createDialog_to_conversationData(
          createDialogueResponse
        );
        setChatList({ page: 1 }, serverInfo, () => {
          setNewLoading(false);
        });

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
          status: StatusType.Process
        };
        initMessageData.current = p;

        setCurrentChat([{ ...p }]);

        sseController.current = new AbortController();
        api_startChat_re({
          data: {
            sessionId: createDialogueResponse.sessionId,
            queryId: newQueryId,
            fileUids: _fileUids,
            name: newConversation.name ? newConversation.name : "untitled",
            lastDate: new Date().getTime().toString(),
            type: audioConfig?.audioUrl ? "audio" : "text",
            content: data,
            configId: conversationData.assist_id!,
            audioUrl: audioConfig?.audioUrl || "",
            onMessage: onMessageCallback,
            onError: onErrorCallback,
            onClose: onCloseCallback,
            signal: sseController.current.signal
          },
          config: {
            url: serverInfo.baseURL,
            token: serverInfo.token,
            enableMock: serverInfo.mockMode
          }
        });
        setConversationData((pre) => ({
          ...pre,
          status: StatusType.Process,
          queryId: newQueryId
        }));
      } catch (error) {
        setNewLoading(false);
        // 这里可以添加错误处理逻辑，例如显示错误消息
        console.error("创建对话失败:", error);
        throw error; // 重新抛出错误，让外部业务逻辑处理
      }
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
        status: StatusType.Process
      };
      initMessageData.current = p;
      setCurrentChat((prevChat) => {
        return [...(prevChat || []), { ...p }];
      });
      sseController.current = new AbortController();
      api_startChat_re({
        data: {
          sessionId: appData.activedConversation!,
          fileUids: _fileUids,
          queryId: newQueryId,
          name: conversationData.name!,
          lastDate: new Date().getTime().toString(),
          type: audioConfig?.audioUrl ? "audio" : "text",
          content: data,
          configId: conversationData.assist_id!,
          audioUrl: audioConfig?.audioUrl || "",
          onMessage: onMessageCallback,
          onError: onErrorCallback,
          onClose: onCloseCallback,
          signal: sseController.current.signal
        },
        config: {
          url: serverInfo.baseURL,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      });
      setConversationData((pre) => ({ ...pre, status: StatusType.Process }));
    }
    clearInputer(inputer.current);
  };

  const stopStream = () => {
    //toAbort = true;
    isFaqStopRef.current = true;
    sseController.current.abort();

    setConversationData((pre) => ({
      ...pre,
      status: StatusType.Done
    }));
    setCurrentChat((prevChat) => {
      const p = prevChat?.length ? prevChat : [];
      const i = prevChat?.length ? prevChat?.length - 1 : 0;
      if (p?.[i]) {
        p[i] = {
          ...p[i],
          status: StatusType.Done
        };
        return [...p];
      }
      return prevChat;
    });
  };

  const reGenerate = () => {
    handleQuestionSend("reGenerate");
  };
  const handleSd = (type: string, data?: any) => {
    switch (type) {
      case "click:indexes":
        setOpen(true);
        setContent(data);
        break;
      case "open":
        setDrawerData(data);
        setSdDrawerOpen(true);
        break;
      case "close":
        setSdDrawerOpen(false);
        break;
    }
  };

  useEffect(() => {
    return () => {
      clearFaqInterval();
    };
  }, []);

  const [isDialogLoading, setIsDialogLoading] = useState(false);
  const getChatHistory = async (data: any) => {
    sessionId = data.sessionId;
    try {
      setIsDialogLoading(true);
      const res = await api_getChatHistory({
        data: { sessionId: data.sessionId },
        config: {
          url: serverInfo.baseURL,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      });
      setIsDialogLoading(false);
      setDialogData(res);
    } catch (error) {
      setIsDialogLoading(false);
    }
  };

  const btnLoading = useMemo(() => {
    return conversationData.status == StatusType.Process;
  }, [conversationData.status]);

  useEffect(() => {
    if (dialogData?.queryReplyPairList?.length) {
      const last =
        dialogData.queryReplyPairList[dialogData.queryReplyPairList.length - 1];
      if (last?.reply?.recommendQuestion) {
        const recom = JSON.parse(last.reply.recommendQuestion);
        setRecommendData(recom);
      }
    }
  }, [dialogData]);
  return {
    AppElement: (
      <>
        <ConfigProvider
          theme={{
            algorithm: [],
            token: {
              borderRadius: 3,
              fontSize: 14,
              fontFamilyCode: "Helvetica",
              colorText: "#555555",
              fontSizeHeading4: 14,
              fontSizeHeading5: 12,
              lineHeightHeading5: 1.25,
              colorError: "#D70016",
              colorWarning: "#FA8015",
              colorInfo: "#1D70F5",
              colorSuccess: "#15AD2C",
              colorPrimary: "#1963D1",
              colorPrimaryActive: "#1D70F5",
              colorTextSecondary: "#cccccc"
            },
            components: {
              Typography: {
                titleMarginBottom: "0.25rem",
                titleMarginTop: "0.25rem"
              },
              Layout: {
                siderBg: "#04336B"
              },
              Button: {
                contentFontSize: 14,
                contentFontSizeSM: 10,
                defaultHoverBorderColor: "",
                defaultHoverColor: "",
                colorBgBase: "#ffffff",
                colorPrimary: "linear-gradient(90deg,#0359FF,#BD9CFF)",
                colorPrimaryHover: "linear-gradient(90deg,#0359FF,#BD9CFF)",
                colorPrimaryActive: "linear-gradient(90deg,#0359FF,#BD9CFF)"
              },
              Popconfirm: {
                borderRadius: 8
              }
            }
          }}
        >
          <HeadLessContainer>
            <TopicListBar
              sortRules={props.sortRules || appData.sortRules}
              actived={appData.activedConversation}
              data={appData.conversations_list}
              eventEmit={(type: string, data: any) => {
                switch (type) {
                  case "create":
                    setIsNew(true);
                    setDialogData([]);
                    sessionId = uid(32);
                    setActiveChat(sessionId);
                    setCurrentChat([]);
                    setRecommendData([]);
                    break;
                  case "click":
                    setIsNew(false);
                    setDialogData([]);
                    getChatHistory(data);
                    setCurrentChat([]);
                    setRecommendData([]);
                    setConversationData((pre) => {
                      return {
                        ...pre,
                        assist_id: "showLoading"
                      };
                    });
                    break;
                }
              }}
            />
            <Content>
              <HeadLessContainer>
                <div
                  className={`${import.meta.env.VITE_HEADLESS === "true" ? "h-[100vh]" : "h-[calc(100vh-60px)]"} w-full relative flex flex-col items-center`}
                >
                  <ChatDisplayer
                    isNew={isNew}
                    currentChat={currentChat}
                    setCurrentChat={setCurrentChat}
                    stopStream={stopStream}
                    reGenerate={reGenerate}
                    handleSd={handleSd}
                    newLoading={newLoading}
                    isLoading={isDialogLoading}
                    data={dialogData}
                    recommendData={recommendData}
                  />
                  <div className="mt-[30px] pl-[30px] pb-[55px] max-w-[1070px] w-[calc(100%-190px)]">
                    <AiInputer
                      onSend={(
                        editor: any,
                        audioText: any,
                        audioConfig: any,
                        docs: any
                      ) =>
                        handleQuestionSend(
                          editor,
                          audioText,
                          audioConfig,
                          docs
                        )
                      }
                      btnLoading={btnLoading}
                      inputer={inputer}
                      conversationData={conversationData}
                      clearInputer={clearInputer}
                      uploadAudio={uploadAudio}
                      className=""
                      hideBtn
                      showFileUpload
                      sessionId={sessionId}
                      handleEvent={() => {
                        setCurrentChat([]);
                      }}
                    />
                  </div>
                </div>
              </HeadLessContainer>
            </Content>
          </HeadLessContainer>
        </ConfigProvider>
        <SdqaDrawer
          open={sdDrawerOpen}
          title={drawerData.file_name}
          close={() => handleSd("close")}
          content={drawerData}
          setContent={setDrawerData}
          showDownload={true}
          is_download={is_download}
        />
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
              <div className="flex items-center">
                <img
                  src={FILEIMG[content?.file_type || "doc"]}
                  width={18}
                  height={18}
                  className="mr-[6px]"
                />
                <div>{`${content?.title}.${content?.file_type}`}</div>
              </div>
            }
            autoFocus={false}
            onClose={() => setOpen(false)}
            open={open}
            width={600}
            className="overflow-x-hidden"
            destroyOnClose
            afterOpenChange={(open) => {
              if (!open) {
                setContent(null);
              }
            }}
          >
            <DrawerContent
              content={content as any}
              onClose={() => setOpen(false)}
            />
          </Drawer>
        </ConfigProvider>
      </>
    )
  };
};
