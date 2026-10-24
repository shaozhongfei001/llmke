import { ReactComponent as MaskIcon } from "@/assets/svg/maskIcon.svg";
import { ReactComponent as Clock } from "@/assets/svg/clock.svg";
import dayjs from "dayjs";
import { v4 as uuidv4 } from "uuid";

import { useEffect, useState } from "react";
import { Popover } from "antd";
import { EllipsisOutlined } from "@ant-design/icons";
import { PrimaryBtn } from "../../common/components/PrimaryBtn";

export const TCard = (props: any) => {
  const { item, btns = [], handleEvent } = props;
  const [showMask, setShowMask] = useState(false);
  const [showFuncMenu, setShowFuncMenu] = useState(false);

  const changeFuncMenu = () => {
    setShowFuncMenu(!showFuncMenu);
  };

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

  useEffect(() => {
    showMask === false && setShowFuncMenu(false);
  }, [showMask]);

  return (
    <div
      className="bg-white mr-[24px] mb-[16px] cursor-pointer min-w-[206px] items-start p-[16px] h-[138px] rounded-[8px] shadow-md border-[1px] border-solid border-[#EDEDED] relative"
      onMouseOver={() => setShowMask(true)}
      onMouseLeave={() => setShowMask(false)}
    >
      {/* 蒙版层，功能按钮 */}
      <div
        className="w-full h-full rounded-[8px]"
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          zIndex: 1,
          display: showMask ? "block" : "none",
          background: "rgba(0,0,0,0.5)"
        }}
      >
        <div className="w-full h-full flex items-center justify-center gap-2">
          <Popover
            content={
              <div className="bg-white rounded-[4px] py-2">
                {btns.map((btn: any) => {
                  const disabled = btnDisabled(btn.key);
                  return (
                    <div
                      key={uuidv4()}
                      className="hover:bg-[#f1f5ff]"
                      style={{
                        cursor: disabled ? "not-allowed" : "pointer",
                        padding: "6px 20px",
                        whiteSpace: "nowrap",
                        zIndex: 9999,
                        display: "flex",
                        alignItems: "center"
                      }}
                      onClick={() => !disabled && handleEvent(btn.key, item)}
                    >
                      {btn.label}
                    </div>
                  );
                })}
              </div>
            }
            open={showFuncMenu}
            arrow={false}
            placement="bottomLeft"
            overlayInnerStyle={{
              padding: 0
            }}
          >
            <div
              className="bg-white w-[32px] h-[32px] rounded-[4px] flex items-center justify-center"
              onClick={changeFuncMenu}
            >
              <EllipsisOutlined style={{ fontSize: "16px" }} />
            </div>
          </Popover>
          <PrimaryBtn
            className="w-[96px] h-[32px] font-bold text-[16px]"
            disabled={btnDisabled("toWrite")}
            style={{
              cursor: btnDisabled("toWrite") ? "not-allowed" : "pointer"
            }}
            onClick={() => handleEvent("toWrite", item)}
          >
            去写作
          </PrimaryBtn>
        </div>
      </div>
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
        <div className="text-[16px] font-bold line-clamp-1 text-ellipsis break-words">
          {item.name}
        </div>
        <div className="mt-[8px] text-[12px] text-text-color3 line-clamp-1 text-ellipsis break-words">
          {item.promptTemplateUser}
        </div>
        <div className="flex mt-[8px] text-[12px] text-text-color3 line-clamp-1 text-ellipsis break-words items-center">
          <Clock className="w-[12px] h-[12px] mr-[4px] shrink-0" />
          <div className=" line-clamp-1 text-ellipsis break-words">
            {item.gmtModified && dayjs(item.gmtModified).format("YYYY-MM-DD")}
          </div>
        </div>
      </div>
    </div>
  );
};
