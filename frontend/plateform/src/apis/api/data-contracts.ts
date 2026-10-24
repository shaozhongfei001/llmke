export interface Type知识库更新请求体 {
  /**
   * 知识库id
   * @format int64
   */
  id: number;
  /** 知识库名称 */
  kbName: string;
  /** 描述 */
  kbDes: string;
  /** 知识库标签 */
  kbLabel?: string;
}

export interface Type知识库解析配置更新请求体 {
  /**
   * 知识库id
   * @format int64
   */
  id: number;
  /**
   * 文本块大小(块token数)
   * @format int32
   */
  chunkSize: number;
  /** 文档类型（解析方法），目前支持四种类型，[naive, laws, book, table] */
  fileType: string;
  /** 嵌入模型名称 */
  embeddingModelName: string;
  /**
   * 单篇文档问答对抽取数量上限
   * @format int32
   */
  fileFaqMaxNums?: number;
  /**
   * 生成相似问个数
   * @format int32
   */
  similarQuestionMaxNums?: number;
  /** faq导入是否润色 默认值false */
  enablePolish?: boolean;
}

export interface Type修改文件启用禁用状态 {
  /** 文件id */
  fileIds: number[];
  /**
   * 0:禁用; 1:启用
   * @format int32
   */
  enableStatus: number;
}

export interface Type更新文本块请求参数 {
  /**
   * 知识库id
   * @format int64
   */
  KbId: number;
  /** 文本块id */
  chunkId: string;
  /** 文本块内容 */
  content: string;
}

export interface Type文本chunk关联图片chunk调整请求参数 {
  /**
   * 文件id
   * @format int64
   */
  fileId: number;
  /**
   * 原来的文本chunkId
   * @format int64
   */
  oldChunkId: number;
  /**
   * 新的文本chunkId
   * @format int64
   */
  newChunkId: number;
  /**
   * 需要调整的图片的chunkId
   * @format int64
   */
  imageChunkId: number;
}

export interface Type文件夹更新请求参数 {
  /**
   * 主键
   * @format int64
   */
  id: number;
  /**
   * 知识库id
   * @format int64
   */
  kbId: number;
  /**
   * 父文件夹id
   * @format int64
   */
  parentId?: number;
  /** 文件夹名称 */
  name: string;
  /**
   * 1:文档解析；2:FAQ抽取
   * @format int32
   */
  type?: number;
}

/** 需要修改或更新的问答对 */
export interface Faq {
  /**
   * 问答对id
   * @format int64
   */
  pk?: number;
  /**
   * 相似问答对关联id
   * @format int64
   */
  relatedPk?: number;
  /**
   * 启用状态，0:待启用，1：已启用
   * @format int32
   */
  status?: number;
  /** 问题 */
  question: string;
  /** 答案 */
  answer: string;
}

export interface Faq创建请求参数 {
  /**
   * 知识库id
   * @format int64
   */
  kbId?: number;
  /**
   * 文件id
   * @format int64
   */
  fileId?: number;
  /** 需要修改或更新的问答对 */
  faqs: Faq[];
}

export interface Faq相似问新增 {
  /**
   * 知识库id
   * @format int64
   */
  kbId: number;
  /**
   * 文件id
   * @format int64
   */
  fileId?: number;
  /**
   * 相似问关联id
   * @format int64
   */
  relatedPk?: number;
  /**
   * 问答对id
   * @format int64
   */
  pk: number;
  /** 相识问题 */
  similarQuestion: string;
}

export interface Faq相似问生成 {
  /**
   * 知识库id
   * @format int64
   */
  kbId: number;
  /**
   * 文件id
   * @format int64
   */
  fileId?: number;
  /** 问答对relatedPk */
  relatedPks?: number[];
  /** 模型名称 */
  modelName?: string;
}

export interface Faq删除请求参数 {
  /**
   * 文件kbId
   * @format int64
   */
  kbId: number;
  /**
   * 文件id
   * @format int64
   */
  fileId?: number;
  /** 文件pks */
  pks?: number[];
}

