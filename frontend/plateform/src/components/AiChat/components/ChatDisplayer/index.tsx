/* eslint-disable react-hooks/exhaustive-deps */
import { useEffect, useMemo, useRef, useState } from "react";
import BScroll from "@better-scroll/core";
import ScrollBar from "@better-scroll/scroll-bar";
import ObserveDOM from "@better-scroll/observe-dom";
import MouseWheel from "@better-scroll/mouse-wheel";
BScroll.use(MouseWheel);
BScroll.use(ObserveDOM);
BScroll.use(ScrollBar);
import ChatView, { FILEIMG } from "./ChatView";
import AssistantSelector from "./AssistantSelector";

import { ConfigProvider, Drawer, Skeleton } from "antd";
import { useStateStore } from "../../core/useStateStore";
import {
  api_feed_back,
  api_feedbackCancel,
  api_getChatHistory,
  api_getFeedbackList,
  api_getHelperConfigList
} from "../../core/services/servers";
import { useDataTransformer } from "../../core/useDataTransformer";
import FeedBackModal from "./components/FeedBackModal";
import { StatusType } from "../../@types/props";
import Prologue from "./components/Prologue";
import { useAiChatCore } from "@root/src/components/AiInputer/common/useAiChatCore";
import "./style.less";
import RecommendItem from "./components/RecommendItem";

