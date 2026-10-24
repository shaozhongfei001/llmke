import { ELEMENT_TYPE } from "@root/src/const/permission";
import IconHeader from "@root/src/pages/Components/IconHeader";
import RightIcon from "./rightIcon";

const TreeListItem = ({
  item,
  selected,
  handleEvent
}: {
  item: { name: string; id: string; type?: string };
  selected: string;
  handleEvent: (type: string, data?: any) => void;
}) => {
  return (
    <div
      className="h-[43px] bg-[#F3F6FF] rounded-[4px] px-[8px] flex items-center cursor-pointer"
      onClick={() => handleEvent && handleEvent("clickItem", item)}
      style={{
        background: selected === item.id ? "#F3F6FF" : "#fff"
      }}
    >
      <IconHeader
        text={item.name}
        rounded={item.type === "company" ? "" : "rounded-full"}
        type={ELEMENT_TYPE.USER}
      />
      <div
        className={`${selected === item.id ? "text-primary-color" : "text-text-color1"} text-[14px] w-[150px]`}
      >
        {item.name}
      </div>
      <RightIcon
        type={0}
        className={`${selected === item.id ? "text-primary-color" : "text-text-color1"} mr-[5px]`}
        handleEvent={(type) =>
          handleEvent && handleEvent("clickRightIcon", { type, item })
        }
      />
    </div>
  );
};

export default TreeListItem;
