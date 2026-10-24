import { cn } from "@udecode/cn";
const closeSize = 0;
const ModulesWraper = ({ open, children }) => {
  return (
    <div
      style={{
        width: `calc(100% - ${closeSize}px)`, // 使用模板字符串来正确传递 `calc` 值
        height: "calc(100%)",
        right: closeSize,
      }}
      className={cn(
        "bg-white shadow  absolute top-0  z-[200]",
        open ? "visible" : "hidden"
      )}
    >
      <div className="h-full w-full relative">{children}</div>
    </div>
  );
};

export default ModulesWraper;
