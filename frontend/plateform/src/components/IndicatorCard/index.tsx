import { ArrowLeftOutlined } from "@ant-design/icons";
import axios$ from "@root/src/apis";
import { useQuery } from "@tanstack/react-query";
import { InputNumber, message, Spin } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import IndicatorTag from "../IndicatorTag";
import "./indicatorTag.css";
/**
 * 拉平成数组
 * @param tree 树的数组
 * @param childrenKey 孩子的键名
 * @returns 扁平化后的数组
 */
export function flattenTree<T extends Record<string, any>>(
  tree: T[],
  childrenKey: string
): T[] {
  const result: T[] = [];
  function traverse(nodes: T[]) {
    for (const node of nodes) {
      result.push(node);
      if (Array.isArray(node[childrenKey]) && node[childrenKey].length > 0) {
        traverse(node[childrenKey]);
      }
    }
  }
  traverse(tree);
  return result;
}

const getTimeRangeLabel = (timeRange?: string) => {
  if (!timeRange) return "";
  return `近${timeRange.slice(1)}年 `;
};

const getTimePointLabel = (timePoint: string) => {
  const obj: any = {
    eop: "期末",
    bop: "期初"
  };
  if (!timePoint) {
    return "";
  }
  return obj[timePoint];
};

function formulaToHtml(formula: string, indicators: any[]) {
  const nNumberSuffixList: string[] = [];
  const indicatorDetailMap: Record<
    string,
    { timePoint: string; timeRange?: string }
  > = {};

  // 匹配 $数字 或 $数字-bop/eop 或 $数字-eop-N6
  const html = formula.replace(
    /\$(\d+)((?:-(?:bop|eop|N\d+))*)/g,
    (match, id, suffix) => {
      // 解析 timePoint 和 timeRange
      let timePoint = "eop";
      let timeRange = undefined;
      if (suffix) {
        // 匹配 -bop 或 -eop
        const tpMatch = suffix.match(/-(bop|eop)/);
        if (tpMatch) {
          timePoint = tpMatch[1];
        }
        // 匹配 -N数字
        const trMatch = suffix.match(/-N(\d+)/);
        if (trMatch) {
          timeRange = `N${trMatch[1]}`;
          const nStr = `-N${trMatch[1]}`;
          if (!nNumberSuffixList.includes(nStr)) {
            nNumberSuffixList.push(nStr.slice(1));
          }
        }
      }
      // 保存到 map
      indicatorDetailMap[id] = {
        timePoint,
        ...(timeRange ? { timeRange } : {})
      };

      const item = (indicators || []).find((i) => String(i.id) === id);
      if (item) {
        return `<span data-indicator="true" data-indicator-id="${
          item.id
        }" data-indicator-suffix="${
          suffix || ""
        }" contenteditable="false" class="indicator-tag-card">${
          getTimeRangeLabel(timeRange) +
          item.indicatorName +
          `${timePoint ? "（" + getTimePointLabel(timePoint) + "）" : ""}`
        }</span>`;
      }
      return match;
    }
  );
  // 返回 html、N+数字结构数组、以及id与bop/eop/Nx的映射
  return { html, nNumberSuffixList, indicatorDetailMap };
}

export interface ItemProps {
  id: number;
  indicatorName: string;
  sourceType: string;
  dataType: DataType;
  path: ItemProps[];
  description?: string;
  calculators?: string[];
  calculatorsIndicators?: any[];
  alias?: string[];
  [key: string]: any;
}
enum DataType {
  NUMBER = 1,
  RATIO = 2,
  DATE = 3,
  STRING = 4,
  OTHER = 5
}

interface Iprops {
  id: number;
  type?: "view" | "editor";
  changeFormulaDetail?: any;
  formulaDetail?: any;
  curIndex?: number;
}

const getDataTypeLabel = (dataType: DataType): string => {
  switch (dataType) {
    case DataType.NUMBER:
      return "数值";
    case DataType.RATIO:
      return "比率";
    case DataType.DATE:
      return "日期";
    case DataType.STRING:
      return "文本";
    case DataType.OTHER:
      return "其他";
    default:
      return "其他";
  }
};

const timePoint = [
  {
    label: "期初",
    value: "bop"
  },
  {
    label: "期末",
    value: "eop"
  }
];

