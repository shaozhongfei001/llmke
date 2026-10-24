import { Outlet } from "react-router-dom";

interface SystemContainerProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
}
export default function SystemContainer({
  children,
  title,
  description
}: SystemContainerProps) {
  return (
    <div className="flex justify-start items-start ml-5 flex-col h-full w-[98%] relative">
      <div className="flex h-[42px]  z-10 bg-transparent gap-x-2 pb-2 flex-row items-center justify-start  w-full">
        <div className=" text-md font-medium">{title}</div>
        <div className=" description text-sm text-gray-500">{description}</div>
      </div>
      <div className="flex  flex-col w-full bg-white border border-white/20 shadow-sm rounded-[8px] h-[calc(100%-40px)]">
        {children}
      </div>
    </div>
  );
}