export interface Type更新faq状态请求参数 {
  /**
   * 知识库id
   * @format int64
   */
  kbId: number;
  /**
   * 文件id
   * @format int64
   */
  fileId?: number;
  /** 禁用的FAQ的relatedPks */
  disabledRelatedpks?: number[];
  /** 启用的FAQ的relatedPks */
  relatedpks?: number[];
  /**
   * 状态 0:禁用;1启用 默认值为1
   * @format int32
   */
  status?: number;
}

export interface Faq信息 {
  /**
   * 相似问关联的pk
   * @format int64
   */
  pk?: number;
  /** 问题 */
  question?: string;
  /** 答案 */
  answer?: string;
  /**
   * 启用状态，0:待启用，1：已启用
   * @format int32
   */
  status?: number;
  /** 文件路径 */
  sourceFile?: string;
  /** 文件名 */
  sourceFileName?: string;
  /**
   * 文档id
   * @format int64
   */
  fileId?: number;
  /** 修订实时间 */
  reviseDate?: string;
  /** 相似问列表 */
  similarQuestions?: Faq信息[];
  /** @format int32 */
  faqType?: number;
}

export interface Faq一键启用禁用请求参数 {
  /**
   * 知识库id
   * @format int64
   */
  kbId: number;
  /**
   * 文件id
   * @format int64
   */
  fileId?: number;
  /** 禁用的FAQ的relatedPks */
  relatedPks?: number[];
  /**
   * 状态 0:禁用;1启用 默认值为1
   * @format int32
   */
  status?: number;
}

export interface Type知识库详情 {
  /**
   * 主键
   * @format int64
   */
  id?: number;
  /** 知识库名称 */
  kbName?: string;
  /** 知识库原始名称,对应算法知识库的名称 */
  primitiveName?: string;
  /**
   * 知识库类型 1:文本 2:音频 3:视频 ...
   * @format int32
   */
  kbType?: number;
  /** 描述 */
  kbDes?: string;
  /** 路径 */
  sourceUrl?: string;
  /**
   * 状态 0:删除;1正常，默认值1
   * @format int32
   */
  status?: number;
  /**
   * 文件总大小 单位:M
   * @format double
   */
  fileTotalSize?: number;
  /**
   * 文件数量
   * @format int32
   */
  fileCount?: number;
  /**
   * 数据权限 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
   * @format int32
   */
  permission?: number;
  /**
   * 文本块大小(块token数)
   * @format int32
   */
  chunkSize?: number;
  /** 文档类型（解析方法），目前支持四种类型，[naive, laws, book, table] */
  fileType?: string;
  /** 嵌入模型名称 */
  embeddingModelName?: string;
  /** 知识库标签 */
  kbLabel?: string;
  /**
   * 单篇文档问答对抽取数量上限
   * @format int32
   */
  fileFaqMaxNums?: number;
  /**
   * 生成相似问个数
   * @format int32
   */
  similarQuestionMaxNums?: number;
  /** faq导入是否润色 默认值false */
  enablePolish?: boolean;
  /** 图谱提示词 */
  graphPrompt?: string;
}

/** 文件解析/抽取异常日志 */
export interface SynLogDTO {
  /** @format int64 */
  id?: number;
  /** @format int64 */
  kbId?: number;
  /** @format int64 */
  targetId?: number;
  /** @format int32 */
  logType?: number;
  errorCode?: string;
  errorMessage?: string;
  errorDetail?: string;
}

