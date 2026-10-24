import AssistantConfig from "@gientech/modual/assistantConfig";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAppPassport } from "@root/src/core/helps";
import { message, Spin } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import { useSelector } from "react-redux";
import { getBtnDisabled } from "@root/src/const/permission";
import "@gientech/modual/style.css";
import "./style.less";

const showGraph = import.meta.env.VITE_CONFIG_SHOW_GRAPH === "true";
export default function DatabasePage({
  isShare,
  disabled
}: {
  isShare?: boolean;
  disabled?: boolean;
}) {
  const navigator = useNavigate();
  const { getToken, getUserInfo } = useAppPassport();
  const useInfo = getUserInfo();
  const { id }: any = useParams();
  const token = getToken() || undefined;
  const globalMenu: any = useSelector((state: any) => state.global.globalMenu);

  const customComponents: any = {
    ContentLoading: () => (
      <div
        className="flex flex-col items-center justify-center"
        style={{
          height: "calc(100vh - 150px)"
        }}
      >
        <div className="text-xl font-semibold mb-3">
          <Spin indicator={<LoadingOutlined spin />} size="large" />
        </div>
        <div className="text-base mb-2" style={{ color: "#055AFF" }}>
          加载中...
        </div>
      </div>
    )
  };

  const databasePermission = useMemo(() => {
    if (!globalMenu) return;
    //这里目前只处理写作模版的权限
    const docMenu = globalMenu.find((i: any) => i.url === "/chats/database");
    if (!docMenu) return false;
    return docMenu.permission;
  }, [globalMenu]);
  const handlePageEventsEmit = (name: string, data: any) => {
    console.log("[DatabasePage] pageEventsEmit ", name, data);
    if (name.startsWith("request:error")) {
      message.error(data.errorMsg);
      return;
    }
    switch (name) {
      case "go_back":
        navigator(-1);
        break;
      default:
        return;
    }
  };
  return (
    <div className="settingsDetail">
      <AssistantConfig
        url="/proxy"
        token={token}
        role={useInfo?.userName || ""}
        showDatabase={databasePermission}
        showGraph={showGraph}
        isShare={isShare}
        disabled={disabled}
        id={id}
        eventsEmit={handlePageEventsEmit}
        CustomComponents={customComponents}
      />
    </div>
  );
}
