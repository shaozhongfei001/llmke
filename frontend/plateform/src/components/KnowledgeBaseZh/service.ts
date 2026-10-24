import { Api } from "@root/src/apis/api/Api";
import {
  Type创建知识库请求体,
  Type知识库更新请求体,
  Type修改文件启用禁用状态,
  Type文本解析请求参数体,
  Faq创建请求参数
} from "@/apis/api/data-contracts";
import { v4 as uuidv4 } from "uuid";
import { IDirList, IFileItemData, tabItems } from "@/const/knowledgebase";
import axios$ from "@root/src/apis";
import { useMyHttpClient } from "@root/src/apis/api/index.tsx";
import { getUrlPrefix } from "@root/src/core/helps";
const prefix = `${getUrlPrefix()}/index`;

export function useServices(platform: string = "rag-qa") {
  const api = new Api(useMyHttpClient());

  const createKb = (data: Type创建知识库请求体) => {
    return new Promise((resolve, reject) => {
      api
        .createKb(data, {
          headers: {
            "X-Platform": platform
          }
        })
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success && data) {
            resolve(data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const getKnowledgeList = (data: any) => {
    return new Promise((resolve, reject) => {
      api
        .list(
          { ...data },
          {
            headers: {
              "X-Platform": platform
            }
          }
        )
        .then((res: any) => {
          resolve(res.data);
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const getShareList = (data: any) => {
    return new Promise((resolve, reject) => {
      api
        .shareList(
          { ...data },
          {
            headers: {
              "X-Platform": platform
            }
          }
        )
        .then((res: any) => {
          resolve(res.data);
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  /**
   * @description delete knowledgebase
   * @param id
   * @returns
   */
  const deleteKbById = (id: number) => {
    return new Promise((resolve, reject) => {
      api
        .deleteById({ id })
        .then((res: any) => {
          resolve(res.data);
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const deleteFileById = (id: string) => {
    return new Promise((resolve, reject) => {
      api
        .delete1(
          { id: Number(id) },
          {
            headers: {
              "X-Platform": platform
            }
          }
        )
        .then((res: any) => {
          resolve(res.data);
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const deleteByIds = (fileIds: number[]) => {
    return new Promise((resolve, reject) => {
      api
        .deleteByIds({ fileIds })
        .then((res: any) => {
          resolve(res.data);
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const updateById = (params: Type知识库更新请求体) => {
    return new Promise((resolve, reject) => {
      api
        .update(params)
        .then((res: any) => {
          const { success, data, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg || "修改失败！");
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const updateEnable = (params: Type修改文件启用禁用状态) => {
    return new Promise((resolve, reject) => {
      api
        .updateEnable(params)
        .then((res: any) => {
          const { success, errorMsg } = res;
          if (success) {
            resolve(success);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const getParentList = (data: any) => {
    return new Promise((resolve, reject) => {
      api
        .parentList({ ...data })
        .then((res: any) => {
          const { success, errorMsg } = res;
          if (success) {
            resolve(res.data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const getFileList = (data: any) => {
    return new Promise((resolve, reject) => {
      api
        .list1({ ...data })
        .then((res: any) => {
          const { success, errorMsg } = res;
          if (success) {
            resolve(res.data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const getKbById = (data: any) => {
    return new Promise((resolve, reject) => {
      api
        .getKbById({ ...data })
        .then((res: any) => {
          const { success, errorMsg } = res;
          if (success) {
            resolve(res.data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const filesParse = (params: Type文本解析请求参数体) => {
    return new Promise((resolve, reject) => {
      api
        .filesParse(params)
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const abstractFaq = (params: Type文本解析请求参数体) => {
    return new Promise((resolve, reject) => {
      api
        .extractFqa(params)
        // .abstractFqa(params)
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const graphParse = (params: Type文本解析请求参数体) => {
    return new Promise((resolve, reject) => {
      api
        .graphParse(params)
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const getFileStatusById = (fileId: number) => {
    return new Promise((resolve, reject) => {
      api
        .getFileStatusById({ fileId })
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const getFaqExtractStatusById = (fileId: number) => {
    return new Promise((resolve, reject) => {
      api
        .getFaqExtractStatusById({ fileId })
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const getGraphParseStatusById = (fileId: number) => {
    // 获取图解析状态 1 未解析；2 解析中 3 解析成功 4 解析失败
    return new Promise((resolve, reject) => {
      api
        .getGraphParseStatus({ fileId })
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const filesReviseDate = (data: { fileId: number; reviseDate: string }) => {
    return new Promise((resolve, reject) => {
      api
        .filesReviseDate(data)
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const createFaq = (data: Faq创建请求参数) => {
    return new Promise((resolve, reject) => {
      api
        .create(data)
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg);
          }
        })
        .catch((e) => {
          const { message } = e;
          reject(message);
        });
    });
  };

  const mergeFolderData = () => {};

  const getFileSuffix = (fileName: string) => {
    const list = fileName.split(".");
    return list.length > 1 ? list[list.length - 1] : "";
  };

  const isDocParse = (type: string) => {
    return tabItems[0].key === type;
  };

  const getStatus = (fileListType: number, p: any) => {
    const _fileListType = +fileListType;
    const { status, faqExtractStatus, graphParseStatus } = p;
    switch (_fileListType) {
      case 1:
        return status;
      case 2:
        return status === 3 ? faqExtractStatus : status;
      case 3:
        return status === 3 ? graphParseStatus : status;
    }
  };

  const getFolderList = async (params: any) => {
    console.log("fileListType", params.fileListType);

    const { fileListType, kbId, folderId } = params;
    try {
      const res: any = await axios$.get(
        `${prefix}/knowledgeBase/file/folder/list?${new URLSearchParams(
          params
        ).toString()}`,
        {
          headers: {
            "X-Platform": platform
          }
        }
      );

      const { success, data } = res;
      if (success) {
        const { total, records } = data;
        const _list: IFileItemData[] = records.map((r: any) => {
          const {
            chunkSize,
            convertedFilePath,
            count,
            faqExtractStatus,
            fileName,
            // filePath,
            fileSize,
            fileType,
            folderId,
            folderName,
            id,
            isFolder,
            parentFileName,
            reviseDate,
            status,
            uploadTime,
            filePath,
            synLogs,
            nodeCount,
            edgeCount,
            graphParseStatus,
            pdfPage,
            permission,
            chunking,
            label
          } = r;

          const isDir = !!isFolder;
          const _status = getStatus(params.fileListType, {
            status,
            faqExtractStatus,
            graphParseStatus
          });
          return {
            id: uuidv4(),
            customId: isFolder ? `folder-${folderId}` : `file-${id}`,
            fileId: id,
            folderId,
            url: convertedFilePath,
            fileSize,
            isDir,
            hasParent: parentFileName,
            uploadTime,
            fileName,
            name: isDir ? folderName : fileName,
            type: isDir ? "folder" : getFileSuffix(fileName || ""),
            status: _status,
            chunkSize,
            parseType: fileType,
            reviseDate,
            count,
            filePath,
            synLogs,
            nodeCount,
            edgeCount,
            convertedFilePath,
            pdfPage,
            permission,
            needChunk: !!chunking,
            label
          };
        });
        const _res: IDirList = { limit: total, data: _list };

        return _res;
      }
      return false;
    } catch (e) {
      console.log("e", e);
      return false;
    }
  };

  const createFolder = (params: any) => {
    return new Promise((resolve, reject) => {
      axios$
        .post(`${prefix}/folder/save`, params)
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg || "创建失败，请联系管理员！");
          }
        })
        .catch((e) => {
          console.log("e", e);
          const { message } = e;
          reject(message);
        });
    });
  };

  const renameFolder = (params: any) => {
    return new Promise((resolve, reject) => {
      axios$
        .put(`${prefix}/folder/rename`, params)
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg || "重命名失败，请联系管理员！");
          }
        })
        .catch((e) => {
          console.log("e", e);
          const { message } = e;
          reject(message);
        });
    });
  };

  const deleteFolder = (id: string) => {
    return new Promise((resolve, reject) => {
      axios$
        .delete(`${prefix}/folder/delete?id=${id}`, {
          headers: {
            "X-Platform": platform
          }
        })
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg || "删除失败，请联系管理员！");
          }
        })
        .catch((e) => {
          console.log("e", e);
          const { message } = e;
          reject(message);
        });
    });
  };

  const getBizLabelList = async (params: any) => {
    try {
      const res: any = await axios$.get(
        `${prefix}/bizLabel/historyOfKbLabel?kbId=${params.id}`,
        {
          headers: {
            "X-Platform": platform
          }
        }
      );
      const { success, data } = res;
      if (success) {
        return data;
      }
      return false;
    } catch (e) {
      console.log("e", e);
      return false;
    }
  };

  const saveBizLabel = (params: any) => {
    return new Promise((resolve, reject) => {
      axios$
        .post(`${prefix}/bizLabel`, params)
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
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

  const getCountApi = (params: any) => {
    return new Promise((resolve, reject) => {
      axios$
        .get(
          `${prefix}/knowledgeBase/file/getSequenceCodeByFileId?fileId=${params.fileId}`
        )
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg || "获取失败，请联系管理员！");
          }
        })
        .catch((e) => {
          console.log("e", e);
          const { message } = e;
          reject(message);
        });
    });
  };

  const getBizLabelLabels = (params: any) => {
    return new Promise((resolve, reject) => {
      axios$
        .post(`${prefix}/bizLabel/labels`, params)
        .then((res: any) => {
          console.log("getBizLabelLabels", res);
          const { data, success, errorMsg } = res;

          if (success) {
            resolve(data);
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

  const getSynLog = (params: any) => {
    return new Promise((resolve, reject) => {
      axios$
        .get(
          `${prefix}/synLog/list?pageNo=1&pageSize=9999&fileId=${params.fileId}`
        )
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg || "获取失败，请联系管理员！");
          }
        })
        .catch((e) => {
          console.log("e", e);
          const { message } = e;
          reject(message);
        });
    });
  };

  return {
    getSynLog,
    batchTransferFolder,
    createKb,
    deleteKbById,
    deleteFileById,
    deleteByIds,
    updateById,
    updateEnable,
    filesParse,
    getFileStatusById,
    getFaqExtractStatusById,
    filesReviseDate,
    abstractFaq,
    getKnowledgeList,
    getShareList,
    getParentList,
    getFileList,
    getKbById,
    getFolderList,
    createFolder,
    renameFolder,
    deleteFolder,
    getGraphParseStatusById,
    graphParse,
    saveBizLabel,
    getBizLabelList,
    getBizLabelLabels,
    setFolderTransfer,
    getCountApi
  };
}
