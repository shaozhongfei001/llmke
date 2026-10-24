import { useState } from "react";
import { Button } from "antd";
import { ReactComponent as MaskIcon } from "@/assets/svg/maskIcon.svg";
import { DeleteOutlined } from "@ant-design/icons";

const TCard = (props: any) => {
  const { item, handleEvent } = props;
  const [showAction, setShowAction] = useState(false);

  return (
    <div
      key={item.id}
      className="cardBox relative px-[5px] w-[162px] h-[138px] rounded-[8px] cursor-pointer pt-[20px] pl-[16px]"
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
                background: "linear-gradient(180deg, #FFEEDF 0%, #FEF9F2 100%)",
              }}
              className="absolute top-0 right-0 rounded-tr-lg rounded-bl-lg px-2 py-[2px] text-[#F58020]"
            >
              格式模板
            </div>
          )}
        </>
      )}
      <MaskIcon />
      <div>
        <div className="mt-[3px] w-[130px] line-clamp-1 overflow-ellipsis break-words text-text-color1 font-bold text-[16px]">
          {item.name}
        </div>
        <div className="mt-[12px] w-[130px] line-clamp-1 overflow-ellipsis break-words text-text-color3 text-[12px]">
          {item.promptTemplateUser || "简介"}
        </div>
      </div>
      {showAction && (
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
      )}
    </div>
  );
};

export default TCard;
