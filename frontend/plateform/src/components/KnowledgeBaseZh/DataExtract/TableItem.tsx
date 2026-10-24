import { CaretDownOutlined } from "@ant-design/icons";
import { useEffect, useRef, useState } from "react";
import { formatThousandComma } from "./utils";
import { getIcon } from ".";
import { Input, message, Tooltip } from "antd";
import DeleteConfirm from "../../DeletModal";

export enum ValueState {
  HighReliability = 1,
  NoSource,
  Default,
  Multivalued,
  VerificationFailed
}

interface ExtractResult {
  value: number;
  displayValue: string;
  state: ValueState;
  errorMsg: string;
  source: any;
}
export interface ItemProps {
  id: number;
  parentId?: number;
  categoryId: number;
  indicatorName: string;
  sourceType: string;
  extractResult: {
    bop: ExtractResult;
    eop: ExtractResult;
  };
  subIndicators?: ItemProps[];
}

interface Iprops {
  item: ItemProps;
  depth: number;
  isExpanded: boolean;
  children?: React.ReactNode;
  clickItem: (item: ExtractResult & { title: string }) => any;
  handleUpdateIndicatorValue: (params: any) => any;
  handleAddIndicatorValue: (params: any) => any;
}

export const getItemValueIcon = (timePoint: ExtractResult) => {
  const { state, errorMsg } = timePoint || {};
  let msg = "";
  switch (state) {
    case ValueState.HighReliability:
      msg = "点击查看溯源文件";
      break;
    case ValueState.NoSource:
      msg = "无溯源";
      break;
    case ValueState.Multivalued:
      msg = "检测到多个来源值，请确认";
      break;
    case ValueState.VerificationFailed:
      msg = errorMsg;
      break;
    default:
      break;
  }
  return (
    <Tooltip
      // open={true}
      title={<span className="text-[#2A2A2A]">{msg}</span>}
      color="#fff"
    >
      <span className="ml-[8px] cursor-pointer">
        {/* 暂时隐藏无溯源和溯源成功 */}
        {/* {state && state !== ValueState.Default && getIcon(state)} */}
        {state &&
          [ValueState.Multivalued, ValueState.VerificationFailed].includes(
            state
          ) &&
          getIcon(state)}
      </span>
    </Tooltip>
  );
};

const timePointObj = {
  bop: "期初",
  eop: "期末"
};

const initDelItemInfo = {
  open: false,
  curItem: null,
  type: "eop"
};

