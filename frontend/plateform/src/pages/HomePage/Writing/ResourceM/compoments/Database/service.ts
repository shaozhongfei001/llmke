import axios$ from "@root/src/apis";
import { useMutation } from "@tanstack/react-query";

export const useServices = () => {
  const getOnlineDb = useMutation({
    mutationFn: (data: any) =>
      axios$
        .post("/cecProxy/dw/dataSource/online/db", data)
        .then((res) => res?.data)
  });
  const getOnlineDbTables = useMutation({
    mutationFn: (data: any) =>
      axios$
        .post("/cecProxy/dw/dataSource/online/table", data)
        .then((res) => res?.data)
  });
  const createDb = useMutation({
    mutationFn: (data: any) =>
      axios$.post("/cecProxy/dw/dataSource/db", data).then((res) => res?.data)
  });

  const getDbList = ({
    searchWord,
    pageNo,
    pageSize
  }: {
    searchWord?: string;
    pageNo: number;
    pageSize: number;
  }) => {
    const url = `/cecProxy/dw/dataSource/db?searchWord=${searchWord}&pageNo=${pageNo}&pageSize=${pageSize}`;
    return axios$.get(url).then((res) => res?.data);
  };

  const delDbById = useMutation({
    mutationFn: (id: any) =>
      axios$.delete(`/cecProxy/dw/dataSource/db/${id}`).then((res) => res?.data)
  });

  const getDbDetailById = useMutation({
    mutationFn: (id: any) =>
      axios$.get("/cecProxy/dw/dataSource/db/" + id).then((res) => res?.data)
  });

  const getOnlineDbTablesById = useMutation({
    mutationFn: (id: any) =>
      axios$
        .post("/cecProxy/dw/dataSource/online/table", id)
        .then((res) => res?.data)
  });

  const updateDbTablesById = useMutation({
    mutationFn: (data: any) =>
      axios$
        .put("/cecProxy/dw/dataSource/db/" + data.id, {
          tables: data.tables
        })
        .then((res) => res?.data)
  });

  const delDbTableById = useMutation({
    mutationFn: (id: any) =>
      axios$
        .delete("/cecProxy/dw/dataSource/table/" + id)
        .then((res) => res?.data)
  });

  const getTableListByTableId = (tableId: number | string) => {
    const url = `/cecProxy/dw/dataSource/table/${tableId}`;
    return axios$.get(url).then((res) => res?.data);
  };

  const getOnlineTableListByTableId = (tableId: number | string) => {
    const url = `/cecProxy/dw/dataSource/online/table/${tableId}/field`;
    return axios$.get(url).then((res) => res?.data);
  };

  const delLocalFieldById = useMutation({
    mutationFn: (ids: any) =>
      axios$
        .delete("/cecProxy/dw/dataSource/field/" + ids)
        .then((res) => res?.data)
  });

  const updateFieldById = useMutation({
    mutationFn: (data: any) =>
      axios$
        .put("/cecProxy/dw/dataSource/field/" + data.id, data)
        .then((res) => res?.data)
  });

  const insertField = useMutation({
    mutationFn: (data: any) =>
      axios$
        .post("/cecProxy/dw/dataSource/field", data)
        .then((res) => res?.data)
  });

  const getLocalAndRemoteData = (tableId: number | string) => {
    return Promise.all([
      getTableListByTableId(tableId),
      getOnlineTableListByTableId(tableId)
    ]).then((res) => {
      return res;
    });
  };

  return {
    getOnlineDb,
    getOnlineDbTables,
    createDb,
    getDbList,
    delDbById,
    getDbDetailById,
    getOnlineDbTablesById,
    updateDbTablesById,
    delDbTableById,
    getTableListByTableId,
    getOnlineTableListByTableId,
    delLocalFieldById,
    updateFieldById,
    insertField,
    getLocalAndRemoteData
  };
};
