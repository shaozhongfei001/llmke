/** ArticleDto */
export interface ArticleDto {
  /** @format byte */
  articleSubType?: string;
  /** @format byte */
  articleType?: string;
  /** @format int64 */
  articleTypeId?: number;
  /** @format int64 */
  articleTypeVersionId?: number;
  content?: string;
  contentAbstract?: string;
  contentSources?: ContentSourcesDto[];
  /** @format byte */
  contentType?: string;
  extraParams?: object;
  /** @format date-time */
  gmtCreate?: string;
  /** @format date-time */
  gmtModified?: string;
  /** @format int64 */
  id?: number;
  /** @format int64 */
  lastHintVersionId?: number;
  /** @format int32 */
  lengthLimit?: number;
  /** @format int32 */
  lengthLimitLow?: number;
  /** @format int32 */
  outlineGenType?: number;
  outlines?: OutlinesDto;
  /** @format int64 */
  relatedTemplateId?: number;
  /** @format byte */
  status?: string;
  title?: string;
  userId?: string;
}

/** ArticleErrorDto */
export interface ArticleErrorDto {
  errorContent?: string;
  errorContext?: ErrorContextDto;
  /** @format int32 */
  errorType?: number;
  /** @format int32 */
  id?: number;
  targetContent?: string;
  tips?: string;
}

/** ArticleFeedbackDTO */
export interface ArticleFeedbackDTO {
  articleId?: string;
  /** @format byte */
  feedbackType?: string;
  /** @format date-time */
  gmtCreate?: string;
  /** @format date-time */
  gmtModified?: string;
  /** @format int64 */
  id?: number;
  rawContent?: string;
  /** @format byte */
  scene?: string;
  targetContent?: string;
  userComment?: string;
  userId?: string;
}

/** ArticleFeedbackReportRequest */
export interface ArticleFeedbackReportRequest {
  articleId?: string;
  /** @format byte */
  feedbackType: string;
  rawContent?: string;
  /** @format byte */
  scene: string;
  targetContent?: string;
  userComment?: string;
}

/** ArticleMaterialDTO */
export interface ArticleMaterialDTO {
  /** 存储源空间桶名称 */
  bucketName?: string;
  /**
   * 上传用户id
   * @example "admin"
   */
  creatorId?: string;
  /**
   * 文件名
   * @example "文档.docx"
   */
  fileName?: string;
  /**
   * 文件大小, 单位B
   * @format int64
   * @example 1
   */
  fileSize?: number;
  /**
   * 文件后缀
   * @example ".doc"
   */
  fileSuffix?: string;
  /**
   * 文件访问路径
   * @example "http://ip:9000/dev-rag-data/测试/xxx.pdf"
   */
  fileUrl?: string;
  /**
   * 上传时间
   * @format date-time
   */
  gmtCreate?: string;
  /**
   * 更新时间
   * @format date-time
   */
  gmtModified?: string;
  /**
   * 文件id
   * @format int64
   * @example 1
   */
  id?: number;
  /**
   * 大模型解析后的文件信息
   * @example "我是由"作文.doc"文件经过大模型解析后的信息"
   */
  parseMessage?: string;
  /** 解析后的url */
  parsedUrl?: string;
  /**
   * 状态
   * @format byte
   */
  state?: string;
  /**
   * 状态 1:有效  -1:已删除。默认1
   * @format int32
   * @example 1
   */
  status?: number;
  /**
   * 存储源标识
   * @example "minio"
   */
  storeFlag?: string;
}

/** ArticleTypeCreateRequest */
export interface ArticleTypeCreateRequest {
  contentRule?: string;
  desc?: string;
  fixedContent?: string;
  formatTemplate?: string;
  name: string;
  paramsSchema?: string;
  promptTemplateSystem?: string;
  promptTemplateUser: string;
}

/** ArticleTypeDto */
export interface ArticleTypeDto {
  contentRule?: string;
  desc?: string;
  fixedContent?: string;
  formatTemplate?: string;
  /** @format date-time */
  gmtCreate?: string;
  /** @format date-time */
  gmtModified?: string;
  /** @format int64 */
  id?: number;
  modelId?: string;
  modelTemperature?: string;
  name?: string;
  paramsSchema?: string;
  promptTemplateSystem?: string;
  promptTemplateUser?: string;
  /** @format int64 */
  versionId?: number;
}

