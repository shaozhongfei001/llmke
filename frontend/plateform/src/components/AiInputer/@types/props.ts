export interface ListItemType {
  label: string;
  sessionId: string;
  gmtModified: number;
  assistant?: any;
  [key: string]: any;
}
export interface ListType {
  activedItem: string;
  data: ListItemType[];
  sortRules?: { label: string; dayPeriod: number }[];
}

export interface SortRule {
  label: string;
  dayPeriod: number;
}

export enum ChatSystemType {
  Chat = "KNO_INDEX", // 知识索引
  Retrieval = "INT_SESSION" // 智能问答
}
