import React, { useState, useMemo, useEffect, useRef } from "react";
import { Button, Input, Tooltip, Popconfirm } from "antd";
import { FxIcon } from "@/components/Icon";
import { initialRow, editTypeObj, changeType } from "./";

interface ArticulationItemProps {
  item: any;
  editId: string | undefined;
  editType: string;
  isLoading: boolean;
  rowDataChange: (row: any, type: changeType, obj?: any) => void;
}

const ArticulationItem: React.FC<ArticulationItemProps> = (props) => {
  const { item, editId, editType, isLoading, rowDataChange } = props;
  const nameIptRef = useRef<any>(null);
  const [isShowTip, setIsShowTip] = useState<boolean>(false);

  const stopPropagation = (e: any) => {
    e.stopPropagation();
  };

  const handlerIptConfirm = (row: any, type: string) => (e: any) => {
    const val = e.target.value.trim();

    switch (type) {
      case editTypeObj.checkName:
        rowDataChange(row, isNew ? changeType.ADD_NODE : changeType.EDIT_ROW, {
          checkName: val
        });
        break;
    }
  };

  const editCell = (row: any, type: string) => () => {
    rowDataChange(row, changeType.EDIT_INIT, {
      editIptType: type
    });
  };

  const configCalculator = (row: any) => () => {
    rowDataChange(row, changeType.CALCULATOR_CLICK, {});
    setIsShowTip(false);
  };

  const deleteCell = (row: any) => () => {
    rowDataChange(row, changeType.DELETE, {});
  };

  const isNew = useMemo(() => {
    return !!(String(editId) === initialRow.id);
  }, [editId]);

  useEffect(() => {
    if (editId && editId === item.id) {
      switch (editType) {
        case editTypeObj.checkName:
          nameIptRef.current.focus();
          break;
      }
    }
  }, [editId, editType, item]);

  return (
    <div
      className="flex w-full justify-between h-12 leading-[48px] box-border min-w-[1284px] hover:bg-[#f5f5f5] group"
      style={{ borderBottom: "1px solid #e4e6f8" }}
    >
      <div className="w-[18%] relative min-w-60 pl-4 box-border break-words text-ellipsis line-clamp-1">
        {editId === item.id && editType === editTypeObj.checkName ? (
          <div className="">
            <Input
              defaultValue={item.checkName}
              ref={nameIptRef}
              disabled={isLoading}
              placeholder="请输入校验项名称"
              allowClear
              onClick={stopPropagation}
              onBlur={handlerIptConfirm(item, editType)}
              onPressEnter={handlerIptConfirm(item, editType)}
            />
          </div>
        ) : (
          <div className="relative px-1">
            <span
              className="absolute top-[6px] bottom-[6px] -right-0 -left-1 border-0 z-10 select-none px-2 py-[6px] cursor-pointer rounded hover:border-[#d9d9d9] hover:border-solid hover:border hover:px-[7px] hover:py-[5px]"
              title={item.checkName}
              onClick={editCell(item, editTypeObj.checkName)}
            ></span>
            {item.checkName || "-"}
          </div>
        )}
      </div>
      <div className="w-[45%] min-w-[578px] pl-4 box-border break-words text-ellipsis line-clamp-1">
        {item.formulas && item.formulas.length ? (
          <b title={item.formulas.join("，")}>{item.formulas.join("，")}</b>
        ) : (
          "-"
        )}
      </div>
      <div className="w-[6%] min-w-20 pl-4 box-border invisible group-hover:visible">
        <Tooltip
          placement="top"
          open={isShowTip}
          zIndex={1}
          onOpenChange={setIsShowTip}
          color="white"
          title={<div className="text-gray-2a">编辑勾稽校验公式</div>}
        >
          <Button
            type="text"
            className="px-0 hover:!bg-white group"
            icon={
              <FxIcon
                className={`"text-gray-2a cursor-pointer hover:text-[#0359FC]`}
                onClick={configCalculator(item)}
              />
            }
          />
        </Tooltip>
      </div>
      <div className="w-[13%] min-w-[268px] pl-4 box-border break-words text-ellipsis line-clamp-1">
        {item.sourceTypeList && item.sourceTypeList.length ? (
          <span title={item.sourceTypeList.join("，")}>
            {item.sourceTypeList.join("，")}
          </span>
        ) : (
          "-"
        )}
      </div>
      <div className="w-[18%] min-w-20 pl-4 box-border">
        <Popconfirm
          title="删除"
          description="你确定删除配置项么?"
          onConfirm={deleteCell(item)}
          okText="确定"
          cancelText="取消"
        >
          <Button
            type="link"
            size="small"
            className={`text-primary-color text-sm px-0`}
          >
            删除
          </Button>
        </Popconfirm>
      </div>
    </div>
  );
};

export default ArticulationItem;
