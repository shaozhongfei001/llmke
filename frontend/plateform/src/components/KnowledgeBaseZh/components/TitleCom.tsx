import { useEffect, useMemo, useState } from "react";
import { Tooltip } from "antd";

const OTHERS_WIDTH = 1165;

const TitleCom = ({
  title,
  isFolder,
  icon,
  handleClick
}: {
  title: string;
  isFolder: boolean;
  icon: any;
  handleClick: any;
}) => {
  const [windowSize, setWindowSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight
  });

  useEffect(() => {
    // 处理窗口大小变化的函数
    function handleResize() {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight
      });
    }

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  const cellWidth = useMemo(() => {
    const r = (windowSize.width || 1200) - OTHERS_WIDTH;
    return Math.max(160, r);
  }, [windowSize]);

  return (
    <div
      onClick={handleClick}
      className={`${isFolder ? "text-[#2a2a2a]" : "text-[#305eba]"} cursor-pointer flex`}
    >
      {icon}
      <Tooltip placement="topLeft" title={title}>
        <span className={`break-words break-all text-ellipsis line-clamp-1`}>
          {title}
        </span>
      </Tooltip>
    </div>
  );
};

export default TitleCom;
