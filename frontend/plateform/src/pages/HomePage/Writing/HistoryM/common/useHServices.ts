import { version } from "@/const";
import { useMyHttpClient } from "@root/src/apis/docApi";
import { DocApi } from "@root/src/apis/docApi/DocApi";
import { Type知识库列表请求参数 } from "@root/src/apis/api/data-contracts";
import { useMutation, useQuery } from "@tanstack/react-query";
import axios$ from "@root/src/apis";

const prefix = "/cecProxy/dw";

const apiPath = {
  articleTask: "/articleTask"
};

const paramSerialize = (params: any) => {
  const list: Array<string> = [];
  Object.keys(params).forEach((key) => {
    if (params[key]) {
      list.push(`${key}=${params[key]}`);
    }
  });
  return list.length ? `?${list.join("&")}` : "";
};

interface Iprops {
  listParams?: Type知识库列表请求参数;
  search: string | undefined;
  pageNo?: number;
  taskDetailOpen?: boolean;
  taskState?: any;
}
export function useHServices(props: Iprops) {
  const { search, pageNo = 1, taskDetailOpen, taskState } = props;
  const api = new DocApi(useMyHttpClient());

  const queryArticleList = useQuery({
    queryKey: ["queryArticleList", pageNo, search, taskState],

    queryFn: () =>
      api
        .queryArticleListUsingGet({
          search: search,
          pageSize: 10,
          pageNo,
          taskState: taskState === "all" ? undefined : taskState
        })
        .then((res) => res.data),
    enabled: !!pageNo && !taskDetailOpen,
    refetchInterval: 10000 // 每10秒刷新一次
  });

  const deleteArticle = useMutation({
    mutationFn: (articleId: number) =>
      api.deleteArticleUsingPost({ articleId }).then((res) => res?.data)
  });

  const exportDoc = useMutation({
    mutationFn: ({ articleId, version }: any) => {
      const curVersion = version
        ? version === "odt"
          ? "odf"
          : version
        : "docx";
      return api
        .exportUsingGet(
          { articleId, offlineExport: true, version: curVersion },
          {
            type: "application/msword",
            format: "blob"
          }
        )
        .then((res) => {
          return res;
        });
    }
  });

  return {
    queryArticleList,
    deleteArticle,
    exportDoc
  };
}

// 获取任务历史列表
export const getTaskByArticleId = (params: any) => {
  return new Promise((resolve, reject) => {
    axios$
      .get(`${prefix}${apiPath.articleTask}${paramSerialize(params)}`)
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

// 获取任务详情
export const getTaskDetailById = (id: string | number) => {
  return new Promise((resolve, reject) => {
    axios$
      .get(`${prefix}${apiPath.articleTask}/${id}`)
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

// 取消任务
export const cancleTaskById = (id: string | number) => {
  return new Promise((resolve, reject) => {
    axios$
      .delete(`${prefix}${apiPath.articleTask}/${id}`)
      .then((res: any) => {
        const { success, errorMsg } = res;
        if (res && success) {
          resolve(res);
        } else {
          reject(errorMsg || false);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

// 暂停任务
export const pauseTaskByTaskId = (taskId: string | number) => {
  return new Promise((resolve, reject) => {
    axios$
      .put(`${prefix}${apiPath.articleTask}/${taskId}/pause`)
      .then((res: any) => {
        const { success, errorMsg } = res;
        if (res && success) {
          resolve(res);
        } else {
          reject(errorMsg || false);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

// 继续任务
export const resumeTaskByTaskId = (taskId: string | number) => {
  return new Promise((resolve, reject) => {
    axios$
      .put(`${prefix}${apiPath.articleTask}/${taskId}/resume`)
      .then((res: any) => {
        const { success, errorMsg } = res;
        if (res && success) {
          resolve(res);
        } else {
          reject(errorMsg || false);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

// 重试任务
export const retryTaskBySectionIds = ({
  taskId,
  sectionIds
}: {
  taskId: string | number;
  sectionIds?: string | undefined;
}) => {
  return new Promise((resolve, reject) => {
    axios$
      .put(
        `${prefix}${apiPath.articleTask}/${taskId}/retry${paramSerialize({
          sectionIds
        })}`
      )
      .then((res: any) => {
        const { success, errorMsg } = res;
        if (res && success) {
          resolve(res);
        } else {
          reject(errorMsg || false);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};
