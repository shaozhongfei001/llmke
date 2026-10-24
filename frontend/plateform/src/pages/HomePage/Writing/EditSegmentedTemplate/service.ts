import axios$ from "@root/src/apis";

export const useServices = () => {
  const getTableTree = () => {
    return axios$
      .get("/cecProxy/dw/dataSource/table/tree")
      .then((res) => res?.data);
  };

  const getTableDetail = (id: any) => {
    return axios$
      .get(`/cecProxy/dw/dataSource/table/${id}`)
      .then((res) => res?.data);
  };

  // 场景配置分析组件树
  const getSceneAnalysisTree = () => {
    return axios$
      .get(`/cecProxy/dw/component/analysis/category?full=true&canApply=true`)
      .then((res) => res?.data);
  };

  return { getTableTree, getTableDetail, getSceneAnalysisTree };
};
