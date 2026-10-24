import { ReactNode } from "react";

const LayoutCom = ({
  title,
  children
}: {
  title: string;
  children: ReactNode;
}) => {
  return (
    <div className="w-full h-full">
      <div className="mb-[20px] font-bold text-[16px]">{title}</div>
      <div className="h-[calc(100%-40px)] bg-white rounded-[8px]">
        {children}
      </div>
    </div>
  );
};

export default LayoutCom;
