import {
  EventSourceMessage,
  fetchEventSource
} from "@microsoft/fetch-event-source";
import { message } from "antd";
import MockAdapter from "axios-mock-adapter";
import axios, { AxiosHeaderValue, AxiosInstance } from "axios";
import { apis } from "./apis";
import { ChatSystemType } from "../../@types/props";
import { useEffect, useRef, useState } from "react";
import { chat_start_mock } from "../mocks/chat_start_mock";
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

interface TYPE_api_renameDialogue
  extends ServerBase<{ label: number | string; sessionId: number | string }> {}
export const api_renameDialogue = (props: TYPE_api_renameDialogue) => {
  const { url, method, mockData } = apis.dialog_rename;
  const data = {
    label: props.data.label,
    sessionId: props.data.sessionId
  };
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

interface TYPE_api_deleteDialogue extends ServerBase<{ id: string }> {}
export const api_deleteDialogue = (props: TYPE_api_deleteDialogue) => {
  const { url, method, mockData } = apis.dialog_delete;
  const queryUrl = `${url}?sessionId=${props.data.id}`;
  const http = createAxiosInstance(props.config.url, props.config.token);
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method
  }).then((res) => res.data);
};

interface TYPE_api_startChat
  extends ServerBase<{
    sessionId: string;
    queryId: string;
    name: string;
    lastDate: string;
    type: string;
    content: string;
    configId: string;
    audioUrl: string;
    onMessage: (ev: EventSourceMessage) => void;
    onError: (err: any) => number | null | undefined | void;
    onClose: () => void;
    signal?: AbortSignal;
  }> {}
export const api_startChat = (props: TYPE_api_startChat) => {
  const { url, method } = apis.chat_start;
  const eventSourceUrl = `${props.config.url}${url}`;
  const params = {
    sessionId: props.data.sessionId,
    queryId: props.data.queryId,
    name: props.data.name,
    lastDate: props.data.lastDate,
    type: props.data.type,
    content: props.data.content,
    configId: props.data.configId,
    audioUrl: props.data.audioUrl
  };

  if (props.config.enableMock) {
    const mockDataLines = chat_start_mock.trim().split("\n");
    let index = 0;

    const intervalId = setInterval(() => {
      if (index < mockDataLines.length) {
        const mockEvent = { data: mockDataLines[index].replace("data:", "") };
        props.data.onMessage(mockEvent as any);
        index++;
      } else {
        clearInterval(intervalId);
        props.data.onClose();
      }
    }, 500); // 每500毫秒发送一行数据

    return;
  }

  fetchEventSource(eventSourceUrl, {
    method: method,
    signal: props.data.signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      Authorization: props.config.token || ""
    },
    openWhenHidden: true,
    body: JSON.stringify(params),
    onmessage: (event) => {
      props.data.onMessage(event);
    },
    onerror: (error) => {
      props.data.onError(error);
    },
    onclose: () => {
      props.data.onClose();
    }
  });
};

interface TYPE_api_startChat_re
  extends ServerBase<{
    sessionId: string;
    queryId: string;
    name: string;
    lastDate: string;
    type: string;
    content: string;
    configId: string;
    audioUrl: string;
    onMessage: (ev: EventSourceMessage) => void;
    onError: (err: any) => number | null | undefined | void;
    onClose: () => void;
    signal?: AbortSignal;
  }> {}

export const api_startChat_re = (props: TYPE_api_startChat_re) => {
  const { url, method } = apis.chat_start;
  const eventSourceUrl = `${props.config.url}${url}_re`;
  const params = {
    sessionId: props.data.sessionId,
    queryId: props.data.queryId,
    name: props.data.name,
    lastDate: props.data.lastDate,
    type: props.data.type,
    content: props.data.content,
    configId: props.data.configId,
    audioUrl: props.data.audioUrl
  };

  if (props.config.enableMock) {
    setTimeout(() => {
      // 模拟服务器发送的事件
    }, 1000);
    return;
  }

  fetchEventSource(eventSourceUrl, {
    method: method,
    signal: props.data.signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      Authorization: props.config.token || ""
    },
    openWhenHidden: true,
    body: JSON.stringify(params),
    onmessage: (event) => {
      props.data.onMessage(event);
    },
    onerror: (error) => {
      props.data.onError(error);
    },
    onclose: () => {
      props.data.onClose();
    }
  });
};