const TableItem = ({
  item,
  depth,
  isExpanded,
  children,
  clickItem,
  handleUpdateIndicatorValue,
  handleAddIndicatorValue
}: Iprops) => {
  const [expanded, setExpanded] = useState(isExpanded);
  const { indicatorName, extractResult, subIndicators } = item;
  const { bop, eop } = extractResult || {};

  const [bopValue, setBopValue] = useState("");
  const bopValueRef = useRef<string>("");
  const [eopValue, setEopValue] = useState("");
  const eopValueRef = useRef<string>("");

  const [dispalyInput, setDispalyInput] = useState<"bop" | "eop" | "">("");

  useEffect(() => {
    if (bop) {
      setBopValue(bop.displayValue);
      bopValueRef.current = bop.displayValue;
    }
  }, [bop]);
  useEffect(() => {
    if (eop) {
      setEopValue(eop.displayValue);
      eopValueRef.current = eop.displayValue;
    }
  }, [eop]);

  const handleClickItem = (type: "bop" | "eop", itemObj: ExtractResult) => {
    const { state } = itemObj || {};
    if ([ValueState.NoSource, ValueState.Default].includes(state) || !state)
      return;
    clickItem &&
      clickItem({
        ...itemObj,
        title: item.indicatorName + timePointObj[type]
      });
  };

  const handleTimePoint = (type: "bop" | "eop", newValue: string) => {
    const setStateFn = type === "bop" ? setBopValue : setEopValue;
    setStateFn(newValue);
  };

  const handleClickDisplayValue = (
    type: "bop" | "eop",
    itemObj?: ExtractResult
  ) => {
    const curValue = type === "bop" ? bopValue : eopValue;
    const { state } = itemObj || {};
    // 如果没抽出来，但是状态不是缺省，则不允许点击
    // 20251030允许未抽出数据的修改
    // if (!curValue && state !== ValueState.Default) {
    //   message.warning("暂不支持新增数据");
    //   return;
    // }
    setDispalyInput(type);
  };

  const [delItemInfo, setDelItemInfo] = useState<any>(initDelItemInfo);

  const handleSubmitValue = async (type: "bop" | "eop") => {
    const isBop = type === "bop";
    const curValue = isBop ? bopValue : eopValue;
    const curSetStateFn = isBop ? setBopValue : setEopValue;
    const curValueRef = isBop ? bopValueRef : eopValueRef;
    const curTimePointObj = isBop ? bop : eop;
    // 修改内容为空的情况下
    if (!curValue && curValueRef.current) {
      setDelItemInfo({
        open: true,
        curItem: curTimePointObj,
        type
      });
      return;
    }
    // 没有修改的情况下直接返回
    if (curValue === curValueRef.current) {
      setDispalyInput("");
      return;
    }
    let params: any = {
      refTableNames: [],
      refIds: []
    };
    (curTimePointObj?.source || []).forEach((item: any) => {
      params.refTableNames.push(item.tableName);
      params.refIds.push(item.id);
    });
    params.newValue = curValue || "";

    let apiHandler = handleUpdateIndicatorValue;
    // 兼容抽取数据失败，无溯源的指标，调用新接口
    if (params.refIds.length === 0 && params.refTableNames.length === 0) {
      params = {
        dateType: isBop ? 0 : 1,
        fixedValue: curValue || "",
        indicatorUnit: "元",
        indicatorName: item.indicatorName
      };
      apiHandler = handleAddIndicatorValue;
    }
    try {
      await apiHandler(params);
      setDispalyInput("");
    } catch (e) {
      curSetStateFn(curValueRef.current);
      setDispalyInput("");
    }
  };

  const handleCloseModal = () => {
    const { type } = delItemInfo;
    const isBop = type === "bop";
    const curValueRef = isBop ? bopValueRef : eopValueRef;
    const curSetStateFn = isBop ? setBopValue : setEopValue;
    curSetStateFn(curValueRef.current);
    setDispalyInput("");
    setDelItemInfo(initDelItemInfo);
  };
  const handleConfirmModal = async () => {
    const { curItem, type } = delItemInfo;
    const isBop = type === "bop";
    const curValueRef = isBop ? bopValueRef : eopValueRef;
    const curSetStateFn = isBop ? setBopValue : setEopValue;
    const curValue = isBop ? bopValue : eopValue;
    let params: any = {
      refTableNames: [],
      refIds: []
    };
    (curItem?.source || []).forEach((item: any) => {
      params.refTableNames.push(item.tableName);
      params.refIds.push(item.id);
    });
    params.newValue = curValue || "";
    try {
      setDelItemInfo(initDelItemInfo);
      await handleUpdateIndicatorValue(params);
      setDispalyInput("");
    } catch (e) {
      curSetStateFn(curValueRef.current);
      setDispalyInput("");
    }
  };

  return (
    <>
      <DeleteConfirm
        isShowDeleteModal={delItemInfo.open}
        closeModal={handleCloseModal}
        confirmModal={handleConfirmModal}
        content="删除后不能恢复，是否确认删除"
        loading={false}
      />
      <div className="w-full h-[48px] box-border flex px-[15px] items-center text-[#2a2a2a] font-[14px] border-0 border-b-[1px] border-[#E4E8F6] border-solid hover:bg-[#F5F5F5]">
        <div
          className="flex items-center w-[calc(100%-500px)]"
          style={{
            paddingLeft: `${depth * 32}px`
          }}
        >
          <div className="w-[24px] h-[48px] flex items-center">
            {subIndicators && !!subIndicators.length && (
              <CaretDownOutlined
                className="text-[16px] cursor-pointer text-[#888888]"
                rotate={expanded ? 0 : -90}
                onClick={() => setExpanded(!expanded)}
              />
            )}
          </div>
          <div className="truncate flex-1" title={indicatorName || "--"}>
            {indicatorName || "--"}
          </div>
        </div>
        <div className="w-[250px] flex justify-end items-center">
          {dispalyInput === "bop" ? (
            <Input
              autoFocus
              value={bopValue}
              onChange={(e) => handleTimePoint("bop", e.target.value)}
              onBlur={() => handleSubmitValue("bop")}
            />
          ) : (
            <>
              {bop ? (
                <span
                  className="cursor-pointer h-[32px] inline-block text-right w-[150px] leading-[32px] rounded hover:border-[1px] hover:border-solid hover:border-[#d9d9d9]"
                  onClick={() => handleClickDisplayValue("bop", bop)}
                >
                  {formatThousandComma(bopValue) || ""}
                </span>
              ) : (
                <span
                  className="block h-8 cursor-pointer w-[150px] rounded hover:border-[1px] hover:border-solid hover:border-[#d9d9d9]"
                  onClick={() => handleClickDisplayValue("bop")}
                />
              )}
            </>
          )}
          <span onClick={() => handleClickItem("bop", bop)}>
            {getItemValueIcon(bop)}
          </span>
        </div>
        <div className="w-[250px]  flex justify-end items-center">
          {dispalyInput === "eop" ? (
            <Input
              autoFocus
              value={eopValue}
              onChange={(e) => handleTimePoint("eop", e.target.value)}
              onBlur={() => handleSubmitValue("eop")}
            />
          ) : (
            <>
              {eop ? (
                <span
                  className="cursor-pointer h-[32px] inline-block text-right w-[150px] leading-[32px] rounded hover:border-[1px] hover:border-solid hover:border-[#d9d9d9]"
                  onClick={() => handleClickDisplayValue("eop", eop)}
                >
                  {formatThousandComma(eopValue) || ""}
                </span>
              ) : (
                <span
                  className="block h-8 cursor-pointer w-[150px] rounded hover:border-[1px] hover:border-solid hover:border-[#d9d9d9]"
                  onClick={() => handleClickDisplayValue("eop")}
                />
              )}
            </>
          )}
          <span onClick={() => handleClickItem("eop", eop)}>
            {getItemValueIcon(eop)}
          </span>
        </div>
      </div>
      {expanded && children}
    </>
  );
};

export default TableItem;
