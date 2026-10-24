import axios from "axios";
import { useEffect, useMemo, useState } from "react";
import { useAppPassport } from "@root/src/core/helps";
import {
  KnowledgeGraphPreview,
  registerPreviewViewer
} from "@mxmweb/nodegraph";
import { CloseOutlined } from "@ant-design/icons";
registerPreviewViewer();

const DrawerGraphPreview = ({
  curFileInfo,
  onClose
}: {
  curFileInfo: any;
  onClose: any;
}) => {
  const { getToken } = useAppPassport();
  const config = {
    title: "",
    subtitle: "",
    backgroundColor: "#f8f9fa",
    showGrid: false,
    showLegend: false,
    showTooltip: false,
    showFullscreen: false,
    showMinimap: false
  };
  const [graphList, setGraphList] = useState<any>({
    nodeList: [],
    edgeList: []
  });

  useEffect(() => {
    console.log("curFileInfo", curFileInfo);
  }, [curFileInfo]);

  const getGraphData = async (curFileInfo: any) => {
    const token = getToken();
    if (!curFileInfo?.id || !curFileInfo?.cyphers || !curFileInfo?.fetchUrl)
      return;
    try {
      const { cyphers, fetchUrl, id } = curFileInfo || {};
      //   [
      //   "match (n:`疾病`)-[e]-(m) where id(n) == \"疾病上睑下垂\" return n,e,m;"
      // ]
      console.log("getGraphData params", cyphers, fetchUrl, id);

      const res = await axios.post(
        fetchUrl,
        { cyphers, ontologyId: id },
        {
          headers: { Authorization: token }
        }
      );
      console.log("getGraphData res", res);
      setGraphList(res?.data || {});
    } catch (error) {
      console.log("error", error);
    }
  };
  useEffect(() => {
    getGraphData(curFileInfo);
  }, [curFileInfo]);

  return (
    <div>
      <div className="flex justify-between h-[52px] leading-[52px] font-bold text-[16px] px-[15px] overflow-hidden border-t-none border-l-none border-b-[1px] border-solid border-[rgb(222,226,230)]">
        <div>{curFileInfo?.name || "图谱预览"}</div>
        <CloseOutlined className="cursor-pointer" onClick={() => onClose()} />
      </div>
      <div
        className="w-full h-[calc(100vh-52)]"
        style={{ width: "100%", height: "calc(100vh - 52px)" }}
      >
        <KnowledgeGraphPreview
          centerNode={{
            vid: curFileInfo?.traceNode?.vid
          }}
          data={graphList}
          layout={{ type: "force", linkDistance: 190 }}
          title={config.title}
          subtitle={config.subtitle}
          backgroundColor={config.backgroundColor}
          showGrid={false}
          showLegend={config.showLegend}
          showTooltip={config.showTooltip}
          showFullscreen={config.showFullscreen}
          showMinimap={config.showMinimap}
          customPlugins={{}}
          onReady={(graph: any) => {
            console.log("KnowledgeGraphPreview ready:", graph);
          }}
        />
      </div>
    </div>
  );
};

export default DrawerGraphPreview;
