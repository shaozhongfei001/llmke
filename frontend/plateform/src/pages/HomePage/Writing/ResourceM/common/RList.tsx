import {
  DeleteOutlined,
  FolderAddOutlined,
  RedoOutlined
} from "@ant-design/icons";
import { Button, Popover, Flex } from "antd";
import ellipse from "@/assets/writing/ellipse.png";
import dots from "@/assets/writing/dots3.png";
import xls from "@/assets/writing/xls.png";
import doc from "@/assets/writing/doc.png";
import pdf from "@/assets/writing/pdf.png";
import ppt from "@/assets/writing/ppt.png";
import dayjs from "dayjs";

const FILEIMG: any = {
  docx: doc,
  doc: doc,
  pdf: pdf,
  xls: xls,
  xlsx: xls,
  ppt: ppt,
  pptx: ppt,
  pub: ppt
};

enum STATUS {
  NORMAL = 1,
  PARSING,
  SUCCESS,
  FAIL
}

export const RList = (props: any) => {
  const { item, showWarning, handleAddDoc } = props;

  const getTag = (item: any) => {
    const { state } = item;
    if (!state) return;
    switch (state) {
      case STATUS.PARSING:
        return (
          <span className="text-[10px] py-[2px] px-[6px] bg-[#E8F3FF] rounded text-[#014DDF] absolute right-[10px] top-[10px]">
            解析中
          </span>
        );
      case STATUS.SUCCESS:
        return (
          <span className="text-[10px] py-[2px] px-[6px] bg-[#EDFFEC] rounded text-[#36AB38] absolute right-[10px] top-[10px]">
            解析成功
          </span>
        );
      case STATUS.FAIL:
        return (
          <span
            className="text-[10px] py-[2px] px-[6px] bg-[#FFECE8] rounded text-[#ED5A41] absolute right-[10px] top-[10px]"
            onClick={(e) => {
              e.stopPropagation();
              handleAddDoc("retryParse", item);
            }}
          >
            <RedoOutlined className="mr-1" />
            解析失败
          </span>
        );
      default:
        break;
    }
  };

  return (
    <div>
      <div
        className="flex cursor-pointer bg-white justify-center flex-col items-center p-[12px] h-[162px]   rounded-[8px] shadow-md border-[1px] border-solid border-[#EDEDED] active:border-[#014DDF] hover:bg-[#F7FAFF] relative"
        onClick={() => {
          handleAddDoc("detail", item);
        }}
      >
        {getTag(item)}
        <img
          src={FILEIMG[item.fileSuffix] || doc}
          alt="ellipse"
          className="w-[46px] h-[46px] mr-[6px]"
        />
        <div className=" font-medium mt-[20px]  line-clamp-2 overflow-ellipsis break-words text-center">
          {item.fileName}
        </div>
      </div>
      <div className="flex justify-between items-center mt-[12px] mb-[30px]">
        <div className=" text-[#666] text-[14px] text-ellipsis overflow-hidden">
          {item.gmtModified &&
            dayjs(item.gmtModified).format("YYYY-MM-DD HH:mm:ss")}
        </div>
        <Popover
          placement="rightTop"
          content={
            <Flex vertical>
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
      </div>
    </div>
  );
};
