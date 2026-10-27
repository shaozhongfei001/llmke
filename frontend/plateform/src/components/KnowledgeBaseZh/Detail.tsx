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
import VersionDetail from "./VersionDetail";
import FolderDetail from "./FolderDetail";
import GraphBox from "./GraphBox";
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
    } else if (tabKey === tabItems[1].key) {
      setDetailType(detailTypes[2].key);
    }
  }, [tabKey]);

  useEffect(() => {
    fetchKBDetail();
  }, []);

  return (
    <div className="detail-wrap">
      {intro === "hide" ? null : (
        <>
          <div className="detail-nav-wrap">
            <div className="breadcrumb-wrap" onClick={goBack}>
              <span>{kbInfo.kbName}</span>
            </div>
          </div>
          <div className="detail-info-wrap">
            <div className="flex w-full">
              <span
                className="detail-info-img"
                style={{
                  background: `center url(${kb_title_icon}) no-repeat`
                }}
              ></span>
              <span className="detail-info-content">
                <div className="detail-name">{kbInfo.kbName}</div>
                <div className="detail-info-tag-wrap flex">
                  <span className="detail-info-tags mr-5">
                    {tagList.length ? (
                      tagList.map((tag: any, index: any) => (
                        <Tag color="blue" key={index} bordered={false}>
                          {tag}
                        </Tag>
                      ))
                    ) : (
                      <label>暂无标签</label>
                    )}
                  </span>
                  <span className="detail-info-statistices">
                    {`文件数：${kbInfo?.fileCount || "暂无"}  `}
                    <span className="ml-2">
                      {`大小：${formatFileSize(kbInfo?.fileTotalSize)}`}
                    </span>
                  </span>
                </div>
              </span>
            </div>
            <div className="detail-info-btn-group">
              <Tabs
                items={((intro || {}).tabOpt || tabItems) as any}
                onChange={tabKeyOnChange}
                activeKey={tabKey}
              />
            </div>
          </div>
        </>
      )}
      {newPanelTypes.includes(tabKey) ? (
        // new panel render here
        <RetrieveTest setKbInfo={kbInfo} />
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
                {tabKey === tabItems[0].key &&
                  detailType === Detail_Types.GRAPH_MANAGE && (
                    <GraphBox
                      tabKey={tabKey}
                      detailType={detailType}
                      tableLoading={tableLoading}
                      kbName={kbInfo.kbName}
                      fetchKBDetail={fetchKBDetail}
                      setTableLoading={setTableLoading}
                      kbInfo={kbInfo}
                    />
                  )}
                {tabKey === tabItems[1].key &&
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
