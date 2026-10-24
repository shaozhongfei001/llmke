import {
  ArticleFeedbackReportRequest,
  ArticleTypeCreateRequest,
  ArticleTypeSaveRequest,
  BriefReportAddRequest,
  BriefReportEditRequest,
  CommonResponseArticleDto,
  CommonResponseArticleFeedbackDTO,
  CommonResponseArticleMaterialDTO,
  CommonResponseArticleTypeDto,
  CommonResponseBoolean,
  CommonResponseBriefReportDTO,
  CommonResponseCommonPageResultArticleDto,
  CommonResponseCommonPageResultArticleMaterialDTO,
  CommonResponseCommonPageResultArticleTypeDto,
  CommonResponseIntelligenceSubsDTO,
  CommonResponseListArticleErrorDto,
  CommonResponseListUploadArticleMaterialDTO,
  CommonResponseMapStringString,
  CommonResponseObject,
  CommonResponseOutlinesDto,
  CommonResponsePageIntelligenceSubsDTO,
  CommonResponsePageIntelligenceTopnewsDTO,
  CommonResponsePageSubsExecutionDTO,
  FluxReplyDTO,
  GenerateOutlinesRequest,
  IntelligenceSubsCreateRequest,
  IntelligenceSubsQueryRequest,
  IntelligenceSubsUpdateRequest,
  IntelligenceTopnewsQueryRequest,
  OptimizeContentRequest,
  RelayMqRequest,
  SaveArticleContentRequest,
  SaveArticleSettingsRequest,
  SubsExecutionQueryRequest
} from "./data-contracts";
import { ContentType, HttpClient, RequestParams } from "./http-client";

export class DocApi<SecurityDataType = unknown> {
  http: HttpClient<SecurityDataType>;

  constructor(http: HttpClient<SecurityDataType>) {
    this.http = http;
  }

  /**
   * No description
   *
   * @tags article-controller
   * @name CompleteArticleUsingGet
   * @summary 生成全文
   * @request GET:/dw/article/completeArticle
   * @response `200` `FluxReplyDTO` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  completeArticleUsingGet = (
    query: {
      /**
       * articleId
       * @format int64
       */
      articleId: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<FluxReplyDTO, void>({
      path: `/dw/article/completeArticle`,
      method: "GET",
      query: query,
      ...params
    });

