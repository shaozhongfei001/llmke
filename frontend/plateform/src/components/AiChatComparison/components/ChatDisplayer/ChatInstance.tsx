/* eslint-disable react-hooks/exhaustive-deps */
import AssistantSelector from "./AssistantSelector";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAiCompareCore } from "../../core/operators/useAiCompareCore";
import { useStateStore } from "../../core/useStateStore";
import EmptyWithoutAssist from "./EmptyWithoutAssist";
import { ChatSystemType, QAChatItem, StatusType } from "../../@types/sys";
import {
  api_createDialogue,
  api_feed_back,
  api_feedbackCancel,
  api_getFeedbackList,
  api_startChat_re
} from "../../core/services/servers";
import { useAsyncEffect } from "ahooks";
import { useDataTransformer } from "../../core/useDataTransformer";
import ChatView from "./ChatView";
import { CloseOutlined } from "@ant-design/icons";
import { message } from "antd";
import FeedBackModal from "./FeedBackModal";

interface IChatInstance {
  id: string;
  first?: boolean;
  data?: any;
  configLoading: boolean;
  index: number;
  key: string;
  clickIndexes: (arg: any) => void;
  setSendLoading: React.Dispatch<React.SetStateAction<number>>;
  handleEvent?: (type: string, data?: any) => void;
  dataChange?: (data: any[]) => void;
}

