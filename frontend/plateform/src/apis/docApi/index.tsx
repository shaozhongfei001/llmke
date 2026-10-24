import { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import _ from "lodash";
import { ApiConfig, HttpClient } from "./http-client";
import { message } from "antd";
import { baseURL } from "../common";
import { getTokenLocal } from "../token";

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
      config.baseURL = "/cecProxy";
      config.headers.Authorization = getTokenLocal();
      return config;
    }
  );
  return httpClientInstance;
}
