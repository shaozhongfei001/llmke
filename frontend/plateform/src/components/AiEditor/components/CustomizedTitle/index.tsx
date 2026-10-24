import { theme } from "antd";

export const CustomizedTitle = ({ text }) => {
  const { useToken } = theme;
  const { token } = useToken();
  const { colorPrimary } = token;
  return (
    <div
      style={{
        display: "flex",
      }}
    >
      <div
        style={{
          color: colorPrimary || "#1166EF",
          display: "flex",
          alignItems: "center",
          gap: "5px",
          position: "relative",
          paddingLeft: "5px",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: "0px",
            height: "50%",
            width: "100%",
            top: "65%",
            background: `linear-gradient(to right, ${colorPrimary || "#1166EF"}, rgba(0,0,0,0))`,
            opacity: 0.3,
          }}
        ></div>
        <div
          style={{
            width: "4px",
            height: "12px",
            background: colorPrimary || "#1166EF",
            borderRadius: "999px",
          }}
        ></div>
        <div>{text}</div>
      </div>
      <div className="flex-1"></div>
    </div>
  );
};