  sceneClassUsingGet = (params: RequestParams = {}) =>
    this.http.request<any, void>({
      path: `/dw/articleType/class`,
      method: "GET",
      ...params
    });
  /**
   * No description
   *
   * @tags article-controller
   * @name DeleteArticleUsingPost
   * @summary 删除文章
   * @request POST:/dw/article/deleteArticle
   * @response `200` `CommonResponseBoolean` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  deleteArticleUsingPost = (
    query: {
      /**
       * articleId
       * @format int64
       */
      articleId: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseBoolean, void>({
      path: `/dw/article/deleteArticle`,
      method: "POST",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags article-controller
   * @name ExportUsingGet
   * @summary 导出文章 type=word
   * @request GET:/dw/article/export
   * @response `200` `void` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  exportUsingGet = (
    query: {
      /**
       * articleId
       * @format int64
       */
      articleId: number;
      /** type */
      type: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<void, void>({
      path: `/dw/article/export`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags article-controller
   * @name GenerateOutlinesUsingPost
   * @summary 智能生成大纲
   * @request POST:/dw/article/generateOutlines
   * @response `200` `CommonResponseOutlinesDto` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  generateOutlinesUsingPost = (
    data: GenerateOutlinesRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseOutlinesDto, void>({
      path: `/dw/article/generateOutlines`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags article-controller
   * @name OptimizeContentUsingPost
   * @summary 优化文章:1-润色,2-扩写,3-缩写  流式响应
   * @request POST:/dw/article/optimize
   * @response `200` `FluxReplyDTO` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  optimizeContentUsingPost = (
    data: OptimizeContentRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<FluxReplyDTO, void>({
      path: `/dw/article/optimize`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags article-controller
   * @name QueryArticleDetailUsingGet
   * @summary 查询文章详情
   * @request GET:/dw/article/queryArticleDetail
   * @response `200` `CommonResponseArticleDto` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  queryArticleDetailUsingGet = (
    query: {
      /**
       * articleId
       * @format int64
       */
      articleId: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseArticleDto, void>({
      path: `/dw/article/queryArticleDetail`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags article-controller
   * @name QueryArticleListUsingGet
   * @summary 查询文章列表
   * @request GET:/dw/article/queryArticleList
   * @response `200` `CommonResponseCommonPageResultArticleDto` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  queryArticleListUsingGet = (
    query?: {
      /** search */
      search?: string;
      /**
       * pageNo
       * @format int32
       */
      pageNo?: number;
      /**
       * pageSize
       * @format int32
       */
      pageSize?: number;
      /** sort */
      sort?: string;
      /** order */
      order?: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseCommonPageResultArticleDto, void>({
      path: `/dw/article/queryArticleList`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags article-controller
   * @name ReviewArticleUsingPost
   * @summary 审核整篇文章:返回值，1-错别字,2-文法错误,3-标点不当
   * @request POST:/dw/article/review
   * @response `200` `CommonResponseListArticleErrorDto` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  reviewArticleUsingPost = (
    query: {
      /**
       * articleId
       * @format int64
       */
      articleId: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseListArticleErrorDto, void>({
      path: `/dw/article/review`,
      method: "POST",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags article-controller
   * @name ReviewArticleByContentRuleUsingGet
   * @summary 根据内容规范审核文章
   * @request GET:/dw/article/reviewArticleByContentRule
   * @response `200` `CommonResponseObject` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  reviewArticleByContentRuleUsingGet = (
    query: {
      /**
       * articleId
       * @format int64
       */
      articleId: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseObject, void>({
      path: `/dw/article/reviewArticleByContentRule`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags article-controller
   * @name SaveArticleContentUsingPost
   * @summary 保存文章内容
   * @request POST:/dw/article/saveArticleContent
   * @response `200` `CommonResponseArticleDto` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  saveArticleContentUsingPost = (
    data: SaveArticleContentRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseArticleDto, void>({
      path: `/dw/article/saveArticleContent`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags article-controller
   * @name SaveArticleSettingsUsingPost
   * @summary 保存文章配置
   * @request POST:/dw/article/saveArticleSettings
   * @response `200` `CommonResponseArticleDto` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  saveArticleSettingsUsingPost = (
    data: SaveArticleSettingsRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseArticleDto, void>({
      path: `/dw/article/saveArticleSettings`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags article-material-controller
   * @name ListUsingGet
   * @summary 查询素材列表 支持筛选条件如 id=1,2,3
   * @request GET:/dw/articleMaterial
   * @response `200` `CommonResponseCommonPageResultArticleMaterialDTO` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  listUsingGet = (
    query?: {
      /** id列表，如：id=1,2,3 */
      id?: string;
      /** 文件名,用于模糊匹配 */
      fileName?: string;
      /**
       * 状态:1-已创建/待处理 2-解析中 3-解析完成 4-解析失败
       * @format byte
       */
      state?: string;
      /** 用户号 */
      userId?: string;
      /**
       * 第几页
       * @format int32
       * @min 1
       * @exclusiveMin false
       */
      pageNo?: number;
      /**
       * 每页大小
       * @format int32
       * @min 1
       * @exclusiveMin false
       */
      pageSize?: number;
      /** 排序字段名 */
      sort?: string;
      /** 降序/升序标识:desc/asc */
      order?: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseCommonPageResultArticleMaterialDTO, void>({
      path: `/dw/articleMaterial`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * @description 上传一个或多个文件作为文章素材。请确保使用 multipart/form-data 格式发送请求
   *
   * @tags article-material-controller
   * @name UploadArticleMaterialUsingPost
   * @summary 上传素材文件
   * @request POST:/dw/articleMaterial
   * @response `200` `CommonResponseListUploadArticleMaterialDTO` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  uploadArticleMaterialUsingPost = (
    data: {
      /** 素材文件列表 */
      files: File[];
    },
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseListUploadArticleMaterialDTO, void>({
      path: `/dw/articleMaterial`,
      method: "POST",
      body: data,
      type: ContentType.FormData,
      ...params
    });
  /**
   * No description
   *
   * @tags article-material-controller
   * @name QueryMaterialOrderFieldUsingGet
   * @summary 获取素材文件所有字段信息,Map<字段名,字段类型>
   * @request GET:/dw/articleMaterial/field
   * @response `200` `CommonResponseMapStringString` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  queryMaterialOrderFieldUsingGet = (params: RequestParams = {}) =>
    this.http.request<CommonResponseMapStringString, void>({
      path: `/dw/articleMaterial/field`,
      method: "GET",
      ...params
    });
  /**
   * No description
   *
   * @tags article-material-controller
   * @name RetryParseMaterialUsingPost
   * @summary 重试解析素材文件
   * @request POST:/dw/articleMaterial/parse/{id}
   * @response `200` `CommonResponseBoolean` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  retryParseMaterialUsingPost = (id: number, params: RequestParams = {}) =>
    this.http.request<CommonResponseBoolean, void>({
      path: `/dw/articleMaterial/parse/${id}`,
      method: "POST",
      ...params
    });
  /**
   * No description
   *
   * @tags article-material-controller
   * @name QueryArticleMaterialByIdUsingGet
   * @summary 查询素材文件详情
   * @request GET:/dw/articleMaterial/{id}
   * @response `200` `CommonResponseArticleMaterialDTO` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  queryArticleMaterialByIdUsingGet = (id: number, params: RequestParams = {}) =>
    this.http.request<CommonResponseArticleMaterialDTO, void>({
      path: `/dw/articleMaterial/${id}`,
      method: "GET",
      ...params
    });
  /**
   * No description
   *
   * @tags article-material-controller
   * @name DeleteByIdUsingDelete
   * @summary 删除素材文件
   * @request DELETE:/dw/articleMaterial/{id}
   * @response `200` `CommonResponseBoolean` OK
   * @response `204` `void` No Content
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   */
  deleteByIdUsingDelete = (id: number, params: RequestParams = {}) =>
    this.http.request<CommonResponseBoolean, void>({
      path: `/dw/articleMaterial/${id}`,
      method: "DELETE",
      ...params
    });
  /**
   * No description
   *
   * @tags article-type-controller
   * @name QueryArticleTypeListUsingGet
   * @summary 查询文章类型列表
   * @request GET:/dw/articleType
   * @response `200` `CommonResponseCommonPageResultArticleTypeDto` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  queryArticleTypeListUsingGet = (
    query?: {
      /** search */
      search?: string;
      /**
       * pageNo
       * @format int32
       */
      pageNo?: number;
      /**
       * pageSize
       * @format int32
       */
      pageSize?: number;
      /** sort */
      sort?: string;
      /** order */
      order?: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseCommonPageResultArticleTypeDto, void>({
      path: `/dw/articleType`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags article-type-controller
   * @name CreateArticleTypeUsingPost
   * @summary 新增文章类型
   * @request POST:/dw/articleType
   * @response `200` `CommonResponseArticleTypeDto` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  createArticleTypeUsingPost = (
    data: ArticleTypeCreateRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseArticleTypeDto, void>({
      path: `/dw/articleType`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags article-type-controller
   * @name QueryArticleTypeUsingGet
   * @summary 查询文章类型详情
   * @request GET:/dw/articleType/{id}
   * @response `200` `CommonResponseArticleTypeDto` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  queryArticleTypeUsingGet = (id: number, params: RequestParams = {}) =>
    this.http.request<CommonResponseArticleTypeDto, void>({
      path: `/dw/articleType/${id}`,
      method: "GET",
      ...params
    });
  /**
   * No description
   *
   * @tags article-type-controller
   * @name SaveArticleTypeUsingPut
   * @summary 保存文章类型
   * @request PUT:/dw/articleType/{id}
   * @response `200` `CommonResponseArticleTypeDto` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  saveArticleTypeUsingPut = (
    id: number,
    data: ArticleTypeSaveRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseArticleTypeDto, void>({
      path: `/dw/articleType/${id}`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags article-type-controller
   * @name DeleteArticleTypeUsingDelete
   * @summary 删除文档
   * @request DELETE:/dw/articleType/{id}
   * @response `200` `CommonResponseBoolean` OK
   * @response `204` `void` No Content
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   */
  deleteArticleTypeUsingDelete = (id: number, params: RequestParams = {}) =>
    this.http.request<CommonResponseBoolean, void>({
      path: `/dw/articleType/${id}`,
      method: "DELETE",
      ...params
    });
  /**
   * No description
   *
   * @tags article-type-controller
   * @name QueryArticleTypeByVersionIdUsingGet
   * @summary 根据版本id查询文章类型详情
   * @request GET:/dw/articleType/{id}/version/{versionId}
   * @response `200` `CommonResponseArticleTypeDto` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  queryArticleTypeByVersionIdUsingGet = (
    id: number,
    versionId: number,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseArticleTypeDto, void>({
      path: `/dw/articleType/${id}/version/${versionId}`,
      method: "GET",
      ...params
    });
  /**
   * No description
   *
   * @tags brief-report-controller
   * @name DeleteBriefReportUsingPost
   * @summary 删除简报
   * @request POST:/dw/BriefReport/delete
   * @response `200` `CommonResponseBoolean` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  deleteBriefReportUsingPost = (data: number, params: RequestParams = {}) =>
    this.http.request<CommonResponseBoolean, void>({
      path: `/dw/BriefReport/delete`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags brief-report-controller
   * @name EditBriefReportUsingPost
   * @summary 编辑简报
   * @request POST:/dw/BriefReport/edit
   * @response `200` `CommonResponseBriefReportDTO` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  editBriefReportUsingPost = (
    data: BriefReportEditRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseBriefReportDTO, void>({
      path: `/dw/BriefReport/edit`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags brief-report-controller
   * @name GenerateBriefReportUsingPost
   * @summary 生成简报
   * @request POST:/dw/BriefReport/generate
   * @response `200` `CommonResponseBriefReportDTO` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  generateBriefReportUsingPost = (
    data: BriefReportAddRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseBriefReportDTO, void>({
      path: `/dw/BriefReport/generate`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags brief-report-controller
   * @name GetBriefReportByIdUsingPost
   * @summary 查询简报详情
   * @request POST:/dw/BriefReport/geyById
   * @response `200` `CommonResponseBriefReportDTO` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  getBriefReportByIdUsingPost = (data: number, params: RequestParams = {}) =>
    this.http.request<CommonResponseBriefReportDTO, void>({
      path: `/dw/BriefReport/geyById`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags callback-controller
   * @name RelayMqUsingPost
   * @summary 转发MQ消息
   * @request POST:/dw/callback/relayMq
   * @response `200` `CommonResponseBoolean` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  relayMqUsingPost = (data: RelayMqRequest, params: RequestParams = {}) =>
    this.http.request<CommonResponseBoolean, void>({
      path: `/dw/callback/relayMq`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags intelligence-subs-controller
   * @name CreateUsingPost
   * @summary 新增订阅配置
   * @request POST:/dw/intelligenceSubs/create
   * @response `200` `CommonResponseIntelligenceSubsDTO` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  createUsingPost = (
    data: IntelligenceSubsCreateRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseIntelligenceSubsDTO, void>({
      path: `/dw/intelligenceSubs/create`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags intelligence-subs-controller
   * @name DeleteByIdUsingDelete1
   * @summary 逻辑删除订阅配置
   * @request DELETE:/dw/intelligenceSubs/delete
   * @response `200` `CommonResponseBoolean` OK
   * @response `204` `void` No Content
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   */
  deleteByIdUsingDelete1 = (
    query: {
      /**
       * id
       * @format int64
       */
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseBoolean, void>({
      path: `/dw/intelligenceSubs/delete`,
      method: "DELETE",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags intelligence-subs-controller
   * @name EditUsingPut
   * @summary 修改订阅配置
   * @request PUT:/dw/intelligenceSubs/edit
   * @response `200` `CommonResponseIntelligenceSubsDTO` OK
   * @response `201` `void` Created
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  editUsingPut = (
    data: IntelligenceSubsUpdateRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseIntelligenceSubsDTO, void>({
      path: `/dw/intelligenceSubs/edit`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags intelligence-subs-controller
   * @name GetByUserUsingGet
   * @summary 查看用户的订阅配置
   * @request GET:/dw/intelligenceSubs/getSubsByUserId
   * @response `200` `CommonResponseIntelligenceSubsDTO` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  getByUserUsingGet = (
    query: {
      /** userId */
      userId: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponseIntelligenceSubsDTO, void>({
      path: `/dw/intelligenceSubs/getSubsByUserId`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags intelligence-subs-controller
   * @name ListUsingGet1
   * @summary 条件查看订阅配置列表
   * @request GET:/dw/intelligenceSubs/list
   * @response `200` `CommonResponsePageIntelligenceSubsDTO` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  listUsingGet1 = (
    data: IntelligenceSubsQueryRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponsePageIntelligenceSubsDTO, void>({
      path: `/dw/intelligenceSubs/list`,
      method: "GET",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags intelligence-topnews-controller
   * @name ListUsingGet2
   * @summary 条件查看情报要闻列表
   * @request GET:/dw/intelligenceTopnews/list
   * @response `200` `CommonResponsePageIntelligenceTopnewsDTO` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  listUsingGet2 = (
    data: IntelligenceTopnewsQueryRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponsePageIntelligenceTopnewsDTO, void>({
      path: `/dw/intelligenceTopnews/list`,
      method: "GET",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags subs-execution-controller
   * @name ListUsingGet3
   * @summary 条件查看情报订阅执行记录
   * @request GET:/dw/subsExecution/list
   * @response `200` `CommonResponsePageSubsExecutionDTO` OK
   * @response `401` `void` Unauthorized
   * @response `403` `void` Forbidden
   * @response `404` `void` Not Found
   */
  listUsingGet3 = (
    data: SubsExecutionQueryRequest,
    params: RequestParams = {}
  ) =>
    this.http.request<CommonResponsePageSubsExecutionDTO, void>({
      path: `/dw/subsExecution/list`,
      method: "GET",
      body: data,
      type: ContentType.Json,
      ...params
    });
}
