import { useMyHttpClient } from "@root/src/apis/docApi";
import { DocApi } from "@root/src/apis/docApi/DocApi";
import { Type知识库列表请求参数 } from "@root/src/apis/api/data-contracts";
import { useMutation, useQuery } from "@tanstack/react-query";

interface Iprops {
  pageNo: number;
  pageSize: number;
  search: undefined | string;
  fuzzyNameOrId?: string;
  forceRequest?: number;
  taskIds?: string;
  bizType?: string;
  scene: string;
  articleStyle: string;
}
export function useHServices(props: Iprops) {
  const {
    search,
    pageNo,
    pageSize,
    forceRequest,
    taskIds,
    bizType,
    scene,
    articleStyle
  } = props;
  const api = new DocApi(useMyHttpClient());

  const getMaterialList = useQuery({
    queryKey: [
      "queryArticleMaterial",
      pageNo,
      search,
      forceRequest,
      bizType,
      scene,
      articleStyle
    ],
    queryFn: () =>
      api
        .listUsingGet({
          pageSize: pageSize,
          fileName: search,
          bizType,
          scene,
          articleStyle,
          pageNo
        })
        .then((res) => res),
    enabled: !!pageNo
  });

  const getAnalysisIdsProcess = useQuery({
    queryKey: ["getAnalysisIdsProcess ", taskIds],
    queryFn: () =>
      api
        .listUsingGet({
          id: taskIds
        })
        .then((res) => res),
    enabled: !!taskIds,
    refetchInterval: 10 * 1000
  });

  const deleteMaterial = useMutation({
    mutationFn: (id: number) => api.deleteByIdUsingDelete(id).then((res) => res)
  });

  const queryMaterial = useMutation({
    mutationFn: (id: number) =>
      api.queryArticleMaterialByIdUsingGet(id).then((res) => res?.data)
  });

  const retryParseMaterial = useMutation({
    mutationFn: (id: number) =>
      api.retryParseMaterialUsingPost(id).then((res) => res?.data)
  });

  return {
    getMaterialList,
    deleteMaterial,
    queryMaterial,
    getAnalysisIdsProcess,
    retryParseMaterial
  };
}
