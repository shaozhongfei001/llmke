import { AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { token } from "./config";
import { message } from "antd";
import { getUrlPrefix } from "../core/helps";
export const baseURL = getUrlPrefix();
export const handleRequest = () => {
  return (config: InternalAxiosRequestConfig) => {
    if (config.url === "/author/userInfo/updateHeaderPic") {
      config.headers["Content-Type"] = "multipart/form-data";
    }

    if (config.url === "/author/userInfo/kaptcha") {
      config.responseType = "arraybuffer";
      config.url = `${config.url}?${Math.random()}`;
    }
    if (config.url !== "/author/userInfo/getMenus") {
      config.headers.Authorization = token();
    }

    if (
      config.url === "/author/userInfo/login/oss" &&
      config.headers.Authorization
    ) {
      delete config.headers.Authorization;
    }
    return config;
  };
};

export const handleResponseError = () => {
  return (error: any) => {
    if (
      error?.response?.data?.errorCode === "30013" ||
      error?.response?.data?.errorCode === "30023"
    ) {
      message.error(
        (error?.response?.data || {}).errorMsg || "请求出错，请稍后再试"
      );
      location.pathname = "/login";
      return;
    }
    if (error.response && error.response.status === 401) {
      // 这里处理 401 错误。例如，可以重定向到登录页面。
      console.error("用户权限已经过期或者未登陆");
      // 重定向到登录
      // if((error.response.data?.data || {}).isFromOss){
      //   window.location.href = import.meta.env.VITE_YUANQI_URL
      // }else{
      //   window.location.href = '/login'
      // }
      // if (import.meta.env.VITE_APP_MODE === 'dev') {
      //   window.location.href = '/login'
      // } else {
      //   window.location.href = '/jumpprompt'
      // }
      window.location.href = "/login";
    }
    // 如果你想继续抛出错误以供其他 catch 块捕获，可以这样做：
    return Promise.reject(error);
  };
};

export const handleResponse = () => {
  return (response: AxiosResponse) => {
    return response;
  };
};
