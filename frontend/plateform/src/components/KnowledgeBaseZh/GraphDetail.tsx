import GraphCanvas from "./GraphCanvas";

/**
 * R14-LIVE-06：整图视图容器。
 *
 * 原实现渲染 vendored 的 <AiGraph />（@mxmweb/somelib），它在本地环境静默失败：
 * 画布尺寸正常、数据接口 200（87 节点 / 61 关系），却停在 `app_init -> app_wait`
 * 一个节点都不画，也不抛错。改为自研 <GraphCanvas />，数据直接取自
 * /proxy/graph/search/wholeGraphSearch 与 /graph/search/subGraph。
 */
const GraphDetail = ({
  gientechServer,
  setShowGraph
}: {
  gientechServer: {
    type: "allGraph" | "subGraph";
    spaceName: string;
    fileId?: string;
    fileName?: string;
  };
  setShowGraph: (arg: boolean) => void;
  kbInfo?: any;
}) => {
  return (
    <div className="w-full h-[calc(100%-20px)] relative graphView">
      <GraphCanvas
        spaceName={gientechServer?.spaceName}
        fileId={gientechServer?.fileId}
        type={gientechServer?.type || "allGraph"}
        onBack={() => setShowGraph(false)}
      />
    </div>
  );
};

export default GraphDetail;
