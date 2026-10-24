import { DatabaseTableView } from "@mxmweb/xviewer";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useAppPassport } from "@root/src/core/helps";
import { message, Spin } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import EmptyImg from "@root/src/assets/img/empty.png";
import { getBtnDisabled } from "@root/src/const/permission";
import "@gientech/modual/style.css";
const EmptyData: React.FC<{ dbType: "DataTable" | "DirectDB" }> = () => (
  <div className="flex flex-col items-center justify-center h-full">
    <div className="text-xl font-semibold mb-3">
      <img src={EmptyImg} width={120} />
    </div>
    <div className="text-base mb-2" style={{ color: "#888888" }}>
      暂无数据
    </div>
  </div>
);

export default function DatabasePage() {
  const navigator = useNavigate();
  const { dbId, fileId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const dbType: any = searchParams.get("dbtype") || "DataTable";
  const tbName: any = searchParams.get("name");
  const tableId: any = searchParams.get("tbId");
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
    ),
    EmptyData
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
      case "table_action_view":
        if (dbType == "DataTable") {
          navigator(`${data.id}`);
          break;
        }
        if (dbType == "DirectDB") {
          const tbName = data.data.find((d: any) => d.columnId == "name").value;
          navigator(`/${tbName}`);
          break;
        }
        break;
      default:
        return;
    }
  };
  return (
    <>
      {fileId && (
        <DatabaseTableView
          url="/proxy/index/database"
          token={token}
          role={useInfo?.userName || ""}
          fileId={fileId}
          dbId={dbId}
          tableId={tableId}
          tableName={tbName}
          dbType={dbType}
          eventsEmit={handlePageEventsEmit}
          CustomComponents={customComponents}
          getBtnDisabled={getBtnDisabled}
        />
      )}
    </>
  );
}
