import { useState } from "react";
import { Tooltip } from "antd";
import { ReactComponent as MaskIcon } from "@/assets/svg/maskIcon.svg";
import { EllipsisOutlined } from "@ant-design/icons";
import { ReactComponent as Clock } from "@/assets/svg/clock.svg";
import dayjs from "dayjs";
import { v4 as uuidv4 } from "uuid";

enum PermissionCode {
  Usage = 1,
  Edit = 2,
  Manage = 3
}

enum TempOperations {
  Preview = "preview",
  Edit = "edit",
  Copy = "copy",
  Delete = "delete",
  Vision = "vision",
  Auth = "auth",
  ToWrite = "toWrite"
}

const permissionMap = {
  [PermissionCode.Usage]: [TempOperations.Preview],
  [PermissionCode.Edit]: [
    TempOperations.Preview,
    TempOperations.Edit,
    TempOperations.Copy,
    TempOperations.Vision
  ],
  [PermissionCode.Manage]: [
    TempOperations.Preview,
    TempOperations.Edit,
    TempOperations.Copy,
    TempOperations.Vision,
    TempOperations.Delete
  ]
};

const btns = [
  { label: "预览", key: TempOperations.Preview },
  { label: "删除", key: TempOperations.Delete }
  // { label: "去写作", key: "toWrite" },
];

const getOperationBtnOpts = ({ code }: { code: PermissionCode }) => {
  return btns.filter((i) => permissionMap[code].includes(i.key));
};

const HomeCard = (props: any) => {
  const { item, handleEvent } = props;

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
      key={item.id}
      className="cardBox relative px-[5px] w-[162px] h-[138px] rounded-[8px] cursor-pointer pt-[20px] pl-[16px]"
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
      <MaskIcon />
      <div
        className="mt-[3px] w-[130px] line-clamp-1 overflow-ellipsis break-words text-text-color1 font-bold text-[16px]"
        title={item.name}
      >
        {item.name}
      </div>
      <div className="mt-[4px] w-[130px] line-clamp-1 overflow-ellipsis break-words text-text-color3 text-[12px]">
        {item.promptTemplateUser || "简介"}
      </div>
      <div className="mt-[4px] flex justify-between">
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
          title={
            <div className="w-[68px] text-center leading-[32px]">
              {getOperationBtnOpts({ code: item?.permission || 1 }).map(
                (btn: any) => {
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
                }
              )}
            </div>
          }
          color={"#fff"}
        >
          <EllipsisOutlined
            className="hover:bg-[#F1F5FF] hover:text-[#055AFF] cursor-pointer"
            onClick={(e) => e.stopPropagation()}
          />
        </Tooltip>
      </div>
      {/* {showAction && (
        <div
          className={`absolute flex justify-between items-center bottom-[1px] w-[calc(100%-2px)] left-[1px] h-[40px] bg-[linear-gradient(#FFFFFF,#F0F5FF)] rounded-b-[8px] opacity-85`}
        >
          <Button
            type="link"
            className="w-full"
            disabled={!item.hasFormatTemplate}
            onClick={() => handleEvent("preview", item)}
          >
            预览
          </Button>
          <Button
            type="link"
            className="w-full"
            onClick={() => handleEvent("toWrite", item)}
          >
            去写作
          </Button>
        </div>
      )} */}
    </div>
  );
};

export default HomeCard;
