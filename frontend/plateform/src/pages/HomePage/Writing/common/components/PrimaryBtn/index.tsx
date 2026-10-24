import { Button } from "antd";
import { ButtonProps } from "antd/es/button/button";

// 此组件仅仅用于统一主题按钮渐变色
export const PrimaryBtn = ({ children, style, ...props }: ButtonProps) => {
  return (
    <Button
      style={{
        background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
        color: "#fff",
        border: "none",
        ...(style || {})
      }}
      {...props}
    >
      {children}
    </Button>
  );
};

// 此组件仅仅用于普通主题按钮渐变色
export const CommonBtn = ({ children, style, ...props }: ButtonProps) => {
  return (
    <Button
      className="hover:text-[#055aff]"
      style={{
        color: "#2a2a2a",
        border: "1px solid #eee",
        ...(style || {})
      }}
      {...props}
    >
      {children}
    </Button>
  );
};
