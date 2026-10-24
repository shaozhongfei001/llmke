import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";

const prefix = `${getUrlPrefix()}/index`;

const api_allModelPage = async () => {
  try {
    const res: any = await axios$.get(
      `${prefix}/modelInfo/allPage?pageNo=1&pageSize=9999`
    );
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const api_modelInfo_create = async (params: any) => {
  try {
    const res: any = await axios$.post(`${prefix}/modelInfo/create`, params);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

export { api_allModelPage, api_modelInfo_create };

const resInfo = (name: string, res: any) => {
  console.log(`${name}---------->`, res);
};