/** ArticleTypeSaveRequest */
export interface ArticleTypeSaveRequest {
  contentRule?: string;
  desc?: string;
  fixedContent?: string;
  formatTemplate?: string;
  name?: string;
  paramsSchema?: string;
  promptTemplateSystem?: string;
  promptTemplateUser?: string;
}

/** BriefReportAddRequest */
export interface BriefReportAddRequest {
  content?: string;
  contentAbstract?: string;
  contentSource?: string;
  outline?: string;
  /** @format int64 */
  templateId?: number;
  title?: string;
}

/** BriefReportDTO */
export interface BriefReportDTO {
  content?: string;
  contentAbstract?: string;
  contentSource?: string;
  creatorId?: string;
  /** @format int64 */
  id?: number;
  outline?: string;
  /** @format int32 */
  status?: number;
  /** @format int64 */
  templateId?: number;
  title?: string;
  url?: string;
}

/** BriefReportEditRequest */
export type BriefReportEditRequest = object;

/** CommonPageResult«ArticleDto» */
export interface CommonPageResultArticleDto {
  details?: ArticleDto[];
  /** @format int64 */
  pageNo?: number;
  /** @format int64 */
  pageSize?: number;
  /** @format int64 */
  totalCount?: number;
}

/** CommonPageResult«ArticleMaterialDTO» */
export interface CommonPageResultArticleMaterialDTO {
  details?: ArticleMaterialDTO[];
  /** @format int64 */
  pageNo?: number;
  /** @format int64 */
  pageSize?: number;
  /** @format int64 */
  totalCount?: number;
}

/** CommonPageResult«ArticleTypeDto» */
export interface CommonPageResultArticleTypeDto {
  details?: ArticleTypeDto[];
  /** @format int64 */
  pageNo?: number;
  /** @format int64 */
  pageSize?: number;
  /** @format int64 */
  totalCount?: number;
}

