import React, { createContext, useContext, useState, ReactNode, useMemo, useRef } from 'react';
import { IAssistant } from '../@types/props';
import { create } from 'zustand';
import { PlateEditor } from '@udecode/plate-common/react';
import { IAppData, IConversation } from '../@types/sys';
import { uid } from 'uid';
import { ListItemType } from '../../AiChat/@types/props';
const defaultLLMOptions = {
  model: 'openai-api',
  maxTokens: 512,
  temperature: 0.7,
};
// 定义状态类型
interface State {
  inputer: React.MutableRefObject<null | PlateEditor>;
  appData: IAppData;
  setAppData: React.Dispatch<React.SetStateAction<IAppData>>;
  serverInfo: { token: string; url: string; mockMode?: boolean };
  setServerInfo: React.Dispatch<
    React.SetStateAction<{ token: string; url: string; mockMode?: boolean }>
  >;
}

// 创建 Context
const AiChatContext = createContext<State | undefined>(undefined);

const AiCompareProvider: React.FC<any> = ({ children, name }) => {
  const inputer = useRef<null | PlateEditor>(null);
  const [serverInfo, setServerInfo] = useState<{ token: string; url: string; mockMode?: boolean }>({
    token: '',
    url: '',
    mockMode: false,
  });

  const [appData, setAppData] = useState<IAppData>({
    retriever_info: [],
    assist_list: [],
    status: 0,
    instanceLimit: 3,
    conversations: [
      {
        id: uid(32),
        name: '',
        status: 0,
        modify_timeStamp: new Date().getTime(),
        sseController: new AbortController(),
      },
      {
        id: uid(32),
        name: '',
        status: 0,
        modify_timeStamp: new Date().getTime(),
        sseController: new AbortController(),
      },
    ],
  });
  const [conversationData, setConversationData] = useState<IConversation>({
    id: undefined,
    name: 'untitled',
    status: '0',
    modify_timeStamp: new Date().getTime(),
    // history_data: []
  });
  const providerValue = useMemo(
    () => ({
      appData,
      setAppData,
      serverInfo,
      setServerInfo,
      inputer,
    }),
    [appData, serverInfo, conversationData]
  );

  return <AiChatContext.Provider value={providerValue}>{children}</AiChatContext.Provider>;
};

const useStateStore = () => {
  const context = useContext(AiChatContext);

  if (!context) {
    console.error('useAiChat must be used within a AiChatProvider');
    throw new Error('useAiChat must be used within a AiChatProvider');
  }

  return context;
};

export { AiCompareProvider, useStateStore };
