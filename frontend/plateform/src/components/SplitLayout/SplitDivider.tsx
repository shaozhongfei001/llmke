import React from "react";

interface SplitDividerProps {
  handleMouseDown: (e: any) => void;
  isDragging: boolean;
}

const SplitDivider: React.FC<SplitDividerProps> = (props) => {
  const { isDragging, handleMouseDown } = props;
  return (
    <div
      className={`cursor-col-resize relative h-full w-1.5 select-none group bg-transparent hover:bg-transparent transition-colors ${isDragging ? "z-10" : ""}
      `}
      onMouseDown={handleMouseDown}
    >
      <div
        className={`absolute inset-y-0 left-1/2 transform -translate-x-1/2 w-0.5 border-0 border-solid border-r border-r-[#eee]  group-hover:border-r-primary-color group-hover:border-r-2 transition-colors duration-200 ${isDragging ? "border-r-primary-color border-r-2" : ""}`}
      />
    </div>
  );
};

export default SplitDivider;
