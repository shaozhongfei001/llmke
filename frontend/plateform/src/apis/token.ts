import { RAG_APP_NAME, RAG_AUTH_PLUGIN_PREFIX } from "../const";

export const getTokenLocal = () => {
  const userInfo_str =
    localStorage.getItem(`${RAG_AUTH_PLUGIN_PREFIX}${RAG_APP_NAME}`) || "";
  const data = userInfo_str ? JSON.parse(userInfo_str) : "";
  if (data) {
    return data.userInfo.token;
  } else {
    if (window.location.pathname === "/login") return;
    window.location.pathname = "/login";
  }
};
