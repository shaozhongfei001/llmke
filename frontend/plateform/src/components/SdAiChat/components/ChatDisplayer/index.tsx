/* eslint-disable react-hooks/exhaustive-deps */
import { useEffect, useMemo, useRef, useState } from "react";
import BScroll from "@better-scroll/core";
import ScrollBar from "@better-scroll/scroll-bar";
import ObserveDOM from "@better-scroll/observe-dom";
import MouseWheel from "@better-scroll/mouse-wheel";
BScroll.use(MouseWheel);
BScroll.use(ObserveDOM);
BScroll.use(ScrollBar);
import ChatView from "./ChatView";
import AssistantSelector from "./AssistantSelector";

import { Layout } from "antd";
import { useStateStore } from "../../core/useStateStore";
import {
  api_feed_back,
  api_feedbackCancel,
  api_getFeedbackList,
  api_getHelperConfigList
} from "../../core/services/servers";
import { useDataTransformer } from "../../core/useDataTransformer";
import FeedBackModal from "./components/FeedBackModal";
import Prologue from "./components/Prologue";

interface IChatDisplayer {
  isNew?: boolean;
  currentChat: any;
  setCurrentChat: any;
  stopStream: () => void;
  reGenerate: () => void;
  handleEvent?: (type: string, data?: any) => void;
  handleSd?: (type: string, data?: any) => void;
}
BScroll.use(ObserveDOM);
const ChatDisplayer = (props: IChatDisplayer) => {
  const chatContainerRef: any = useRef(null);
  const {
    currentChat,
    setCurrentChat,
    stopStream,
    reGenerate,
    handleEvent,
    handleSd
  } = props;
  const {
    appData,
    setAppData,
    serverInfo,
    conversationData,
    setConversationData
  } = useStateStore();

  const { assistantDTO_to_SelectOption } = useDataTransformer();
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
        if (res && res.records) {
          const output = assistantDTO_to_SelectOption(res.records);
          setAppData((pre) => {
            return {
              ...pre,
              assist_list: output
            };
          });
          setConfigLoading(false);
          if (output.length > 0) {
            setConversationData((pre) => {
              return {
                ...pre,
                assist_id: pre.assist_id || output[0].value
              };
            });
          }
        }
      });
    }
  }, [serverInfo]);

  const getDefaultAssistId = () => {
    return conversationData.assist_id || "";
  };

  useEffect(() => {
    setTimeout(() => {
      if (!chatContainerRef?.current?.scrollTo || currentChat?.type === "feed")
        return;
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: "smooth"
      });
    }, 167);
  }, [currentChat]);

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

  return (
    <>
      <Layout className="h-full w-full relative">
        <Layout.Content
          ref={chatContainerRef}
          className="chat-displater w-full pb-[90px] mx-auto overflow-x-hidden overflow-y-auto h-[calc(100%-90px)] mt-[90px]"
        >
          <div className="chatView flex pb-[60px] pt-[30px] flex-col overflow-y-hidden px-[8px]">
            {prologue && <Prologue data={prologue} />}
            {currentChat &&
              currentChat.length > 0 &&
              currentChat.map((item: any, index: any) => (
                <ChatView
                  key={`chat-${index}`}
                  data={item}
                  clickIndexes={(data) =>
                    handleEvent && handleEvent("clickIndexes", data)
                  }
                  stopStream={stopStream}
                  reGenerate={reGenerate}
                  handleFeed={handleFeed}
                  chatDataLen={currentChat.length}
                  curIndex={index}
                  handleEvent={handleEvent}
                  handleSd={handleSd}
                  queryBgColor="bg-[#E0DFFC]"
                />
              ))}
          </div>
        </Layout.Content>
        <div className="absolute top-[24px] left-[24px] flex">
          <AssistantSelector
            assistList={appData.assist_list}
            value={getDefaultAssistId()}
            onChange={(value) =>
              setConversationData((prev) => ({ ...prev, assist_id: value }))
            }
            className="z-50"
            loading={configLoading}
          />
        </div>
      </Layout>
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
