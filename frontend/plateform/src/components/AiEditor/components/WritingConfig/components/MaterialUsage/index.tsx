import { Button, Checkbox, CheckboxChangeEvent, Modal } from "antd";
import { useEffect, useMemo, useState } from "react";
import "./index.less";
import { PrimaryBtn } from "@root/src/pages/HomePage/Writing/common/components/PrimaryBtn";
import Detail from "./Detail";
import { MaterialItemWithCustomId } from "../type";

interface Iprops {
  selectAll: MaterialItemWithCustomId[];
  handleCancelModal: () => void;
  getAllMertail: (item: MaterialItemWithCustomId[]) => any;
}

export const MaterialUsage = ({
  selectAll,
  handleCancelModal,
  getAllMertail
}: Iprops) => {
  const [open, setOpen] = useState(false);
  //   全选
  const [checkAll, setCheckAll] = useState(false);
  const [list, setList] = useState<any[]>([]);

  useEffect(() => {
    if (!selectAll.length) return;
    setList(
      selectAll.map((i) => ({
        ...i,
        checkboxValue: false
      }))
    );
    setOpen(true);
  }, [selectAll]);

  //   是否全选/全不选，
  const operationInfo = useMemo(() => {
    let _notAllowTemp = false;
    let _indeterminate = false;
    // 有选中
    let _isCheck = false;
    let _notCheck = false;
    let _noList = false;

    list.forEach((i) => {
      // 存在知识库/文件夹则不能作为样本范文和两者都用
      if (i.refEntityType !== "document" && i.checkboxValue) {
        _notAllowTemp = true;
      }
      if (i.checkboxValue) {
        _isCheck = true;
      } else {
        _notCheck = true;
      }
    });
    if (_isCheck && !_notCheck) {
      setCheckAll(true);
    } else if (!_isCheck && _notCheck) {
      setCheckAll(false);
    } else if (_isCheck && _notCheck) {
      _indeterminate = true;
      setCheckAll(false);
    } else {
      // 都是false证明没有数组，不考虑，会把操作按钮禁用
      setCheckAll(false);
      _noList = true;
    }

    return {
      notAllowTemp: _notAllowTemp,
      indeterminate: _indeterminate,
      noList: _noList
    };
  }, [list]);

  const handleCheckAll = (e: CheckboxChangeEvent) => {
    const check = e.target.checked;
    setList((_list) => {
      return _list.map((i) => ({
        ...i,
        checkboxValue: check
      }));
    });
  };

  const handleDel = (item: any) => {
    setList((_list) => {
      return _list.filter((i) => i.customId !== item.customId);
    });
  };

  const handleUsage = (type: string) => {
    setList((_list) => {
      return _list.map((i) => ({
        ...i,
        usage: i.checkboxValue ? type : i.usage
      }));
    });
  };

  //   取消弹窗
  const handleCancel = () => {
    handleCancelModal();
    setOpen(false);
    setList([]);
    setCheckAll(false);
  };

  const handleConfirm = () => {
    const _list: MaterialItemWithCustomId[] = list.map((i: any) => {
      if (typeof i.checkboxValue === "boolean" || i.checkboxValue) {
        delete i.checkboxValue;
      }
      return i;
    });
    getAllMertail(_list);
    handleCancel();
  };

  const handleDelAll = () => {
    setList((_list) => {
      return _list.filter((i) => !i.checkboxValue);
    });
  };

  return (
    <Modal
      open={open}
      width="1000px"
      className="material-usage-box"
      onCancel={handleCancel}
      title={
        <div className="font-bold pl-[24px] inline-block pt-[20px] pb-[11px]">
          选择素材使用方式
        </div>
      }
      style={{ padding: 0, minWidth: "1000px", maxWidth: "1000px" }}
      footer={
        <div
          className="flex justify-end px-[24px] py-[20px]"
          style={{ borderTop: "1px solid #E9E9E9" }}
        >
          <div className="flex gap-[12px]">
            <Button
              style={{
                border: "1px solid #eee"
              }}
              onClick={handleCancel}
            >
              取消
            </Button>
            <PrimaryBtn onClick={handleConfirm}>确定</PrimaryBtn>
          </div>
        </div>
      }
    >
      <div className="h-[450px] px-[24px] pb-[16px] box-border">
        <div className="pl-[16px] flex gap-[16px]">
          <Checkbox
            className="mr-[17px]"
            checked={checkAll}
            indeterminate={operationInfo.indeterminate}
            disabled={operationInfo.noList}
            onChange={handleCheckAll}
          />
          <Button
            style={{
              border: "1px solid #eee"
            }}
            disabled={
              operationInfo.noList ||
              (!operationInfo.indeterminate && !checkAll)
            }
            onClick={() => handleUsage("content")}
          >
            选择为内容来源
          </Button>
          <Button
            style={{
              border: "1px solid #eee"
            }}
            disabled={
              operationInfo.noList ||
              (!operationInfo.indeterminate && !checkAll)
            }
            onClick={() => handleUsage("template")}
          >
            选择为样本例文
          </Button>
          <Button
            style={{
              border: "1px solid #eee"
            }}
            disabled={
              operationInfo.noList ||
              (!operationInfo.indeterminate && !checkAll)
            }
            onClick={() => handleUsage("both")}
          >
            选择为全部
          </Button>
          <Button
            style={{
              border: "1px solid #eee"
            }}
            onClick={handleDelAll}
            disabled={
              operationInfo.noList ||
              (!operationInfo.indeterminate && !checkAll)
            }
          >
            删除
          </Button>
        </div>
        <div className="overflow-y-auto h-[420px] w-full overflow-x-hidden">
          {list.map((i) => {
            return (
              <Detail
                item={i}
                setList={setList}
                handleDel={handleDel}
                key={i.customId}
              />
            );
          })}
        </div>
      </div>
    </Modal>
  );
};

export default MaterialUsage;
