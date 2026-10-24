import DatabaseView from "@gientech/modual/database";
import { useNavigate } from "react-router-dom";
import { useAppPassport } from "@root/src/core/helps";
import { message, Spin } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import { getBtnDisabled } from "@root/src/const/permission";
import "@gientech/modual/style.css";

export default function DatabasePage() {
  const navigator = useNavigate();
  const { getToken, getUserInfo } = useAppPassport();
  const useInfo = getUserInfo();
  const token = getToken() || undefined;
  const customComponents: any = {
    ContentLoading: () => (
      <div className="flex flex-col items-center justify-center h-full">
        <div className="text-xl font-semibold mb-3">
          <Spin indicator={<LoadingOutlined spin />} size="large" />
        </div>
        <div className="text-base mb-2" style={{ color: "#055AFF" }}>
          加载中...
        </div>
      </div>
    )
  };
  const handlePageEventsEmit = (name: string, data: any) => {
    console.log("[DatabasePage] pageEventsEmit ", name, data);
    if (name.startsWith("request:error")) {
      message.error(data.errorMsg);
      return;
    }
    switch (name) {
      case "card_clicked":
        navigator(
          `/chats/database/${data.cardId}?dbtype=${data.cardData.datasourceType}`
        );
        break;
      default:
        return;
    }
  };
  return (
    <DatabaseView
      url="/proxy/index/database"
      token={token}
      role={useInfo?.userName || ""}
      eventsEmit={handlePageEventsEmit}
      CustomComponents={customComponents}
      getBtnDisabled={getBtnDisabled}
      styles={{
        theme: {
          colors: {
            listBackground: "#ffffff"
          }
        },
        mode: "light"
      }}
    />
  );
}
