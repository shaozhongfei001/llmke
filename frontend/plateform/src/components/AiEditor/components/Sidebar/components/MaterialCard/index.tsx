import { MinusCircleOutlined, PlusCircleOutlined } from "@ant-design/icons";
import { Tooltip } from "antd";
import xls from "@/components/AiEditor/assets/img/xls.png";
import doc from "@/components/AiEditor/assets/img/doc.png";
import pdf from "@/components/AiEditor/assets/img/pdf.png";
import ppt from "@/components/AiEditor/assets/img/ppt.png";
import jpg from "@/components/AiEditor/assets/img/jpg.png";
import png from "@/components/AiEditor/assets/img/png.png";
import other from "@/components/AiEditor/assets/img/default.png";

const FILEIMG: any = {
  docx: doc,
  doc: doc,
  pdf: pdf,
  xls: xls,
  xlsx: xls,
  ppt: ppt,
  pptx: ppt,
  pub: ppt,
  jpg: jpg,
  png: png,
  default: other,
};

export interface Item {
  id: string | number;
  fileName?: string;
  fileSuffix?: string;
  fileUrl?: string;
  fileSize?: number;
  [key: string]: any;
}

interface Iprops {
  item: Item;
  type: "add" | "del";
  itemClick?: ({ type, item }) => any;
}

export const MaterialCard = (props: Iprops) => {
  const { item, type = "add", itemClick } = props;
  const handleClick = () => {
    itemClick && itemClick({ type, item });
  };
  return (
    <div className="flex justify-center flex-col items-center p-[12px] h-[162px] w-[212px] box-border rounded-[8px] shadow-md border-[1px] border-solid border-[#EDEDED] active:border-[#014DDF] hover:bg-[#F7FAFF] relative">
      <div
        className="absolute right-[15px] top-[15px] cursor-pointer"
        onClick={handleClick}
      >
        {type === "add" ? (
          <PlusCircleOutlined
            style={{
              fontSize: "16px",
              color: "#0067DE",
            }}
          />
        ) : (
          <MinusCircleOutlined
            style={{
              fontSize: "16px",
              color: "#F0594C",
            }}
          />
        )}
      </div>
      <img
        src={FILEIMG[item?.fileSuffix || "default"] || FILEIMG["default"]}
        alt="ellipse"
        className="w-[46px] h-[46px] mr-[6px]"
      />
      <div className="w-[180px] h-[42px] text-[14px] font-medium mt-[20px] line-clamp-2 overflow-ellipsis break-words">
        <Tooltip title={item.fileName}>{item.fileName}</Tooltip>
      </div>
    </div>
  );
};
