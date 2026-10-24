import { getUrlPrefix, useAppPassport } from "@root/src/core/helps";
import { AiGraph, GraphRefType } from "./components/@mxmweb/somelib";
import { useLocation } from "react-router-dom";

const GraphDetail = ({
  gientechServer,
  setShowGraph,
  kbInfo
}: {
  gientechServer: {
    type: "allGraph" | "subGraph";
    spaceName: string;
    fileId?: string;
    fileName: string;
  };
  setShowGraph: (arg: boolean) => void;
  kbInfo: any;
}) => {
  const { getToken, userInfo } = useAppPassport();
  const token: any = getToken();
  return (
    <div className="w-full h-[calc(100%-20px)] relative graphView">
      <AiGraph
        url={`${getUrlPrefix()}/graph`}
        token={token}
        gientechServer={{
          url: `${getUrlPrefix()}/graph`,
          token: token,
          spaceName: gientechServer.spaceName,
          fileId: gientechServer.fileId,
          fileName: gientechServer.fileName
        }}
        initData={null}
        createBy={userInfo?.userName}
        graphModeType={gientechServer.type}
        handleCallBack={(type: string, data?: any) => {
          switch (type) {
            case "back":
              setShowGraph(false);
              break;
          }
        }}
      />
    </div>
  );
};

export default GraphDetail;
