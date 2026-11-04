import { useNavigate, useParams, useLocation } from "react-router-dom";
import { ReactNode, useEffect, useState } from "react";
import { message, Tag, Tabs, TableProps } from "antd";
import kb_title_icon from "@/assets/knowledgebase/knowledge_base_title_icon.svg";
import Configuration from "./Configuration";
import { useServices } from "./service";
import {
  konwledgeTitles,
  chatPathPrefix,
  tabItems,
  detailTypes,
  Detail_Types,
  KnowledgeBaseTabType,
  newPanelTypes
} from "@/const/knowledgebase";
import "@/assets/styles/knowledgebase.less";
import "./v2/workbench.less";
import VersionDetail from "./VersionDetail";
import FolderDetail from "./FolderDetail";
import GraphWorkbench from "./v2/GraphWorkbench";
import FaqManageList from "./FAQ/indexAll";
import { ColumnProps } from "antd/es/table";
import {
  FILE_BTN,
  PERMISSION_RULES,
  PERMISSION_STATUS
} from "@root/src/const/permission";
import RetrieveTest from "./RetrieveTest";
import DataExtract from "./DataExtract";
import { formatFileSize } from "@root/src/core/helps";

interface KnowledgeBaseTabOpt {
  key: KnowledgeBaseTabType;
  label: string;
}
interface KnowledgeBaseDetailTabOpt {
  key: Detail_Types;
  label: string;
}
interface Iprops {
  pathPrefix?: string;
  intro?:
    | {
        tabOpt: KnowledgeBaseTabOpt[] | KnowledgeBaseTabType;
        settingOpt: {
          [key: string]: boolean;
        };
      }
    | "hide";
  detailTabOpt?: KnowledgeBaseDetailTabOpt[] | Detail_Types;
  //点击文件名预览文件，隐藏问答模块
  hideQA?: boolean;
  uploadBoxOpt?: {
    docParse: boolean;
    faq: boolean;
    chunk: boolean;
  };
  operationOpt?: {
    uploadBtn?: ReactNode | false;
    newFolder?: ReactNode | false;
    moreOperation?: ReactNode | false;
    parseState?: ReactNode | false;
  };
  tableOpt?: {
    // antd Table组件传参ColumnProps, TableProps
    tableProps?: TableProps;
    column?: ColumnProps[];
    // 1，Detail组件内表格SelectChange时调用 2，选择/取消选择知识库时调用
    handleItem?: (item: any) => any;
  };
  isSelect?: boolean;
  kbId?: string;
  noPagination?: boolean;
  getTableData?: (fileListInfo: any) => void;
  platform?: string;
}

