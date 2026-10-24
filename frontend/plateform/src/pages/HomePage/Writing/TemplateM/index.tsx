import {
  Input,
  Button,
  Flex,
  Tabs,
  Modal,
  Table,
  Spin,
  Space,
  Radio,
  ConfigProvider,
  Drawer
} from "antd";
import {
  CloseOutlined,
  PlusCircleOutlined,
  SearchOutlined
} from "@ant-design/icons";
import useController from "./common/useController";
import DeleteConfirm from "../common/components/DeleteModal";
import TemplateCard from "../common/components/Cards/TemplateCard";
import InfiniteScroll from "react-infinite-scroll-component";
import useTemplatePermission from "../common/hook/useTemplatePermission";
import { ProCard } from "@ant-design/pro-components";
import empty from "@/assets/img/empty.png";
import TempPreview from "./components/TempPreview";
import { sceneTypes, sceneList } from "@/const/scene";
import IconScene from "@/assets/writing/icon-scene.svg";
import IconRightArrow from "@/assets/writing/icon-right-arrow.svg";
import "../index.less";
import { CommonLayout } from "../common/components/CommonLayout";
import PermissionConfig from "@root/src/pages/Components/PermissionConfig";
const { Search } = Input;

enum PermissionCode {
  Usage = 1,
  Edit = 2,
  Manage = 3
}

enum TempOperations {
  Preview = "preview",
  Edit = "edit",
  Copy = "copy",
  Delete = "delete",
  Vision = "vision",
  Auth = "auth",
  ToWrite = "toWrite"
}

const permissionMap = {
  [PermissionCode.Usage]: [TempOperations.Preview],
  [PermissionCode.Edit]: [
    TempOperations.Preview,
    TempOperations.Edit,
    TempOperations.Copy,
    TempOperations.Vision
  ],
  [PermissionCode.Manage]: [
    TempOperations.Preview,
    TempOperations.Edit,
    TempOperations.Copy,
    TempOperations.Vision,
    TempOperations.Delete
  ]
};

const btnOpts = [
  { label: "预览", key: TempOperations.Preview },
  { label: "编辑", key: TempOperations.Edit },
  { label: "复制", key: TempOperations.Copy },
  { label: "删除", key: TempOperations.Delete },
  { label: "版本", key: TempOperations.Vision }
  // { label: "授权", key: TempOperations.Auth }
  // { label: "去写作", key: "toWrite" },
];

/*
参数
code:当前场景的权限
authManagement:能否对别人进行授权,由系统资源决定
*/
const getOperationBtnOpts = ({
  code,
  authManagement
}: {
  code: PermissionCode;
  authManagement: boolean;
}) => {
  const resOpts = btnOpts.filter((i) => permissionMap[code].includes(i.key));
  if (authManagement) {
    resOpts.push({ label: "授权", key: TempOperations.Auth });
  }
  return resOpts;
};

