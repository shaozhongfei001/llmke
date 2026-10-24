import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";

const prefix = `${getUrlPrefix()}/index`;
const prefix2 = `${getUrlPrefix()}/graph`;

const getFaqFileList = async (params: any) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/knowledgeBase/file/list?${new URLSearchParams(
        params
      ).toString()}`
    );
    resInfo("getFaqFileList", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const getCecAllFileList = async (params: any) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/knowledgeBase/file/flatList?${new URLSearchParams(
        params
      ).toString()}`
    );
    resInfo("getFileList", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const deleteFaqFileById = async (ids: string) => {
  try {
    const res: any = await axios$.delete(
      `${prefix}/knowledgeBase/file/deleteByIds?fileIds=${ids}`
    );
    resInfo("deleteFaqFileByIds", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const faqDownloadTemplate = async (params: any) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/faq/downloadTemplate?${new URLSearchParams(params).toString()}`
    );
    resInfo("faqDownloadTemplate", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const getFaqList = async (params: any) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/faq/list?${new URLSearchParams(params).toString()}`
    );
    resInfo("getFaqList", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const faqParse = async (params: any) => {
  try {
    const res: any = await axios$.post(
      `${prefix}/knowledgeBase/file/extractFQA`,
      params
    );
    resInfo("faqParse", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const saveFaq = async (params: any) => {
  try {
    const res: any = await axios$.post(`${prefix}/faq/saveOrUpdate`, params);
    resInfo("createFaq", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const deleteFaq = async (params: any) => {
  try {
    const res: any = await axios$.post(`${prefix}/faq/delete`, params);
    resInfo("deleteFaq", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const deleteAll = async (params: any) => {
  try {
    const res: any = await axios$.put(`${prefix}/faq/deleteAll`, params);
    resInfo("deleteAll", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const addSimilarQuestion = async (params: any) => {
  try {
    const res: any = await axios$.post(
      `${prefix}/faq/similarQuestion/add`,
      params
    );
    resInfo("addSimilarQuestion", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

//
const getFAQExtractStatusById = async (params: any) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/knowledgeBase/file/getFAQExtractStatusById?${new URLSearchParams(
        params
      ).toString()}`
    );
    resInfo("getFAQExtractStatusById", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const downLoadTemplate = async (fileType: string) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/faq/downloadTemplate?fileType=${fileType}`
    );
    resInfo("downLoadTemplate", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const createFaq = async (params: any) => {
  try {
    const res: any = await axios$.post(`${prefix}/faq/create`, params);
    resInfo("createFaq", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const updateFaq = async (params: any) => {
  try {
    const res: any = await axios$.put(`${prefix}/faq/update`, params);
    resInfo("createFaq", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const changeStatus = (params: any) => {
  return new Promise((resolve, reject) => {
    axios$
      .put(`${prefix}/faq/changeStatus`, params)
      .then((res: any) => {
        resInfo("changeStatus", res);
        const { data, success, errorMsg } = res;
        if (success) {
          resolve({
            data,
            success
          });
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        console.log("e", e);
        const { message } = e;
        reject(message);
      });
  });
};

const changeAllStatus = (params: any) => {
  return new Promise((resolve, reject) => {
    axios$
      .put(`${prefix}/faq/changeAllStatus`, params)
      .then((res: any) => {
        resInfo("changeAllStatus", res);
        const { data, success, errorMsg } = res;
        if (success) {
          resolve({
            data,
            success
          });
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        console.log("e", e);
        const { message } = e;
        reject(message);
      });
  });
};

const similarQuestionEdit = (params: any) => {
  return new Promise((resolve, reject) => {
    axios$
      .put(`${prefix}/faq/update`, params)
      .then((res: any) => {
        resInfo("similarQuestionEdit", res);
        const { data, success, errorMsg } = res;
        if (success) {
          resolve({
            data,
            success
          });
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        console.log("e", e);
        const { message } = e;
        reject(message);
      });
  });
};

const repeatCheck = async (kbId: any) => {
  try {
    const res: any = await axios$.get(`${prefix}/faq/repeatCheck?kbId=${kbId}`);
    resInfo("repeatCheck", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const generateSimilarQuestion = (params: any) => {
  return new Promise((resolve, reject) => {
    axios$
      .put(`${prefix}/faq/gen/similarQuestion`, params)
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        resInfo("generateSimilarQuestion", data);
        if (success) {
          resolve({
            data,
            success
          });
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        console.log("e", e);
        const { message } = e;
        reject(message);
      });
  });
};

const deleteFaqSimilarQuestion = async (params: any) => {
  try {
    const res: any = await axios$.delete(
      `${prefix}/faq/similarQuestion/delete`,
      { data: params }
    );

    const { success, data } = res;
    resInfo("deleteFaqSimilarQuestion", data);
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};
const deleteFaqSimilarByPks = async (params: any) => {
  try {
    const res: any = await axios$.delete(`${prefix}/faq/deleteByPks`, {
      data: params
    });

    const { success, data } = res;
    resInfo("deleteFaqSimilarByPks", data);
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const getKbById = async (id: any, cb?: () => void) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/knowledgeBase/getKbById?id=${id}`
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
      `${prefix}/knowledgeBase/file/getById?id=${id}`
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
      `${prefix}/knowledgeBase/file/reExtractFQA`,
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
    const res: any = await axios$.post(`${prefix}/faq/polish`, params);
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
      `${prefix}/faq/getFaqByRelatedPk?kbId=${params.kbId}&relatedPks=${params.relatedPk}`
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

const getWholeGraphSearch = async (params: any, cb?: () => void) => {
  try {
    const res: any = await axios$.post(
      `${prefix2}/search/wholeGraphSearch`,
      params
    );
    const { success, data } = res;
    resInfo("getWholeGraphSearch", data);
    cb && cb();
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb();
    return false;
  }
};
const setFolderTransfer = (params: {
  targetFolderId: number;
  targetId: number;
  bizType: number;
  kbName: string;
}) => {
  return new Promise((resolve, reject) => {
    axios$
      .post(`${prefix}/folder/transfer`, params)
      .then((res: any) => {
        console.log("setFolderTransfer", res);
        const { data, success, errorMsg } = res;

        if (success) {
          resolve(res);
        } else {
          reject(errorMsg || "保存失败，请联系管理员！");
        }
      })
      .catch((e) => {
        console.log("e", e);
        const { message } = e;
        reject(message);
      });
  });
};

const batchTransferFolder = (params: {
  targetFolderId: number;
  target: any[];
}) => {
  return new Promise((resolve, reject) => {
    axios$
      .post(`${prefix}/folder/transferBatch`, params)
      .then((res: any) => {
        console.log("batchTransferFolder", res);
        const { data, success, errorMsg } = res;

        if (success) {
          resolve(res);
        } else {
          reject(errorMsg || "保存失败，请联系管理员！");
        }
      })
      .catch((e) => {
        console.log("e", e);
        const { message } = e;
        reject(message);
      });
  });
};

const deleteFaqFolder = async (params: {
  kbId: number;
  fileIds?: number[];
  folderIds?: number[];
}) => {
  try {
    const res: any = await axios$.put(`${prefix}/faq/deleteFaq`, params);
    resInfo("deleteFaqFolder", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};
export {
  deleteFaqFolder,
  batchTransferFolder,
  setFolderTransfer,
  getWholeGraphSearch,
  deleteFaqSimilarQuestion,
  getFaqFileList,
  deleteFaqFileById,
  faqDownloadTemplate,
  getFaqList,
  faqParse,
  saveFaq,
  deleteFaq,
  deleteAll,
  getFAQExtractStatusById,
  downLoadTemplate,
  createFaq,
  updateFaq,
  addSimilarQuestion,
  changeStatus,
  changeAllStatus,
  repeatCheck,
  similarQuestionEdit,
  generateSimilarQuestion,
  faqPolish,
  filegetById,
  getKbById,
  reExtractFAQ,
  getCecAllFileList,
  deleteFaqSimilarByPks
};

const resInfo = (name: string, res: any) => {
  console.log(`${name}---------->`, res);
};
