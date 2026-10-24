import { message } from "antd";
import axios from "axios";
import { RAG_APP_NAME, RAG_AUTH_PLUGIN_PREFIX } from "../const";
import { getTokenLocal } from "./token";

const specialErrorCodes = ["10014"];

// 创建一个独立的axios实例
const axios$ = axios.create({
  baseURL: "",
  // 配置请求超时时间
  timeout: 1000000
});
// 请求拦截
axios$.interceptors.request.use((config: any) => {
  let target_cookie = getTokenLocal();
  const noA = [
    "user/login",
    "user/kaptcha",
    "user/regist",
    "auth/userSecurityQuestion/findByUserName",
    "auth/kaptcha/kaptchaSix",
    "auth/userSecurityQuestion/validateSecurityQuestion",
    "auth/userSecurityQuestion/updatePasswordByQuestion"
  ];
  // dangerous behaviour
  if (
    !target_cookie &&
    !noA.some((item: string) => config.url.includes(item))
  ) {
    window.location.pathname = "/login";
    return;
  }

  const userInfo: any = getLocalUserInfo();

  // console.log(
  //   "Request Headers: ",
  //   userInfo.userInfo.userName,
  //   userInfo.userInfo.id
  // );
  config.headers.Authorization = target_cookie || "";
  // 这里传中文会报错
  config.headers.userName =
    userInfo.userInfo.userName === "未登录用户"
      ? ""
      : userInfo.userInfo.userName;
  config.headers.userId = userInfo.userInfo.id;
  return config;
});
// 返回拦截
axios$.interceptors.response.use(
  (response) => {
    if (
      response.config.url?.includes("/proxy/index/knowledgeBase/file/stream")
    ) {
      return response;
    }
    // 获取接口返回结果
    const noA = ["user/kaptcha", "auth/kaptcha/kaptchaSix"];
    const res = response.data;
    if (
      noA.some(
        (item: string) =>
          response.config.url && response.config.url.includes(item)
      )
    ) {
      return res;
    }
    if (res.size && res.type) {
      return res;
    }
    const { success, errorMsg, errorCode } = res;
    // 处理特殊错误码的情况,页面自己处理错误，例如上传文件重复
    if (specialErrorCodes.includes(errorCode)) {
      return res;
    }
    if (success) {
      if (res.data === null || res.data === undefined) {
        return { ...res, data: res.data ? res.data : res.success };
      } else {
        return { ...res, data: res.data };
      }
    }
    message.error(errorMsg || "请求出错，请稍后再试");
    return false;
  },
  (error) => {
    // 主动取消请求，不给报错信息
    if (error.message === "canceled") {
      return;
    }
    if (
      error?.response?.data?.errorCode === "30013" ||
      error?.response?.data?.errorCode === "30023"
    ) {
      message.error(
        (error?.response?.data || {}).errorMsg || "请求出错，请稍后再试"
      );
      location.pathname = "/login";
    }
    if (error?.response?.status === 401) {
      console.log("Error url:", error?.request?.responseURL);
      message.error((error?.response?.data || {}).errorMsg || "没有足够权限");
      return;
      //window.location.pathname = "/login";
    }
    console.log("Error occurs", error);
    if ("未设置默认配置！" != (error?.response?.data || {}).errorMsg) {
      message.error(
        (error?.response?.data || {}).errorMsg || "请求出错，请稍后再试"
      );
    }
  }
);

export default axios$;

export const getLocalUserInfo = () => {
  const userInfo_str = localStorage.getItem(
    `${RAG_AUTH_PLUGIN_PREFIX}${RAG_APP_NAME}`
  );
  let userInfo: any = {};
  if (userInfo_str) {
    userInfo = JSON.parse(userInfo_str);
  }
  return userInfo;
};