export interface Type文件详情 {
  /**
   * 主键
   * @format int64
   */
  id?: number;
  /**
   * 知识库id
   * @format int64
   */
  kbId?: number;
  /** 文件名称 */
  fileName?: string;
  /**
   * 文件大小 M
   * @format double
   */
  fileSize?: number;
  /** 文件路径 */
  filePath?: string;
  /** 更易于算法解析的文件的路径 */
  convertedFilePath?: string;
  /**
   * 状态  0:删除 1:正常 2:解析中，3:解析成功 4: 解析失败 5:问答对解析中 6:问答对解析成功 7:问答对解析失败
   * @format int32
   */
  status?: number;
  /**
   * 启用禁用状态 0:禁用;1启用
   * @format int32
   */
  isEnable?: number;
  /**
   * 文件解析类型: 1 文件解析；2 FAQ解析
   * @format int32
   */
  parseType?: number;
  /**
   * 文本块大小(块token数)
   * @format int32
   */
  chunkSize?: number;
  /** 文档类型（解析方法），目前支持四种类型，[naive, laws, book, table] */
  fileType?: string;
  /** 嵌入模型名称 */
  embeddingModelName?: string;
  /** 解析后的文件路径 */
  parsedFilePath?: string;
  /**
   * faq抽取状态 1 未抽取；2 抽取成功 2 抽取失败 默认值 1
   * @format int32
   */
  faqExtractStatus?: number;
  /** 修订实时间 */
  reviseDate?: string;
  /** 父文件名称 */
  parentFileName?: string;
  /** 版本号 */
  version?: string;
  /**
   * 文件夹id
   * @format int64
   */
  folderId?: number;
  /** 文件夹名称 */
  folderName?: string;
  /** 文件导入url */
  sourceUrl?: string;
  /** 文件解析/抽取异常日志 */
  synLogs?: SynLogDTO[];
  /** 子文件 */
  kbFiles?: Type文件详情[];
  /**
   * 是否是文件夹 0:否  1:是
   * @format int32
   */
  isFolder?: number;
  /** 图片路径 */
  imagePaths?: string[];
  /**
   * pdf 文件页数
   * @format int32
   */
  pdfPage?: number;
  /**
   * 节点数
   * @format int32
   */
  nodeCount?: number;
  /**
   * 关系数
   * @format int32
   */
  edgeCount?: number;
  /**
   * 图解析状态 1 未解析；2 解析中 3 解析成功 4 解析失败
   * @format int32
   */
  graphParseStatus?: number;
  /**
   * 文件上传时间
   * @format date-time
   */
  uploadTime?: string;
  /**
   * 问答对数
   * @format int64
   */
  aqCount?: number;
}

/** 件路径列表，和文件夹路径、文件ID列表不允许同时为空或者None */
export interface File {
  /**
   * 文件id
   * @format int64
   */
  file_id?: number;
  /** 源文件路径 */
  file_path?: string;
  /** 更易于算法解析的路径 */
  converted_file_path?: string;
  /** 文件大小 */
  file_size?: string;
  /** 父文件名称 */
  parent_file_name?: string;
}

export interface Type文本解析请求参数体 {
  /** 文件夹id */
  folder_ids?: number[];
  /** 件路径列表，和文件夹路径、文件ID列表不允许同时为空或者None */
  files: File[];
  /** 文件ID列表，minIO中对应的文件ID，和文件路径列表、文件夹路径不能同时为空或者None */
  file_ids?: string[];
  /** 知识库名称 */
  knowledge_base_name: string;
  /**
   * 知识库id
   * @format int64
   */
  knowledge_base_id?: number;
  /** 是否覆盖同名文件 默认值 ture */
  override?: boolean;
  /**
   * 文本块大小(块token数) 默认500
   * @format int32
   */
  chunk_size?: number;
  /**
   * 文本块重叠大小 默认20
   * @format int32
   */
  chunk_overlap?: number;
  /** 文档类型（解析方法），目前支持四种类型，[naive, laws, book, table] */
  file_type?: string;
  /** 嵌入模型名称 */
  embedding_model_name?: string;
  /** 抽取模型名称 */
  extract_model_name?: string;
  /** 是否素材库上传 */
  save_txt?: boolean;
  /** 是否作为内容来源 */
  need_chunk?: boolean;
}

export interface FileMergeReq {
  /** @format int64 */
  kbId?: number;
  fileName?: string;
  fileMd5?: string;
  /** @format int32 */
  chunks?: number;
}

