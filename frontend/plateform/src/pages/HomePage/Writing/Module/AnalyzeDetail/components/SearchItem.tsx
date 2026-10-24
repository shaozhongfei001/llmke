import { DeleteOutlined } from "@ant-design/icons";
import IndicatorCard from "@root/src/components/IndicatorCard";
import { Popover } from "antd";
import { useMemo } from "react";

enum DataType {
  NUMBER = 1,
  RATIO = 2,
  DATE = 3,
  STRING = 4,
  OTHER = 5
}

export interface ItemProps {
  id: number;
  indicatorName: string;
  sourceType: string;
  dataType: DataType;
  path: ItemProps[];
  [key: string]: any;
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

interface Iprops {
  detail: ItemProps;
  itemClick?: (item: ItemProps) => void;
  delItem?: (item: ItemProps) => void;
}

// 用 forwardRef 包裹
const SearchItem = ({ detail, itemClick, delItem }: Iprops) => {
  const pathStr = useMemo(() => {
    return (detail.path || [])
      .map((item: ItemProps) => item.indicatorName)
      .join(" / ");
  }, [detail.path]);

  const handleItemClick = () => {
    itemClick && itemClick(detail);
  };

  const handleDelItem = (e: React.MouseEvent) => {
    delItem && delItem(detail);
  };

  return (
    <Popover
      destroyOnHidden
      content={<IndicatorCard id={detail.id}></IndicatorCard>}
      placement="right"
      arrow={false}
      styles={{
        body: {
          padding: 0,
          boxSizing: "border-box",
          borderRadius: "8px",
          width: "364px"
        }
      }}
    >
      <div
        className="py-3 px-4 rounded bg-[#FAFAFA] cursor-pointer hover:bg-[#F1F5FF] h-[66px] box-border mb-1 w-full flex justify-between items-center"
        onClick={handleItemClick}
      >
        <div className=" w-[calc(100%-24px)]">
          <div className="flex gap-2">
            <div className="max-w-[70%] truncate">{detail.indicatorName}</div>
            <div className="text-[12px] text-[#5BBC48] border border-[#9DD6B0] border-solid rounded px-1 bg-[#F2FFF8] truncate">
              {detail.sourceType}
            </div>
            <div className="text-[12px] text-[#1886EC] rounded px-1 bg-[#E5F6FF] max-w-[72px] min-w-[25px] truncate leading-24">
              {getDataTypeLabel(detail.dataType)}
            </div>
          </div>
          <div className="mt-2 truncate text-[12px] text-[#888]">
            <span title={pathStr} className="w-full truncate">
              {pathStr}
            </span>
          </div>
        </div>
        {delItem && (
          <div
            className="h-[24px] w-[24px] flex justify-center items-center cursor-pointe hover:bg-white"
            onClick={handleDelItem}
          >
            <DeleteOutlined className="text-[#888] hover:text-[#055aff]" />
          </div>
        )}
      </div>
    </Popover>
  );
};

export default SearchItem;
