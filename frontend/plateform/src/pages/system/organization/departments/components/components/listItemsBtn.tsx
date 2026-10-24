import CustomTooltip from "@root/src/components/CustomTooltip";
import { getEditPermission } from "@root/src/const/permission";
import { Popover } from "antd";

const LinkItemsBtn = ({
  handleEvent,
  item,
  disabled,
  tip
}: {
  handleEvent: (type: string, data?: any) => void;
  item: any;
  disabled?: boolean;
  tip?: any;
}) => {
  return (
    <CustomTooltip content={tip} type="warning" position="top">
      <div
        key={item.key}
        className={`text-[14px] ${disabled ? "cursor-not-allowed text-text-color2" : "cursor-pointer text-primary-color"}`}
        onClick={(e) => {
          if (disabled) return;
          e.stopPropagation();
          handleEvent && handleEvent(item.key, item);
        }}
      >
        {item.name}
      </div>
    </CustomTooltip>
  );
};

export default LinkItemsBtn;
