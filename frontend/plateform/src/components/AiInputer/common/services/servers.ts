import { message } from "antd";
import MockAdapter from "axios-mock-adapter";
import axios, { AxiosInstance } from "axios";
import { apis } from "./apis";
import { ChatSystemType } from "../../@types/props";
interface ServerBase<D> {
  data: D;
  config: {
    url: string;
    token?: string;
    enableMock?: boolean;
  };
}
//新的方案，hook造成初始化问题解决

const createAxiosInstance = (url: string, token?: string, headers?: any) => {
  const instance = axios.create({
    baseURL: url // 替换为你的API基础URL
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
      return response.data;
    },
    (error) => {
      message.error(
        (error?.response?.data || {})?.errorMsg || "请求出错，请稍后再试"
      );
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

interface TYPE_api_createDialogue
  extends ServerBase<{
    label: number | string;
    sessionId: number | string;
    assist_id: string;
  }> {}
export const api_createDialogue = (props: TYPE_api_createDialogue) => {
  const { url, method, mockData } = apis.dialog_create;
  const data = {
    label: props.data.label,
    sessionId: props.data.sessionId,
    sysType: ChatSystemType.Retrieval,
    configId: props.data.assist_id
  };
  const queryUrl = `${url}`;

  const http = createAxiosInstance(props.config.url, props.config.token);
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method,
    data
  }).then((res) => res.data);
};

interface TYPE_api_uploadAudio extends ServerBase<{ formData: FormData }> {}
export const api_uploadAudio = (props: TYPE_api_uploadAudio) => {
  const { url, method, mockData } = apis.audio_upload;
  const data = props.data.formData;
  const http = createAxiosInstance(props.config.url, props.config.token);
  const queryUrl = `${url}`;
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method,
    data
  }).then((res) => res.data);
};

interface TYPE_api_getDialogueList
  extends ServerBase<{ page?: string; pageSize?: string }> {}
export const api_getDialogueList = (props: TYPE_api_getDialogueList) => {
  const { url, method, mockData } = apis.dialog_history;
  const http = createAxiosInstance(props.config.url, props.config.token);
  const queryUrl = `${url}?pageNo=${props.data.page || 1}&pageSize=${
    props.data.pageSize || 50
  }&sysType=${ChatSystemType.Retrieval}`;
  // console.log(props.config.enableMock, '函数里面');
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method,
    data: props.data
  }).then((res) => res.data);
};

export const api_uploadFiles = (props: any) => {
  const { url, method, mockData } = apis.upload_files;
  const data = {
    kbId: props.data.kbId,
    files: props.data.files
  };
  const queryUrl = `${url}`;

  const http = createAxiosInstance(props.config.url, props.config.token, {
    "Content-Type": "multipart/form-data"
  });
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method,
    data: props.data
  }).then((res) => res.data);
};

export const api_getFileStatusById = (props: any) => {
  const { url, method, mockData } = apis.file_status;
  const http = createAxiosInstance(props.config.url, props.config.token);
  const queryUrl = `${url}?fileId=${props.data.fileId}`;
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method,
    data: props.data
  }).then((res) => res.data);
};

export const api_getFileStatusByUid = (props: any) => {
  const { url, method, mockData } = apis.file_status_uids;
  const http = createAxiosInstance(props.config.url, props.config.token);
  const queryUrl = `${url}?uids=${props.data.uids}`;
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method,
    data: props.data
  }).then((res) => res.data);
};

export const api_getFileExist = (props: any) => {
  const { url, method, mockData } = apis.file_exist;
  const http = createAxiosInstance(props.config.url, props.config.token);
  const queryUrl = `${url}?kbName=${props.data.kbName}&fileName=${props.data.fileName}`;
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method,
    data: props.data
  }).then((res) => res.data);
};
