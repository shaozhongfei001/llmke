import { ReactComponent as MaskIcon } from "@/assets/svg/maskIcon.svg";
import { ReactComponent as Clock } from "@/assets/svg/clock.svg";
import dayjs from "dayjs";
import { v4 as uuidv4 } from "uuid";

import { useEffect, useState } from "react";
import { Tooltip } from "antd";
import { EllipsisOutlined } from "@ant-design/icons";

const TemplateCard = (props: any) => {
  const { item, btns = [], handleEvent } = props;

  const btnDisabled = (key: any) => {
    switch (key) {
      case "preview":
        return !item.hasFormatTemplate;
      case "toWrite":
        return item?.state == 0;
      default:
        return false;
    }
  };

  return (
    <div
      className="bg-white cursor-pointer min-w-[206px] items-start p-[16px] h-[138px] rounded-[8px] shadow-md  relative hover:border-[1px] hover:border-solid hover:border-[#055aff]"
      style={{
        cursor: btnDisabled("toWrite") ? "not-allowed" : "pointer"
      }}
      onClick={() => {
        if (btnDisabled("toWrite")) {
          return;
        } else {
          handleEvent("toWrite", item);
        }
      }}
    >
      <>
        {item.hasFormatTemplate && (
          <div
            style={{
              background: "linear-gradient(180deg, #FFEEDF 0%, #FEF9F2 100%)"
            }}
            className="absolute top-0 right-0 rounded-tr-lg rounded-bl-lg px-2 py-[2px] text-[#F58020]"
          >
            格式模板
          </div>
        )}
        {item.state == 0 && (
          <div
            style={{
              background: "linear-gradient(180deg, #ECECFF 0%, #F2F2FF 100%)"
            }}
            className="absolute top-0 right-0 rounded-tr-lg rounded-bl-lg px-2 py-[2px] text-[#055AFF]"
          >
            编辑中
          </div>
        )}
      </>
      <MaskIcon className="w-[36px] h-[36px]" />
      <div>
        <div
          className="text-[16px] font-bold mt-[10px] line-clamp-1 text-ellipsis break-words"
          title={item.name}
        >
          {item.name}
        </div>
        <div className="mt-[8px] flex justify-between">
          <div className="flex text-[12px] text-text-color3 line-clamp-1 text-ellipsis break-words items-center">
            <Clock className="w-[12px] h-[12px] mr-[4px] shrink-0" />
            <div className=" line-clamp-1 text-ellipsis break-words">
              {item.gmtModified && dayjs(item.gmtModified).format("YYYY-MM-DD")}
            </div>
          </div>
          <Tooltip
            className="inline-block"
            placement="right"
            arrow={false}
            overlayInnerStyle={{
              padding: 0
            }}
            zIndex={1000}
            trigger="hover"
            title={
              <div className="w-[68px] text-center leading-[32px]">
                {btns.map((btn: any) => {
                  const disabled = btnDisabled(btn.key);
                  return (
                    <div
                      key={uuidv4()}
                      className="text-[#555555] hover:bg-[#F1F5FF] w-full"
                      style={{
                        cursor: disabled ? "not-allowed" : "pointer"
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        !disabled && handleEvent(btn.key, item);
                      }}
                    >
                      {btn.label}
                    </div>
                  );
                })}
              </div>
            }
            color={"#fff"}
          >
            <EllipsisOutlined
              className="hover:bg-[#F1F5FF] hover:text-[#055AFF] cursor-pointer h-6 px-1 text-base rounded pt-[2px]"
              onClick={(e) => e.stopPropagation()}
            />
          </Tooltip>
        </div>
      </div>
    </div>
  );
};

export default TemplateCard;
