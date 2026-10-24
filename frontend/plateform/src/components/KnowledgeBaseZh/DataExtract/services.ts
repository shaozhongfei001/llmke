import axios$ from "@root/src/apis";
import { getCecUrlPrefix } from "@root/src/core/helps";
import { useMutation, useQuery } from "@tanstack/react-query";

export const queryAllSelectOptsApi = ({ id, fileId }: any) => {
  return useQuery({
    queryKey: ["queryAllSelectOpts", id, fileId],
    queryFn: () =>
      axios$
        .get(`${getCecUrlPrefix()}/dw/knowledgeBase/${id}/indicator/options`, {
          params: {
            fileId
          }
        })
        .then((res) => res.data),
    enabled: !!id
  });
};

export const queryExtractResApi = ({
  id,
  fileId,
  companyName,
  tableName,
  year,
  periodType
}: any) => {
  return useQuery({
    queryKey: [
      "queryAllSelectOpts",
      id,
      fileId,
      companyName,
      tableName,
      year,
      periodType
    ],
    queryFn: () =>
      axios$
        .get(`${getCecUrlPrefix()}/dw/knowledgeBase/${id}/indicator`, {
          params: {
            fileId,
            companyName,
            categoryId: tableName,
            year,
            periodType
          }
        })
        .then((res) => res.data),
    enabled: !!id && !!companyName && !!tableName && !!year && !!periodType
  });
};

export const updateIndicatorValueApi = () => {
  return useMutation({
    mutationFn: ({ kbId, params }: any) => {
      return axios$
        .put(`${getCecUrlPrefix()}/dw/knowledgeBase/${kbId}/indicator/revise`, {
          ...params
        })
        .then((res) => {
          return res.data;
        });
    }
  });
};

/**
 *
 * @params private String companyName;
 * @params private String companyFullName;
 * @params private String year;
 * @params private String periodType;
 * @params private String dateType;0-期初，1-期末
 * @params private String indicatorName;
 * @params private String fixedValue;
 * @params private String indicatorUnit; 固定写死'元'
 * @params private String tableName;
 * @params private String knowledgeBaseName;
 */
export const addIndicatorValueApi = () => {
  return useMutation({
    mutationFn: ({ kbId, params }: any) => {
      return axios$
        .put(`${getCecUrlPrefix()}/dw/knowledgeBase/${kbId}/indicator/add`, {
          ...params
        })
        .then((res) => {
          return res.data;
        });
    }
  });
};
