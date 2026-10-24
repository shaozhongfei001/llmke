import {
  Faq一键启用禁用请求参数,
  Faq信息,
  Faq修改请求参数,
  Faq创建请求参数,
  Faq删除请求参数,
  Faq润色请求参数,
  Faq相似问删除,
  Faq相似问新增,
  Faq相似问生成,
  File,
  FileMergeReq,
  PageFaq信息,
  Page文件chunk信息,
  Page文件夹详情,
  Page文件详情,
  Page知识库详情,
  Type修改文件启用禁用状态,
  Type创建知识库请求体,
  Type山粗文本块请求参数,
  Type文件夹保存请求参数,
  Type文件夹更新请求参数,
  Type文件夹详情,
  Type文件详情,
  Type文件转移请求参数,
  Type文本chunk关联图片chunk调整请求参数,
  Type文本解析请求参数体,
  Type更新faq状态请求参数,
  Type更新文本块请求参数,
  Type知识库列表请求参数,
  Type知识库文件查询请求参数,
  Type知识库更新请求体,
  Type知识库解析配置更新请求体,
  Type知识库详情
} from "./data-contracts";
import { ContentType, HttpClient, RequestParams } from "./http-client";

export class Api<SecurityDataType = unknown> {
  http: HttpClient<SecurityDataType>;

  constructor(http: HttpClient<SecurityDataType>) {
    this.http = http;
  }

