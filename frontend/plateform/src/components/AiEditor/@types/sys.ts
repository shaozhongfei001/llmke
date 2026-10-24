import { FormInstance, ProFormColumnsType } from "@ant-design/pro-form";
import { ReactNode } from "react";

export enum ModueEnum {
  Writing = "writing",
  // Polish = 'polishing',
  Review = "review",
  Material = "material"
}

// export enum ProjectEnum {
//   UNPUBLISHED = -1,
//   UNTITILED = 0,
//   PUBLISHED = 1,
// }
export enum ProjectStatus {
  Waiting,
  Process,
  Error
}

export enum ArticleStatus {
  //Temp
  UNTITILED = 0,
  PUBLISHED = 1
}

export type IModulesResult = {
  [key in ModueEnum]: any;
};

export interface ModeTypes {
  id: string;
  type_id: string;
  name: string;
  version: string;
  promptTemplateUser?: string;
  isSystem?: boolean;
}

export enum DocState {
  pending = 1,
  processing = 2,
  success = 3,
  failure = 4,
  paused = 5,
  stopped = 6
}

export const statusText = {
  [DocState.pending]: "等待中",
  [DocState.processing]: "写作中",
  [DocState.success]: "已完成",
  [DocState.failure]: "失败",
  [DocState.paused]: "暂停中",
  [DocState.stopped]: "已取消"
};

export interface IProject {
  title: string;
  id: string;
  supported_types?: ModeTypes[];
  article_type?: string;
  //自定义mode,内置mode
  article_type_mode?: string;
  article_type_version?: string;
  articleTypeKey?: string;
  article_content?: string;
  supportMaterials?: number; // 支持上传素材 1-支持 0-不支持
  supportOutlines?: number; // 支持写作大纲 1-支持 0-不支持
  content_review?: {
    errors: any;
    document: string;
  };
  article_prompt?: string;
  // 自定义模版（html模版+样式）目前是红头文件格式
  customized_style: {
    enable: boolean; //是否展示使用格式模版的checkbox
    styles: any;
    htmlSchema: any; // 存储转换后的模版（接口返回的htmlSchema转换成前端编辑器展示的模版）
    formSchemaMap: any; //模版表单映射,对应右侧表单展示
    originHtmlSchema?: any; // 存储接口返回的原始htmlSchema，saveSetting接口需要使用
  };
  //aritcle_status?: ArticleStatus;
  status: ProjectStatus;
  type?: any;
  // articleTypeVersionId?: string;
  updateTime?: number;
  currentModule: ModueEnum;
  defaultOpenSilde?: boolean;
  // 大纲
  outlines?: IStructures[];
  //素材
  contentSources?: any[];
  // article_version slate版本
  version?: any[];
  extraParams?: any;
  lengthLimit?: number;
  //内容标注
  contentAbstract?: string;
  // 用于参考文档
  files?: any[];
  // 用于溯源
  sourceList?: any[];
  // 用于处理生成文章后的保存问题，init为初始进入项目，不保存文章
  saveArticle: "init" | number;
  // 用于全文审核，自定义模板如果拥有这个字段则审核，否则不走审核
  contentRule?: "";
  // 当前表单实例
  form: FormInstance<any>;
  // 当前文章是否使用模板
  useTemplate?: string;
  // 素材去写作功能，素材文件信息
  fileInfo?: {
    fileName: string;
    fileUrl: string;
    suffix: string;
  };
  // 1--markdown 0或者null，html
  outputFormat: number | null;
  // 从后端获取场景详情的数据
  articleTypeDetail?: any;
  // 从后端获取的文章详情的数据
  articelInfo?: any;
  // 是否分段生成，1分段生成
  generateType?: number;
  // 文章总字数
  total?: number;
  // 封面section
  coverPage?: any;
  sensitiveWords?: any; //敏感词
  // 任务状态
  taskState?: DocState;
  // 任务总数
  totalTasks?: number;
  // 已完成任务数
  completedTasks?: number;
  // 总共的章节
  totalSections?: number;
  // 已生成的章节
  generatedSections?: number;
}
export interface IStructures {
  title: string;
  contentAbstract?: string;
  subParagraphs?: IStructures[];
  sectionId?: number;
  // 0-保留 1-重新生成。只有前端会用到，后端无需感知
  contentOperation?: string;
  section?: any;
  sources?: any;
  id?: string;
}

export type DataItem = {
  name: string;
  state: string;
};

export enum ModuleStatus {
  Waiting,
  Process,
  Error
}
export interface IModule {
  name: string;
  value: ModueEnum;
  uiSchema?: ProFormColumnsType<DataItem>[];
  formData?: any;
  icon?: ReactNode;
  status?: ModuleStatus;
  review_list?: IRevieweRes[];
  cssStyle?: any;
  enable_style?: boolean;
  reference?: any[];
  feedback?: {
    openModal: boolean;
    data?: {
      id?: string;
      errorType: string | number | null;
      source: string;
      target?: string;
      suggestion?: string;
      // 反馈场景:0-写作1润色 2-扩写3-缩写 4-字词审核 5-敏感词审核
      scene: number;
    };
  };
}

enum ReviewItemStatus {
  Unprocess,
  Accept,
  Refuse
}
export interface IRevieweRes {
  id: string;
  value: string;
  target_value: string;
  error_type: string;
  status: ReviewItemStatus;
  [key: string]: any;
}
export enum EditorStatus {
  // 等待
  Waiting,
  // 正在理解中
  WaitingForGen,
  // 全文生成中
  GeneratingFullText,
  // 全文审核中
  ReviewingFullText,
  // 写作完成
  Success,
  // 审核中
  Reviewing,
  // 审核完成
  ReviewingSuccess,
  // 分段生成中
  GeneratingPartialText
}
export interface EditorManager {
  id: string;
  status: EditorStatus;
  parsed_data: any;
  version?: any[];
  styles?: any;
}

export enum EditorType {
  // 预览
  Preview = "1",
  // 编辑
  Edit = "2"
}
