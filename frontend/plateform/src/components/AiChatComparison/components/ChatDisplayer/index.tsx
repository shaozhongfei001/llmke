import { useEffect, useMemo, useRef, useState } from "react";
import BScroll from "@better-scroll/core";
import ScrollBar from "@better-scroll/scroll-bar";
import ObserveDOM from "@better-scroll/observe-dom";
import MouseWheel from "@better-scroll/mouse-wheel";
BScroll.use(MouseWheel);
BScroll.use(ObserveDOM);
BScroll.use(ScrollBar);
import { Button, Flex } from "antd";
import { useStateStore } from "../../core/useStateStore";
import { api_getHelperConfigList } from "../../core/services/servers";
import { useDataTransformer } from "../../core/useDataTransformer";
import { useAiCompareCore } from "../../core/operators/useAiCompareCore";
import {
  IAppData,
  IConversation,
  StatusType,
  SystemStatus
} from "../../@types/sys";
import ChatInstance from "./ChatInstance";
import { PlusCircleOutlined } from "@ant-design/icons";

interface IChatDisplayer {
  isNew?: boolean;
  clickIndexes: (arg: any) => void;
  setSendLoading: React.Dispatch<React.SetStateAction<number>>;
  handleEvent?: (type: string, data?: any) => void;
  dataChange?: (data: any[]) => void;
}
const ChatDisplayer = ({
  clickIndexes,
  setSendLoading,
  handleEvent,
  dataChange
}: IChatDisplayer) => {
  const { appData, setAppData, serverInfo, inputer } = useStateStore();
  const { isRetriveSideOpen, addComparisonChat, clearInputer } =
    useAiCompareCore();
  const { parseHistoryData, assistantDTO_to_SelectOption } =
    useDataTransformer();
  const [configLoading, setConfigLoading] = useState(false);

  useEffect(() => {
    setConfigLoading(true);
    if (serverInfo.url) {
      api_getHelperConfigList({
        data: {
          page: 1,
          pageSize: 1000
        },
        config: {
          url: serverInfo.url,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      }).then((res) => {
        if (res && res.length) {
          const output = assistantDTO_to_SelectOption(res);
          setAppData((pre) => {
            return {
              ...pre,
              assist_list: output
            };
          });
          setConfigLoading(false);
        }
      });
    }
  }, [serverInfo]);

  //总体调整appdata.status
  useEffect(() => {
    const allConversationsNotInProcess = appData.conversations.every(
      (conv: IConversation) => conv.status !== StatusType.Process
    );
    if (allConversationsNotInProcess) {
      setAppData((prevAppData: IAppData) => ({
        ...prevAppData,
        status: SystemStatus.Waiting // 请根据实际需要设置新的状态值
      }));
    }
  }, [appData.conversations]);

  const handleAddComparisonChat = () => {
    if (
      appData.instanceLimit &&
      appData.conversations &&
      appData.conversations?.length < appData.instanceLimit
    ) {
      addComparisonChat();
    }
    return;
  };
  return (
    <div className="h-[calc(100%-133px)]">
      <Flex justify="space-between" gap={12} className="h-full">
        {appData.conversations?.map((conversation, index) => (
          <ChatInstance
            configLoading={configLoading}
            index={index}
            key={conversation.id || ""}
            id={conversation.id || ""}
            first={conversation.id === appData.conversations?.[0]?.id}
            clickIndexes={clickIndexes}
            setSendLoading={setSendLoading}
            handleEvent={handleEvent}
            dataChange={dataChange}
          />
        ))}
      </Flex>
      <div>
        {appData.conversations &&
          appData.conversations.length < (appData.instanceLimit || 0) && (
            <div className="flex h-full items-center justify-start mt-[8px]">
              <Button
                icon={<PlusCircleOutlined />}
                onClick={handleAddComparisonChat}
                type="link"
              >
                添加助手
              </Button>
              <div className="text-[12px] text-[#999999]">
                (每次最多同时运行3个助手)
              </div>
            </div>
          )}
      </div>
    </div>
  );
};

export default ChatDisplayer;
