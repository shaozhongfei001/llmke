import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";
const prefix = `${getUrlPrefix()}/graph`;

const getFileByPageNum = async (params: any) => {
  try {
    const p = new URLSearchParams(params).toString();
    const res: any = await axios$.get(`${prefix}/search/file/pageNum?${p}`);
    const { success, data } = res;
    if (success) {
      resInfo("getFileByPageNum", data);
      return data;
    } else {
      return false;
    }
  } catch (e) {
    console.log("getConfigEditStatus error", e);
  }
};

const resInfo = (name: string, res: any) => {
  console.log(`${name}---------->`, res);
};

export { getFileByPageNum };
