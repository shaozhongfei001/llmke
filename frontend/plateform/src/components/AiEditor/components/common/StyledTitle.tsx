import { X } from "lucide-react";

const StyledTitle = ({ title, close }: { title: string; close: () => any }) => {
  return (
    <div className="flex justify-between items-center px-5 pt-4 pb-1 h-[43px]">
      <div className="text-[#2A2A2A] flex items-center justify-start text-[18px] font-medium">
        <div
          className="block rounded-[2px]"
          style={{
            width: "4px",
            height: "16px",
            background:
              "linear-gradient(to top, #BD9CFF 0%, #3C6DFF 69%, #0359FF 100%)",
            marginRight: "8px",
          }}
        ></div>
        <div>{title}</div>
      </div>
      <X color="#555555" className="cursor-pointer w-[16px]" onClick={close} />
    </div>
  );
};

export default StyledTitle;
