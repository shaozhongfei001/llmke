import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { Button, message } from "antd";
import IconGoBack from "@/assets/knowledgebase/go_back_arrow.svg";
import DetailInfo from "./components/info";
import DetailTableList from "./components/tableList";
import TableDetail from "./components/tableDetail";

// mockdata
import {
  getMockDbDetailData,
  getLocalTablesByDbId,
  getRemoteTablesByDbId,
  postSyncTables,
  getTableDetailById
} from "@/const/database";
import { useServices } from "../ResourceM/compoments/Database/service";
import {
  getQueryOnlineParams,
  transformDbDetail,
  transformLocalTableList
} from "./dataTransform";
import { uniq, uniqueId } from "lodash";
import DeleteConfirm from "../common/components/DeleteModal";
import { useQuery } from "@tanstack/react-query";

interface Iprops {}
export type Ttables = {
  // 本地
  local: any[];
  // 远端
  remote: any[];
};
export type TtableDetail = {
  local: any;
  remote: any;
  otherInfo?: any;
};
const initialTables: Ttables = {
  local: [],
  remote: []
};
const initialTableDetail: TtableDetail = {
  local: [],
  remote: []
};

const DataBaseDetail = (props: Iprops) => {
  const params = useParams();
  const navigator = useNavigate();
  const {
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
  } = useServices();
  const [detailInfo, setDetailInfo] = useState<any>({});
  // 数据表list，包括本地和远端，渲染在下部左侧
  const [tables, setTables] = useState<Ttables>({ ...initialTables });
  // 当前选中的数据表Id
  const [curTableId, setCurTableId] = useState<number | undefined>(undefined);
  // 当前选中数据表的详情，渲染在下部右侧
  const [tableDetail, setTableDetail] = useState<TtableDetail>({
    ...initialTableDetail
  });
  // 刷新下部右侧数据表详情
  // 用于删除，启用，关联关系等操作过后刷新列表
  const [refreshTableDetail, setRefreshTableDetail] = useState<boolean>(false);
  // 删除数据表相关
  const [isShowDeleteModal, setIsShowDeleteModal] = useState<boolean>(false);
  const delTableId = useRef<number | undefined>(undefined);

  // 获取下部右侧本地数据表字段
  // const queryTableList = useQuery({
  //   queryKey: ["queryTableList", curTableId, refreshTableDetail],
  //   queryFn: () => getTableListByTableId(curTableId as number),
  //   enabled: !!curTableId
  // });

  // // 获取下部右侧远程数据表字段
  // const querygetOnlineTableList = useQuery({
  //   queryKey: ["querygetOnlineTableList", curTableId, refreshTableDetail],
  //   queryFn: () => getOnlineTableListByTableId(curTableId as number),
  //   enabled: !!curTableId
  // });

  const queryTableList = useQuery({
    queryKey: ["queryTableList", curTableId, refreshTableDetail],
    queryFn: () => getLocalAndRemoteData(curTableId as number),
    enabled: !!curTableId
  });

  useEffect(() => {
    setTableDetail({
      ...initialTableDetail
    });
  }, [curTableId]);

  // 面包屑返回
  const goBack = () => {
    navigator(`/docWriting/resource`, {
      state: { currentTab: "db" }
    });
  };

  // 模拟获取数据库详情
  const fetchDatabaseDetail = async () => {
    const res: any = await getDbDetailById.mutateAsync(Number(params.id));
    setDetailInfo(transformDbDetail(res));
  };

  // 模拟根据数据库id获取本地及远端数据表列表
  const fetchDatabaseTables = async () => {
    // const localRes: any = await getLocalTablesByDbId(Number(params.id));
    const localRes = await getDbDetailById.mutateAsync(Number(params.id));
    const remoteRes: any = await getOnlineDbTablesById.mutateAsync(
      getQueryOnlineParams(localRes)
    );

    fixTables(
      transformLocalTableList(localRes),
      (remoteRes || []).map((item: any) => ({
        ...item,
        id: uniqueId("remote_")
      }))
    );
  };

  // 默认选中当前第一个本地数据表，并保存远端和本地数据到state
  const fixTables = (localTables: any[], remoteTables: any[]) => {
    const curId = localTables.length ? localTables[0].id : undefined;
    setCurTableId(curId);
    setTables({ local: localTables, remote: remoteTables });
  };

  // 删除表
  const deleteTableById = async () => {
    // 调用接口删除表并同步数据
    await delDbTableById.mutateAsync(delTableId.current);
    delTableId.current = undefined;
    setIsShowDeleteModal(false);
    fetchDatabaseTables();
  };

  // 数据表列表点击调用事件，传入tableList组件
  const selectTable = (tableId: number) => {
    setCurTableId(tableId);
  };

  // 同步远端数据到本地
  const syncTableData = async (ids: number[], cb?: any) => {
    if (ids.length === 0) {
      message.warning("请至少选择一张数据表！");
      return;
    }
    const allTables = [...tables.local, ...tables.remote];
    const needSyncTables = allTables.filter((item) => ids.includes(item.id));
    // 调用接口同步数据
    await updateDbTablesById.mutateAsync({
      id: Number(params.id),
      tables: needSyncTables
    });
    fetchDatabaseTables();
    cb && cb();
    // postSyncTables({ ids, id: Number(params.id) })
    //   .then((res: any) => {
    //     const { success } = res;
    //     if (success) {
    //       message.success("更新数据表成功！");
    //       // 刷新数据
    //       fetchDatabaseTables();
    //     }
    //   })
    //   .finally(() => {
    //     cb && cb();
    //   });
  };

  // 根据当前选中的数据表id获取数据表详情
  // const fetchTableDetail = async () => {
  //   if (curTableId) {
  //     const res: any = await getTableDetailById(curTableId);
  //     const { success, data } = res;
  //     if (success) {
  //       const { local, remote } = data;
  //       setTableDetail({ local, remote });
  //     }
  //   }
  // };

  useEffect(() => {
    if (!queryTableList.data || queryTableList.isFetching) return;
    const [_local, _remote] = queryTableList.data;
    setTableDetail({
      local: _local?.fields || [],
      remote: (_remote || []).map((item: any) => ({
        ...item,
        id: uniqueId("remote_")
      })),
      otherInfo: _local
    });
  }, [queryTableList.data, queryTableList.isFetching]);

  // 绑定字段关联关系
  const bindRelations = (propertyId: number, relations?: any[]) => {
    // params.id 数据库id
    // curTableId 数据表id
    // propertyId 字段id
    // 根据relations判断是新建关联还是编辑已有关联
    // 触发关联模态框的显示及数据初始化
    // 关联成功后刷新数据
    setRefreshTableDetail(!refreshTableDetail);
  };

  // 调用接口，删除远端已删除的字段
  const deleteProperty = async (propertyId: number) => {
    // params.id 数据库id
    // curTableId 数据表id
    // propertyId 字段id
    // 根据字段id删除远端已经删除的字段
    // 删除成功后刷新数据
    await delLocalFieldById.mutateAsync(propertyId);
    setRefreshTableDetail(!refreshTableDetail);
  };

  const init = async () => {
    try {
      await fetchDatabaseDetail();
      await fetchDatabaseTables();
    } catch (e) {
      console.log(e);
    }
  };

  useEffect(() => {
    if (params.id) {
      // id存在，获取数据库详情及数据表列表
      init();
    }
  }, [params.id]);

  const cancelDelete = () => {
    setIsShowDeleteModal(false);
  };

  const openDelModal = (tableId: number, cb?: any) => {
    delTableId.current = tableId;
    setIsShowDeleteModal(true);
  };

  // 编辑字段 启用/禁用操作,描述修改
  const updateField = async (params: any) => {
    // 调用接口更新字段状态
    await updateFieldById.mutateAsync(params);
    setRefreshTableDetail(!refreshTableDetail);
  };

  // 新增字段
  const addField = async (data: any) => {
    // 调用接口新增字段
    await insertField.mutateAsync({
      ...data,
      tableId: curTableId
    });
    setRefreshTableDetail(!refreshTableDetail);
  };

  return (
    <>
      <DeleteConfirm
        isShowDeleteModal={isShowDeleteModal}
        closeModal={cancelDelete}
        confirmModal={deleteTableById}
        loading={delDbTableById.isLoading}
      />
      <div className="h-full overflow-hidden max-w-full pr-5">
        <div className="mt-5 mb-4 flex items-center">
          <Button
            icon={<img src={IconGoBack} />}
            type="link"
            onClick={goBack}
          />
          <b className="relative -mt-2 ml-4 text-[#2a2a2a] text-base">
            {detailInfo.name}
          </b>
        </div>
        <div className="mb-3">
          <DetailInfo info={detailInfo} />
        </div>
        <div className="flex rounded-lg bg-white min-h-[calc(100vh-255px)]">
          <div className="w-[334px] py-4 pl-5 pr-4  border-solid border-0 border-r-[1px] border-[#eee] text-[#2a2a2a] text-sm">
            <DetailTableList
              tables={tables}
              curTableId={curTableId}
              selectTable={selectTable}
              syncTableData={syncTableData}
              openDelModal={openDelModal}
              loading={
                getDbDetailById.isLoading || getOnlineDbTablesById.isLoading
              }
            />
          </div>
          <div className="flex-1 px-5 py-4 text-[#2a2a2a] text-sm">
            <TableDetail
              dbDetail={detailInfo}
              tableDetail={tableDetail}
              bindRelations={bindRelations}
              deleteProperty={deleteProperty}
              delLoading={delLocalFieldById.isLoading}
              tableLoading={
                queryTableList.isFetching ||
                updateFieldById.isLoading ||
                insertField.isLoading
              }
              updateField={updateField}
              addField={addField}
            />
          </div>
        </div>
      </div>
    </>
  );
};
export default DataBaseDetail;