interface IChatDisplayer {
  newLoading: boolean;
  isNew?: boolean;
  currentChat: any;
  setCurrentChat: any;
  stopStream: () => void;
  reGenerate: () => void;
  handleSd?: (type: string, data?: any) => void;
  isLoading: boolean;
  data: any;
  recommendData: any[];
}
BScroll.use(ObserveDOM);
const ChatDisplayer = (props: IChatDisplayer) => {
  const chatContainerRef: any = useRef(null);
  const {
    currentChat,
    setCurrentChat,
    stopStream,
    reGenerate,
    handleSd,
    newLoading,
    isLoading,
    data,
    recommendData
  } = props;
  const {
    appData,
    setAppData,
    serverInfo,
    conversationData,
    setConversationData,
    inputer
  } = useStateStore();

  const { conversationsMap } = useAiChatCore({
    inputer,
    appData,
    setAppData,
    serverInfo,
    conversationData
  });
  const { parseHistoryData, assistantDTO_to_SelectOption } =
    useDataTransformer();
  const [configLoading, setConfigLoading] = useState(false);
  const [openFeed, setOpenFeed] = useState(false);

  const [feedParam, setFeedParam] = useState<{
    queryId?: number | string | undefined;
    restult?: number;
  }>({});
  const [feedBackList, setFeedBackList] = useState<any>([]);

  const getFeedBack = async () => {
    try {
      const res = await api_getFeedbackList({
        data: { pageNo: 1 },
        config: {
          url: serverInfo.baseURL,
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
    if (!serverInfo.baseURL) return;

    getFeedBack();
  }, [serverInfo.baseURL]);

  const setFeed = (queryId: any, restult: any) => {
    setCurrentChat((pre: any) => {
      const newPre = pre.map((item: any) => {
        if (item.query.queryId === queryId) {
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
    queryId: number | string | undefined,
    restult: number | undefined
  ) => {
    if (type === "thumbsUp") {
      if (restult === 1) {
        // 取消
        api_feedbackCancel({
          data: { queryId },
          config: {
            url: serverInfo.baseURL,
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
            url: serverInfo.baseURL,
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
            url: serverInfo.baseURL,
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

  useEffect(() => {
    setConfigLoading(true);
    if (serverInfo.token) {
      api_getHelperConfigList({
        data: {
          page: 1,
          pageSize: 1000
        },
        config: {
          url: serverInfo.baseURL,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      }).then((res) => {
        if (res) {
          const output = assistantDTO_to_SelectOption(res);
          setAppData((pre) => {
            return {
              ...pre,
              assist_list: output
            };
          });
          setConfigLoading(false);
          if (output.length > 0) {
            const defaultAssis = output.filter((i: any) => i.isDefault);
            setConversationData((pre) => {
              const assist_id = pre.assist_id
                ? pre.assist_id
                : defaultAssis.length
                  ? defaultAssis[0].value
                  : output?.[0].value;
              return {
                ...pre,
                assist_id
              };
            });
          }
        }
      });
    }
  }, [serverInfo]);

  useEffect(() => {
    if (!isLoading && data) {
      if (
        data?.queryReplyPairList?.length === 1 &&
        data.queryReplyPairList[0].reply === null
      )
        return;
      const output = parseHistoryData(data);
      const curConversation = conversationsMap.get(
        appData?.activedConversation
      );

      setConversationData((pre) => {
        return {
          ...pre,
          id: appData.activedConversation,
          name: curConversation?.label,
          queryId: output?.length
            ? output?.[output?.length - 1]?.id
            : undefined,
          assist_id:
            curConversation?.configId ||
            data?.configId ||
            (pre.assist_id === "showLoading" ? "" : pre.assist_id),
          status: output?.length
            ? output?.[output?.length - 1]?.id
              ? StatusType.Done
              : StatusType.Pending
            : StatusType.Pending
        };
      });

      output?.length && setCurrentChat(output);
    }
  }, [data, isLoading]);

  const getDefaultAssistId = () => {
    return conversationData.assist_id || "";
  };

  useEffect(() => {
    if (!chatContainerRef?.current?.scrollTo || currentChat?.type === "feed")
      return;
    chatContainerRef.current.addEventListener("wheel", (event: any) => {
      event.preventDefault(); // 阻止默认滚动行为
      const { deltaY } = event; // 获取滚动方向和速度
      chatContainerRef.current.scrollTop -= deltaY; //  反转方向
    });
  }, []);

  const prologue = useMemo(() => {
    const v = getDefaultAssistId();
    const curAssistant = appData.assist_list.find((item) => {
      return item.value === v;
    });
    if (curAssistant) {
      return curAssistant.details.prologue;
    } else {
      return "";
    }
  }, [props.isNew, appData.assist_list, conversationData]);

  const getShowSkeleton = () => {
    return (
      (isLoading && !props.isNew && !currentChat?.length) ||
      (newLoading && !prologue)
    );
  };

  return (
    <>
      <div
        ref={chatContainerRef}
        style={{ direction: "ltr", transform: "rotate(180deg)" }}
        className="flex flex-col overflow-x-hidden overflow-y-auto hide-scrollbar flex-1 mt-[70px] max-w-[1100px] w-[calc(100%-180px)]"
      >
        <div
          style={{
            flexGrow: 1,
            flexShrink: 1,
            flex: 1
          }}
        ></div>
        <div className="w-full">
          {getShowSkeleton() ? (
            <Skeleton
              active
              className="pl-[50px] pr-[16px]"
              style={{ transform: "rotate(180deg)" }}
            />
          ) : (
            <div className="flex flex-col-reverse overflow-hidden">
              {prologue && (
                <Prologue
                  data={prologue}
                  className="mr-[12px]"
                  style={{ transform: "rotate(180deg)" }}
                />
              )}
              {currentChat &&
                currentChat.length > 0 &&
                currentChat.map((item: any, index: any) => (
                  <ChatView
                    key={`chat-${index}`}
                    data={item}
                    clickIndexes={(data) =>
                      handleSd && handleSd("click:indexes", data)
                    }
                    stopStream={stopStream}
                    reGenerate={reGenerate}
                    handleFeed={handleFeed}
                    chatDataLen={currentChat.length}
                    curIndex={index}
                    handleSd={handleSd}
                  />
                ))}
              {!!recommendData.length && !props.isNew && (
                <div
                  className="flex flex-col pl-[55px] pr-[22px]"
                  style={{ transform: "rotate(180deg)" }}
                >
                  <div className="text-[#888888] text-[12px] py-[16px]">
                    你可以继续问我：
                  </div>
                  <div className="flex flex-wrap">
                    {recommendData.map((item, index) => {
                      return (
                        <RecommendItem
                          key={index}
                          data={item}
                          handleEvent={(data: string) => {
                            if (inputer?.current?.tf?.setValue) {
                              inputer.current.tf.setValue([
                                {
                                  type: "p",
                                  children: [{ text: data }]
                                }
                              ]);
                            }
                          }}
                        />
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="absolute top-[16px] left-[20px] flex">
        <AssistantSelector
          appData={appData}
          assistList={appData.assist_list}
          value={getDefaultAssistId()}
          onChange={(value) =>
            setConversationData((prev) => ({ ...prev, assist_id: value }))
          }
          className="z-50"
          disabled={!props.isNew}
          loading={configLoading}
        />
      </div>
      <FeedBackModal
        open={openFeed}
        feedBackList={feedBackList}
        setOpen={setOpenFeed}
        feedParam={feedParam}
        setCurrentChat={setCurrentChat}
      />
    </>
  );
};

export default ChatDisplayer;
