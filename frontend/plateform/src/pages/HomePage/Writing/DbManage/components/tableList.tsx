import { useEffect, useState, useMemo } from "react";
import { Button, Checkbox, Empty, Spin } from "antd";
import type { CheckboxProps } from "antd";

import db_table from "@/assets/img/db_table.png";
import IconTableDisabled from "@/assets/svg/icon-table-disabled.svg";
import {
  PlusCircleOutlined,
  DeleteOutlined,
  CloseOutlined
} from "@ant-design/icons";
import type { Ttables } from "../detail";
import "./style.less";

interface Iprops {
  tables: Ttables;
  curTableId: number | undefined;
  selectTable: (tableId: number) => void;
  syncTableData: (ids: number[], cb?: () => void) => void;
  openDelModal: (tableId: number, cb?: any) => void;
  loading: boolean;
}

const DataBaseDetailTables = (props: Iprops) => {
  const {
    tables,
    curTableId,
    selectTable,
    syncTableData,
    openDelModal,
    loading
  } = props;
  // 是否显示同步数据表弹出层
  const [isShowChooseTable, setIsShowChooseTable] = useState<boolean>(false);
  // 初始化时的本地数据表id数组，用来关闭时比对是否有变化；
  const [defaultCheckedKeys, setDefaultCheckedKeys] = useState<number[]>([]);
  // 当前操作时变化选中的远端数据表id数组
  const [checkedKeys, setCheckedKeys] = useState<number[]>([]);
  // 全选变量
  const [allChecked, setAllChecked] = useState<boolean>(false);
  // 显示Spin
  const [isSyncTableS, setIsSyncTableS] = useState<boolean>(false);

  // 切换显示隐藏同步远端数据表的浮层
  const switchTableChoose = (sta: boolean) => () => {
    setIsShowChooseTable(sta);
    !sta && setIsSyncTableS(false);
  };

  // 全选checkbox的change事件
  const allCheckedOnChange: CheckboxProps["onChange"] = (e) => {
    const isChecked = e.target.checked;
    const { remote } = tables;
    setCheckedKeys(isChecked ? [...remote.map((i: any) => i.id)] : []);
    setAllChecked(e.target.checked);
  };

  // 远端数据表checkbox的change事件
  const checkTableHandler = (id: number) => (e: any) => {
    const isChecked = e.target.checked;
    const _checkedKeys = [...checkedKeys];
    if (isChecked) {
      _checkedKeys.push(id);
    } else {
      const idx = _checkedKeys.findIndex((_id: any) => _id === id);
      idx >= 0 && _checkedKeys.splice(idx, 1);
    }
    setCheckedKeys([...Array.from(new Set(_checkedKeys))]);
  };

  // 显示浮层时比对当前本地已存在远端的数据表id数组
  const checkExistTable = () => {
    const { local, remote } = tables;
    const _existlocal: any[] = [];
    remote.forEach((i: any) => {
      if (local.some((j: any) => j.name === i.name)) {
        _existlocal.push(i.id);
      }
    });
    setDefaultCheckedKeys([..._existlocal]);
    setCheckedKeys([..._existlocal]);
  };

  // 关闭浮层时同步数据方法
  const syncTableListHandler = () => {
    // 是否有数据表变化，若无变化则只关闭浮层，不调用接口
    let isChange = true;
    if (
      checkedKeys.length === defaultCheckedKeys.length &&
      checkedKeys.every((id: number) => defaultCheckedKeys.includes(id))
    ) {
      isChange = false;
    }
    if (isChange) {
      setIsSyncTableS(true);
      const _ids = [...checkedKeys, ...unUseTables.map((i: any) => i.id)];
      syncTableData && syncTableData(_ids, switchTableChoose(false));
    } else {
      setIsShowChooseTable(false);
    }
  };

  // 数据表删除按钮事件，调用接口删除
  const deleteTableHandler = (tableId: number) => async () => {
    openDelModal(tableId, () => {
      console.log("可以处理loading！");
    });
  };

  // 点击数据表事件，将id传给父组件传入的方法selectTable
  const selectTableHandler = (tableId: number) => () => {
    selectTable(tableId);
  };

  // 本地存在但远端已删除的数据表列表，用于显示删除效果
  const unUseTables = useMemo(() => {
    const { local, remote } = tables;
    const _unUse: any[] = [];
    local.forEach((i: any) => {
      if (!remote.some((j: any) => j.name === i.name)) {
        _unUse.push(i);
      }
    });
    return _unUse;
  }, [tables]);

  // 本地数据表
  const localUseTable = useMemo(() => {
    const { local, remote } = tables;
    const _localUse: any[] = [];

    local.forEach((i: any) => {
      if (remote.some((j: any) => j.name === i.name)) {
        _localUse.push(i);
      }
    });
    return _localUse;
  }, [tables]);

  // 是否半选
  const isIndeterminate = useMemo(() => {
    const { remote } = tables;
    return !!(
      checkedKeys.length &&
      remote &&
      remote.length &&
      checkedKeys.length < remote.length
    );
  }, [checkedKeys, tables]);

  useEffect(() => {
    if (isShowChooseTable) {
      // 显示浮层时，同步已选中数据
      checkExistTable();
    }
  }, [isShowChooseTable]);

  useEffect(() => {
    const isCheckAll = !!(
      checkedKeys.length && checkedKeys.length === tables.remote.length
    );
    if (isCheckAll !== allChecked) {
      // 数据表单选全部选中时，同步设置全选checkbox状态
      setAllChecked(isCheckAll);
    }
  }, [checkedKeys, tables.remote]);

  return (
    <>
      <div className="flex justify-between items-center mb-4">
        <b className="">全部数据表（{localUseTable.length || 0}）</b>
        <span className="relative">
          <Button
            onClick={switchTableChoose(true)}
            type="link"
            icon={<PlusCircleOutlined className="text-[#055aff]" />}
          />
          <div
            className={`${isShowChooseTable ? "" : "hidden "}absolute -left-14 w-72 bg-transparent z-10 top-2 px-1 pt-6`}
          >
            <div className="z-20 pl-5 pr-1 py-4 rounded-lg bg-white border-solid border-[1px] border-[#eee] shadow-[0px_2px_12px_0px_#5C667966] text-[32a2a2a] text-sm">
              <Spin spinning={isSyncTableS}>
                <div className="flex justify-between items-center pr-1 mb-2">
                  <b>选择数据表</b>
                  <Button
                    onClick={syncTableListHandler}
                    type="link"
                    icon={
                      <CloseOutlined className="text-[#555] w-3 hover:opacity-80" />
                    }
                  />
                </div>
                <div className="pr-4 max-h-[260px] overflow-y-auto">
                  <div className="mb-1">
                    <Checkbox
                      disabled={!tables.remote.length}
                      checked={allChecked}
                      onChange={allCheckedOnChange}
                      indeterminate={isIndeterminate}
                    >
                      全选
                      {/* {String(allChecked)} */}
                    </Checkbox>
                  </div>
                  {tables.remote.length ? (
                    tables.remote.map((i: any, idx: number) => {
                      return (
                        <div
                          className="flex h-8 items-center"
                          key={`table-remote-${i.id}-${idx}`}
                        >
                          <Checkbox
                            checked={checkedKeys.includes(i.id)}
                            onChange={checkTableHandler(i.id)}
                          />
                          <img src={db_table} width={20} className="mx-3" />
                          <div className="truncate w-60" title={i.name}>
                            {i.name}
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <Empty className="-mt-10" />
                  )}
                </div>
              </Spin>
            </div>
          </div>
        </span>
      </div>
      <Spin spinning={loading}>
        <div className="max-h-[calc(100vh-320px)] overflow-y-auto">
          {localUseTable.map((i: any, idx: number) => {
            return (
              <div
                key={`remote-table-${idx}`}
                className={`${curTableId && curTableId === i.id ? "bg-[#f1f5ff] cursor-default " : "cursor-pointer hover:opacity-85 "}flex items-center justify-between h-10 leading-10 rounded hover:bg-[#f1f5ff] table-list-row`}
                onClick={selectTableHandler(i.id)}
              >
                <img src={db_table} width={20} />
                <div className="flex-1 mx-2">{i.name}</div>
                <span className={`${"del-btn-wrap"}`}>
                  <Button
                    onClick={deleteTableHandler(i.id)}
                    type="link"
                    icon={<DeleteOutlined className="text-[#888]" />}
                  />
                </span>
              </div>
            );
          })}
          {(unUseTables || []).map((i: any, idx: number) => {
            return (
              <div
                key={`remote-table-${idx}`}
                className="flex items-center h-10 leading-10 rounded hover:bg-[#f1f5ff] table-list-row"
              >
                <img src={IconTableDisabled} width={20} />
                <div className="mx-2 text-[#bbb] relative">
                  {i.name}
                  <b className="inline-block h-[1px] absolute -left-7 -right-2 top-1/2 border-solid border-0 border-b-[1px] border-b-[#bbb]"></b>
                </div>
                <span className="del-btn-wrap flex-1 text-right">
                  <Button
                    onClick={deleteTableHandler(i.id)}
                    type="link"
                    icon={<DeleteOutlined className="text-[#888]" />}
                  />
                </span>
              </div>
            );
          })}
        </div>
      </Spin>
    </>
  );
};
export default DataBaseDetailTables;
