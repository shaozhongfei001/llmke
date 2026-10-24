import { ContentType } from "@/apis/docApi/http-client";
import { useMyHttpClient } from "@root/src/apis/docApi/";
import { DocApi } from "@root/src/apis/docApi/DocApi";
import { useMutation, useQuery } from "@tanstack/react-query";

export function useServices() {
  const api = new DocApi(useMyHttpClient());

  const getDocList = useQuery({
    queryKey: ["getDocList"],
    queryFn: () =>
      api
        .queryArticleListUsingGet({
          pageSize: 6,
          pageNo: 1
        })
        .then((res: any) => res),
    retry: 0
  });

  const getTemplateList = useQuery({
    queryKey: ["listSimTemplateUsingGet"],
    queryFn: () =>
      api
        .queryArticleTypeListUsingGet({
          pageSize: 999,
          pageNo: 1
        })
        .then((res) => res),
    retry: 0
  });

  const queryArticleTypeUsingGet = useMutation({
    mutationFn: (id: number | string) =>
      api.queryArticleTypeUsingGet(id as number).then((res) => res?.data)
  });

  const deleteTemplate = useMutation({
    mutationFn: (id: number) =>
      api.deleteArticleTypeUsingDelete(id).then((res) => res?.data)
  });

  const getSceneClass = useQuery({
    queryKey: ["sceneList"],
    queryFn: () => api.sceneClassUsingGet().then((res) => res)
  });

  return {
    getDocList,
    getTemplateList,
    queryArticleTypeUsingGet,
    deleteTemplate,
    getSceneClass
  };
}