  /**
   * No description
   *
   * @tags 知识库接口
   * @name Update
   * @summary 更新
   * @request PUT:/knowledgeBase/update
   * @response `200` `boolean` OK
   */
  update = (data: Type知识库更新请求体, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/update`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name UpdateConf
   * @summary 更新知识库解析配置
   * @request PUT:/knowledgeBase/updateConf
   * @response `200` `boolean` OK
   */
  updateConf = (
    data: Type知识库解析配置更新请求体,
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/updateConf`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name UpdateEnable
   * @summary 修改知识库文件状态
   * @request PUT:/knowledgeBase/file/updateEnable
   * @response `200` `boolean` OK
   */
  updateEnable = (data: Type修改文件启用禁用状态, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/updateEnable`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name UpdateChunk
   * @summary 更新文本块内容
   * @request PUT:/knowledgeBase/file/updateChunk
   * @response `200` `boolean` OK
   */
  updateChunk = (data: Type更新文本块请求参数, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/updateChunk`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name ChunkChange
   * @summary 文本chunk关联图片chunk调整
   * @request PUT:/knowledgeBase/file/image/chunkChange
   * @response `200` `boolean` OK
   */
  chunkChange = (
    data: Type文本chunk关联图片chunk调整请求参数,
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/image/chunkChange`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name FilesReviseDate
   * @summary 文件的修订时间
   * @request PUT:/knowledgeBase/file/filesReviseDate
   * @response `200` `boolean` OK
   */
  filesReviseDate = (
    query: {
      /** @format int64 */
      fileId: number;
      reviseDate: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/filesReviseDate`,
      method: "PUT",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件夹
   * @name Rename
   * @summary 重命名
   * @request PUT:/folder/rename
   * @response `200` `boolean` OK
   */
  rename = (data: Type文件夹更新请求参数, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/folder/rename`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name Update1
   * @summary 更新
   * @request PUT:/faq/update
   * @response `200` `boolean` OK
   */
  update1 = (data: Faq创建请求参数, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/faq/update`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name SimilarQuestionEdit
   * @summary 修改相似问
   * @request PUT:/faq/similarQuestion/edit
   * @deprecated
   * @response `200` `boolean` OK
   */
  similarQuestionEdit = (data: Faq相似问新增, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/faq/similarQuestion/edit`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name GenSimilarQuestion
   * @summary 生成相似问
   * @request PUT:/faq/gen/similarQuestion
   * @response `200` `boolean` OK
   */
  genSimilarQuestion = (data: Faq相似问生成, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/faq/gen/similarQuestion`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name DeleteAll
   * @summary 一键启删除
   * @request PUT:/faq/deleteAll
   * @response `200` `boolean` OK
   */
  deleteAll = (data: Faq删除请求参数, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/faq/deleteAll`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name ChangeStatus
   * @summary faq启用/禁用
   * @request PUT:/faq/changeStatus
   * @response `200` `((Faq信息)[])[]` OK
   */
  changeStatus = (data: Type更新faq状态请求参数, params: RequestParams = {}) =>
    this.http.request<Faq信息[][], any>({
      path: `/faq/changeStatus`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name ChangeAllStatus
   * @summary 一键启用/禁用
   * @request PUT:/faq/changeAllStatus
   * @response `200` `((Faq信息)[])[]` OK
   */
  changeAllStatus = (
    data: Faq一键启用禁用请求参数,
    params: RequestParams = {}
  ) =>
    this.http.request<Faq信息[][], any>({
      path: `/faq/changeAllStatus`,
      method: "PUT",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name RebuildNew
   * @summary 根据旧知识库重建新知识库并解析所有原知识库文档
   * @request POST:/knowledgeBase/rebuildNew
   * @response `200` `Type知识库详情` OK
   */
  rebuildNew = (
    query: {
      /** @format int64 */
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Type知识库详情, any>({
      path: `/knowledgeBase/rebuildNew`,
      method: "POST",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name ReParse
   * @summary 重新解析所有知识库文档
   * @request POST:/knowledgeBase/reParse
   * @response `200` `boolean` OK
   */
  reParse = (
    query: {
      /** @format int64 */
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/reParse`,
      method: "POST",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name ChunkUpload
   * @summary 上传文件片段
   * @request POST:/knowledgeBase/file/upload
   * @response `200` `boolean` OK
   */
  chunkUpload = (
    query: {
      fileMd5: string;
    },
    data: {
      /** @format binary */
      file: File;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/upload`,
      method: "POST",
      query: query,
      body: data,
      type: ContentType.FormData,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name UploadFile
   * @summary 上传解析后文件并返回文件的路径
   * @request POST:/knowledgeBase/file/uploadParsedFile
   * @response `200` `Type文件详情` OK
   */
  uploadFile = (
    query: {
      /** @format int64 */
      kbId: number;
      /** @format int64 */
      fileId: number;
      /** @default true */
      isOverwrite?: boolean;
    },
    data: {
      /** @format binary */
      file: File;
      imagesFiles?: File[];
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Type文件详情, any>({
      path: `/knowledgeBase/file/uploadParsedFile`,
      method: "POST",
      query: query,
      body: data,
      type: ContentType.FormData,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name UploadFileList
   * @summary 批量上传文件(包含文件重复性校验、父文件、多版本)
   * @request POST:/knowledgeBase/file/uploadFileList
   * @response `200` `object` OK
   */
  uploadFileList = (
    query: {
      uploadFileParam: string;
      files: File[];
    },
    params: RequestParams = {}
  ) =>
    this.http.request<object, any>({
      path: `/knowledgeBase/file/uploadFileList`,
      method: "POST",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name ReExtractFqa
   * @summary FAQ重新抽取
   * @request POST:/knowledgeBase/file/reExtractFQA
   * @response `200` `boolean` OK
   */
  reExtractFqa = (data: Type文本解析请求参数体, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/reExtractFQA`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name ChunkMerge
   * @summary 文件片段合并
   * @request POST:/knowledgeBase/file/merge
   * @response `200` `boolean` OK
   */
  chunkMerge = (data: FileMergeReq, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/merge`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name ImportUrlList
   * @summary 从url列表导入文件(包含文件重复性校验、父文件、多版本)
   * @request POST:/knowledgeBase/file/importUrlList
   * @response `200` `object` OK
   */
  importUrlList = (
    query: {
      importUrlListParam: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<object, any>({
      path: `/knowledgeBase/file/importUrlList`,
      method: "POST",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name GraphParse
   * @summary 图解析
   * @request POST:/knowledgeBase/file/graphParse
   * @response `200` `boolean` OK
   */
  graphParse = (data: Type文本解析请求参数体, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/graphParse`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name FilesParse
   * @summary 文件解析
   * @request POST:/knowledgeBase/file/filesParse
   * @response `200` `boolean` OK
   */
  filesParse = (data: Type文本解析请求参数体, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/filesParse`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name FilesAllParse
   * @summary 一键解析
   * @request POST:/knowledgeBase/file/filesAllParse
   * @response `200` `boolean` OK
   */
  filesAllParse = (
    query: {
      /** @format int64 */
      kbId: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/filesAllParse`,
      method: "POST",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name ExtractFqa
   * @summary FAQ抽取
   * @request POST:/knowledgeBase/file/extractFQA
   * @response `200` `boolean` OK
   */
  extractFqa = (data: Type文本解析请求参数体, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/extractFQA`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name ExtractAllFqa
   * @summary FAQ一键抽取
   * @request POST:/knowledgeBase/file/extractAllFQA
   * @response `200` `boolean` OK
   */
  extractAllFqa = (
    query: {
      /** @format int64 */
      kbId: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/extractAllFQA`,
      method: "POST",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name GetEmbeddingModels
   * @summary 文件解析模型列表
   * @request POST:/knowledgeBase/embeddingModels
   * @response `200` `(string)[]` OK
   */
  getEmbeddingModels = (params: RequestParams = {}) =>
    this.http.request<string[], any>({
      path: `/knowledgeBase/embeddingModels`,
      method: "POST",
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name DownloadKbFiles
   * @summary 下载知识库所有文档
   * @request POST:/knowledgeBase/downloadKbFiles
   * @response `200` `boolean` OK
   */
  downloadKbFiles = (
    query: {
      /** @format int64 */
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/downloadKbFiles`,
      method: "POST",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name CreateKb
   * @summary 创建知识库
   * @request POST:/knowledgeBase/create
   * @response `200` `Type知识库详情` OK
   */
  createKb = (data: Type创建知识库请求体, params: RequestParams = {}) =>
    this.http.request<Type知识库详情, any>({
      path: `/knowledgeBase/create`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件夹
   * @name SaveFolderInfo
   * @summary 保存
   * @request POST:/folder/save
   * @response `200` `boolean` OK
   */
  saveFolderInfo = (data: Type文件夹保存请求参数, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/folder/save`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件夹
   * @name FileTransfer
   * @summary 文件转移
   * @request POST:/folder/file/transfer
   * @response `200` `boolean` OK
   */
  fileTransfer = (data: Type文件转移请求参数, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/folder/file/transfer`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name UploadFiles
   * @summary 上传文件
   * @request POST:/faq/uploadFiles
   * @response `200` `boolean` OK
   */
  uploadFiles = (
    query: {
      /** @format int64 */
      kbId: number;
      files: File[];
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/faq/uploadFiles`,
      method: "POST",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name SimilarQuestionAdd
   * @summary 新增相似问
   * @request POST:/faq/similarQuestion/add
   * @response `200` `boolean` OK
   */
  similarQuestionAdd = (data: Faq相似问新增, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/faq/similarQuestion/add`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name SaveOrUpdate
   * @summary 新增或更新
   * @request POST:/faq/saveOrUpdate
   * @response `200` `boolean` OK
   */
  saveOrUpdate = (data: Faq创建请求参数, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/faq/saveOrUpdate`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name Polish
   * @summary FAQ润色
   * @request POST:/faq/polish
   * @response `200` `(Faq信息)[]` OK
   */
  polish = (data: Faq润色请求参数, params: RequestParams = {}) =>
    this.http.request<Faq信息[], any>({
      path: `/faq/polish`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name Delete
   * @summary 通过pk删除问答对或相似问
   * @request POST:/faq/delete
   * @response `200` `boolean` OK
   */
  delete = (data: Faq删除请求参数, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/faq/delete`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name Create
   * @summary 新增
   * @request POST:/faq/create
   * @response `200` `boolean` OK
   */
  create = (data: Faq创建请求参数, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/faq/create`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name ShareList
   * @summary 共享知识库列表数据
   * @request GET:/knowledgeBase/share/list
   * @response `200` `Page知识库详情` OK
   */
  shareList = (
    query: {
      arg0: Type知识库列表请求参数;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Page知识库详情, any>({
      path: `/knowledgeBase/share/list`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name SearchList
   * @summary 所有知识库数据(用户自己的知识库 + 共享数据的知识库)
   * @request GET:/knowledgeBase/searchList
   * @response `200` `(Type知识库详情)[]` OK
   */
  searchList = (
    query?: {
      fuzzy?: string;
      userName?: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Type知识库详情[], any>({
      path: `/knowledgeBase/searchList`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name List
   * @summary 知识库列表数据
   * @request GET:/knowledgeBase/list
   * @response `200` `Page知识库详情` OK
   */
  list = (
    query: {
      arg0: Type知识库列表请求参数;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Page知识库详情, any>({
      path: `/knowledgeBase/list`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name GetKbById
   * @summary 通过id查询知识库信息
   * @request GET:/knowledgeBase/getKbById
   * @response `200` `Type知识库详情` OK
   */
  getKbById = (
    query: {
      /**
       * 知识库id
       * @format int64
       */
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Type知识库详情, any>({
      path: `/knowledgeBase/getKbById`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name Precheck
   * @summary 文件预检接口
   * @request GET:/knowledgeBase/file/precheck
   * @response `200` `(string)[]` OK
   */
  precheck = (
    query: {
      fileNameList: string[];
    },
    params: RequestParams = {}
  ) =>
    this.http.request<string[], any>({
      path: `/knowledgeBase/file/precheck`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name ParentList
   * @summary 知识库父文件以及子文件查询
   * @request GET:/knowledgeBase/file/list
   * @response `200` `Page文件详情` OK
   */
  parentList = (
    query: {
      arg0: Type知识库文件查询请求参数;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Page文件详情, any>({
      path: `/knowledgeBase/file/list`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name GetGraphParseStatus
   * @summary 获取图解析状态 1 未解析；2 解析中 3 解析成功 4 解析失败
   * @request GET:/knowledgeBase/file/getGraphParseStatus
   * @response `200` `number` OK
   */
  getGraphParseStatus = (
    query: {
      /** @format int64 */
      fileId: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<number, any>({
      path: `/knowledgeBase/file/getGraphParseStatus`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name GetFileStatusById
   * @summary 查看文件解析状态
   * @request GET:/knowledgeBase/file/getFileStatusById
   * @response `200` `number` OK
   */
  getFileStatusById = (
    query: {
      /** @format int64 */
      fileId: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<number, any>({
      path: `/knowledgeBase/file/getFileStatusById`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name GetFileChunks
   * @summary 查看文件chunk
   * @request GET:/knowledgeBase/file/getFileChunks
   * @response `200` `Page文件chunk信息` OK
   */
  getFileChunks = (
    query: {
      /** @format int64 */
      kbId: number;
      /** @format int64 */
      docId: number;
      /** @format int32 */
      pageNo: number;
      /** @format int32 */
      pageSize: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Page文件chunk信息, any>({
      path: `/knowledgeBase/file/getFileChunks`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name GetFaqExtractStatusById
   * @summary 获取抽取状态
   * @request GET:/knowledgeBase/file/getFAQExtractStatusById
   * @response `200` `number` OK
   */
  getFaqExtractStatusById = (
    query: {
      /** @format int64 */
      fileId: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<number, any>({
      path: `/knowledgeBase/file/getFAQExtractStatusById`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name GetById
   * @summary 获取文件详情
   * @request GET:/knowledgeBase/file/getById
   * @response `200` `Type文件详情` OK
   */
  getById = (
    query: {
      /** @format int64 */
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Type文件详情, any>({
      path: `/knowledgeBase/file/getById`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name FolderList
   * @summary 知识库文件列表(包含文件夹)
   * @request GET:/knowledgeBase/file/folder/list
   * @response `200` `Page文件详情` OK
   */
  folderList = (
    query: {
      arg0: Type知识库文件查询请求参数;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Page文件详情, any>({
      path: `/knowledgeBase/file/folder/list`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name CheckCunkFile
   * @summary 判断文件是否上传过，是否存在分片(-1 文件没有上传过; -2 文件已存在; 文件上传中断过，返回当前已经上传到的下标)
   * @request GET:/knowledgeBase/file/check
   * @response `200` `number` OK
   */
  checkCunkFile = (
    query: {
      /** @format int64 */
      kbId: number;
      fileName: string;
      fileMd5: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<number, any>({
      path: `/knowledgeBase/file/check`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name CanUpdateConf
   * @summary 知识库解析配置是否可编辑
   * @request GET:/knowledgeBase/canUpdateConf
   * @response `200` `boolean` OK
   */
  canUpdateConf = (
    query: {
      /** @format int64 */
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/canUpdateConf`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件夹
   * @name List1
   * @summary 分页查询
   * @request GET:/folder/list
   * @response `200` `Page文件夹详情` OK
   */
  list1 = (
    query?: {
      /** @format int64 */
      pageNo?: number;
      /** @format int64 */
      pageSize?: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Page文件夹详情, any>({
      path: `/folder/list`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件夹
   * @name LeveList
   * @summary 通过知识库id查询文件目录(有层级关系)
   * @request GET:/folder/leve/list
   * @response `200` `(Type文件夹详情)[]` OK
   */
  leveList = (
    query: {
      kbIds: number[];
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Type文件夹详情[], any>({
      path: `/folder/leve/list`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件夹
   * @name QueryFolderInfo
   * @summary 通过id查询数据
   * @request GET:/folder/id
   * @response `200` `Type文件夹详情` OK
   */
  queryFolderInfo = (
    query: {
      /** @format int64 */
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Type文件夹详情, any>({
      path: `/folder/id`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name RepeatCheck
   * @summary faq重复性校验
   * @request GET:/faq/repeatCheck
   * @response `200` `((Faq信息)[])[]` OK
   */
  repeatCheck = (
    query: {
      /** @format int64 */
      kbId: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Faq信息[][], any>({
      path: `/faq/repeatCheck`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name List2
   * @summary 问答列表数据
   * @request GET:/faq/list
   * @response `200` `PageFaq信息` OK
   */
  list2 = (
    query: {
      arg0: Faq修改请求参数;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<PageFaq信息, any>({
      path: `/faq/list`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name GetFaqByRelatedPk
   * @summary 通过RelatedPk查询faq以及相似问
   * @request GET:/faq/getFaqByRelatedPk
   * @response `200` `Faq信息` OK
   */
  getFaqByRelatedPk = (
    query: {
      arg0: Faq修改请求参数;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Faq信息, any>({
      path: `/faq/getFaqByRelatedPk`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name DownloadTemplate
   * @summary 模板下载
   * @request GET:/faq/downloadTemplate
   * @response `200` `File` OK
   */
  downloadTemplate = (
    query: {
      fileType: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<File, any>({
      path: `/faq/downloadTemplate`,
      method: "GET",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name Delete1
   * @summary 通过id删除文件
   * @request DELETE:/knowledgeBase/file/delete
   * @response `200` `boolean` OK
   */
  delete1 = (
    query: {
      /**
       * id
       * @format int64
       */
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/delete`,
      method: "DELETE",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name DeleteChunk
   * @summary 通过文本块id删除
   * @request DELETE:/knowledgeBase/file/deleteChunks
   * @response `200` `boolean` OK
   */
  deleteChunk = (data: Type山粗文本块请求参数, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/deleteChunks`,
      method: "DELETE",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件
   * @name DeleteByIds
   * @summary 通过id批量删除文件
   * @request DELETE:/knowledgeBase/file/deleteByIds
   * @response `200` `boolean` OK
   */
  deleteByIds = (
    query: {
      fileIds: number[];
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/file/deleteByIds`,
      method: "DELETE",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库接口
   * @name DeleteById
   * @summary 删除知识库
   * @request DELETE:/knowledgeBase/delete
   * @response `200` `boolean` OK
   */
  deleteById = (
    query: {
      /**
       * 知识库id
       * @format int64
       */
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/knowledgeBase/delete`,
      method: "DELETE",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 知识库文件夹
   * @name DeleteFolderInfoById
   * @summary 通过id删除
   * @request DELETE:/folder/delete
   * @response `200` `boolean` OK
   */
  deleteFolderInfoById = (
    query: {
      /** @format int64 */
      id: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/folder/delete`,
      method: "DELETE",
      query: query,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name SimilarQuestionDel
   * @summary 相似问删除
   * @request DELETE:/faq/similarQuestion/delete
   * @response `200` `boolean` OK
   */
  similarQuestionDel = (data: Faq相似问删除, params: RequestParams = {}) =>
    this.http.request<boolean, any>({
      path: `/faq/similarQuestion/delete`,
      method: "DELETE",
      body: data,
      type: ContentType.Json,
      ...params
    });
  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name DeleteFileById
   * @summary 通过id删除文件
   * @request DELETE:/faq/deleteFileByIds
   * @deprecated
   * @response `200` `boolean` OK
   */
  deleteFileById = (
    query: {
      fileIds: number[];
    },
    params: RequestParams = {}
  ) =>
    this.http.request<boolean, any>({
      path: `/faq/deleteFileByIds`,
      method: "DELETE",
      query: query,
      ...params
    });

  /**
   * No description
   *
   * @tags 创建集合
   * @name CreateKb
   * @summary 创建知识库
   * @request POST:/knowledgeBase/file/createCollect
   * @response `200` `Type知识库详情` OK
   */
  createCollect = (
    data: {
      kbId: number | string;
      fileIds: number[];
      groupIds: number[];
      fileListType: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Type知识库详情, any>({
      path: `/knowledgeBase/file/createCollect`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });

  /**
   * No description
   *
   * @tags 解散集合
   * @name CreateKb
   * @summary 创建知识库
   * @request POST:/knowledgeBase/file/dissolve
   * @response `200` `Type知识库详情` OK
   */
  dissolve = (
    data: { kbId: number | string; groupIds: string[]; fileListType: number },
    params: RequestParams = {}
  ) =>
    this.http.request<Type知识库详情, any>({
      path: `/knowledgeBase/file/dissolve`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });

  /**
   * No description
   *
   * @tags 文件归集转移
   * @name CreateKb
   * @summary 创建知识库
   * @request POST:/knowledgeBase/file/transfer
   * @response `200` `Type知识库详情` OK
   */
  fileGroupTransfer = (
    data: {
      kbId: string;
      fileIds?: string[];
      srcGroupIds?: string;
      parentFileName: string;
      groupId: string;
      fileListType: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Type知识库详情, any>({
      path: `/knowledgeBase/file/transfer`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });

  /**
   * No description
   *
   * @tags 问答对(FAQ)
   * @name DownloadTemplate
   * @summary 模板下载
   * @request GET:/faq/downloadTemplate
   * @response `200` `File` OK
   */
  collectList = (
    query: {
      kbId: string;
      fileListType: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<File, any>({
      path: `/knowledgeBase/file/collect/list`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * No description
   *
   * @tags 通过文件集id查询
   * @name DownloadTemplate
   * @summary 模板下载
   * @request GET:/faq/downloadTemplatescatter
   * @response `200` `File` OK
   */
  getByGroupId = (
    query: {
      groupId: string;
      kbId: string;
      fileListType: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<File, any>({
      path: `/knowledgeBase/file/getByGroupId`,
      method: "GET",
      query: query,
      ...params
    });

  /**
   * No description
   *
   * @tags 通过文件集id查询
   * @name DownloadTemplate
   * @summary 模板下载
   * @request GET:/faq/downloadTemplatescatter
   * @response `200` `File` OK
   */
  getScatterList = (
    query: {
      kbId: string;
      fileListType: number;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<File, any>({
      path: `/knowledgeBase/file/scatter/list`,
      method: "GET",
      query: query,
      ...params
    });

  fileRemove = (
    data: {
      kbId: string;
      fileIds: string[];
    },
    params: RequestParams = {}
  ) =>
    this.http.request<Type知识库详情, any>({
      path: `/knowledgeBase/file/remove`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });

  /**
   * 检索召回测试接口
   * @tags 问答和引用
   * @name RetrieveTecallTest
   * @request POST:/ai/retrieveTecallTest
   * @response `200` `any` OK
   */
  retrieveTecallTest = (
    data: {
      sessionId?: string;
      queryId?: string;
      sysType?: string;
      lastDate?: string;
      audioUrl?: string;
      type?: string;
      content?: string;
      configId?: number;
      fileUids?: string[];
      config?: string;
    },
    params: RequestParams = {}
  ) =>
    this.http.request<any, any>({
      path: `/ai/retrieveTecallTest`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params
    });
}
