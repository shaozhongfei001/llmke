import { getUrlPrefix } from "../core/helps";
import { storeName } from "../storage/os/config";

export const token = () => {
  try {
    if (localStorage.getItem(storeName)) {
      const store = JSON.parse(localStorage.getItem(storeName) as string);
      if (store.userInfo && store.userInfo.token) {
        return store.userInfo.token;
      }
    }
  } catch (e) {
    console.log(e);
  }
};

export const UPLOAD_BASE_URL = `${getUrlPrefix()}/build`;
