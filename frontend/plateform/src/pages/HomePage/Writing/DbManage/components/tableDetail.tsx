import { useEffect, useState, useMemo, useRef } from "react";
import { Empty, Switch, Button, Spin, message, Input } from "antd";
import type { TtableDetail } from "../detail";
import { dataTypes } from "@/const/database";
import IconRelation from "@/assets/svg/icon-relation.svg";
import { DeleteOutlined } from "@ant-design/icons";
import DeleteConfirm from "../../common/components/DeleteModal";
import { cloneDeep } from "lodash";
import RelationsModal from "./RelationsModal";

interface Iprops {
  dbDetail: any;
  tableDetail: TtableDetail;
  bindRelations: (propertyId: number, relations?: any[]) => void;
  deleteProperty: (propertyId: number) => void;
  delLoading: boolean;
  tableLoading: boolean;
  updateField: (params: any) => void;
  addField: (data: any) => void;
}

const DataBaseTableDetail = (props: Iprops) => {
  const {
    dbDetail,
    tableDetail,
    bindRelations,
    deleteProperty,
    delLoading,
    tableLoading,
    updateField,
    addField
  } = props;
  // 本地与远端同步的字段
  const [commonKeys, setCommonKeys] = useState<any[]>([]);
  // 仅本地存在的字段
  const [localKeys, setlocalKeys] = useState<any[]>([]);
  // 仅远端存在的字段
  const [remoteKeys, setRemoteKeys] = useState<any[]>([]);
  // 删除相关
  const [isShowDeleteModal, setIsShowDeleteModal] = useState(false);
  const propertyIdRef = useRef<number | number>();
  // 当前填写描述的项
  const inputRef = useRef<any>(null);
  const [curInputDesItem, setCurInputDesItem] = useState({
    originItem: {},
    id: "",
    value: ""
  });

  //控制关联关系modal弹窗
  const [relationsModalData, setRelationsModalData] = useState<{
    isOpen: boolean;
    tableName?: string;
    dbName?: string;
    propertyName?: string;
    propertyId?: number;
    relations?: any[];
  }>({
    isOpen: false
  });

  // 分组数据表的字段，分为两端都存在的commonKeys、仅存在远端的remoteKeys，仅存在本地的localKeys
  const groupKeys = () => {
    const { local, remote } = tableDetail;
    if (local && remote) {
      const _commonKeys: any = [];
      const _localKeys: any = [];
      const _remoteKeys: any = [];
      local.forEach((i: any) => {
        if (remote.some((j: any) => j.name === i.name)) {
          if (!_commonKeys.some((j: any) => j.name === i.name)) {
            _commonKeys.push({ ...i });
          }
        } else {
          if (!_localKeys.some((j: any) => j.name === i.name)) {
            _localKeys.push({ ...i });
          }
        }
      });
      remote.forEach((i: any) => {
        if (!local.some((j: any) => j.name === i.name)) {
          if (!_remoteKeys.some((j: any) => j.name === i.name)) {
            _remoteKeys.push({ ...i });
          }
        }
      });
      setCommonKeys([..._commonKeys]);
      setlocalKeys([..._localKeys]);
      setRemoteKeys([..._remoteKeys]);
    }
  };

  useEffect(() => {
    groupKeys();
  }, [tableDetail]);

  useEffect(() => {
    if (!inputRef.current) return;
    if (curInputDesItem.originItem.toString() !== "{}") {
      inputRef.current.focus();
    }
  }, [curInputDesItem]);

  const relationHandler = (info: any) => () => {
    if (String(info.id).includes("remote_") && !info.description) {
      message.warning("请先填写描述");
      return;
    }
    console.log("--------info", info);
    // 初始化绑定关系弹窗数据
    setRelationsModalData({
      isOpen: true,
      tableName: tableDetail.otherInfo.name,
      propertyName: info.name,
      propertyId: info.id,
      relations: info.refField
    });
  };
  const onRelationsModalClose = async (relations: any[]) => {
    const curItem = [...tableDetail.local, ...tableDetail.remote].find(
      (i) => String(i.id) === String(relationsModalData.propertyId)
    );
    if (String(curItem.id).includes("remote_")) {
      addField({
        ...curItem,
        refField: relations
      });
    } else {
      updateField({
        id: curItem.id,
        refField: relations
      });
    }
    closeModal();
  };

  const closeModal = () => {
    setRelationsModalData({
      isOpen: false
    });
  };

  // 数据表详细信息
  const tableOtherInfo = useMemo(() => {
    return tableDetail?.otherInfo || {};
  }, [tableDetail]);

  // 删除相关
  const deletePropertyHandler = async () => {
    if (!propertyIdRef.current) return;
    await deleteProperty(propertyIdRef.current);
    setIsShowDeleteModal(false);
  };
  const cancelDelete = () => {
    setIsShowDeleteModal(false);
  };
  const openDelModal = (tableId: number) => {
    propertyIdRef.current = tableId;
    setIsShowDeleteModal(true);
  };

  // 禁用/启用
  const commonSwitchHandler = async (item: any, checked: boolean) => {
    if (!item.id) {
      message.warning("字段id不存在");
      return;
    }
    updateField({ id: item.id, enableStatus: checked ? 1 : 0 });
  };
  // 新增
  const remoteSwitchHandler = async (item: any, checked: boolean) => {
    if (!item.description) {
      message.warning("请先填写描述");
      return;
    }
    const params = cloneDeep(item);
    delete params.id;
    await addField({ ...params, enableStatus: checked ? 1 : 0 });
  };

  const descriptionChange = (e: any) => {
    const newValue = e.target.value;
    setCurInputDesItem((p) => {
      return {
        ...p,
        value: newValue
      };
    });
  };
  // 新增字段/修改描述
  const descriptionHandler = async () => {
    if (!curInputDesItem.value) {
      message.warning("描述不能为空");
      return;
    }
    // 存在remote_代表需要新增
    if (String(curInputDesItem.id).includes("remote_")) {
      const _params: any = cloneDeep(curInputDesItem.originItem);
      if (_params.id) {
        delete _params.id;
      }
      addField({ ..._params, description: curInputDesItem.value });
    } else {
      if (curInputDesItem.value === curInputDesItem.originItem?.description) {
        setCurInputDesItem({
          originItem: {},
          id: "",
          value: ""
        });
        return;
      }
      // 只需要修改
      updateField({
        ...curInputDesItem.originItem,
        description: curInputDesItem.value
      });
    }
    setCurInputDesItem({
      originItem: {},
      id: "",
      value: ""
    });
  };

  return (
    <>
      <DeleteConfirm
        isShowDeleteModal={isShowDeleteModal}
        closeModal={cancelDelete}
        confirmModal={deletePropertyHandler}
        loading={delLoading}
      />
      <div className="bg-white">
        <div className="font-bold mb-4">
          {tableOtherInfo.name ? `${tableOtherInfo.name}数据表详情` : "-"}
        </div>
        <div className="text-[#555] mb-4 leading-5">
          <span className="text-[#888]">描述：</span>
          {tableOtherInfo.description || "-"}
        </div>
        <Spin spinning={tableLoading}>
          <div className="flex py-4 text-[#555] font-bold bg-[#fafafa] border-solid border-0 border-b-[1px] border-[#eee]">
            <div className="pl-8 w-44">字段名称</div>
            <div className="pl-4 w-32">数据类型</div>
            <div className="pl-4 flex-1">描述</div>
            <div className="pl-4 w-20">关联关系</div>
            <div className="pl-4 w-24">启用</div>
          </div>
          {commonKeys.length + localKeys.length + remoteKeys.length ? (
            <div className="overflow-y-auto h-[calc(100vh-412px)]">
              {commonKeys.map((i: any, idx: number) => {
                return (
                  <div
                    key={`common-key-${i.id}-${idx}`}
                    className="flex py-4 text-[#555] border-solid border-0 border-b-[1px] border-[#eee] items-center kew-row hover:bg-[#f1f5ff]"
                  >
                    <div
                      className="pl-8 w-44 h-8 leading-8 truncate"
                      title={i.name}
                    >
                      {i.name}
                    </div>
                    <div className="pl-4 w-32">{i.type || "-"}</div>
                    <div className="pl-4 flex-1 truncate">
                      {curInputDesItem.id !== i.id ? (
                        <span
                          className="inline-block w-full h-full"
                          onDoubleClick={() => {
                            setCurInputDesItem({
                              originItem: i,
                              id: i.id,
                              value: i.description || ""
                            });
                          }}
                        >
                          {i.description || "-"}
                        </span>
                      ) : (
                        <Input
                          placeholder="请添加描述"
                          value={curInputDesItem.value}
                          onBlur={descriptionHandler}
                          onChange={descriptionChange}
                          ref={inputRef}
                        />
                      )}
                    </div>
                    <div className="pl-4 w-20">
                      <Button
                        onClick={relationHandler(i)}
                        className={`${i.refField && i.refField.length ? "" : "link-btn "} hover:opacity-85`}
                        type="link"
                        icon={<img src={IconRelation} className="mt-1" />}
                      />
                      {i.refField && i.refField.length ? (
                        <span>{i.refField.length}</span>
                      ) : null}
                    </div>
                    <div className="pl-4 w-24">
                      <Switch
                        // defaultChecked={!!i.enableStatus}
                        checked={!!i.enableStatus}
                        onChange={(checked) => commonSwitchHandler(i, checked)}
                      />
                    </div>
                  </div>
                );
              })}
              {remoteKeys.map((i: any, idx: number) => {
                return (
                  <div
                    key={`remote-key-${i.id}-${idx}`}
                    className="flex py-4 text-[#555]  border-solid border-0 border-b-[1px] border-[#eee] items-center kew-row hover:bg-[#f1f5ff]"
                  >
                    <div className="w-8 h-8 leading-8 text-center">
                      <span className="inline-block w-2 h-2 rounded-lg bg-[#ffa500]"></span>
                    </div>
                    <div className="pl-1 w-36 truncate" title={i.name}>
                      {i.name}
                    </div>
                    <div className="pl-4 w-32">{i.type || "-"}</div>
                    <div className="pl-4 flex-1 truncate">
                      {curInputDesItem.id !== i.id ? (
                        <span
                          className="inline-block w-full h-full"
                          onDoubleClick={() => {
                            setCurInputDesItem({
                              originItem: i,
                              id: i.id,
                              value: i.description || ""
                            });
                          }}
                        >
                          {i.description || "-"}
                        </span>
                      ) : (
                        <Input
                          placeholder="请添加描述"
                          value={curInputDesItem.value}
                          onBlur={descriptionHandler}
                          onChange={descriptionChange}
                          ref={inputRef}
                        />
                      )}
                    </div>
                    <div className="pl-4 w-20">
                      <Button
                        // 按目前逻辑，未同步的字段并不会触发关联关系，如有误，可加上点击事件
                        onClick={relationHandler(i)}
                        disabled={!i.description}
                        className="link-btn hover:opacity-85"
                        type="link"
                        icon={<img src={IconRelation} className="mt-1" />}
                      />
                    </div>
                    <div className="pl-4 w-24">
                      <Switch
                        checked={!!i.enableStatus}
                        // defaultChecked={!!i.enableStatus}
                        onChange={(checked) => remoteSwitchHandler(i, checked)}
                      ></Switch>
                    </div>
                  </div>
                );
              })}
              {localKeys.map((i: any, idx: number) => {
                return (
                  <div
                    key={`local-key-${i.id}-${idx}`}
                    className="relative flex py-4 text-[#bbb] border-solid border-0 border-b-[1px] border-[#eee] items-center kew-row hover:bg-[#f1f5ff]"
                  >
                    <div
                      className="pl-8 w-44 h-8 leading-8 truncate"
                      title={i.name}
                    >
                      {i.name}
                    </div>
                    <div className="pl-4 w-32">{i.type || "-"}</div>
                    <div className="pl-4 flex-1 truncate">
                      {i.description || "-"}
                    </div>
                    <div className="del-btn-wrap text-right w-[170px]">
                      <Button
                        onClick={() => openDelModal(i.id)}
                        type="link"
                        icon={<DeleteOutlined className="text-[#888]" />}
                      />
                    </div>
                    <div className="absolute h-[1px] left-1 top-1/2 border-solid border-0 border-b-[1px] border-[#bbb] w-[760px]"></div>
                  </div>
                );
              })}
            </div>
          ) : (
            <Empty className="mt-20" />
          )}
        </Spin>
      </div>
      <RelationsModal
        isModalOpen={relationsModalData.isOpen}
        relatedFields={relationsModalData.relations}
        initdata={{
          table: relationsModalData.tableName,
          field: relationsModalData.propertyName,
          db: dbDetail
        }}
        onClose={closeModal}
        onFinish={onRelationsModalClose}
      />
    </>
  );
};
export default DataBaseTableDetail;
