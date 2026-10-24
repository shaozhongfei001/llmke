export const konwledgeTitles: any[] = [
  {
    key: 1,
    label: "我的知识库"
  },
  {
    key: 2,
    label: "共享知识库"
  }
];

export interface ITabs {
  key: number;
  label: string;
}

export enum ANALYSIS_STATUS {
  DELETE = 0, //     0: "删除",
  NORMAL, //     1: "正常",
  ANALYSISING, //     2: "解析中",
  SUCCESS, //     3: "解析成功",
  FAILURE, //     4: "解析失败",
  PENDING = 99, // 99: 排队等待
  RETRY = 98, // 98: 重试中
  RE_ANALYSISING = 5 // 重新向量化
}

export enum KnowledgeBaseTabType {
  KONWLEDGE_ANALYSIS = "1",
  FAQ = "2",
  SETTING = "3",
  RETRIEVE_TEST = "4",
  DATA_EXTRACT = "5"
}

export const tabItems = [
  {
    key: KnowledgeBaseTabType.KONWLEDGE_ANALYSIS,
    label: "知识解析"
  },
  {
    key: KnowledgeBaseTabType.FAQ,
    label: "FAQ"
  },
  {
    key: KnowledgeBaseTabType.SETTING,
    label: "配置"
  },
  {
    key: KnowledgeBaseTabType.RETRIEVE_TEST,
    label: "检索测试"
  }
];

export enum Detail_Types {
  FILE_MANAGE = "file_manage",
  VERSION_MANAGE = "version_manage",
  GRAPH_MANAGE = "graph_manage",
  FAQ_MANAGE = "faq_manage"
}

export const detailTypes = [
  {
    key: Detail_Types.FILE_MANAGE,
    label: "文件管理",
    file: true
  },
  {
    key: Detail_Types.VERSION_MANAGE,
    label: "版本管理",
    file: true
  },
  {
    key: Detail_Types.FAQ_MANAGE,
    label: "FAQ管理",
    faq: true
  },
  {
    key: Detail_Types.FILE_MANAGE,
    label: "FAQ抽取",
    faq: true
  },
  {
    key: Detail_Types.GRAPH_MANAGE,
    label: "图谱增强",
    file: true,
    developing: true
  }
];

export const newPanelTypes = [KnowledgeBaseTabType.RETRIEVE_TEST];

export const statusCfg = {
  // [ANALYSIS_STATUS.DELETE]: {
  //   status: ANALYSIS_STATUS.DELETE,
  //   text: "删除",
  // },
  [ANALYSIS_STATUS.NORMAL]: {
    status: ANALYSIS_STATUS.NORMAL,
    text: {
      [tabItems[0].key]: "未解析",
      [tabItems[1].key]: "未抽取"
    },
    color: "#ffa81c",
    isBranch: true
  },
  [ANALYSIS_STATUS.PENDING]: {
    status: ANALYSIS_STATUS.PENDING,
    text: {
      [tabItems[0].key]: "排队等待",
      [tabItems[1].key]: "排队等待"
    },
    color: "#055aff",
    isBranch: true
  },
  [ANALYSIS_STATUS.RETRY]: {
    status: ANALYSIS_STATUS.RETRY,
    text: {
      [tabItems[0].key]: "解析中",
      [tabItems[1].key]: "抽取中"
    },
    color: "#055aff",
    isBranch: true,
    isLoading: true
  },
  [ANALYSIS_STATUS.ANALYSISING]: {
    status: ANALYSIS_STATUS.ANALYSISING,
    text: {
      [tabItems[0].key]: "解析中",
      [tabItems[1].key]: "抽取中"
    },
    color: "#055aff",
    isBranch: true,
    isLoading: true
  },
  [ANALYSIS_STATUS.SUCCESS]: {
    status: ANALYSIS_STATUS.SUCCESS,
    text: {
      [tabItems[0].key]: "解析完成",
      [tabItems[1].key]: "抽取完成"
    },
    color: "#52c41a",
    isBranch: true
  },
  [ANALYSIS_STATUS.FAILURE]: {
    status: ANALYSIS_STATUS.FAILURE,
    text: {
      [tabItems[0].key]: "解析失败",
      [tabItems[1].key]: "抽取失败"
    },
    color: "#ff4d4f",
    isBranch: true
  },
  [ANALYSIS_STATUS.RE_ANALYSISING]: {
    status: ANALYSIS_STATUS.RE_ANALYSISING,
    text: {
      [tabItems[0].key]: "解析中",
      [tabItems[1].key]: "抽取中"
    },
    color: "#055aff",
    isBranch: true,
    isLoading: true
  }
} as any;

export const chatPathPrefix = "/chats/knowledgeBase";

export enum faqBatchType {
  TRANSFER = "transfer",
  ENABLE = "enable",
  FORBIDDEN = "forbidden",
  DELETE = "delete",
  BATCH_ENABLE = "batchEnable",
  SIMILAR_GENERATE = "similar_generate",
  SIMILAR_DELETE = "similar_delete"
}

export enum similarBatchType {
  ENABLE = "enable",
  DELETE = "delete",
  BATCH_ENABLE = "batchEnable",
  BATCH_DELETE = "batchDelete"
}

export const faqBatchlist = [
  {
    label: "启用",
    value: faqBatchType.ENABLE,
    canDisabled: true
  },
  {
    label: "禁用",
    value: faqBatchType.FORBIDDEN,
    canDisabled: true
  },
  {
    label: "相似问生成",
    value: faqBatchType.SIMILAR_GENERATE,
    canDisabled: true
  },
  {
    label: "相似问删除",
    value: faqBatchType.SIMILAR_DELETE,
    canDisabled: true
  },
  {
    label: "转移",
    value: faqBatchType.TRANSFER,
    canDisabled: true
  },
  {
    label: "删除",
    value: faqBatchType.DELETE,
    canDisabled: true
  }
];

export const faqSimilarOptions = [
  {
    label: "批量删除",
    value: faqBatchType.DELETE
  }
];

export interface IDirList {
  limit: number;
  data: IFileItemData[];
}

interface IRecordData {
  chunkSize: number | null;
  parseType: string | null;
  reviseDate: string | null;
  count: number | null;
}
export interface IFileItemData {
  id: string;
  fileId?: number;
  folderId?: number;
  url?: string;
  fileSize?: number;
  isDir: boolean;
  hasParent?: string;
  modifyData?: string | number;
  uploadTime: string | number;
  name: string;
  type?: string;
  status: ANALYSIS_STATUS;
  // data?: IRecordData[];
  chunkSize: number | null;
  parseType: string | null;
  reviseDate: string | null;
  count: number | null;
  synLogs: Array<any>;
}

export const urlPattern =
  // eslint-disable-next-line
  /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w\.-]*)*\/?$/;
