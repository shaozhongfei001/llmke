import { konwledgeTitles } from "@/const/knowledgebase";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import MockAdapter from "axios-mock-adapter";
import axios, { AxiosInstance, GenericAbortSignal } from "axios";
import { apis } from "./apis";
import {
  completeArticle_mockData,
  completeSection_mockData,
  optimize_mockData
} from "../mocks";
import { message } from "antd";
import { generateUrl } from "../operators/help/utils";
import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";
interface ServerBase<D> {
  data: D;
  config: {
    baseURL: string;
    token: string;
    enableMock?: boolean;
  };
}

const createAxiosInstance = (params: any) => {
  const {
    baseURL,
    token,
    headers,
    responseType,
    config,
    isSkipSuccess = false
  } = params;
  const instance = axios.create({
    baseURL: baseURL, // 替换为你的API基础URL
    responseType: responseType,
    ...config
  });

  // 请求拦截器，附加token
  instance.interceptors.request.use(
    (config) => {
      if (token) {
        config.headers = {
          ...config.headers,
          ...headers
        };
        config.headers.Authorization = `${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // 响应拦截器，可以处理响应错误或进行其他操作
  instance.interceptors.response.use(
    (response) => {
      if (response.status === 401) {
        throw new Error("令牌已经过期或没有权限查看");
      }
      if (response.status === 200) {
        // 下载接口直接返回
        if (typeof response.data !== "object") return response.data;
        if (response.config.url?.includes("/dw/article/export"))
          return response.data;
        // 其余接口根据success判断是否请求成功
        const data = response.data;
        if (isSkipSuccess) {
          // 不需要提示错误文字，前端页面自己判断处理
          return data;
        }
        if (!data.success) {
          message.error(data.errorMsg || "请求出错，请稍后再试");
          return Promise.reject(data.errorMsg);
        } else {
          return data;
        }
      }
      return Promise.reject(response);
    },
    (error) => {
      if (error.code !== "ERR_CANCELED") {
        message.error(
          (error?.response?.data || {})?.errorMsg || "请求出错，请稍后再试"
        );
      }
      return Promise.reject(error);
    }
  );

  return instance;
};

const mockApiResponse = (
  http: AxiosInstance,
  method: "get" | "post" | "put" | "delete" | string,
  url: string,
  mockData: any
) => {
  const mock = new MockAdapter(http, { delayResponse: 800 });
  switch (method) {
    case "get":
      return mock.onGet(url).reply(200, mockData);
    case "post":
      return mock.onPost(url).reply(200, mockData);
    case "put":
      return mock.onPut(url).reply(200, mockData);
    case "delete":
      return mock.onDelete(url).reply(200, mockData);
    default:
      throw new Error(`Unsupported method: ${method}`);
  }
};

//根据id获取当前文档的详情
interface TYPE_api_getArticleById
  extends ServerBase<{
    articleId: string | number;
    needSectionContent?: boolean;
  }> {}
export const api_getArticleById = (props: TYPE_api_getArticleById) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.getArticleById;
  const queryUrl = `${url}?articleId=${data.articleId}&needSectionContent=${
    data.needSectionContent || false
  }`;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method: method
  }).then((res) => res.data);
};

//根据提交数据进行大纲的生成
interface TYPE_api_generateOutlines extends ServerBase<{ params: any }> {}
export const api_generateOutlines = (props: TYPE_api_generateOutlines) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.generateOutline;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: url,
    method,
    data: data.params
  }).then((res) => res.data);
};

//根据文章id进行文档的审核
interface TYPE_api_doReviewing
  extends ServerBase<{ articleId: string | number }> {}
export const api_doReviewing = (props: TYPE_api_doReviewing) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.review;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  const queryUrl = `${url}?articleId=${data.articleId}`;
  if (config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method: method
  }).then((res) => res.data);
};

//保存文章内容
interface TYPE_api_saveArticleContent extends ServerBase<{ params: any }> {}
export const api_saveArticleContent = (props: TYPE_api_saveArticleContent) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.saveArticleContent;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: url,
    method,
    data: data.params
  }).then((res) => res.data);
};

//保存文章配置
interface TYPE_api_saveArticleSetting extends ServerBase<{ params: any }> {}
export const api_saveArticleSetting = (props: TYPE_api_saveArticleSetting) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.saveArticleSetting;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: url,
    method,
    data: data.params
  }).then((res) => res.data);
};

// 写作前检测章节是否有依赖
interface TYPE_api_putDependencyDetect
  extends ServerBase<{
    articleId: string | number;
    sectionIds: string[] | number[];
  }> {}
export const api_putDependencyDetect = (
  props: TYPE_api_putDependencyDetect
) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.putDependencyDetect;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
    // isSkipSuccess: true
  });
  const { articleId, sectionIds } = data;
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: url,
    method,
    data: {
      articleId,
      sectionIds
    }
  }).then((res) => res);
};

// 获取素材列表
interface TYPE_api_getArticleMaterialList
  extends ServerBase<{
    fileName?: string;
    bizType?: string;
    scene?: string;
    articleStyle?: string;
    pageSize: number;
    pageNo: number;
    state?: number;
  }> {}
export const api_getArticleMaterialList = (
  props: TYPE_api_getArticleMaterialList
) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.getArticleMaterialList;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  // state=3，过滤解析成功的文件
  const queryUrl = generateUrl(url, data);
  // const queryUrl = `${url}?pageNo=1&pageSize=999&fileName=${fileName}&bizType=${bizType}&sence=${sence}&articleStyle=${articleStyle}&state=3`;
  if (config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method: method
  }).then((res) => res.data);
};

// 获取模板列表
interface TYPE_api_getArticleTypeList extends ServerBase<{}> {}
export const api_getArticleTypeList = (props: TYPE_api_getArticleTypeList) => {
  const { config } = props;
  const { url, method, mockData } = apis.getArticleTypeList;
  const queryUrl = `${url}?pageNo=1&pageSize=999`;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method: method
  }).then((res) => res.data);
};

// 获取文章模板详情
interface TYPE_api_getArticleTypeDetails
  extends ServerBase<{
    id: string | number;
    versionId?: string | number;
  }> {}
export const api_getArticleTypeDetails = (
  props: TYPE_api_getArticleTypeDetails
) => {
  const { config, data } = props;
  const { url, method, mockData } = apis.getArticleTypeDetails;
  const queryUrl = data.versionId
    ? `${url}/${data.id}/version/${data.versionId}`
    : `${url}/${data.id}`;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method: method
  }).then((res) => res.data);
};

// 敏感词审核
interface TYPE_api_markSensitiveWord
  extends ServerBase<{
    articleId: string | number;
  }> {}
export const api_markSensitiveWord = (props: TYPE_api_markSensitiveWord) => {
  const { config, data } = props;
  const { url, method, mockData } = apis.markSensitiveWord;
  const queryUrl = `${url}/${data.articleId}/markSensitiveWord`;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method: method
  }).then((res) => res.data);
};

// 审核文章
interface TYPE_api_reviewArticleByContentRule
  extends ServerBase<{
    articleId: string | number;
    content: string;
    signal?: any;
  }> {}
export const api_reviewArticleByContentRule = (
  props: TYPE_api_reviewArticleByContentRule
) => {
  const { config, data } = props;
  const { articleId, content } = data;
  const { url, method, mockData } = apis.reviewArticleByContentRule;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: url,
    method: method,
    signal: props.data.signal,
    data: {
      articleId,
      content
    }
  }).then((res) => res.data);
};

// 反馈文章
interface TYPE_api_articleFeedback
  extends ServerBase<{
    articleId?: string | number;
    errorType?: string | number;
    // 反馈类型:0-comment 1-like 2-unlike'
    feedbackType: 0 | 1 | 2;
    [key: string]: any;
  }> {}
export const api_articleFeedback = (props: TYPE_api_articleFeedback) => {
  const { config, data } = props;
  const { url, method, mockData } = apis.articleFeedback;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: url,
    method,
    data
  }).then((res) => res.data);
};

// 下载文章
interface TYPE_api_exportArticleById
  extends ServerBase<{
    articleId: string | number;
    version?: string;
  }> {}
export const api_exportArticleById = (props: TYPE_api_exportArticleById) => {
  const { config, data } = props;
  const { url, method, mockData } = apis.exportArticleById;
  const { version } = data;
  const curVersion = version ? (version === "odt" ? "odf" : version) : "docx";
  const queryUrl = `${url}?articleId=${data.articleId}&version=${curVersion}  `;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token,
    headers: {
      "Content-Type": "application/msword;charset=UTF-8"
    },
    responseType: "blob"
  });
  if (config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method: method,
    responseType: "blob"
  }).then((res) => res);
};

// 上传文档获取html
interface TYPE_api_getParseTextByUploadFile
  extends ServerBase<{
    file: FormData;
    onUploadProgress: any;
  }> {}
export const api_getParseTextByUploadFile = (
  props: TYPE_api_getParseTextByUploadFile
) => {
  const { config, data } = props;
  const { url, method, mockData } = apis.getParseTextByUploadFile;
  const { onUploadProgress, file } = data;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token,
    config: {
      onUploadProgress
    }
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: url,
    method: method,
    data: file,
    onUploadProgress
  }).then((res) => res.data);
};

// 上传图片，用于导出文章股权结构图
interface TYPE_api_storeFiles
  extends ServerBase<{
    file: FormData;
  }> {}
export const api_storeFiles = (props: TYPE_api_storeFiles) => {
  const { config, data } = props;
  const { url, method, mockData } = apis.storeFiles;
  const { file } = data;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: url,
    method: method,
    data: file
  }).then((res) => res.data);
};

// 根据文件地址获取文件内容，用于素材写作
interface TYPE_api_getFileContent
  extends ServerBase<{
    fileUrl: string;
  }> {}
export const api_getFileContent = (props: TYPE_api_getFileContent) => {
  const { config, data } = props;
  const { method, mockData } = apis.getFileContent;
  const { fileUrl } = data;
  const http = createAxiosInstance({});
  // if (config.enableMock) {
  //   mockApiResponse(http, method, fileUrl, mockData);
  // }
  return http({
    url: fileUrl,
    method: method
  }).then((res) => {
    return res;
  });
};

// 缩写，扩写，润色
interface TYPE_api_optimize
  extends ServerBase<{
    signal: AbortSignal;
    params: {
      lengthLimit?: number;
      lengthLimitLow?: number;
      // 1-润色，2-扩写，3-缩写
      optType: number;
      rawContent: string;
      userPrompt?: string;
    };
    onmessage: (ev: any) => any;
    onerror?: (err: any) => any;
    onclose?: () => any;
  }> {}
export const api_optimize = (props: TYPE_api_optimize) => {
  const { config, data } = props;
  const { onmessage, onerror, params, signal, onclose } = data;
  const eventSourceUrl = `${config.baseURL}/dw/article/optimize`;

  if (config.enableMock) {
    // 模拟服务器发送的事件
    const mockData = optimize_mockData.map((i) => ({
      ...i,
      data: JSON.stringify(i.data)
    }));
    let index = 0;
    const timer: any = setInterval(() => {
      if (index === mockData.length) {
        clearInterval(timer);
        onclose && onclose();
      } else {
        onmessage(mockData[index]);
        index++;
      }
    }, 100);
    return;
  }

  // 实际的 fetchEventSource 请求
  fetchEventSource(eventSourceUrl, {
    openWhenHidden: true,
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      Authorization: config.token
    },
    body: JSON.stringify(params),
    onmessage: onmessage,
    onerror: onerror
  });
};

// 生成全文
export interface TYPE_api_completeArticle
  extends ServerBase<{
    signal?: AbortSignal;
    articleId: string | number;
    isHtml?: boolean;
    onmessage: (ev: any) => any;
    onerror?: (err: any) => any;
    onclose?: () => any;
  }> {}
export const api_completeArticle = (props: TYPE_api_completeArticle) => {
  const { config, data } = props;
  const {
    onmessage,
    onerror,
    articleId,
    signal,
    isHtml = false,
    onclose
  } = data;
  const eventSourceUrl = `${config.baseURL}/dw/article/completeArticle?articleId=${articleId}&isHtml=${isHtml}`;

  if (config.enableMock) {
    // 模拟服务器发送的事件
    let index = 0;
    const timer: any = setInterval(() => {
      if (index === completeArticle_mockData.length) {
        clearInterval(timer);
        onclose && onclose();
      } else {
        onmessage(completeArticle_mockData[index]);
        index++;
      }
    }, 100);
    return;
  }

  // 实际的 fetchEventSource 请求
  fetchEventSource(eventSourceUrl, {
    openWhenHidden: true,
    signal,
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: config.token
    },
    onmessage,
    onerror,
    onclose
  });
};

// 分段生成
export interface TYPE_api_completeSection
  extends ServerBase<{
    signal?: AbortSignal;
    articleId: string | number;
    sectionId: string | number;
    params: any;
    onmessage: (ev: any) => any;
    onerror?: (err: any) => any;
    onclose?: () => any;
  }> {}
export const api_completeSection = (props: TYPE_api_completeSection) => {
  const { config, data } = props;
  const { articleId, sectionId, onmessage, onerror, signal, onclose } = data;
  const eventSourceUrl = `${config.baseURL}/dw/article/${articleId}/section/${sectionId}/complete`;

  if (config.enableMock) {
    // 模拟服务器发送的事件
    let index = 0;
    const timer: any = setInterval(() => {
      if (index === completeSection_mockData.length) {
        clearInterval(timer);
        onclose && onclose();
      } else {
        onmessage(completeSection_mockData[index]);
        index++;
      }
    }, 1000);
    return;
  }

  // 实际的 fetchEventSource 请求
  fetchEventSource(eventSourceUrl, {
    openWhenHidden: true,
    signal,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: config.token
    },
    body: JSON.stringify(data.params),
    onmessage,
    onerror,
    onclose
  });
};

interface TYPE_api_queryMaterialList
  extends ServerBase<{
    id: string;
    pageSize: number;
    pageNo: number;
  }> {}
export const api_queryMaterialList = (props: TYPE_api_queryMaterialList) => {
  const { config, data } = props;
  const { method, url } = apis.getFileStatusByIds;
  const queryUrl = `${url}?id=${data.id}&pageSize=${data.pageSize}&pageNo=${data.pageNo}`;
  const { id } = data;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  return http({
    url: queryUrl,
    method: method
  }).then((res) => {
    return res;
  });
};
//retryParseMaterialUsingPost
interface TYPE_api_retryParseMaterialUsing extends ServerBase<{ id: string }> {}
export const api_retryParseMaterialUsing = (
  props: TYPE_api_retryParseMaterialUsing
) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.retryParseMaterial;
  const queryUrl = `${url}/${data.id}`;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: queryUrl,
    method
  }).then((res) => res.data);
};
interface TYPE_api_queryMaterialType
  extends ServerBase<{
    id?: string;
  }> {}
export const api_queryMaterialType = (props: TYPE_api_queryMaterialType) => {
  const { config, data } = props;
  const { method, url } = apis.getMaterialType;
  const queryUrl = `${url}`;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  return http({
    url: queryUrl,
    method: method
  }).then((res) => {
    return res;
  });
};

interface TYPE_api_querySectionById
  extends ServerBase<{
    id?: string;
  }> {}
export const api_querySectionById = (props: TYPE_api_querySectionById) => {
  const { config, data } = props;
  const { method, url } = apis.getSectionById;
  const queryUrl = `${url}/${data.id}`;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  return http({
    url: queryUrl,
    method: method
  }).then((res) => {
    return res;
  });
};

interface TYPE_api_getSectionByVersionId
  extends ServerBase<{
    articleTypeId: string;
    versionId: string;
    sectionId: string;
  }> {}
export const api_getSectionByVersionId = (
  props: TYPE_api_getSectionByVersionId
) => {
  const { config, data } = props;
  const { articleTypeId, versionId, sectionId } = data;
  const { method, url } = apis.getSectionByVersionId;
  const queryUrl = `${url}/${articleTypeId}/version/${versionId}/section/${sectionId}`;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  return http({
    url: queryUrl,
    method: method
  }).then((res) => {
    return res;
  });
};

interface TYPE_api_EditSectionById
  extends ServerBase<{
    params: any;
    id?: string;
    articleId?: string;
    updateContent?: boolean;
  }> {}
export const api_editSectionById = (props: TYPE_api_EditSectionById) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.editSectionById;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  const { updateContent } = data;
  let saveUrl = "";
  if (updateContent) {
    saveUrl = `${url}/${data.articleId}/section/${data.id}?updateContent=true`;
  } else {
    saveUrl = `${url}/${data.articleId}/section/${data.id}`;
  }

  return http({
    url: saveUrl,
    method,
    data: data.params
  }).then((res) => res.data);
};

interface TYPE_api_EditArticleTypeSectionById
  extends ServerBase<{ params: any; id?: string; articleTypeId?: string }> {}
export const api_editArticleTypeSectionById = (
  props: TYPE_api_EditArticleTypeSectionById
) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.editArticleTypeSectionById;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: `${url}/${data.articleTypeId}/section/${data.id}`,
    method,
    data: data.params
  }).then((res) => res.data);
};

interface TYPE_api_DeleteSectionByIds
  extends ServerBase<{
    ids?: string;
    articleId?: string;
    type: "article" | "articleType";
    params: any;
  }> {}
export const api_deleteSectionByIds = (props: TYPE_api_DeleteSectionByIds) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.deleteSections;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: `${url}/${data.type}/${data.articleId}/section/${data.ids}`,
    method,
    data: data.params
  }).then((res) => res);
};

interface TYPE_api_ApplyOutlines
  extends ServerBase<{
    articleId?: string;
    params: any;
  }> {}
export const api_applyOutlines = (props: TYPE_api_ApplyOutlines) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.applyOutlines;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: `${url}/${data.articleId}/applyOutlines`,
    method,
    data: data.params
  }).then((res) => res);
};

enum scopeTypes {
  scene,
  writing
}
interface TYPE_api_ApplySection
  extends ServerBase<{
    id: string | number;
    params: {
      articleId?: string | number; //文章id
      articleTypeId?: string | number; //场景id
      scope: scopeTypes; //0-场景时应用， 1-写作时应用
    };
  }> {}
export const api_applySection = (props: TYPE_api_ApplySection) => {
  const { data, config } = props;
  const { id, params } = data;
  const { url, method, mockData } = apis.applySection;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: `${url}/${id}/apply`,
    method,
    data: { ...params }
  }).then((res) => res);
};

interface TYPE_api_AddArticleTypeSection
  extends ServerBase<{ params: any; id?: string; articleTypeId?: string }> {}
export const api_addArticleTypeSection = (
  props: TYPE_api_AddArticleTypeSection
) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.addArticleTypeSection;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: `${url}/${data.articleTypeId}/section`,
    method,
    data: data.params
  }).then((res) => res.data);
};

interface TYPE_api_GetDatabase extends ServerBase<{ params: any }> {}
export const api_getDatabase = (props: TYPE_api_GetDatabase) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.getDataBase;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: `${url}`,
    method,
    data: data.params
  }).then((res) => res.data);
};

interface TYPE_api_AddSection
  extends ServerBase<{ params: any; id?: string; articleId?: string }> {}
export const api_addSection = (props: TYPE_api_AddSection) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.addSection;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: `${url}/${data.articleId}/section`,
    method,
    data: data.params
  }).then((res) => res.data);
};

interface TYPE_api_putArticleMaterialList
  extends ServerBase<{ params: any; id?: string }> {}
export const api_putArticleMaterialList = (
  props: TYPE_api_putArticleMaterialList
) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.putArticleMaterialList;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: `${url}/${data.id}`,
    method,
    data: data.params
  }).then((res) => res.data);
};

interface TYPE_api_batchSave
  extends ServerBase<{ params: any; id: string | number }> {}
export const api_batchSave = (props: TYPE_api_batchSave) => {
  const { data, config } = props;
  const { url, method, mockData } = apis.batchSave;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: `/dw/article/${data.id}${url}`,
    method,
    data: data.params
  }).then((res) => res.data);
};

export const fetchKnowledgeBase = async () => {
  try {
    return axios$
      .get(`${getUrlPrefix()}/index/knowledgeBase/list?pageNo=1&pageSize=999`)
      .then((result: any) => {
        if (result?.data?.records) {
          const format_data = result?.data?.records.map((kb: any) => {
            return {
              label: kb.kbName,
              value: kb.id
            };
          });
          return format_data;
        }
        return [];
      });
  } catch (error) {
    console.log("e", error);
  }
};
interface TYPE_api_completeChart
  extends ServerBase<{
    articleId: string | number;
    sectionId: string | number;
  }> {}
export const api_completeChart = (props: TYPE_api_completeChart) => {
  const { data, config } = props;
  const { articleId, sectionId } = data;
  const { url, method, mockData } = apis.completeChart;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(
      http,
      method,
      `/dw/article/${articleId}/section/${sectionId}/completeChart`,
      mockData
    );
  }
  return http({
    url: `/dw/article/${articleId}/section/${sectionId}/completeChart`,
    method
  }).then((res) => res.data);
};

// 新增离线写作任务
interface TYPE_api_addArticleTask
  extends ServerBase<{
    articleId: string | number;
    outlinesSnapshot?: {
      [paragraphs: string]: any[];
    };
    sectionIds?: string[] | number[];
  }> {}
export const api_addArticleTask = (props: TYPE_api_addArticleTask) => {
  const { config, data } = props;
  const { url, method, mockData } = apis.addArticleTask;
  const http = createAxiosInstance({
    baseURL: config.baseURL,
    token: config.token
  });
  if (config.enableMock) {
    mockApiResponse(http, method, url, mockData);
  }
  return http({
    url: url,
    method,
    data
  }).then((res) => res);
};
