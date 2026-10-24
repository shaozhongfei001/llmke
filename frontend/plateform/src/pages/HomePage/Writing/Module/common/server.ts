import axios$ from "@root/src/apis";
import { useMutation } from "@tanstack/react-query";
import { ISection, IAnalysis, IAnalysisCategoryTreeItem } from "./type";

export const useServices = () => {
  // 章节组件分类相关api
  const getChapterTree = useMutation({
    mutationFn: (search?: string) =>
      axios$
        .get(
          `/cecProxy/dw/component/section/tree${
            search ? "?search=" + search : ""
          }`
        )
        .then((res) => res?.data)
  });

  const addChapter = useMutation({
    mutationFn: (data: { parentId: number; sectionTitle: string }) =>
      axios$
        .post("/cecProxy/dw/component/section", data)
        .then((res) => res.data)
  });

  const deleteChapter = useMutation({
    mutationFn: (id: any) =>
      axios$.delete("/cecProxy/dw/component/section/" + id).then((res) => res)
  });
  const updateChanpter = useMutation({
    mutationFn: (data: ISection & { id: any }) =>
      axios$
        .put("/cecProxy/dw/component/section/" + data.id, {
          ...data
        })
        .then((res) => res)
  });

  const getChapterById = useMutation({
    mutationFn: (id: any) =>
      axios$
        .get("/cecProxy/dw/component/section/" + id)
        .then((res) => res?.data)
  });

  const copyChapter = useMutation({
    mutationFn: (id: any) =>
      axios$
        .post(`/cecProxy/dw/component/section/${id}/copy`)
        .then((res) => res)
  });

  const testChapter = useMutation({
    mutationFn: (id: any) =>
      axios$
        .post(`/cecProxy/dw/component/section/${id}/test`)
        .then((res) => res?.data)
  });

  const moveChapter = useMutation({
    mutationFn: ({ id, newParentId, prevId, nextId }: any) =>
      axios$
        .post(`/cecProxy/dw/component/section/${id}/move`, {
          newParentId,
          prevId,
          nextId
        })
        .then((res) => res?.data)
  });

  // 分析组件分类相关api
  const getAnalysisCategoryTree = useMutation({
    mutationFn: (search?: string) =>
      axios$
        .get(
          `/cecProxy/dw/component/analysis/category${
            search ? `?search=${search}` : ""
          }`
        )
        .then((res) => res?.data)
  });

  const addAnalysisCategory = useMutation({
    mutationFn: (data: { parentId: string; categoryName: string }) =>
      axios$
        .post("/cecProxy/dw/component/analysis/category", data)
        .then((res) => res?.data)
  });

  const deleteAnalysisCategory = useMutation({
    mutationFn: (data: { id: any; deleteComponent: boolean }) =>
      axios$
        .delete(
          "/cecProxy/dw/component/analysis/category/" +
            data.id +
            `?deleteComponent=${data.deleteComponent}`
        )
        .then((res) => res)
  });

  const updateAnalysisCategory = useMutation({
    mutationFn: (data: IAnalysisCategoryTreeItem) =>
      axios$
        .put("/cecProxy/dw/component/analysis/category/" + data.id, {
          ...data
        })
        .then((res) => res)
  });

  const getAnalysisCategoryById = useMutation({
    mutationFn: (id: string) =>
      axios$
        .get("/cecProxy/dw/component/analysis/category/" + id)
        .then((res) => res?.data)
  });

  // 分析组件相关api
  const getAnalysisList = useMutation({
    mutationFn: (data: { id?: string; search?: string }) => {
      let url: string = `/cecProxy/dw/component/analysis`;
      if (data?.id) {
        url = `/cecProxy/dw/component/analysis?categoryId=${data.id}`;
      }
      if (data?.search) {
        url = `/cecProxy/dw/component/analysis?search=${data.search}`;
      }
      return axios$.get(url).then((res) => res?.data);
    }
  });

  const addAnalysis = useMutation({
    mutationFn: (data: { categoryId: string; name: string }) =>
      axios$
        .post("/cecProxy/dw/component/analysis", data)
        .then((res) => res?.data)
  });

  const deleteAnalysis = useMutation({
    mutationFn: (id: any) =>
      axios$.delete("/cecProxy/dw/component/analysis/" + id).then((res) => res)
  });

  const updateAnalysis = useMutation({
    mutationFn: (data: IAnalysis & { id: any }) =>
      axios$
        .put("/cecProxy/dw/component/analysis/" + data.id, {
          ...data
        })
        .then((res) => res)
  });

  const getAnalysisById = useMutation({
    mutationFn: (id: any) =>
      axios$
        .get("/cecProxy/dw/component/analysis/" + id)
        .then((res) => res?.data)
  });

  const copyAnalysis = useMutation({
    mutationFn: (id: any) =>
      axios$
        .post(`/cecProxy/dw/component/analysis/${id}/copy`)
        .then((res) => res)
  });

  const testAnalysis = useMutation({
    mutationFn: (id: any) =>
      axios$
        .post(`/cecProxy/dw/component/analysis/${id}/test`)
        .then((res) => res?.data)
  });

  return {
    getChapterTree,
    addChapter,
    deleteChapter,
    updateChanpter,
    getChapterById,
    copyChapter,
    testChapter,
    moveChapter,
    getAnalysisList,
    addAnalysis,
    deleteAnalysis,
    updateAnalysis,
    getAnalysisById,
    copyAnalysis,
    testAnalysis,
    getAnalysisCategoryTree,
    addAnalysisCategory,
    deleteAnalysisCategory,
    updateAnalysisCategory,
    getAnalysisCategoryById
  };
};
