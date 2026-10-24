import { useState, useEffect } from "react";
import ModelManageView from "@gientech/modual/modelManage";
import { useNavigate } from "react-router-dom";
import { useAppPassport } from "@root/src/core/helps";
import { message, Spin, Drawer, Button } from "antd";
import { LoadingOutlined, CloseOutlined } from "@ant-design/icons";
import { getBtnDisabled } from "@root/src/const/permission";
import PermisssonConfig, {
  TypeDrawConfig
} from "../../Components/PermissionConfig";
import "@gientech/modual/style.css";

const showModelReplace =
  import.meta.env.VITE_CONFIG_SHOW_MODEL_REPLACE === "true";

export default function DatabasePage() {
  const { getToken, getUserInfo } = useAppPassport();
  const token = getToken() || undefined;
  const useInfo = getUserInfo();
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

  const [drawerVisible, setDrawerVisible] = useState(false);
  const [drawConfig, setDrawConfig] = useState<TypeDrawConfig>({
    type: "create"
  });

  const handlePageEventsEmit = (name: string, data: any) => {
    console.log("[DatabasePage] pageEventsEmit ", name, data);
    if (name.startsWith("request:error")) {
      message.error(data.errorMsg);
      return;
    }
    switch (name) {
      case "table_action_auth": {
        setDrawConfig((pre: any) => {
          return { ...pre, type: "permission", data: data };
        });
        setDrawerVisible(true);
        break;
      }
      default:
        return;
    }
  };

  const closeDrawer = () => {
    setDrawerVisible(false);
  };

  const handleSubmit = async (values?: any) => {
    console.log("提交的表单数据:", values);
    message.success("已更新授权设置");
    setDrawerVisible(false);
  };
  return (
    <>
      <ModelManageView
        url="/proxy/index/modelInfo"
        token={token}
        role={useInfo?.userName || ""}
        eventsEmit={handlePageEventsEmit}
        CustomComponents={customComponents}
        showModelReplace={showModelReplace}
        getBtnDisabled={getBtnDisabled}
      />
      <Drawer
        title="授权"
        placement="right"
        width={560}
        onClose={closeDrawer}
        closeIcon={false}
        extra={<CloseOutlined onClick={closeDrawer} />}
        open={drawerVisible}
        destroyOnClose
        footer={
          <div className={`flex justify-end items-center gap-3`}>
            <Button onClick={closeDrawer}>取消</Button>
            <Button type="primary" onClick={handleSubmit}>
              确认
            </Button>
          </div>
        }
      >
        <PermisssonConfig
          drawConfig={drawConfig}
          subTitle="模型公开范围"
          bizType={3}
          type="modelRight"
        />
      </Drawer>
    </>
  );
}
