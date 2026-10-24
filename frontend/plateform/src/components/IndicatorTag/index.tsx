import { CloseOutlined } from "@ant-design/icons";
import { useEffect, useMemo } from "react";

interface Item {
  label: string;
  value: string;
}
interface Iprops {
  item: Item;
  handleClickTag?: (item: Item) => any;
  active?: string;
  width?: number | string;
  handleDel?: (item: Item) => any;
}
const IndicatorTag = ({
  item,
  handleClickTag,
  active = "",
  handleDel
}: Iprops) => {
  const handleClick = () => {
    handleClickTag && handleClickTag(item);
  };

  const isActive = useMemo(() => {
    return active === item.value;
  }, [active, item.value]);

  return (
    <div
      className="text-[14px] rounded px-3 flex gap-1 justify-center items-center h-[32px] cursor-pointer"
      onClick={handleClick}
      style={{
        color: isActive ? "#055aff" : "#2A2A2A",
        background: isActive ? "#e2e9ff" : "#F5F6FA",
        width: ["bop", "eop"].includes(item.value) ? "100%" : ""
      }}
    >
      {item.label || "--"}
      {handleDel && (
        <CloseOutlined
          onClick={(e) => {
            e.stopPropagation();
            handleDel && handleDel(item);
          }}
        />
      )}
    </div>
  );
};
export default IndicatorTag;
