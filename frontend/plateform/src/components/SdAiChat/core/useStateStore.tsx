import React, {
  createContext,
  useContext,
  useState,
  ReactNode,
  useMemo,
  useRef
} from "react";
import { IAssistant, ListItemType, StatusType } from "../@types/props";
import { PlateEditor } from "@udecode/plate-common/react";
import { IAppData, IConversation } from "../@types/sys";
const defaultLLMOptions = {
  model: "openai-api",
  maxTokens: 512,
  temperature: 0.7
};
// 定义状态类型
interface State {
  inputer: React.MutableRefObject<null | PlateEditor>;
  appData: IAppData;
  sseController: React.MutableRefObject<AbortController>;
  setAppData: React.Dispatch<React.SetStateAction<IAppData>>;
  conversationData: IConversation;
  setConversationData: React.Dispatch<React.SetStateAction<IConversation>>;
  serverInfo: { token: string; baseURL: string; mockMode?: boolean };
  setServerInfo: React.Dispatch<
    React.SetStateAction<{ token: string; baseURL: string; mockMode?: boolean }>
  >;
}

// 创建 Context
const AiChatContext = createContext<State | undefined>(undefined);

const SdAiChatProvider: React.FC<any> = ({ children, name }) => {
  //如果不需要同级互传的设计可以把这些值都移动到core代码
  const sseController = useRef(new AbortController());
  const inputer = useRef<null | PlateEditor>(null);
  const [serverInfo, setServerInfo] = useState<{
    token: string;
    baseURL: string;
    mockMode?: boolean;
  }>({
    baseURL: "",
    token: "",
    mockMode: false
  });
  const [appData, setAppData] = useState<IAppData>({
    conversations_list: [],
    retriever_info: {
      open: false,
      data: null
    },
    assist_list: [],
    activedConversation: undefined,
    status: "0",
    sortRules: [{ label: "当天", dayPeriod: 1 }],
    conversations_list_pagging: { pageNo: 1, totalPages: 0 }
  });
  const [conversationData, setConversationData] = useState<IConversation>({
    id: undefined,
    queryId: undefined,
    name: "untitled",
    status: StatusType.Pending,
    modify_timeStamp: new Date().getTime()
  });
  const providerValue = useMemo(
    () => ({
      appData,
      setAppData,
      conversationData,
      setConversationData,
      serverInfo,
      setServerInfo,
      sseController,
      inputer
    }),
    [appData, serverInfo, conversationData]
  );

  return (
    <AiChatContext.Provider value={providerValue}>
      {children}
    </AiChatContext.Provider>
  );
};

const useStateStore = () => {
  const context = useContext(AiChatContext);

  if (!context) {
    console.error("useAiChat must be used within a AiChatProvider");
    throw new Error("useAiChat must be used within a AiChatProvider");
  }

  return context;
};

export { SdAiChatProvider, useStateStore };
