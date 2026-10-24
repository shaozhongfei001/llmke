// export interface IuseAiChat {
//   url: string;
//   token?: string;
//   mockMode?: boolean;
//   eventsManager?: (e: string, data?: any) => void;
//   styles?: any;
//   device?: string;
//   sortRules?: { label: string; dayPeriod: number }[];
// }
// export interface ListItemType {
//   label: string;
//   sessionId: string;
//   gmtModified: number;
//   assistant?: any;
//   [key: string]: any;
// }
// export interface ListType {
//   activedItem: string;
//   data: ListItemType[];
//   sortRules?: { label: string; dayPeriod: number }[];
// }

// export interface SortRule {
//   label: string;
//   dayPeriod: number;
// }
// export enum ChatStatus {
//   Wait,
//   Process,
//   Done,
//   Error,
// }

// export interface ChatItem {
//   sessionId: string;
//   label: string;
//   status: ChatStatus;
//   filePath?: string;
//   queryReplyPairList: any[];
//   [key: string]: any;
// }

export interface ChatQaContent {
  queryId: string;
  type: "query" | "anwser" | "system";
  gmtCreate: number;
  createBy?: string;
  content: string;
  [key: string]: any;
}

export enum ChatProcess {
  StartQuery,
  WaitForAnswer,
  ProcessAnswser,
  Finished
}

export interface ChatItem {
  conversationId: string;
  status: ChatProcess;
  timeStamp: number;
  chat_list: QAChatItem[];
}

export interface QAChatItem {
  id: string;
  query: {
    content: string;
    type?: "text" | "audio";
    audioUrl?: string | any;
    queryId?: string;
  };
  answer: {
    content: string;
    type?: "text" | "audio";
    reference?: IReference[];
    feedbackResult?: undefined | number;
    id?: string | number;
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
  contents: any[];
  pic_url_list?: any[];
  pdfPages: number;
  file_name: string;
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
  Error
}
