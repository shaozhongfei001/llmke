import { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import _ from "lodash";
import { ApiConfig, HttpClient } from "./http-client";
import { message } from "antd";
import { baseURL } from "../common";
import { RAG_APP_NAME, RAG_AUTH_PLUGIN_PREFIX } from "@root/src/const";

export function useMyHttpClient(apiConfig?: ApiConfig) {
  const httpClientInstance = new HttpClient(apiConfig);
  httpClientInstance.instance.interceptors.response.use(
    (response: AxiosResponse) => {
      if (response.status === 200) {
        if (response.data?.success === false) {
          message.error(response.data?.errorMsg);
          response.data = false;
        }
        if (response.data?.error) {
          message.error((response.data?.error || {})?.message || "");
        }
      }
      return response?.data;
    },
    (error: AxiosError) => {
      const { response } = error;
      if (response) {
        if (response.status === 401) {
          window.location.pathname = "/login";
        }
        const _data = response.data || ({} as any);
        if (response.status && response.status === 500) {
          message.error(_data?.errorMsg || "请求出错，请稍后再试");
        } else {
          message.error("请求出错，请稍后再试");
        }
      } else {
        message.error("请求出错，请稍后再试");
      }
      return Promise.reject(error);
    }
  );

  httpClientInstance.instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      config.baseURL = baseURL + "/index";

      const userInfo_str =
        localStorage.getItem(`${RAG_AUTH_PLUGIN_PREFIX}${RAG_APP_NAME}`) || "";
      const data = JSON.parse(userInfo_str);
      if (data) {
        config.headers.Authorization = data.userInfo.token;
      }

      return config;
    }
  );
  return httpClientInstance;
}