/** CommonResponse«ArticleDto» */
export interface CommonResponseArticleDto {
  data?: ArticleDto;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«ArticleFeedbackDTO» */
export interface CommonResponseArticleFeedbackDTO {
  data?: ArticleFeedbackDTO;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«ArticleMaterialDTO» */
export interface CommonResponseArticleMaterialDTO {
  data?: ArticleMaterialDTO;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«ArticleTypeDto» */
export interface CommonResponseArticleTypeDto {
  data?: ArticleTypeDto;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«BriefReportDTO» */
export interface CommonResponseBriefReportDTO {
  data?: BriefReportDTO;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«CommonPageResult«ArticleDto»» */
export interface CommonResponseCommonPageResultArticleDto {
  data?: CommonPageResultArticleDto;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«CommonPageResult«ArticleMaterialDTO»» */
export interface CommonResponseCommonPageResultArticleMaterialDTO {
  data?: CommonPageResultArticleMaterialDTO;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«CommonPageResult«ArticleTypeDto»» */
export interface CommonResponseCommonPageResultArticleTypeDto {
  data?: CommonPageResultArticleTypeDto;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«IntelligenceSubsDTO» */
export interface CommonResponseIntelligenceSubsDTO {
  data?: IntelligenceSubsDTO;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«List«ArticleErrorDto»» */
export interface CommonResponseListArticleErrorDto {
  data?: ArticleErrorDto[];
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«List«UploadArticleMaterialDTO»» */
export interface CommonResponseListUploadArticleMaterialDTO {
  data?: UploadArticleMaterialDTO[];
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«Map«string,string»» */
export interface CommonResponseMapStringString {
  data?: Record<string, string>;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«OutlinesDto» */
export interface CommonResponseOutlinesDto {
  data?: OutlinesDto;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«Page«IntelligenceSubsDTO»» */
export interface CommonResponsePageIntelligenceSubsDTO {
  data?: PageIntelligenceSubsDTO;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«Page«IntelligenceTopnewsDTO»» */
export interface CommonResponsePageIntelligenceTopnewsDTO {
  data?: PageIntelligenceTopnewsDTO;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«Page«SubsExecutionDTO»» */
export interface CommonResponsePageSubsExecutionDTO {
  data?: PageSubsExecutionDTO;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** CommonResponse«boolean» */
export interface CommonResponseBoolean {
  data?: boolean;
  errorCode?: string;
  errorMsg?: string;
  success?: boolean;
}

/** ContentSources */
export interface ContentSources {
  content?: string;
  refIds?: string[];
  refNames?: string[];
  sourceType?: string;
}

/** ContentSourcesDto */
export interface ContentSourcesDto {
  content?: string;
  refIds?: string[];
  refNames?: string[];
  sourceType?: string;
}

/** ErrorContextDto */
export interface ErrorContextDto {
  errorContent?: string;
  targetContent?: string;
}

/** Flux«ReplyDTO» */
export interface FluxReplyDTO {
  /** @format int32 */
  prefetch?: number;
}

/** GenerateOutlinesRequest */
export interface GenerateOutlinesRequest {
  contentAbstract: string;
  sources?: ContentSources[];
  title: string;
}

/** IntelligenceSubsCreateRequest */
export interface IntelligenceSubsCreateRequest {
  contentKeyword?: string;
  contentType?: string;
  moreScene?: string;
  /** @format int32 */
  recommendType?: number;
  /** @format int32 */
  regularCycle?: number;
  userId?: string;
}

/** IntelligenceSubsDTO */
export interface IntelligenceSubsDTO {
  contentKeyword?: string;
  contentType?: string;
  /** @format date-time */
  gmtCreate?: string;
  /** @format date-time */
  gmtModified?: string;
  /** @format int64 */
  id?: number;
  /** @format date-time */
  lastExecuteTime?: string;
  moreScene?: string;
  /** @format int32 */
  recommendType?: number;
  /** @format int32 */
  regularCycle?: number;
  /** @format int32 */
  status?: number;
  userId?: string;
}

/** IntelligenceSubsQueryRequest */
export interface IntelligenceSubsQueryRequest {
  /** @format int32 */
  pageNo?: number;
  /** @format int32 */
  pageSize?: number;
  searchWord?: string;
  /** @format int32 */
  status?: number;
}

/** IntelligenceSubsUpdateRequest */
export interface IntelligenceSubsUpdateRequest {
  contentKeyword?: string;
  contentType?: string;
  /** @format int64 */
  id?: number;
  moreScene?: string;
  /** @format int32 */
  recommendType?: number;
  /** @format int32 */
  regularCycle?: number;
  userId?: string;
}

/** IntelligenceTopnewsDTO */
export interface IntelligenceTopnewsDTO {
  contentType?: string;
  /** @format int64 */
  fileId?: number;
  fileName?: string;
  fileUrl?: string;
  /** @format date-time */
  gmtCreate?: string;
  /** @format date-time */
  gmtModified?: string;
  /** @format int64 */
  id?: number;
  intelligenceId?: string;
  level?: string;
  /** @format date-time */
  publishTime?: string;
  /** @format int32 */
  sequenceNo?: number;
  source?: string;
  /** @format int32 */
  status?: number;
  /** @format int64 */
  subsExecutionId?: number;
  /** @format int64 */
  subsId?: number;
  userId?: string;
}

/** IntelligenceTopnewsQueryRequest */
export interface IntelligenceTopnewsQueryRequest {
  /** @format date-time */
  begainDate?: string;
  contentType?: string;
  /** @format date-time */
  endDate?: string;
  level?: string;
  /** @format int32 */
  pageNo?: number;
  /** @format int32 */
  pageSize?: number;
  userId?: string;
}

/** OptimizeContentRequest */
export interface OptimizeContentRequest {
  /** @format int32 */
  articleId?: number;
  /** @format int32 */
  lengthLimit?: number;
  /** @format int32 */
  lengthLimitLow?: number;
  /** @format int32 */
  optType: number;
  rawContent: string;
  userPrompt?: string;
}

/** Outlines */
export interface Outlines {
  /** @format date-time */
  create_time?: string;
  paragraphs?: Paragraph[];
  template_id?: string;
  /** @format date-time */
  update_time?: string;
}

/** OutlinesDto */
export interface OutlinesDto {
  /** @format date-time */
  createTime?: string;
  paragraphs?: ParagraphDto[];
  templateId?: string;
  /** @format date-time */
  updateTime?: string;
}

/** Page«IntelligenceSubsDTO» */
export interface PageIntelligenceSubsDTO {
  /** @format int64 */
  current?: number;
  /** @format int64 */
  pages?: number;
  records?: IntelligenceSubsDTO[];
  /** @format int64 */
  size?: number;
  /** @format int64 */
  total?: number;
}

/** Page«IntelligenceTopnewsDTO» */
export interface PageIntelligenceTopnewsDTO {
  /** @format int64 */
  current?: number;
  /** @format int64 */
  pages?: number;
  records?: IntelligenceTopnewsDTO[];
  /** @format int64 */
  size?: number;
  /** @format int64 */
  total?: number;
}

/** Page«SubsExecutionDTO» */
export interface PageSubsExecutionDTO {
  /** @format int64 */
  current?: number;
  /** @format int64 */
  pages?: number;
  records?: SubsExecutionDTO[];
  /** @format int64 */
  size?: number;
  /** @format int64 */
  total?: number;
}

/** Paragraph */
export interface Paragraph {
  contentAbstract?: string;
  contentSources?: ContentSources[];
  subParagraphs?: Paragraph[];
  title?: string;
}

/** ParagraphDto */
export interface ParagraphDto {
  contentAbstract?: string;
  contentSources?: ContentSourcesDto[];
  subParagraphs?: ParagraphDto[];
  title?: string;
}

/** RelayMqRequest */
export interface RelayMqRequest {
  message: string;
  topic: string;
}

/** ReplyContentDTO */
export interface ReplyContentDTO {
  /** 答案内容 */
  content?: string;
  /** 类型 */
  type?: string;
}

/** ReplyDTO */
export interface ReplyDTO {
  /** 召回文档 */
  docs?: string;
  /**
   * 问题提交时间
   * @format date-time
   */
  lastDate?: string;
  /** 文档溯源标记 */
  match?: MatchDto;
  /** 提问id */
  queryId?: string;
  /** 答案内容 */
  reply?: ReplyContentDTO;
  /** 会话id */
  sessionId?: string;
  /** 答案类型体：1.进行中，2.结束，3.异常 */
  status?: "1" | "2" | "3";
}

/** SaveArticleContentRequest */
export interface SaveArticleContentRequest {
  content: string;
  /** @format int64 */
  id: number;
}

/** SaveArticleSettingsRequest */
export interface SaveArticleSettingsRequest {
  /** @format byte */
  articleSubType?: string;
  /** @format byte */
  articleType?: string;
  /** @format int64 */
  articleTypeId?: number;
  /** @format int64 */
  articleTypeVersionId?: number;
  /**
   * @minLength 0
   * @maxLength 500
   */
  contentAbstract?: string;
  contentSources?: ContentSources[];
  extraParams?: object;
  /** @format int64 */
  id?: number;
  /** @format int64 */
  lastHintVersionId?: number;
  /** @format int32 */
  lengthLimit?: number;
  /** @format int32 */
  lengthLimitLow?: number;
  outlines?: Outlines;
  /** @format int32 */
  outlinesGenType?: number;
  /** @format int64 */
  relatedTemplateId?: number;
  /**
   * @minLength 0
   * @maxLength 50
   */
  title: string;
}

/** SubsExecutionDTO */
export interface SubsExecutionDTO {
  executionConfig?: string;
  failMessage?: string;
  /** @format int64 */
  id?: number;
  /** @format int32 */
  schedulerType?: number;
  /** @format int32 */
  status?: number;
  /** @format int64 */
  subsId?: number;
}

/** SubsExecutionQueryRequest */
export interface SubsExecutionQueryRequest {
  /** @format int64 */
  id?: number;
  /** @format int32 */
  pageNo?: number;
  /** @format int32 */
  pageSize?: number;
  /** @format int32 */
  status?: number;
  /** @format int64 */
  subsId?: number;
}

/** UploadArticleMaterialDTO */
export interface UploadArticleMaterialDTO {
  fileName?: string;
  /** @format int64 */
  id?: number;
  /** @format int32 */
  index?: number;
  /** @format int32 */
  status?: number;
}