export const api_sd_startChat_re = (props: any) => {
  const { url, method } = apis.sd_chat_start;
  const eventSourceUrl = `${props.config.url}${url}`;
  const params = {
    sessionId: props.data.sessionId,
    queryId: props.data.queryId,
    sysType: "INT_SESSION",
    name: props.data.name,
    lastDate: props.data.lastDate,
    type: props.data.type,
    content: props.data.content,
    configId: props.data.configId,
    audioUrl: props.data.audioUrl,
    documentTitle: props.data.documentTitle,
    qaHistory: props.data.qaHistory,
    newConfigId: props.data.newConfigId,
    fileUrl: props.data.fileUrl
  };

  if (props.config.enableMock) {
    setTimeout(() => {
      // 模拟服务器发送的事件
    }, 1000);
    return;
  }

  fetchEventSource(eventSourceUrl, {
    method: method,
    signal: props.data.signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      Authorization: props.config.token || ""
    },
    openWhenHidden: true,
    body: JSON.stringify(params),
    onmessage: (event) => {
      props.data.onMessage(event);
    },
    onerror: (error) => {
      props.data.onError(error);
    },
    onclose: () => {
      props.data.onClose();
    }
  });
};

interface TYPE_api_getChatHistory
  extends ServerBase<{ sessionId: string | undefined }> {}
export const api_getChatHistory = (props: TYPE_api_getChatHistory) => {
  const { url, method, mockData } = apis.chat_history_data;
  const queryUrl = `${url}?sessionId=${props.data.sessionId}`;
  const http = createAxiosInstance(props.config.url, props.config.token);
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method
  }).then((respones) => respones.data);
};

interface TYPE_api_getReferenceList
  extends ServerBase<{
    sessionId: string | undefined;
    queryId: string;
    name: string;
    type: string;
    content: string;
  }> {}
export const api_getReferenceList = (props: TYPE_api_getReferenceList) => {
  const { url, method, mockData } = apis.chat_reference;
  const data = {
    sessionId: props.data.sessionId,
    queryId: props.data.queryId,
    name: props.data.name,
    type: props.data.type,
    content: props.data.content
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

interface TYPE_api_getHelperConfigList
  extends ServerBase<{ page: number | string; pageSize: number | string }> {}
export const api_getHelperConfigList = (
  props: TYPE_api_getHelperConfigList
) => {
  const { url, method, mockData } = apis.helper_list;
  const queryUrl = `${url}?pageNo=${props.data.page || 1}&pageSize=${props.data.pageSize || 999}`;
  const http = createAxiosInstance(props.config.url, props.config.token);
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method
  }).then((res) => res.data);
};

interface TYPE_api_feed_back
  extends ServerBase<{
    queryId: string | number | undefined;
    restult: number | undefined;
    ansPoor?: string;
    formatError?: string;
    harmfulInfo?: string;
    othres?: string;
  }> {}

export const api_feed_back = (props: TYPE_api_feed_back) => {
  const { url, method, mockData } = apis.feed_back;
  const queryUrl = `${url}`;
  const http = createAxiosInstance(props.config.url, props.config.token);
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  const data = {
    // queryId: props.data.queryId,
    // restult: props.data.restult,
    // ansPoor: props.data.ansPoor,
    // formatError: props.data.formatError,
    // harmfulInfo: props.data.harmfulInfo,
    // othres: props.data.othres,
    ...props.data
  };
  return http({
    url: queryUrl,
    method,
    data
  }).then((res) => res.data);
};

interface TYPE_api_getFeedbackList extends ServerBase<any> {}
export const api_getFeedbackList = (props: TYPE_api_getFeedbackList) => {
  const { url, method, mockData } = apis.feedback_list;
  const queryUrl = url;
  const http = createAxiosInstance(props.config.url, props.config.token);
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method
  }).then((respones) => respones.data);
};

interface TYPE_api_feedbackCancel extends ServerBase<any> {
  data: { queryId: string | number | undefined };
}
export const api_feedbackCancel = (props: TYPE_api_feedbackCancel) => {
  const { url, method, mockData } = apis.feedback_cancel;
  const queryUrl = `${url}?queryId=${props.data.queryId}`;
  const http = createAxiosInstance(props.config.url, props.config.token);
  if (props.config.enableMock) {
    mockApiResponse(http, method, queryUrl, mockData);
  }
  return http({
    url: queryUrl,
    method
  }).then((res) => res.data);
};
