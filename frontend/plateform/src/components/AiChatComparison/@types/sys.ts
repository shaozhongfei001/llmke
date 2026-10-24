export interface Item {
  id: string;
}

export interface IChatHistoryItem {
  id: string;
  query: any;
  answer: any;
  mode?: 'chat' | 'complete';
  response_mode: 'streaming' | 'blocking';
  files: any[];
  retriever_resources?: any[];
}

export interface IAssistant {
  details: {
    model_name: string;
    temperature: string;
    max_tokens: number;
  };
  label: string;
  value: string;
}

export interface IAppData {
  retriever_info?: any;
  assist_list: IAssistant[];
  conversations: IConversation[];
  instanceLimit?: number;
  status: any;
  activedConversation?: string;
  // sortRules: { label: string; dayPeriod: number }[];
}

export interface IConversation {
  //这里的id和chat应用不一样，是实例id而不是dialog_id, dialog_id只在组件中chatdata存在，是计算值
  id: string | undefined;
  dialog_id?: string;
  sseController?: any;
  name: string | undefined;
  status: any;
  modify_timeStamp: number;
  assist_id?: string;
  //question_list?: { assist_id: string; content: string; chat_id: string; dialog_id: string };
  question?:
    | { audioConfig?: any; assist_id: string; content: string; chat_id: string; dialog_id: string }
    | undefined;
}

export enum ChatSystemType {
  Chat = 'KNO_INDEX', // 知识索引
  Retrieval = 'INT_SESSION', // 智能问答
  TEMPORARY = 'TEMPORARY', //临时
}

// export enum ChatProcess {
//   StartQuery,
//   WaitForAnswer,
//   ProcessAnswser,
//   Finished,
// }

// export interface ChatItem {
//   conversationId: string;
//   status: ChatProcess;
//   timeStamp: number;
//   chat_list: QAChatItem[];
// }

export interface QAChatItem {
  searchConfigDTO: any;
  id: string;
  query: {
    content: string;
    type?: 'text' | 'audio';
    audioUrl?: string | any;
    queryId?: string;
  };
  answer: {
    content: string;
    type?: 'text' | 'audio';
    reference?: any[];
  };
  timeStamp?: number;
  userFackback?: {
    status: any;
    data?: any;
  };
  status?: number;
}

export interface IReference {
  id: string;
  title: string;
  file_type: string;
  file_source: string;
  metadata: any;
  contents: [
    {
      search_type: string;
      content: string;
      type: string;
    },
  ];
}

export interface IAssistant {
  details: {
    model_name: string;
    temperature: string;
    max_tokens: number;
  };
  label: string;
  value: string;
}

export enum StatusType {
  Pending = 0,
  Process,
  Done,
  Error,
}

export enum SystemStatus {
  Waiting,
  Process,
  Error,
}