export interface Type创建知识库请求体 {
  /** 知识库名称 */
  kbName: string;
  /**
   * 知识库类型 1:文本 2:音频 3:视频 ... 默认值是1
   * @format int32
   */
  kbType?: number;
  /** 描述 */
  kbDes?: string;
  /**
   * 文本块大小(块token数) 默认值 500
   * @format int32
   */
  chunkSize?: number;
  /** 文档类型（解析方法），目前支持四种类型，[naive, laws, book, table] 默认 naive */
  fileType?: string;
  /** 嵌入模型名称 */
  embeddingModelName?: string;
  /** 知识库标签 */
  kbLabel?: string;
  /** 生成图谱的提示词 */
  graphPrompt?: string;
}

export interface Type文件夹保存请求参数 {
  /** 文件夹名称 */
  name?: string;
  /**
   * 知识库id
   * @format int64
   */
  kbId?: number;
  /**
   * 父文件夹id
   * @format int64
   */
  parentId?: number;
  /**
   * 1:文档解析；2:FAQ抽取
   * @format int32
   */
  type?: number;
}

export interface Type文件转移请求参数 {
  /**
   * 目标文件夹的id
   * @format int64
   */
  targetFolderId: number;
  /**
   * 文件id
   * @format int64
   */
  fileId: number;
}

export interface Faq润色请求参数 {
  /**
   * 知识库id
   * @format int64
   */
  kbId: number;
  /**
   * 文件id
   * @format int64
   */
  fileId?: number;
  /** faq主键 */
  pks: number[];
}

export interface Type知识库列表请求参数 {
  /** 名称或id或标签 */
  fuzzy?: string;
  /**
   * 每页大小,默认值20
   * @format int64
   */
  pageSize?: number;
  /**
   * 第几页 默认值1
   * @format int64
   */
  pageNo?: number;
}

export interface OrderItem {
  column?: string;
  asc?: boolean;
}

export interface Page知识库详情 {
  records?: Type知识库详情[];
  /** @format int64 */
  total?: number;
  /** @format int64 */
  size?: number;
  /** @format int64 */
  current?: number;
  orders?: OrderItem[];
  optimizeCountSql?: Page知识库详情;
  searchCount?: Page知识库详情;
  optimizeJoinOfCountSql?: boolean;
  /** @format int64 */
  maxLimit?: number;
  countId?: string;
  /** @format int64 */
  pages?: number;
}

export interface Type知识库文件查询请求参数 {
  /**
   * 知识库id
   * @format int64
   */
  kbId: number;
  /**
   * 状态  1:正常 2:解析中，3:解析成功 4: 解析失败
   * @format int32
   */
  status?: number;
  /**
   * faq抽取状态 1 未抽取；2 抽取中 3 抽取成功 4 抽取失败
   * @format int32
   */
  faqExtractStatus?: number;
  /** 查询关键字 */
  fuzzy?: string;
  /**
   * 列表类型: 1 文件解析列表；2 FAQ解析列表 默认值 1
   * @format int32
   */
  fileListType?: number;
  /** 父文件名称 */
  parentFileName?: string;
  /**
   * 文件夹id
   * @format int64
   */
  folderId?: number;
  /**
   * 第几页 默认值 1
   * @format int64
   */
  pageNo?: number;
  /**
   * 每页大小 默认值 20
   * @format int64
   */
  pageSize?: number;
}

export interface Page文件详情 {
  records?: Type文件详情[];
  /** @format int64 */
  total?: number;
  /** @format int64 */
  size?: number;
  /** @format int64 */
  current?: number;
  orders?: OrderItem[];
  optimizeCountSql?: Page文件详情;
  searchCount?: Page文件详情;
  optimizeJoinOfCountSql?: boolean;
  /** @format int64 */
  maxLimit?: number;
  countId?: string;
  /** @format int64 */
  pages?: number;
}

