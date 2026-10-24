import { AxiosError, AxiosResponse } from "axios";
import { message } from "antd";
import { ApiConfig, HttpClient } from "./http-client";
import { SystemApi } from "./SystemApi";
import { baseURL } from "../common";
import { getTokenLocal } from "../token";

export * from "./data-contracts";

export function useSystemApi(apiConfig?: ApiConfig) {
  const httpClient = new HttpClient({
    ...apiConfig,
    baseURL: baseURL,
  });

  httpClient.instance.interceptors.response.use(
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

  httpClient.instance.interceptors.request.use((config: any) => {
    config.headers.Authorization = getTokenLocal();
    return config;
  });

  return new SystemApi(httpClient);
}

export default useSystemApi; 