const TemplateM = () => {
  const {
    listData,
    showDeleteModal,
    closeDeleteModal,
    confirmModal,
    deleteLoading,
    onSearch,
    activeTabKey,
    tabChange,
    handleEvent,
    tempPreview,
    tempPreviewClose,
    tempPreviewInfo,
    sceneClass,
    isShowSceneChooseModal,
    setIsShowSceneChooseModal,
    searchValueRef,
    sceneId,
    closeVersionModal,
    sceneVersionList,
    versionLoading,
    gotoVersionDetail,
    rollBackVersion,
    listPostData,
    setListPostData,
    setListData,
    listLoading,
    openPermission,
    setOpenPermission,
    drawConfig
  } = useController();

  // 模板管理的权限，系统资源：模板授权
  const { manageTemplatePermission } = useTemplatePermission();

  // const items = [
  //   {
  //     key: "公文",
  //     label: "公文"
  //   },
  //   {
  //     key: "情报",
  //     label: "情报"
  //   },
  //   {
  //     key: "营销",
  //     label: "营销"
  //   },
  //   {
  //     key: "其他",
  //     label: "其他"
  //   }
  // ];

  const showChooseSceneModal = () => {
    // handleEvent("add", "temp");
    setIsShowSceneChooseModal(true);
  };
  const hideChooseSceneModal = () => {
    setIsShowSceneChooseModal(false);
  };

  const versionColumns = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      width: "250px",
      render: (val: string, record: any) => (
        <span className="relative">
          <div className={`truncate`} title={val}>
            {val}
          </div>
          {record.currentVersionId &&
          record.versionId &&
          String(record.currentVersionId) === String(record.versionId) ? (
            <span className="absolute text-green-500 text-xs scale-[0.9] top-5 -left-[2px]">
              当前版本
            </span>
          ) : null}
        </span>
      )
    },
    {
      title: "版本号",
      dataIndex: "version",
      key: "version",
      width: "100px",
      render: (val: string) => <>{`V1.${val}`}</>
    },
    {
      title: "创建时间",
      dataIndex: "gmtCreate",
      key: "gmtCreate"
    },
    {
      title: "类型",
      key: "generateType",
      dataIndex: "generateType",
      width: "120px",
      render: (val: any) => (
        <>{val === 0 ? "全文生成" : val === 1 ? "分段生成" : "-"}</>
      )
    },
    {
      title: "操作",
      key: "action",
      width: "140px",
      render: (_: any, record: any) => (
        <>
          <Button
            className="px-0 mr-1"
            type="link"
            onClick={gotoVersionDetail(record)}
          >
            查看
          </Button>
          <Button
            className="px-0"
            type="link"
            disabled={
              String(record.currentVersionId) === String(record.versionId)
            }
            onClick={rollBackVersionHandler({
              currentVersionId: record.versionId,
              id: record.id,
              rollBackVersion: true
            })}
          >
            版本回退
          </Button>
        </>
      )
    }
  ];

  const rollBackVersionHandler = (params: any) => async () => {
    await rollBackVersion(params);
  };

  const createHandler = (type: sceneTypes) => () => {
    if (type) {
      switch (type) {
        case sceneTypes.FULL_WRITING:
        case sceneTypes.SEGMENTED_WRITING:
          handleEvent(type, "temp");
          break;
      }
    }
  };

  return (
    <CommonLayout
      name="场景管理"
      operationArea={
        <Space>
          <Radio.Group
            value={listPostData.tempType}
            onChange={(e) => {
              setListPostData((p) => ({
                ...p,
                tempType: e.target.value,
                className: ""
              }));
              setListData({
                list: [],
                total: 0
              });
            }}
            size="small"
          >
            <Radio.Button
              value="share"
              style={
                listPostData.tempType === "share"
                  ? {
                      background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                      color: "#fff",
                      borderColor: "rgba(0,0,0,0)"
                    }
                  : {}
              }
            >
              共享给我的
            </Radio.Button>
            <Radio.Button
              value="own"
              style={
                listPostData.tempType === "own"
                  ? {
                      background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                      color: "#fff",
                      borderColor: "rgba(0,0,0,0)"
                    }
                  : {}
              }
            >
              我的场景
            </Radio.Button>
          </Radio.Group>
        </Space>
      }
    >
      <Modal
        open={tempPreview}
        onCancel={tempPreviewClose}
        closable={false}
        width={937}
        styles={{
          content: {
            padding: 0,
            background: "#F4F3F6"
          }
        }}
        onClose={tempPreviewClose}
        footer={null}
      >
        <Flex
          justify="space-between"
          align="center"
          className="h-[64px] bg-white px-[24px] rounded-t-lg"
        >
          <span className="text-[16px] font-[#2A2A2A] font-bold">
            {tempPreviewInfo.name}
          </span>
          <div>
            <Button
              type="primary"
              style={{
                borderRadius: "4px",
                background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                color: "#fff",
                border: "none",
                marginRight: "30px",
                padding: "5px 10px",
                fontSize: "14px"
              }}
              onClick={() => handleEvent("toWrite", tempPreviewInfo.itemData)}
            >
              使用模板
            </Button>
            <CloseOutlined
              onClick={tempPreviewClose}
              style={{ fontSize: "14px" }}
            />
          </div>
        </Flex>
        <div className="py-5 px-6">
          <TempPreview
            htmlTemp={tempPreviewInfo.htmlTemp}
            cssTemp={tempPreviewInfo.cssTemp}
          />
        </div>
      </Modal>
      <div className="h-full overflow-y-auto overflow-x-hidden px-[20px] temp-m-box">
        <Tabs
          activeKey={activeTabKey}
          items={sceneClass}
          onChange={tabChange}
        />
        <Flex
          className="nlp-knowledgebase-manage-operations"
          justify="space-between"
        >
          <Button
            disabled={listPostData.tempType === "share"}
            icon={<PlusCircleOutlined />}
            type="primary"
            onClick={showChooseSceneModal}
            style={{
              background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
              color: "#fff",
              border: "none"
            }}
          >
            新建
          </Button>

          {/* <Search
            placeholder="输入名称搜索"
            style={{ width: "240px", marginRight: "16px" }}
            onSearch={onSearch}
            className="inputSearch border-solid border-[1px] hover:border-[#ABC3F5] rounded-[4px] h-[32px] leading-[32px]"
          /> */}
          <Input
            placeholder="输入名称搜索"
            className="w-[240px] h-[32px]"
            suffix={
              <SearchOutlined
                style={{ color: "#999", fontSize: 16 }}
                onClick={() => onSearch(searchValueRef.current)}
              />
            }
            onChange={(e) => {
              searchValueRef.current = e.target.value;
            }}
          />
        </Flex>
        <Spin spinning={listLoading}>
          {listData?.list && listData?.list?.length ? (
            <InfiniteScroll
              dataLength={listData?.list?.length}
              next={() => {
                // toAddNextList();
              }}
              hasMore={false} //listData?.list?.length < listData.total
              loader={
                <></>
                // <Spin
                //   tip="加载中……"
                //   className="text-[12px] text-[#0759859b] w-full"
                // />
              }
              endMessage={<></>} //<Divider plain>已完成加载</Divider>
              scrollableTarget="scrollableDiv"
            >
              <div className="py-[10px]">
                <ProCard ghost={true} wrap={true} gutter={[24, 16]}>
                  {(listData?.list || []).map((item: any, i: number) => {
                    return (
                      <ProCard
                        colSpan={{
                          xs: 6,
                          sm: 6,
                          md: 6,
                          lg: 6,
                          xl: 6,
                          xxl: 4
                        }}
                        key={item.id + `${i}`}
                        ghost={true}
                      >
                        <TemplateCard
                          item={item}
                          handleEvent={handleEvent}
                          btns={getOperationBtnOpts({
                            code: item?.permission || 1,
                            authManagement: manageTemplatePermission
                          })}
                        />
                      </ProCard>
                    );
                  })}
                </ProCard>
              </div>
            </InfiniteScroll>
          ) : (
            <div className="flex flex-col justify-center items-center w-full h-full mt-[150px]">
              <img src={empty} className="w-[106px] h-[91px]" />
              <div className="text-[16px] text-[#333] ml-[8px] mt-[8px]">
                暂无写作模板
              </div>
              <div className="text-[12px] text-[#999999] ml-[8px] mt-[8px]">
                开始新建吧~
              </div>
            </div>
          )}
        </Spin>
      </div>
      {/* <AddTemplate
        open={showModal}
        onClose={closeModal}
        modalType={modalType}
        editData={editItem}
        cb={refreshList}
      /> */}
      <DeleteConfirm
        isShowDeleteModal={showDeleteModal}
        confirmModal={confirmModal}
        closeModal={closeDeleteModal}
        loading={deleteLoading}
      />
      <Modal
        open={isShowSceneChooseModal}
        title="选择场景类型"
        width={600}
        destroyOnClose={true}
        footer={null}
        onCancel={hideChooseSceneModal}
      >
        {sceneList.map((s: any, idx: number) => {
          return (
            <div
              className="w-[512px] text-[#2a2a2a] hover:text-[#055aff] h-12 box-content bg-[#f1f4f7] flex mb-[17px] p-5 cursor-pointer justify-between rounded-[4px] hover:bg-[#f1f5ff] border-none hover:border-[#2b69ff] hover:border-solid hover:border-[1px]"
              key={`scene_type_${idx}_${s.key}`}
              onClick={createHandler(s.key)}
            >
              <div className="flex flex-grow">
                <div className="mr-4">
                  <img src={IconScene} />
                </div>
                <div>
                  <div className="text-base font-bold mb-1">{s.label}</div>
                  <div className="text-sm text-[#888]">{s.dsc}</div>
                </div>
              </div>
              <div className="flex flex-col justify-center">
                <img src={IconRightArrow} />
              </div>
            </div>
          );
        })}
      </Modal>
      <Modal
        open={!!sceneId}
        title="查看版本"
        width={860}
        destroyOnClose={true}
        footer={null}
        onCancel={closeVersionModal}
      >
        <div className="pb-5">
          <Table
            rowKey={(_) => _.versionId}
            loading={versionLoading}
            columns={versionColumns}
            dataSource={sceneVersionList}
            pagination={false}
            scroll={{
              y: "500px"
            }}
          />
        </div>
      </Modal>
      <ConfigProvider
        drawer={{
          styles: {
            body: { padding: 0 },
            header: { padding: "20px 20px 16px 20px" }
          }
        }}
      >
        <Drawer
          title={
            <div className="flex justify-between items-center">
              <div className="text-[16px] font-bold">授权</div>
              <CloseOutlined
                className="cursor-pointer"
                onClick={() => setOpenPermission(false)}
              />
            </div>
          }
          closable={false}
          width={557}
          onClose={() => setOpenPermission(false)}
          open={openPermission}
        >
          <div className="h-[calc(100vh-100px)] relative px-[20px] pt-[10px] pb-[20px]">
            <PermissionConfig
              drawConfig={drawConfig}
              subTitle="场景公开范围"
              bizType={5}
              type="cec-temp"
            />
          </div>
        </Drawer>
      </ConfigProvider>
    </CommonLayout>
  );
};

export default TemplateM;