const IndicatorCard = ({
  id,
  type = "view",
  changeFormulaDetail,
  formulaDetail,
  curIndex
}: Iprops) => {
  //存储所有的指标详情，用于公式下钻
  const [itemList, setItemList] = useState<number[]>([id]);
  const curItemId = useMemo(() => {
    return itemList[itemList.length - 1];
  }, [itemList]);

  const [curTimePoint, setCurTimePoint] = useState("");

  // 点击时间点
  const timePointClick = (item: { value: string }) => {
    if (item.value === curTimePoint) {
      changeFormulaDetail &&
        changeFormulaDetail({
          curIndex,
          obj: {
            timePoint: ""
          }
        });
      setCurTimePoint("");
      return;
    } else {
      changeFormulaDetail &&
        changeFormulaDetail({
          curIndex,
          obj: {
            timePoint: item.value
          }
        });
      setCurTimePoint(item.value);
    }
  };

  const [timeRangeArr, setTimeRangeArr] = useState([
    {
      label: "近5年",
      value: "N5"
    },
    {
      label: "近3年",
      value: "N3"
    },
    {
      label: "近1年",
      value: "N1"
    }
  ]);
  const [curTimeRange, setCurTimeRange] = useState("");
  // 点击时间范围,时间范围不是必选，可以取消
  const timeRangeClick = (item: { value: string }) => {
    if (item.value === curTimeRange) {
      changeFormulaDetail &&
        changeFormulaDetail({
          curIndex,
          obj: {
            timeRange: ""
          }
        });
      setCurTimeRange("");
    } else {
      changeFormulaDetail &&
        changeFormulaDetail({
          curIndex,
          obj: {
            timeRange: item.value
          }
        });
      setCurTimeRange(item.value);
    }
  };

  // 新增的默认选中
  const handlePressEnter = () => {
    const number = numberValue;
    if (!number) return;
    const value = "N" + number;
    const hasNumber = timeRangeArr.some((i) => value === i.value);
    if (hasNumber) {
      return;
    }
    setTimeRangeArr((p) => {
      return [
        ...p,
        {
          label: `近${number}年`,
          value: value
        }
      ];
    });
    timeRangeClick({ value });
    setNumberValue(undefined);
  };

  const handleDelTag = (item: { value: string }) => {
    const { value } = item;
    if (value === curTimeRange) {
      timeRangeClick(item);
    }
    setTimeRangeArr((p) => p.filter((i) => i.value !== value));
  };

  const [numberValue, setNumberValue] = useState();

  const queryIndicatorDetail = useQuery({
    queryKey: ["queryIndicatorDetail", curItemId],
    queryFn: () =>
      axios$.get(`/cecProxy/dw/indicator/${curItemId}`).then((res) => res?.data)
  });

  const detail: ItemProps = useMemo(() => {
    return queryIndicatorDetail.data;
  }, [queryIndicatorDetail.data]);

  // 根据公式给出active
  useEffect(() => {
    if (!formulaDetail || typeof curIndex !== "number") return;
    const activeItemInfo = formulaDetail[curIndex];
    if (activeItemInfo) {
      if (activeItemInfo?.timePoint) {
        setCurTimePoint(activeItemInfo.timePoint);
      }

      if (activeItemInfo?.timeRange) {
        const hasRange = timeRangeArr.some(
          (i) => i.value === activeItemInfo.timeRange
        );
        if (!hasRange)
          setTimeRangeArr((p) => {
            return [
              ...p,
              {
                label: `近${activeItemInfo?.timeRange.slice(1)}年`,
                value: activeItemInfo.timeRange
              }
            ];
          });

        setCurTimeRange(activeItemInfo.timeRange);
      }
    }
  }, [formulaDetail, timeRangeArr, curIndex]);

  const formulaRef = useRef<any>();

  useEffect(() => {
    if (
      !detail?.calculators ||
      !formulaRef.current ||
      !detail.calculators[0] ||
      !detail.calculatorsIndicators
    ) {
      return;
    }
    const { html } = formulaToHtml(
      detail?.calculators[0],
      detail.calculatorsIndicators
    );
    formulaRef.current.innerHTML = html;

    if (type === "editor") return;
    const container = formulaRef.current;

    // 添加点击事件委托
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.classList.contains("indicator-tag-card")) {
        e.stopPropagation();
        // 这里写你的点击逻辑，比如弹窗、下钻、console.log等
        const indicatorId = target.getAttribute("data-indicator-id");
        // 示例：打印id
        setItemList((p) => {
          return [...p, Number(indicatorId)];
        });
        // 你可以根据需要调用 setItemList、changeFormulaDetail 等
      }
    };

    container.addEventListener("click", handleClick);

    return () => {
      container.removeEventListener("click", handleClick);
    };
  }, [detail?.calculators, type]);

  return (
    <div className="w-[365px] box-border pt-5 pb-4 px-4 bg-white rounded-lg shadow-md">
      {!!detail && !queryIndicatorDetail.isLoading && (
        <div className="w-full box-border">
          {itemList.length > 1 && (
            <div className="mb-[20px]">
              <ArrowLeftOutlined
                style={{
                  color: "#2468F2"
                }}
                onClick={(e) => {
                  e.stopPropagation(); // 阻止冒泡，防止 Popover 关闭
                  const newItemList = itemList.slice(0, itemList.length - 1);
                  setItemList(newItemList);
                }}
              />
            </div>
          )}
          {itemList.length === 1 && type === "editor" && (
            <div className="border-0 border-dashed border-[#eee] border-b-[1px] mb-[20px]">
              <div>
                <div className="font-bold text-[16px] h-[16px] leading-[16px]">
                  高级配置
                </div>
                <div>
                  <div className="my-[8px]">时间点</div>
                  <div className="flex justify-between gap-3 mb-[12px]">
                    {timePoint.map((item) => {
                      return (
                        <IndicatorTag
                          item={item}
                          active={curTimePoint}
                          handleClickTag={timePointClick}
                        />
                      );
                    })}
                  </div>
                </div>
              </div>

              <div>
                <div>
                  <div className="mb-[8px]">时间范围</div>
                  <div className="flex gap-[12px] flex-wrap mb-[16px]">
                    {timeRangeArr.map((item) => {
                      const allowDel = !["N1", "N3", "N5"].includes(item.value);
                      const handleDel = allowDel ? handleDelTag : undefined;
                      return (
                        <IndicatorTag
                          item={item}
                          active={curTimeRange}
                          handleClickTag={timeRangeClick}
                          handleDel={handleDel}
                        />
                      );
                    })}

                    <InputNumber
                      autoFocus={false}
                      placeholder={"自定义"}
                      className="w-[90px]"
                      min={1}
                      onPressEnter={handlePressEnter}
                      onBlur={handlePressEnter}
                      value={numberValue}
                      onChange={(newValue: any) => {
                        setNumberValue(newValue);
                      }}
                      step={1}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
          <div className="mb-[12px] items-center w-full box-border">
            <div
              className="font-bold text-[16px] mb-[4px]"
              title={detail.indicatorName}
            >
              {detail.indicatorName}
            </div>
            <div className="flex gap-2">
              <div className="text-[12px] h-[20px] px-2 box-border text-[#5BBC48] border border-[#9DD6B0] border-solid rounded bg-[#F2FFF8] leading-5">
                {detail.sourceType}
              </div>
              <div className="text-[12px] h-[20px] px-2 box-border text-[#1886EC] rounded bg-[#E5F6FF] flex items-center leading-5 max-w-[72px]">
                {getDataTypeLabel(detail.dataType)}
              </div>
            </div>
          </div>
          <div className="mb-[12px]">
            <div className="text-[#888888] mb-[4px]">描述</div>
            <div>{detail.description || "--"}</div>
          </div>
          {detail.calculators && !!detail.calculators.length && (
            <div className="mb-[12px]">
              <div className="text-[#888888]">公式</div>
              {/* {detail.calculators.map((i) => (
                <div>{i}</div>
              ))} */}
              <div ref={formulaRef}></div>
            </div>
          )}
          {detail.alias && !!detail.alias.length && (
            <div>
              <div className="text-[#888888]">别名</div>
              <div>{detail.alias.join("、")}</div>
            </div>
          )}
        </div>
      )}
      {(!detail || queryIndicatorDetail.isLoading) && (
        <Spin tip="Loading" size="small">
          <div className="h-[480px]"></div>
        </Spin>
      )}
    </div>
  );
};

export default IndicatorCard;
