import { message, Pagination, Spin } from "antd";
import { useEffect, useState, useMemo, useRef } from "react";
import "@/assets/styles/knowledgebase.less";
import { konwledgeTitles, chatPathPrefix } from "@/const/knowledgebase";
import NavBar from "./components/NavBar";
import Empty from "./components/Empty";
import CreateForm from "./components/CreateForm";
import Card from "./components/KnowledgeBaseCard";
import { useServices } from "./service";
import { useNavigate, useLocation } from "react-router-dom";
import { ProCard } from "@ant-design/pro-components";

const initialPage = {
  pageNo: 1,
  pageSize: 12
};
interface KnowledgeBaseProps {
  title?: string;
  konwledgeTitlesTab?:
    | {
        key: number;
        label: string;
      }[]
    | "hide";
  pathPrefix?: string;
  isSelect?: boolean;
  cardProps?: {
    cancelHover?: boolean;
    clickCardItem?: (item: any) => any;
    doubleClickCardItem?: (cardItem: any) => any;
  };
  activeTab?: number;
  uploadBtn?: React.ReactNode;
  cardList?: any[];
  noPagination?: boolean;
  platform?: string;
  selectOpt?: {
    value: number;
    label: string;
  }[];
}

const KnowledgeBase = (props: KnowledgeBaseProps) => {
  const {
    title = "知识库",
    konwledgeTitlesTab,
    pathPrefix = chatPathPrefix,
    isSelect = false,
    cardProps = {},
    activeTab,
    uploadBtn,
    cardList,
    selectOpt,
    platform = "rag-qa"
  } = props;
  const navigator = useNavigate();
  const fuzzyNameOrId = useRef("");
  const { state } = useLocation();
  const [currentTab, setCurrentTab] = useState(
    state && state.currentTab ? state.currentTab : konwledgeTitles[0].key
  );
  const [list, setList] = useState<any[]>([]);
  const [listCount, setListCount] = useState(0);
  const [shareList, setShareList] = useState<any[]>([]);
  const [shareListCount, setShareListCount] = useState(0);
  const [isShowCreateModal, setIsShowCreateModal] = useState(false);
  const [page, setPage] = useState(initialPage);
  const [editRow, setEditRow] = useState({});
  const { getKnowledgeList, getShareList } = useServices(platform);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeTab) {
      setCurrentTab(activeTab);
      onTabChange(activeTab);
    }
  }, [activeTab]);

  const isShare = useMemo(() => {
    return currentTab === konwledgeTitles[1].key;
  }, [currentTab]);

  const total = useMemo(() => {
    return !isShare ? listCount : shareListCount;
  }, [isShare, listCount, shareListCount]);

  const onPageSizeChange = (pageNo: number, pageSize: number) => {
    setPage({
      pageNo,
      pageSize
    });
  };

  const onTabChange = (tabKey: number) => {
    if (tabKey !== currentTab) {
      setCurrentTab(tabKey);
      setPage({
        ...page,
        pageNo: 1
      });
    }
  };

  const onCreateClick = () => {
    setIsShowCreateModal(true);
  };

  const isShowSearchBar = useMemo(() => {
    return list.length > 0;
  }, [list]);

  const closeModal = (isRefresh: boolean) => {
    isRefresh && fetchKnowledgeList();
    setIsShowCreateModal(false);
    setEditRow({});
  };

  const fetchList = (str?: string) => {
    isShare ? fetchShareList(str) : fetchKnowledgeList(str);
  };

  const fetchKnowledgeList = async (str?: string) => {
    const params = {
      ...page,
      fuzzy: str || fuzzyNameOrId.current
    };
    setLoading(true);
    const res: any = await getKnowledgeList(params);
    setLoading(false);
    if (res) {
      const _records = (res.records || []).map((item: any) => ({
        ...item,
        customId: `kb-${item.id}`
      }));

      setListCount(res?.total as any);
      setList(_records);
    }
  };
  const fetchShareList = async (str?: string) => {
    const params = {
      ...page,
      fuzzy: str || fuzzyNameOrId.current
    };
    const res: any = await getShareList(params);
    if (res) {
      const _records = (res.records || []).map((item: any) => ({
        ...item,
        customId: `kb-${item.id}`
      }));
      setShareListCount(res?.total as any);
      setShareList(_records);
    }
  };

  const reNameHandler = (row: any) => {
    setEditRow(row);
    setIsShowCreateModal(true);
  };

  const goToDetail = (row: any) => {
    const { id, kbName, permission } = row;
    if (!permission && isShare) {
      message.error("暂无操作权限，请联系管理员申请");
      return;
    }
    navigator(`${pathPrefix}/${id}`, {
      state: { currentTab, kbName, permission }
    });
  };

  const fetchListByTabType = () => {
    !isShare ? fetchKnowledgeList() : fetchShareList();
  };

  const fetchListByDelDone = () => {
    const { pageSize, pageNo } = page;
    if (listCount - 1 <= pageSize * (pageNo - 1)) {
      setPage({
        ...page,
        pageNo: pageNo > 1 ? pageNo - 1 : 1
      });
    } else {
      fetchKnowledgeList();
    }
  };

  useEffect(() => {
    fetchListByTabType();
  }, [page]);

  return (
    <>
      {title !== "hide" && (
        <div
          style={{
            height: 28,
            fontFamily: `Microsoft YaHei`,
            fontSize: "16px",
            fontWeight: 700,
            marginBottom: 16
          }}
        >
          {title || "知识库"}
        </div>
      )}
      <div className="knowledgebase-wrap">
        <NavBar
          currentTab={currentTab}
          konwledgeTitlesTab={konwledgeTitlesTab}
          selectOpt={selectOpt}
          isShowSearchBar={isShowSearchBar}
          fuzzyNameOrId={fuzzyNameOrId}
          disabled={loading}
          onTabChange={onTabChange}
          onCreateClick={onCreateClick}
          fetchList={fetchList}
          uploadBtn={uploadBtn}
          platform={platform}
          emitEvent={(type:string,data:any)=>{
            switch(type){
              case 'search':
                if(page.pageNo === 1){
                  fetchList(data);
                } else {
                  setPage({
                    ...page,
                    pageNo: 1
                  });
                }
                break;
            }
          }}
        />
        <Spin spinning={loading}>
          <div className="content-wrap">
            {(list.length === 0 && !isShare) ||
            (shareList.length === 0 && isShare) ? (
              <Empty currentTab={currentTab} onCreateClick={onCreateClick} />
            ) : (
              <>
                <div className="list-wrap">
                  <ProCard
                    ghost={true}
                    wrap={true}
                    gutter={[
                      { xs: 8, sm: 16, md: 16, lg: 18, xl: 24, xxl: 32 },
                      16
                    ]}
                  >
                    {(!isShare ? list : shareList).map(
                      (item: any, index: any) => {
                        const isSelected = cardList
                          ? cardList.some((kb) => kb.id === item.id)
                          : false;
                        return (
                          <ProCard
                            key={`${currentTab}_${index}`}
                            colSpan={{
                              xs: 6,
                              sm: 6,
                              md: isSelect ? 7 : 6,
                              lg: isSelect ? 7 : 6,
                              xl: isSelect ? 7 : 6,
                              xxl: isSelect ? 7 : 8
                            }}
                            ghost={true}
                          >
                            <Card
                              key={`${currentTab}-item-${item.id}`}
                              row={item}
                              fetchList={fetchListByDelDone}
                              reNameHandler={reNameHandler}
                              goToDetail={goToDetail}
                              isSelected={isSelected}
                              {...cardProps}
                            />
                          </ProCard>
                        );
                      }
                    )}
                  </ProCard>

                  {isSelect && (
                    <Pagination
                      size="small"
                      align="end"
                      total={total}
                      pageSize={page.pageSize}
                      current={page.pageNo}
                      onChange={onPageSizeChange}
                    />
                  )}
                </div>
                {!isSelect && (
                  <Pagination
                    size="small"
                    align="end"
                    total={total}
                    pageSize={page.pageSize}
                    current={page.pageNo}
                    onChange={onPageSizeChange}
                  />
                )}
              </>
            )}
          </div>
        </Spin>
        <CreateForm
          isShowCreateModal={isShowCreateModal}
          editRow={editRow}
          closeModal={closeModal}
          platform={platform}
        />
      </div>
    </>
  );
};

export default KnowledgeBase;
