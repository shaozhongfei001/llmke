import KnowledgeBaseDetail from "@root/src/components/KnowledgeBaseZh/Detail";
import {
  Detail_Types,
  KnowledgeBaseTabType
} from "@root/src/const/knowledgebase";
const ResourceDetail = () => {
  return (
    <div
      className="h-full overflow-hidden"
      style={{
        maxWidth: "99.6%"
      }}
    >
      <KnowledgeBaseDetail
        pathPrefix="/docWriting/resource"
        intro={{
          tabOpt: [
            {
              key: KnowledgeBaseTabType.KONWLEDGE_ANALYSIS,
              label: "知识解析"
            },
            {
              key: KnowledgeBaseTabType.DATA_EXTRACT,
              label: "数据抽取"
            },
            {
              key: KnowledgeBaseTabType.SETTING,
              label: "配置"
            }
          ],
          settingOpt: {
            embeddingModelName: true,
            fileType: true,
            graphPrompt: false,
            chunkSize: true,
            fileFaqMaxNums: false,
            similarQuestionMaxNums: false
          }
        }}
        detailTabOpt={Detail_Types.FILE_MANAGE}
        hideQA={true}
        uploadBoxOpt={{
          docParse: false,
          faq: false,
          chunk: true
        }}
        platform="intelbrain-dw"
      />
    </div>
  );
};
export default ResourceDetail;
