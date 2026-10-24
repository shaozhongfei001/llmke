import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";

const prefix2 = `${getUrlPrefix()}/index`;

const getKbById = async (id: any, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `${prefix2}/knowledgeBase/getKbById?id=${id}`
    );
    const { success, data } = res;
    resInfo("getGroupUserList", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const filegetById = async (id: any, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `${prefix2}/knowledgeBase/file/getById?id=${id}`
    );
    const { success, data } = res;
    resInfo("FilegetById", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const reExtractFAQ = async (params: any, cb?: () => void) => {
  try {
    const res: any = await axios$.post(
      `${prefix2}/knowledgeBase/file/reExtractFQA`,
      params
    );
    const { success, data } = res;
    resInfo("reExtractFAQ", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const faqPolish = async (params: any, cb?: () => void) => {
  try {
    const res: any = await axios$.post(`${prefix2}/faq/polish`, params);
    const { success, data } = res;
    resInfo("faqPolish", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const getFaqByRelatedPk = async (params: any, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `${prefix2}/faq/getFaqByRelatedPk?kbId=${params.kbId}&relatedPks=${params.relatedPk}`
    );
    const { success, data } = res;
    resInfo("getFaqByRelatedPk", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};

const resInfo = (name: string, res: any) => {
  console.log(`${name}---------->`, res);
};

export { getKbById, filegetById, reExtractFAQ, faqPolish, getFaqByRelatedPk };