export interface Page文件chunk信息 {
  records?: Type文件chunk信息[];
  /** @format int64 */
  total?: number;
  /** @format int64 */
  size?: number;
  /** @format int64 */
  current?: number;
  orders?: OrderItem[];
  optimizeCountSql?: Page文件chunk信息;
  searchCount?: Page文件chunk信息;
  optimizeJoinOfCountSql?: boolean;
  /** @format int64 */
  maxLimit?: number;
  countId?: string;
  /** @format int64 */
  pages?: number;
}

export interface Type文件chunk信息 {
  /** @format int64 */
  id?: number;
  content?: string;
  picChunkIdList?: number[];
  picUrlList?: string[];
  imagePath?: string;
  positions?: {
    empty?: boolean;
  };
  pageNumbers?: {
    empty?: boolean;
  };
  pageSizes?: {
    empty?: boolean;
  };
  offsets?: {
    empty?: boolean;
  };
  type?: string;
  tableName?: string;
}

export interface Page文件夹详情 {
  records?: Type文件夹详情[];
  /** @format int64 */
  total?: number;
  /** @format int64 */
  size?: number;
  /** @format int64 */
  current?: number;
  orders?: OrderItem[];
  optimizeCountSql?: Page文件夹详情;
  searchCount?: Page文件夹详情;
  optimizeJoinOfCountSql?: boolean;
  /** @format int64 */
  maxLimit?: number;
  countId?: string;
  /** @format int64 */
  pages?: number;
}

export interface Type文件夹详情 {
  /**
   * 主键
   * @format int64
   */
  id?: number;
  /** 文件夹名称 */
  name?: string;
  /**
   * 知识库id
   * @format int64
   */
  kbId?: number;
  /**
   * 1:文档解析；2:FAQ抽取
   * @format int32
   */
  type?: number;
  /**
   * 父文件夹id
   * @format int64
   */
  parentId?: number;
  /**
   * 1：正常；-1：删除
   * @format int32
   */
  status?: number;
  /**
   * 创建时间
   * @format date-time
   */
  gmtCreate?: string;
  /**
   * 更新时间
   * @format date-time
   */
  gmtModified?: string;
  /** 创建人 */
  createBy?: string;
  /** 更新人 */
  updateBy?: string;
  /** 完整路径（包含结尾/) */
  fullPath?: string;
  /** 子目录 */
  subFolder?: Type文件夹详情[];
}

export interface Faq修改请求参数 {
  /**
   * 文件kbId
   * @format int64
   */
  kbId?: number;
  /** 知识库名称 */
  primitiveName?: string;
  /** 问题或答案(用于模糊搜索) */
  fuzzy?: string;
  /** faq主键 */
  pks?: number[];
  /** 相似问关联的字段 */
  relatedPk?: number[];
  /**
   * 状态 0:禁用 1 启用  null 所有
   * @format int32
   */
  status?: number;
  /**
   * 文件id
   * @format int64
   */
  fileId?: number;
  /**
   * 第几页 默认值 1
   * @format int32
   */
  pageNo?: number;
  /**
   * 每页大小 默认值 20
   * @format int32
   */
  pageSize?: number;
  expand?: boolean;
}

export interface PageFaq信息 {
  records?: Faq信息[];
  /** @format int64 */
  total?: number;
  /** @format int64 */
  size?: number;
  /** @format int64 */
  current?: number;
  orders?: OrderItem[];
  optimizeCountSql?: PageFaq信息;
  searchCount?: PageFaq信息;
  optimizeJoinOfCountSql?: boolean;
  /** @format int64 */
  maxLimit?: number;
  countId?: string;
  /** @format int64 */
  pages?: number;
}

export interface Type山粗文本块请求参数 {
  /** tableName */
  tableName: string;
  /** 文本块id */
  chunkIds: string[];
}

export interface Faq相似问删除 {
  /**
   * 知识库id
   * @format int64
   */
  kbId: number;
  /**
   * 文件id
   * @format int64
   */
  fileId?: number;
  /** 问答对relatedPk */
  relatedPks?: number[];
}