const ChatInstance = (props: IChatInstance) => {
  const { setSendLoading, handleEvent, dataChange, index } = props;
  const chatContainerRef: any = useRef(null);
  const { removeComparisonChat, clearInputer } = useAiCompareCore();
  const { stremDataToQAdata } = useDataTransformer();
  const { appData, setAppData, serverInfo, inputer } = useStateStore();
  const [chatData, setChatData] = useState<any[]>([]);
  const requestFlag = useRef<string>("");
  const initMessageData = useRef<QAChatItem | undefined>(undefined);
  const streamDataRef = useRef<undefined | any>(undefined);
  const toAbortRef = useRef<string>("");
  const [openFeed, setOpenFeed] = useState(false);
  const [feedParam, setFeedParam] = useState<{
    queryId?: number | string | undefined;
    restult?: number;
  }>({});
  const currentConversation = useMemo(() => {
    return appData.conversations?.find((conv) => conv.id === props.id);
  }, [appData]);

  /****** typewriterEffect begin ******/
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

    setChatData((prevChat) => {
      streamDataRef.current = streamDataRef.current || initMessageData.current;
      const p = prevChat?.length ? prevChat : [];
      const i = prevChat?.length ? prevChat?.length - 1 : 0;
      const lastData = { ...d };
      lastData.reply.content = faqAnswerDisplayRef.current;
      const data = stremDataToQAdata(lastData);
      p[i] = {
        ...streamDataRef.current,
        answer: {
          ...streamDataRef.current.answer,
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
    faqAnswerRef.current = list.join("");
  };

  const clearFaqInterval = () => {
    clearInterval(faqDisplayIntervalRef.current);
    faqDisplayIntervalRef.current = undefined;
    faqAnswerRef.current = "";
    faqAnswerDisplayRef.current = "";
    streamDataRef.current = null;
  };
  /****** typewriterEffect end ******/

  const [feedBackList, setFeedBackList] = useState<any>([]);
  const getFeedBack = async () => {
    try {
      const res = await api_getFeedbackList({
        data: { pageNo: 1 },
        config: {
          url: serverInfo.url,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      });
      setFeedBackList(res);
    } catch (error) {
      console.log(error);
    }
  };

  useEffect(() => {
    if (!serverInfo.url) return;
    getFeedBack();
  }, [serverInfo.url]);

  const errorCallback = (e: any) => {
    setAppData((prevAppData) => ({
      ...prevAppData,
      conversations: prevAppData.conversations?.map((conv) => {
        if (conv.id === props.id) {
          return { ...conv, status: StatusType.Done };
        }
        return conv;
      })
    }));

    setChatData((prevChat) => {
      const p = prevChat?.length ? prevChat : [];
      const i = prevChat?.length ? prevChat?.length - 1 : 0;
      p[i] = {
        ...(streamDataRef.current || initMessageData.current),
        status: StatusType.Done
      };
      streamDataRef.current = undefined;
      return [...p];
    });
    setSendLoading((pre) => {
      const r = --pre;
      return r < 0 ? 0 : r;
    });
    requestFlag.current = "";
    message.error("请求失败!");
    throw e;
  };

  const onMessageCallback = useCallback(
    (event: any) => {
      const curData = JSON.parse(event.data);
      //const data = stremDataToQAdata(curData);
      const { resultType } = curData;
      if (curData.status === StatusType.Done) {
        setAppData((prevAppData) => ({
          ...prevAppData,
          conversations: prevAppData.conversations?.map((conv) => {
            if (conv.id === props.id) {
              return { ...conv, status: StatusType.Done };
            }
            return conv;
          })
        }));

        setChatData((prevChat) => {
          streamDataRef.current =
            streamDataRef.current || initMessageData.current;
          if (streamDataRef.current) {
            const p = prevChat?.length ? prevChat : [];
            const i = prevChat?.length ? prevChat?.length - 1 : 0;
            const lastData = { ...curData };
            lastData.reply.content =
              streamDataRef.current?.answer?.content + curData.reply.content ||
              "";
            const data = stremDataToQAdata(lastData);
            console.log("最新对话的最终处理数据", data);
            p[i] = {
              ...streamDataRef.current,
              answer: {
                ...streamDataRef.current.answer,
                id: data?.qaData?.id || "",
                reference: data?.qaData?.answer?.reference || [],
                content: resultType === 2 ? "" : lastData.reply.content,
                type: "text"
              },
              status: resultType === 2 ? StatusType.Process : StatusType.Done
            };
            console.log("最新对话的最终数据", p[i]);
            streamDataRef.current = undefined;
            if (resultType === 2) {
              faqAnswerDisplay(lastData.reply.content, curData);
            }
            return [...p];
          }
          return prevChat;
        });
        setSendLoading((pre) => {
          const r = --pre;
          return r < 0 ? 0 : r;
        });
        requestFlag.current = "";
      } else if (curData.status === StatusType.Process) {
        if (toAbortRef.current === initMessageData.current?.query?.queryId) {
          currentConversation?.sseController.abort();
          setAppData((prevAppData) => ({
            ...prevAppData,
            conversations: prevAppData.conversations?.map((conv) => {
              if (conv.id === props.id) {
                return { ...conv, status: StatusType.Done };
              }
              return conv;
            })
          }));
          requestFlag.current = "";
          setSendLoading((pre) => {
            const r = --pre;
            return r < 0 ? 0 : r;
          });
        } else {
          setAppData((prevAppData) => ({
            ...prevAppData,
            conversations: prevAppData.conversations?.map((conv) => {
              if (conv.id === props.id) {
                return { ...conv, status: curData.status };
              }
              return conv;
            })
          }));
        }

        if (!streamDataRef.current) {
          streamDataRef.current = initMessageData.current;
        } else {
          streamDataRef.current = {
            ...streamDataRef.current,
            answer: {
              ...(curData.reply || {}),
              content:
                streamDataRef.current.answer.content +
                (curData.reply.content || ""),
              type: "text" // 修正类型
            }
          };
        }
        try {
          setChatData((prevChat) => {
            if (streamDataRef.current) {
              const p = prevChat?.length ? prevChat : [];
              const i = prevChat?.length ? prevChat?.length - 1 : 0;
              const lastData = { ...curData };
              lastData.reply.content =
                streamDataRef.current?.answer?.content || "";
              const data = stremDataToQAdata(lastData);
              if (streamDataRef.current?.answer?.reference) {
                streamDataRef.current.answer.reference =
                  data?.qaData?.answer?.reference || [];
                streamDataRef.current.answer.id = data?.qaData?.id || "";
              }

              p[i] = {
                ...streamDataRef.current,
                status:
                  toAbortRef.current === initMessageData.current?.query?.queryId
                    ? StatusType.Done
                    : StatusType.Process
              };
              return [...p];
            }
            return prevChat;
          });
        } catch (e) {
          console.error(e);
        }
      } else if (curData.status === StatusType.Error) {
        errorCallback(event);
      }
    },
    [setAppData, setChatData, currentConversation, stremDataToQAdata, props.id]
  );

  const onErrorCallback = useCallback(
    (e: any) => {
      errorCallback(e);
    },
    [currentConversation]
  );

  const onCloseCallback = useCallback(() => {
    console.log("onCloseCallback sse");
    console.log("这里已经关闭了，不应该有数据");
    currentConversation?.sseController.abort();
  }, [currentConversation]);

  const availableAssistList = useMemo(() => {
    const selectedAssistIds =
      appData.conversations?.map((conv) => conv.assist_id) || [];
    return appData.assist_list.filter(
      (assist) =>
        !selectedAssistIds.includes(assist.value) ||
        assist.value === currentConversation?.assist_id
    );
  }, [appData.conversations, appData.assist_list]);

  const handleAssistChanged = (aid: string) => {
    setAppData((prevAppData) => {
      const updatedConversations = prevAppData.conversations?.map((conv) => {
        if (conv.id === props.id) {
          return { ...conv, assist_id: aid };
        }
        return conv;
      });

      return {
        ...prevAppData,
        conversations: updatedConversations
      };
    });
  };
  const dialog_Id = useCallback(
    (id: string, assist_id: string) => {
      if (currentConversation?.assist_id) {
        return id + "_" + assist_id;
      }
    },
    [props.id, currentConversation?.assist_id]
  );

  useAsyncEffect(async () => {
    if (
      currentConversation &&
      currentConversation.status === StatusType.Process &&
      currentConversation?.question &&
      requestFlag.current !== props.id
    ) {
      requestFlag.current = props.id || "";
      toAbortRef.current = "";
      streamDataRef.current = undefined;
      if (!currentConversation.id || !currentConversation.assist_id) {
        console.error("想屁吃？没对话id和助手id");
        return;
      }
      const lastQuestion = currentConversation?.question;
      if (!lastQuestion) return;
      const { chat_id, content, audioConfig } = lastQuestion;
      const dialogId = dialog_Id(
        currentConversation.id!,
        currentConversation.assist_id!
      );
      //查看 chatData 是否已经有数据，且最后一条对话dialogId是否一致
      const existingSession = chatData.find((chat) => chat.id === dialogId);
      setSendLoading((pre) => {
        return ++pre;
      });
      try {
        let res = existingSession
          ? {
              sessionId: existingSession.id,
              searchConfigDTO: {},
              name: "",
              configId: existingSession.searchConfigDTO?.configId
            }
          : null;
        clearInputer(inputer.current);
        if (!existingSession) {
          res = await api_createDialogue({
            data: {
              label: content,
              sessionId: dialogId!,
              assist_id: currentConversation.assist_id!,
              sysType: ChatSystemType.TEMPORARY
            },
            config: serverInfo
          });
        }

        if (
          res &&
          chat_id &&
          content &&
          currentConversation.status === StatusType.Process
        ) {
          currentConversation.sseController = new AbortController();
          api_startChat_re({
            data: {
              sessionId: res.sessionId,
              queryId: chat_id,
              name: res.name,
              lastDate: new Date().getTime().toString(),
              type: audioConfig?.audioUrl ? "audio" : "text",
              content: content,
              configId: res.configId,
              audioUrl: audioConfig?.audioUrl || "",
              onMessage: onMessageCallback,
              onError: onErrorCallback,
              onClose: onCloseCallback,
              signal: currentConversation.sseController.signal
            },
            config: {
              url: serverInfo.url,
              token: serverInfo.token,
              enableMock: serverInfo.mockMode
            }
          });
        }
        const p: QAChatItem = {
          id: res ? res.sessionId : dialogId!,
          query: {
            content: content!,
            type: audioConfig?.audioUrl ? "audio" : "text",
            audioUrl: audioConfig?.audioUrl || "",
            queryId: chat_id
          },
          answer: {
            content: ""
          },
          status: StatusType.Pending,
          searchConfigDTO: res ? res.searchConfigDTO : undefined // 添加此行以解决错误
        };
        initMessageData.current = p;
        setChatData((prevChat) => {
          return [...(prevChat || []), { ...p }];
        });
        setAppData((prevAppData) => {
          const updatedConversations = prevAppData.conversations?.map(
            (conv) => {
              if (conv.id === currentConversation.id) {
                return {
                  ...conv,
                  question: undefined
                };
              }
              return conv;
            }
          );
          return {
            ...prevAppData,
            conversations: updatedConversations
          };
        });
      } catch (error) {
        setSendLoading((pre) => {
          const r = --pre;
          return r < 0 ? 0 : r;
        });
      }
    }
  }, [appData.conversations]);

  const setFeed = (queryId: string | undefined, restult: any) => {
    setChatData((pre) => {
      const newPre: any = pre.map((item) => {
        if (item.query?.queryId === queryId) {
          return {
            ...item,
            answer: { ...item.answer, feedbackResult: restult }
          };
        }
        return item;
      });
      newPre.type = "feed";
      return newPre;
    });
  };

  const handleFeed = (
    type: "thumbsUp" | "thumbsDown",
    queryId: string | undefined,
    restult: number | undefined
  ) => {
    if (type === "thumbsUp") {
      if (restult === 1) {
        // 取消
        api_feedbackCancel({
          data: { queryId },
          config: {
            url: serverInfo.url,
            token: serverInfo.token,
            enableMock: serverInfo.mockMode
          }
        }).then((res) => {
          if (!res) return;
          setFeed(queryId, undefined);
        });
      } else {
        api_feed_back({
          data: {
            restult: 1,
            queryId
          },
          config: {
            url: serverInfo.url,
            token: serverInfo.token,
            enableMock: serverInfo.mockMode
          }
        }).then((res) => {
          if (!res) return;
          setFeed(queryId, 1);
        });
      }
    } else {
      if (restult === 0) {
        api_feedbackCancel({
          data: { queryId },
          config: {
            url: serverInfo.url,
            token: serverInfo.token,
            enableMock: serverInfo.mockMode
          }
        }).then((res) => {
          if (!res) return;
          setFeed(queryId, undefined);
        });
      } else {
        setOpenFeed(true);
        setFeedParam({ queryId, restult: 0 });
      }
    }
  };

  const reGenerate = async () => {
    if (currentConversation && requestFlag.current !== props.id) {
      requestFlag.current = props.id || "";
      toAbortRef.current = "";
      streamDataRef.current = undefined;

      if (!chatData?.length) return;
      const curChat = chatData[chatData.length - 1];
      const p: QAChatItem = {
        ...curChat,
        answer: {
          content: ""
        },
        status: StatusType.Pending
      };
      initMessageData.current = p;
      setChatData((prevChat) => {
        const cur = prevChat || [];
        const i = prevChat?.length ? prevChat.length - 1 : 0;
        cur[i] = { ...p };
        return [...cur];
      });

      const [sessionId, assist_id] = curChat.id.split("_");
      currentConversation.sseController = new AbortController();
      api_startChat_re({
        data: {
          sessionId: currentConversation.id || "",
          queryId: curChat.query.queryId || "",
          name: curChat.query.content,
          lastDate: new Date().getTime().toString(),
          type: curChat?.query?.audioUrl ? "audio" : "text",
          content: curChat?.query?.content,
          configId: assist_id,
          audioUrl: curChat?.query?.audioUrl,
          onMessage: onMessageCallback,
          onError: onErrorCallback,
          onClose: onCloseCallback,
          signal: currentConversation.sseController.signal
        },
        config: {
          url: serverInfo.url,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      });
    }
  };

  const stopStream = (id: any) => {
    toAbortRef.current = id;
    isFaqStopRef.current = true;
  };

  useEffect(() => {
    dataChange && dataChange([...chatData]);
    if (
      !chatContainerRef?.current?.scrollTo ||
      (chatData as any).type === "feed"
    )
      return;

    setTimeout(() => {
      if (!chatContainerRef?.current?.scrollTo) return;
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: "smooth"
      });
    }, 167);
  }, [chatData]);

  useEffect(() => {
    const i = index === 2 ? 0 : index;
    if (!currentConversation?.assist_id && availableAssistList?.[i]) {
      handleAssistChanged(availableAssistList?.[i]?.value);
    }
  }, [currentConversation?.assist_id, availableAssistList]);

  useEffect(() => {
    return () => {
      clearFaqInterval();
    };
  }, []);

  return (
    <div key={props.id} className="h-full rounded-[8px] flex-1 flex flex-col">
      <div className="chat-displayer relative h-full rounded-[8px] flex-1 flex flex-col">
        <div className="chat-displayer-header flex justify-between px-[16px] pt-[12px] h-[54px] bg-white rounded-t-[8px]">
          <AssistantSelector
            assistList={availableAssistList}
            value={currentConversation?.assist_id || ""}
            loading={props.configLoading}
            onChange={handleAssistChanged}
          />
          <div>
            {appData.conversations && appData.conversations.length > 2 && (
              <CloseOutlined
                onClick={() => removeComparisonChat(props.id)}
                className="cursor-pointer"
                width={14}
                height={14}
              />
            )}
          </div>
        </div>
        <div
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto overflow-x-hidden bg-white chat-displayer-content px-4 rounded-b-[8px] pb-[16px]"
        >
          {/* {currentConversation?.assist_id && chatData.length < 1 && <Empty />} */}
          {!currentConversation?.assist_id && (
            <EmptyWithoutAssist handleEvent={handleEvent} />
          )}
          {
            <div className="chatView flex pb-[15px] flex-col overflow-y-hidden">
              {chatData &&
                chatData.length > 0 &&
                chatData.map((item, index) => (
                  <ChatView
                    key={`chat-${index}`}
                    data={item}
                    handleFeed={handleFeed}
                    clickIndexes={props.clickIndexes}
                    chatDataLen={chatData.length}
                    curIndex={index}
                    currentConversation={currentConversation}
                    stopStream={stopStream}
                    reGenerate={reGenerate}
                    handleEvent={handleEvent}
                  />
                ))}
            </div>
          }
        </div>
      </div>
      <FeedBackModal
        open={openFeed}
        feedBackList={feedBackList}
        setOpen={setOpenFeed}
        feedParam={feedParam}
        setChatData={setChatData}
      />
    </div>
  );
};
export default ChatInstance;
