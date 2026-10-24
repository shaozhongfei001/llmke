import {
  ArticleTypeCreateRequest,
  ArticleTypeSaveRequest
} from "../../../../../apis/docApi/data-contracts";
import { useMyHttpClient } from "@root/src/apis/docApi";
import { DocApi } from "@root/src/apis/docApi/DocApi";
import { Type知识库列表请求参数 } from "@root/src/apis/api/data-contracts";
import { useMutation, useQuery } from "@tanstack/react-query";

interface Iprops {
  listParams?: Type知识库列表请求参数;
}
export function useTServices(props: Iprops) {
  const api = new DocApi(useMyHttpClient());

  // const queryArticleTypeList = useQuery({
  //   queryKey: ["queryArticleTypeListUsingGet"],
  //   queryFn: () => api.queryArticleTypeListUsingGet().then((res) => res)
  // });

  const deleteArticle = useMutation({
    mutationFn: (articleId: number) =>
      api.deleteArticleUsingPost({ articleId }).then((res) => res?.data)
  });

  const createArticleType = useMutation({
    mutationFn: (data: ArticleTypeCreateRequest) =>
      api.createArticleTypeUsingPost(data).then((res) => res)
  });

  const updateArticleType = useMutation({
    mutationFn: (data: any) =>
      api.saveArticleTypeUsingPut(data.id, data).then((res) => res)
  });

  const getSceneClass = useMutation({
    mutationFn: () => api.sceneClassUsingGet().then((res) => res.data)
  });

  return {
    // queryArticleTypeList,
    deleteArticle,
    createArticleType,
    updateArticleType,
    getSceneClass
  };
}