const KnowledgeBaseDetail = (props: Iprops) => {
  const {
    pathPrefix = chatPathPrefix,
    intro,
    detailTabOpt,
    hideQA = false,
    uploadBoxOpt,
    operationOpt,
    tableOpt,
    isSelect = false,
    kbId,
    noPagination = false,
    getTableData,
    platform = "rag-qa"
  } = props;
  const { getKbById } = useServices(platform);

  const params = useParams();
  const { state } = useLocation();
  const navigator = useNavigate();
  const [prevTab, setPrevTab] = useState(
    state && state.currentTab ? state.currentTab : konwledgeTitles[0].key
  );
  const [tableLoading, setTableLoading] = useState(false);
  const [kbInfo, setKbInfo] = useState<any>({});
  // 文档解析；FAQ解析
  const [tabKey, setTabKey] = useState(
    state && state.prevTabKey ? state.prevTabKey : tabItems[0].key
  );

  useEffect(() => {
    console.log("state", state);
  }, [state]);
  // 文件管理；版本管理
  const [detailType, setDetailType] = useState(
    state && state.prevDetailType ? state.prevDetailType : detailTypes[0].key
  );
  const [tagList, setTagList] = useState([]);
  const [showSettingsPage, setShowSettingsPage] = useState(false);

  const tabKeyOnChange = async (key: string) => {
    if (key === "3") {
      await fetchKBDetail();
      setShowSettingsPage(true);
    } else {
      setShowSettingsPage(false);
    }
    setTabKey(key);
  };

  const detailTypeOnChange = (key: string) => {
    setDetailType(key);
  };

  const fetchKBDetail = async () => {
    const id = kbId || params.id;
    if (id) {
      const res = (await getKbById({ id })) as any;
      if (res) {
        const { permission, kbLabel } = res;
        if (permission === 0) {
          message.error("暂无操作权限，请联系管理员申请");
          goBack();
          return;
        }

        setKbInfo({ ...res });
        setTagList(kbLabel ? kbLabel.split(";") : []);
      }
    }
  };

  const goBack = () => {
    navigator(`${pathPrefix}`, {
      state: { currentTab: prevTab }
    });
  };

  useEffect(() => {
    if (tabKey === tabItems[0].key && detailType === detailTypes[2].key) {
      if (detailTypes[3]) {
        setDetailType(detailTypes[3].key);
      } else {
        setDetailType(detailTypes[0].key);
      }
    } else if (tabKey === KnowledgeBaseTabType.FAQ) {
      setDetailType(detailTypes[2].key);
    }
  }, [tabKey]);

  useEffect(() => {
    fetchKBDetail();
  }, []);

  // 图谱路由作用域：紧凑共享头部（仅本页，不影响其他业务页面）
  useEffect(() => {
    if (tabKey === KnowledgeBaseTabType.GRAPH_VIEW) {
      document.body.classList.add("kgw-route");
    } else {
      document.body.classList.remove("kgw-route");
    }
    return () => document.body.classList.remove("kgw-route");
  }, [tabKey]);

  return (
    <div
      className={`detail-wrap ${
        tabKey === KnowledgeBaseTabType.GRAPH_VIEW ? "is-graph" : ""
      }`}
    >
      {intro === "hide" ? null : (
        <div className="detail-contextbar">
          <div className="detail-contextbar-back" onClick={goBack}>
            <span>{kbInfo.kbName}</span>
          </div>
          <div className="detail-contextbar-info">
            {tagList.length > 0 && (
              <span className="detail-contextbar-tags">
                {tagList.map((tag: any, index: any) => (
                  <Tag color="blue" key={index} bordered={false}>
                    {tag}
                  </Tag>
                ))}
              </span>
            )}
            <span className="detail-contextbar-stats">
              {`文件数：${kbInfo?.fileCount || "暂无"} · 大小：${formatFileSize(kbInfo?.fileTotalSize)}`}
            </span>
          </div>
          <div className="detail-contextbar-tabs">
            <Tabs
              items={((intro || {}).tabOpt || tabItems) as any}
              onChange={tabKeyOnChange}
              activeKey={tabKey}
            />
          </div>
        </div>
      )}
      {tabKey === KnowledgeBaseTabType.GRAPH_VIEW ? (
        <div className="detail-graph-wrap">
          <GraphWorkbench kbInfo={kbInfo} />
        </div>
      ) : newPanelTypes.includes(tabKey) ? (
        // new panel render here
        <div className="detail-retrieve-wrap">
          <RetrieveTest setKbInfo={kbInfo} />
        </div>
      ) : (
        <div className="file-table-wrap">
          {tabKey !== KnowledgeBaseTabType.DATA_EXTRACT ? (
            <div
              className={`w-full h-full ${showSettingsPage ? "hidden" : ""}`}
            >
              {(!detailTabOpt || typeof detailTabOpt !== "string") && (
                <Tabs
                  items={
                    detailTabOpt && Array.isArray(detailTabOpt)
                      ? detailTabOpt
                      : detailTypes.filter((item: any) => {
                          if (item.faq) {
                            return tabKey === tabItems[1].key;
                          }
                          if (item.file) {
                            return tabKey === tabItems[0].key;
                          }
                          return true;
                        })
                  }
                  onChange={detailTypeOnChange}
                  activeKey={detailType}
                />
              )}
              <div
                style={{ height: `calc(100% - 35px)` }}
                className="detail-box"
              >
                {detailType === Detail_Types.FILE_MANAGE && (
                  <FolderDetail
                    tabKey={tabKey}
                    detailType={detailType}
                    tableLoading={tableLoading}
                    kbName={kbInfo.kbName}
                    fetchKBDetail={fetchKBDetail}
                    setTableLoading={setTableLoading}
                    pathPrefix={pathPrefix}
                    hideQA={hideQA}
                    uploadBoxOpt={uploadBoxOpt}
                    operationOpt={operationOpt}
                    tableOpt={tableOpt}
                    isSelect={isSelect}
                    kbId={kbId}
                    noPagination={noPagination}
                    getTableData={getTableData}
                    platform={platform}
                    kbInfo={kbInfo}
                  />
                )}
                {detailType === Detail_Types.VERSION_MANAGE && (
                  <VersionDetail
                    tabKey={tabKey}
                    detailType={detailType}
                    tableLoading={tableLoading}
                    kbName={kbInfo.kbName}
                    fetchKBDetail={fetchKBDetail}
                    setTableLoading={setTableLoading}
                    platform={platform}
                    kbInfo={kbInfo}
                  />
                )}
                {tabKey === KnowledgeBaseTabType.FAQ &&
                  detailType === Detail_Types.FAQ_MANAGE && (
                    <FaqManageList
                      knowledgeBaseId={kbId || params.id}
                      fileId="all"
                      kbInfo={kbInfo}
                    />
                  )}
              </div>
            </div>
          ) : (
            <DataExtract knowledgeBaseName={kbInfo.kbName} />
          )}
          <div className={`w-full h-full ${showSettingsPage ? "" : "hidden"}`}>
            <Configuration
              kbInfo={kbInfo}
              settingOpt={((intro || {}) as any).settingOpt}
              platform={platform}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgeBaseDetail;
