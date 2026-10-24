import { useState, useEffect } from "react";
import DatabaseIdView from "@gientech/modual/databaseId";
import {
  useNavigate,
  useParams,
  useSearchParams,
  useLocation
} from "react-router-dom";
import { useAppPassport } from "@root/src/core/helps";
import { message, Spin, Drawer, Button } from "antd";
import { LoadingOutlined, CloseOutlined } from "@ant-design/icons";
import { getBtnDisabled } from "@root/src/const/permission";
import PermisssonConfig, {
  TypeDrawConfig
} from "../../../Components/PermissionConfig";
import "@gientech/modual/style.css";
// R12：上传走相对路径（dev 由 vite 代理、prod 由 nginx 反代），不再拼内网主机

export default function DatabasePage() {
  const navigator = useNavigate();
  const { dbId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const dbType: any = searchParams.get("dbtype") || "DataTable";
  const { getToken, getUserInfo } = useAppPassport();
  const token = getToken() || undefined;
  const useInfo = getUserInfo();
  const uploadUrl = `/index/database/dataTable/uploadFile`;

  const [permission, setPermission] = useState();

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
    ),
    ContainerLoading: () => (
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
    console.log("[DatabaseIdPage] pageEventsEmit ", name, data);
    if (name.startsWith("request:error")) {
      message.error(data.errorMsg);
      return;
    }
    switch (name) {
      case "goBack":
        navigator(-1);
        break;
      case "toolbar_auth": {
        setDrawerVisible(true);
        setPermission(data?.permission);
        break;
      }
      case "table_action_view":
      case "subtable_view_item":
        const tbName = data.data.find((d: any) => d.columnId == "name").value;
        navigator(
          `/chats/database/${dbId}/table/${
            data.id
          }?dbtype=${dbType}&name=${tbName}&tbId=${data.tableId || data.id}`
        );
        break;
      default:
        return;
    }
  };

  const [drawerVisible, setDrawerVisible] = useState(false);

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
      {dbId && (
        <DatabaseIdView
          url="/proxy/index/database"
          token={token}
          role={useInfo?.userName || ""}
          id={dbId}
          dbType={dbType}
          CustomComponents={customComponents}
          eventsEmit={handlePageEventsEmit}
          uploadUrl={uploadUrl}
          getBtnDisabled={getBtnDisabled}
        />
      )}

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
          drawConfig={{
            data: {
              id: dbId
            }
          }}
          subTitle="数据库公开范围"
          bizType={12}
          type="modelRight"
          kbInfo={{
            permission
          }}
        />
      </Drawer>
    </>
  );
}
