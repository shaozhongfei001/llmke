import { ReactComponent as Model } from "@/assets/svg/model.svg";
import { ReactComponent as Clock } from "@/assets/svg/clock.svg";
import { ReactComponent as Divider } from "@/assets/svg/divider.svg";
import dayjs from "dayjs";
import xls from "@/assets/writing/xls.png";
import doc from "@/assets/writing/doc.png";
import pdf from "@/assets/writing/pdf.png";
import ppt from "@/assets/writing/ppt.png";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "antd";
export const FILEIMG: any = {
  docx: doc,
  doc: doc,
  pdf: pdf,
  xls: xls,
  xlsx: xls,
  ppt: ppt,
  pptx: ppt,
  pub: ppt
};

const styleTagMap = [
  {
    key: "all",
    label: "全部"
  },
  {
    key: "notice",
    label: "通知公告"
  },
  {
    key: "report",
    label: "工作报告"
  },
  {
    key: "survey",
    label: "调研报告"
  },
  {
    key: "invitation",
    label: "邀请函"
  },
  {
    key: "understanding",
    label: "心得体会"
  },
  {
    key: "speech",
    label: "讲话稿"
  },
  {
    key: "other",
    label: "其他"
  }
];

const senceTagMap = [
  {
    key: "all",
    label: "全部"
  },
  {
    key: "bank",
    label: "银行"
  },
  {
    key: "insurance",
    label: "保险"
  },
  {
    key: "security",
    label: "证券"
  },
  {
    key: "other",
    label: "其他"
  }
];
export const TCard = (props: any) => {
  const { item, btns = [], handleEvent, activeKey } = props;
  const [showAction, setShowAction] = useState(false);
  enum STATUS {
    NORMAL = 1,
    PARSING,
    SUCCESS,
    FAIL
  }
  const getStatus = (item: any) => {
    const { state } = item;
    if (!state) return;
    switch (state) {
      case STATUS.PARSING:
        return (
          <span className="text-[12px] py-[2px] px-[6px] bg-[#E8F3FF]  rounded-tr-[8px] rounded-bl-[8px] text-[#014DDF] absolute right-[1px] top-[1px]">
            解析中
          </span>
        );
      case STATUS.SUCCESS:
        return (
          <span className="text-[12px] py-[2px] px-[6px] bg-[#EDFFEC] rounded-tr-[8px] rounded-bl-[8px] text-[#36AB38] absolute right-[1px] top-[1px]">
            解析成功
          </span>
        );
      case STATUS.FAIL:
        return (
          <span
            className="text-[12px] py-[2px] px-[6px] bg-[#FFECE8]  rounded-tr-[8px] rounded-bl-[8px] text-[#ED5A41] absolute right-[1px] top-[1px]"
            onClick={(e) => {
              e.stopPropagation();
              handleEvent("retryParse", item);
            }}
          >
            解析失败
          </span>
        );
      default:
        break;
    }
  };

  const getTag = (item: any, activeKey: string) => {
    const articleStyle =
      styleTagMap.find((s) => s.key == item.articleStyle)?.label || "";
    const sence = senceTagMap.find((s) => s.key == item.scene)?.label || "";
    switch (activeKey) {
      case "demoLib":
        {
          if (item.articleStyle && item.scene) {
            return (
              <div className="h-[20px] mx-[4px] leading-[20px]">
                {articleStyle} · {sence}
              </div>
            );
          } else {
            return (
              <div className="h-[20px] mx-[4px] leading-[20px]">
                {articleStyle || sence}
              </div>
            );
          }
        }
        return;
      case "lawLib":
        return <div className="h-[20px] mx-[4px] leading-[20px]">{sence}</div>;
    }
  };

  const btnDisable = useCallback(
    (btn: any) => {
      if (btn.key == "toPreview") {
        return (
          !["pdf", "txt", "html", "csv", "img"].includes(item.fileSuffix) &&
          (!item.htmlUrl || JSON.parse(item.htmlUrl).length == 0)
        );
      }
      if (btn.key === "toWrite") {
        return (
          !["docx", "doc"].includes(item.fileSuffix) ||
          item.bizType === "lawLib" ||
          !item.htmlUrl
        );
      }
      return true;
    },
    [item]
  );

  return (
    <div
      className="bg-white cursor-pointer min-w-[206px] items-start p-[16px] h-[126px] rounded-[8px] shadow-md border-[1px] border-solid border-[#EDEDED] hover:border-primary-color"
      onMouseOver={() => setShowAction(true)}
      onMouseLeave={() => setShowAction(false)}
    >
      {getStatus(item)}
      <div className="mt-[8px]">
        <div className="text-[16px] font-bold line-clamp-2 text-ellipsis break-words h-[50px]">
          {item.fileName}
        </div>

        <div className="flex mt-[8px] text-[12px] text-text-color3 line-clamp-1 text-ellipsis break-words items-center justify-between">
          <div className="flex flex-row bg-[#E0EEFF]  rounded-[4px] items-center">
            <img
              src={FILEIMG[item.fileSuffix] || doc}
              alt="ellipse"
              className="w-[20px] h-[20px] bg-[#FFFFFF]"
            />
            {getTag(item, activeKey)}
          </div>
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
            if (index === 0) {
              return (
                <Button
                  type="link"
                  className="w-full"
                  // disabled={!allowOperation}
                  onClick={() => handleEvent(btn.key, item)}
                >
                  {btn.label}
                </Button>
              );
            } else {
              return (
                <>
                  <Divider className=" shrink-0" />
                  <Button
                    type="link"
                    className="w-full"
                    disabled={btnDisable(btn)}
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
