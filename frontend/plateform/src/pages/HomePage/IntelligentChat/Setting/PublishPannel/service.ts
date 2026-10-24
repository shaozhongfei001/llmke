import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";

const prefix = `${getUrlPrefix()}/qa`;

const getApiKeys = async (params: any, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/apiKey?pageNo=${params.pageNo}&pageSize=${params.pageSize}&targetId=${params.targetId}`
    );
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.error("e", e);
    return false;
  }
};

const createKey = async (params: any) => {
  try {
    const res: any = await axios$.post(`${prefix}/apiKey`, params);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.error("e", e);
    return false;
  }
};

const deleteKey = async (id: string) => {
  try {
    const res: any = await axios$.delete(`${prefix}/apiKey/${id}`);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.error("e", e);
    return false;
  }
};

export { getApiKeys, createKey, deleteKey };
