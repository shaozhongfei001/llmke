import { MoreOutlined } from "@ant-design/icons";
import { Popover } from "antd";
import { useMemo, useState } from "react";

const RightIcon = ({
  type,
  className,
  handleEvent,
  disabled
}: {
  type: number;
  className: string;
  handleEvent: (type: string, data: any) => void;
  disabled?: boolean;
}) => {
  const [open, setOpen] = useState(false);

  const getItems = useMemo(() => {
    const items = [
      { name: "编辑部门", key: "edit" },
      { name: "添加子部门", key: "add" },
      // { name: "上移", key: "pre" },
      // { name: "下移", key: "next" },
      { name: "删除", key: "delete" }
    ];
    switch (type) {
      case 0:
        return [
          { name: "编辑部门", key: "edit" },
          { name: "添加子部门", key: "add" }
        ];
      // case 1:
      //   items.splice(2, 1);
      //   return items;
      // case 2:
      //   return items;
      // case 3:
      //   items.splice(3, 1);
      //   return items;
      // case 4:
      //   items.splice(2, 2);
      //   return items;
      default:
        return items;
    }
  }, [type]);
  return (
    <Popover
      placement="rightTop"
      open={open}
      onOpenChange={(open: boolean) => {
        setOpen(open);
      }}
      content={
        <div className="w-[82px]">
          {getItems.map((item: any, index: number) => {
            return (
              <div
                key={item.key}
                className={`${disabled ? "cursor-not-allowed text-text-color2" : "cursor-pointer text-primary-color"} rounded-[4px] text-[14px] py-[4px] hover:bg-[#fafafa] px-[6px]`}
                onClick={(e) => {
                  if (disabled) return;
                  e.stopPropagation();
                  setOpen(false);
                  handleEvent && handleEvent(item.key, item);
                }}
              >
                {item.name}
              </div>
            );
          })}
        </div>
      }
      arrow={false}
      trigger="click"
    >
      <MoreOutlined
        onClick={(e) => {
          e.stopPropagation();
        }}
        className={`text-primary-color cursor-pointer ${className}`}
      />
    </Popover>
  );
};

export default RightIcon;
