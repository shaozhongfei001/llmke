export interface ListItemType {
  label: string;
  sessionId: string;
  gmtModified: number;
  assistant?: any;
  [key: string]: any;
}

export interface Item {
  id: string;
}

export interface IChatHistoryItem {
  id: string;
  query: any;
  answer: any;
  mode?: "chat" | "complete";
  response_mode: "streaming" | "blocking";
  files: any[];
  retriever_resources?: any[];
}

export interface IAssistant {
  details: {
    model_name: string;
    temperature: string;
    max_tokens: number;
    prologue: string;
    is_download: boolean;
  };
  label: string;
  value: string;
}

export interface IAppData {
  conversations_list: ListItemType[];
  retriever_info: {
    open: boolean;
    data: any;
  };
  assist_list: IAssistant[];
  activedConversation: string | undefined;
  status: any;
  sortRules: { label: string; dayPeriod: number }[];
  conversations_list_pagging: {
    pageNo: number;
    totalPages: number;
  };
}

export enum StatusType {
  Pending = 0,
  Process,
  Done,
  Error
}

export interface IConversation {
  id: string | undefined;
  queryId: string | undefined;
  name: string | undefined;
  status: StatusType;
  modify_timeStamp: number;
  assist_id?: string;
  history_data?: any[];
}
