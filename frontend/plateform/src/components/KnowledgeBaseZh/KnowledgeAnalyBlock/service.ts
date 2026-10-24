import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";
import axios from "axios";
import chardet from "chardet";
const prefix2 = `${getUrlPrefix()}/index`;

const deleteChunk = async (params: any, cb?: (arg?: any) => void) => {
  try {
    const res: any = await axios$.delete(
      `${prefix2}/knowledgeBase/file/deleteChunks`,
      { data: params }
    );
    const { success, data } = res;
    resInfo("deleteChunk", res);

    if (success) {
      cb && cb(data);
      return data;
    }
    cb && cb(false);
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb(false);
    return false;
  }
};

const updateChunk = async (params: any, cb?: (arg?: any) => void) => {
  try {
    const res: any = await axios$.put(
      `${prefix2}/knowledgeBase/file/updateChunk`,
      params
    );
    const { success, data } = res;
    resInfo("updateChunk", res);

    if (success) {
      cb && cb(data);
      return data;
    }
    cb && cb(false);
    return false;
  } catch (e) {
    console.log("e", e);
    cb && cb(false);
    return false;
  }
};

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

const getConfigEditStatus = async (id: string) => {
  try {
    const res: any = await axios$.get(
      `${prefix2}/knowledgeBase/canUpdateConf?id=${id}`
    );
    const { success, data } = res;
    if (success) {
      return data;
    } else {
      return false;
    }
  } catch (e) {
    console.log("getConfigEditStatus error", e);
  }
};

const getFileChunks = ({
  docId,
  kbId,
  pageNo,
  pageSize
}: {
  docId: string | number;
  kbId: string | number;
  pageNo: number;
  pageSize: number;
}) => {
  return axios$
    .get(
      `${prefix2}/knowledgeBase/file/getFileChunks?docId=${docId}&kbId=${kbId}`,
      {
        params: {
          pageNo: String(pageNo),
          pageSize: String(pageSize)
        }
      }
    )
    .then((res) => res.data);
};

const resInfo = (name: string, res: any) => {
  console.log(`${name}---------->`, res);
};

const getDocByurl = async (url: string) => {
  const response = await fetch(url, {});
  const arrayBuffer = await response.arrayBuffer();
  const detectedEncoding = chardet.detect(new Uint8Array(arrayBuffer));
  const text = detectedEncoding
    ? new TextDecoder(detectedEncoding).decode(arrayBuffer)
    : "";
  return text;
};

const getEmbeddingModels = async () => {
  const params: any = {
    pageNum: 1,
    pageSize: 9999,
    status: 1,
    type: 2
  };
  try {
    const res: any = await axios$.get(
      `${prefix2}/modelInfo/allPage?${new URLSearchParams(params).toString()}`
    );
    const { success, data } = res;
    if (success) {
      console.log("getEmbeddingModels", data);

      return data;
    } else {
      return false;
    }
  } catch (e) {
    console.log("getEmbeddingModels error", e);
  }
};

const getModels = async () => {
  const params: any = {
    pageNum: 1,
    pageSize: 9999,
    status: 1,
    type: 1
  };
  try {
    const res: any = await axios$.get(
      `${prefix2}/modelInfo/allPage?${new URLSearchParams(params).toString()}`
    );
    const { success, data } = res;
    if (success) {
      console.log("getModels", data);

      return data;
    } else {
      return false;
    }
  } catch (e) {
    console.log("getModels error", e);
  }
};
const getMultiModels = async () => {
  const params: any = {
    pageNum: 1,
    pageSize: 9999,
    status: 1,
    type: 4
  };
  try {
    const res: any = await axios$.get(
      `${prefix2}/modelInfo/allPage?${new URLSearchParams(params).toString()}`
    );
    const { success, data } = res;
    if (success) {
      console.log("getMultiModels", data);
      return data;
    } else {
      return false;
    }
  } catch (e) {
    console.log("getMultiModels error", e);
  }
};

const getParseTypes = async () => {
  try {
    const res: any = await axios$.post(
      `${prefix2}/knowledgeBase/getParseTypes`
    );
    const { success, data } = res;
    if (success) {
      console.log("getParseTypes", data);

      return data;
    } else {
      return false;
    }
  } catch (e) {
    console.log("getParseTypes error", e);
  }
};

export {
  getParseTypes,
  getEmbeddingModels,
  getModels,
  getMultiModels,
  getKbById,
  getFileChunks,
  getDocByurl,
  getConfigEditStatus,
  updateChunk,
  deleteChunk
};
