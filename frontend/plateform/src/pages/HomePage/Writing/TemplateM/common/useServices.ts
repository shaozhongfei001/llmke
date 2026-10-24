import { useMyHttpClient } from "@root/src/apis/docApi";
import { DocApi } from "@root/src/apis/docApi/DocApi";
import { Type知识库列表请求参数 } from "@root/src/apis/api/data-contracts";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ContentType } from "@/apis/docApi/http-client";
import axios$ from "@root/src/apis";

interface Iprops {
  pageNo?: number;
  search?: string;
  pageSize?: number;
  className?: string;
  forceRequest?: number;
  tempType?: "own" | "share";
}
export function useServices(props: Iprops) {
  const {
    search,
    className,
    pageNo = 1,
    pageSize = 30,
    forceRequest,
    tempType
  } = props;

  const api = new DocApi(useMyHttpClient());

  const queryTemplateList = useQuery({
    queryKey: [
      "listSimTemplateUsingGet",
      pageNo,
      search,
      forceRequest,
      className,
      tempType
    ],
    queryFn: () =>
      api
        .queryArticleTypeListUsingGet({
          pageSize,
          search,
          className,
          pageNo,
          scope: tempType
        })
        .then((res) => res),
    enabled: !!pageNo && !!className
  });

  const deleteTemplate = useMutation({
    mutationFn: (id: number) =>
      api.deleteArticleTypeUsingDelete(id).then((res) => res?.data)
  });

  const queryTemplateById = useMutation({
    mutationFn: (id: number) =>
      api.queryArticleTypeUsingGet(id).then((res) => res?.data)
  });

  const queryArticleTypeUsingGet = useMutation({
    mutationFn: (id: number | string) =>
      api.queryArticleTypeUsingGet(id as number).then((res) => res?.data)
  });

  const getSceneClass = useQuery({
    queryKey: ["sceneList", tempType],
    queryFn: () =>
      api
        .sceneClassUsingGet({
          query: { scope: tempType }
        })
        .then((res) => res),
    enabled: !!tempType
  });

  const getScecnVersionsById = async (id: string) => {
    const getVersion = (idx: number, len: number) => {
      const str = `000${idx - 1}`.slice(-len);
      const list = str.split("");
      if (list.length > 1) {
        list.splice(1, 0, ".");
      }
      return list.join("");
    };
    try {
      const res: any = await axios$.get(
        `/cecProxy/dw/articleType/${id}/version?pageNo=1&pageSize=9999`
      );
      const { success, data } = res;
      if (success) {
        const { details } = data;
        if (details) {
          const len = details.length.toString().length;
          const _details = (details || [])
            .map((i: any, idx: number) => ({
              ...i,
              version: getVersion(idx + 1, len)
            }))
            .sort((a: any, b: any) => b.versionId - a.versionId);
          console.log("version list:", _details);
          return _details;
        }
      }
      return false;
    } catch (e) {
      return false;
    }
  };

  const getVersionInfoById = useMutation({
    mutationFn: ({ id, versionId }: { id: number; versionId: number }) => {
      return api
        .queryArticleTypeByVersionIdUsingGet(id, versionId)
        .then((res) => res?.data);
    }
  });

  return {
    queryTemplateList,
    deleteTemplate,
    queryTemplateById,
    queryArticleTypeUsingGet,
    getSceneClass,
    getScecnVersionsById,
    getVersionInfoById
  };
}
