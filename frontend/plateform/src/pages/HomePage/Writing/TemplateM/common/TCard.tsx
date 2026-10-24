import { ReactComponent as MaskIcon } from "@/assets/svg/maskIcon.svg";
import { ReactComponent as Clock } from "@/assets/svg/clock.svg";
import { ReactComponent as Divider } from "@/assets/svg/divider.svg";
import dayjs from "dayjs";
import { v4 as uuidv4 } from "uuid";

import { useState } from "react";
import { Button } from "antd";
import { DeleteOutlined } from "@ant-design/icons";

export const TCard = (props: any) => {
  const { item, btns = [], handleEvent } = props;
  const [showAction, setShowAction] = useState(false);

  return (
    <div
      className="bg-white mr-[24px] mb-[16px] cursor-pointer min-w-[206px] items-start p-[16px] h-[154px] rounded-[8px] shadow-md border-[1px] border-solid border-[#EDEDED] hover:border-primary-color relative"
      onMouseOver={() => setShowAction(true)}
      onMouseLeave={() => setShowAction(false)}
    >
      {showAction ? (
        <Button
          className="absolute right-0 top-0"
          type="link"
          icon={<DeleteOutlined />}
          onClick={() => handleEvent("delete", item)}
        />
      ) : (
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
      )}
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
      {showAction && (
        <div
          className={`absolute flex justify-between items-center bottom-[1px] w-[calc(100%-2px)] left-[1px] h-[40px] bg-[linear-gradient(#FFFFFF,#F0F5FF)] rounded-b-[8px] opacity-85`}
        >
          {btns.map((btn: any, index: number) => {
            switch (btn.key) {
              case "edit":
                return (
                  <Button
                    key={uuidv4()}
                    type="link"
                    className="w-full"
                    onClick={() => handleEvent(btn.key, item)}
                  >
                    {btn.label}
                  </Button>
                );
              case "preview":
                return (
                  <>
                    <Divider className=" shrink-0" key={uuidv4()} />
                    <Button
                      key={uuidv4()}
                      type="link"
                      className="w-full"
                      disabled={!item.hasFormatTemplate}
                      onClick={() => handleEvent(btn.key, item)}
                    >
                      {btn.label}
                    </Button>
                  </>
                );
              default:
                return (
                  <>
                    <Divider className=" shrink-0" key={uuidv4()} />
                    <Button
                      key={uuidv4()}
                      type="link"
                      className="w-full"
                      disabled={item?.state == 0}
                      onClick={() => handleEvent(btn.key, item)}
                    >
                      {btn.label}
                    </Button>
                  </>
                );
            }
          })}
        </div>
      )}
    </div>
  );
};
/* <div className="flex justify-between items-center  mt-[12px] mb-[30px]">
        <div className=" text-[#666666] text-[14px] text-ellipsis overflow-hidden">
          {dayjs(item.gmtModified).format("YYYY-MM-DD")}
        </div>
        {allowOperation && (
          <Popover
            placement="rightTop"
            content={
              <Flex vertical>
                <div
                  className="menu-row"
                  onClick={() => handleAddDoc("detail", item)}
                >
                  <EditOutlined style={{ marginRight: "6px" }} />
                  编辑
                </div>
                <div
                  onClick={showWarning}
                  style={{ color: "#F0594C" }}
                  className="menu-row"
                >
                  <DeleteOutlined style={{ marginRight: "6px" }} />
                  删除
                </div>
              </Flex>
            }
            style={{ color: "red!important", flexShrink: 0 }}
          >
            <img src={dots} alt="dots" className="w-[16px] h-[16px] mr-[8px]" />
          </Popover>
        )}
      </div> */
