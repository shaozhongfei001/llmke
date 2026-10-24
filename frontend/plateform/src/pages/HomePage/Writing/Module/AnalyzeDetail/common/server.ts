import axios$ from "@root/src/apis";
import { useMutation } from "@tanstack/react-query";
import { IAnalyzeDetail } from "..";
const reqPrefix = "cecProxy";

export const useServices = () => {
  const getAnalysisDetail = (id: string | number) =>
    axios$
      .get(`/${reqPrefix}/dw/component/analysis/${id}`)
      .then((res) => res?.data);

  const updateAnalyzer = useMutation({
    mutationFn: (data: IAnalyzeDetail & { id: string | number }) =>
      axios$
        .put("/cecProxy/dw/component/analysis/" + data.id, {
          ...data
        })
        .then((res) => res)
  });

  const queryIndicator = useMutation({
    mutationFn: (search: string) =>
      axios$
        .get(`/cecProxy/dw/indicator`, { params: { search } })
        .then((res) => res?.data)
  });

  return {
    getAnalysisDetail,
    updateAnalyzer,
    queryIndicator
  };
};
