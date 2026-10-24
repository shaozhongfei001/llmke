import {
  Input,
  Button,
  Flex,
  Table,
  Pagination,
  Drawer,
  Tabs,
  Select
} from "antd";
import {
  CaretDownOutlined,
  PlusCircleOutlined,
  SearchOutlined,
  UploadOutlined
} from "@ant-design/icons";
import useController from "./common/useController";
import DeleteConfirm from "../common/components/DeleteModal";
import TaskDetail from "./components/TaskDetail";
import { CommonLayout } from "../common/components/CommonLayout";
import "./common/style.less";
const mockData = [
  {
    id: 1,
    title: "对公固定资产调查报告",
    totalChapter: undefined,
    chaptersInWriting: undefined,
    status: 3,
    totalTask: undefined,
    successTask: undefined,
    author: "张三",
    gmtModified: "2025-03-25 10:27",
    isOline: true
  },
  {
    id: 2,
    title: "对公固定资产调查报告",
    totalChapter: 18,
    chaptersInWriting: 2,
    status: 1,
    totalTask: 5,
    successTask: 1,
    author: "张三",
    gmtModified: "2025-03-25 10:27",
    isOline: false,
    taskId: 5,
    articleId: 2757
  },
  {
    id: 3,
    title: "对公固定资产调查报告",
    totalChapter: 18,
    chaptersInWriting: 2,
    status: 2,
    totalTask: 5,
    successTask: 1,
    author: "张三",
    gmtModified: "2025-03-25 10:27",
    isOline: false,
    taskId: 4,
    articleId: 2757
  },
  {
    id: 4,
    title: "对公固定资产调查报告",
    totalChapter: 18,
    chaptersInWriting: 2,
    status: 4,
    totalTask: 5,
    successTask: 1,
    author: "张三",
    gmtModified: "2025-03-25 10:27",
    isOline: false,
    taskId: 5,
    articleId: 2757
  },
  {
    id: 5,
    title: "对公固定资产调查报告",
    totalChapter: 18,
    chaptersInWriting: 2,
    status: 3,
    totalTask: 5,
    successTask: 1,
    author: "张三",
    gmtModified: "2025-03-25 10:27",
    isOline: false,
    taskId: 4,
    articleId: 2757
  }
];

const HistoryM = () => {
  const {
    listData,
    listPostData,
    columns,
    showDeleteModal,
    closeDeleteModal,
    deleteLoading,
    confirmModal,
    handleEvent,
    onSearch,
    handleFileChange,
    fileRefresh,
    onPageSizeChange,
    searchValueRef,
    loading,
    taskDetailOpen,
    closeTaskDetail,
    docTaskItem,
    highlightId,
    operationLoading,
    stateSelectOptions,
    stateSelectValueChange,
    stateSelectOpen,
    handleStateSelectToggle
  }: any = useController();

  return (
    <>
      <CommonLayout name="我的文档">
        <div className="bg-white h-full rounded-[8px] p-[20px] overflow-x-hidden history-doc-box">
          {/* <Tabs></Tabs> */}
          <Flex justify="space-between">
            <div>
              <Button
                icon={<PlusCircleOutlined />}
                type="primary"
                onClick={() => handleEvent("add")}
                style={{
                  background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                  color: "#fff",
                  border: "none",
                  marginRight: "10px",
                  boxShadow: "none"
                }}
              >
                新建
              </Button>
              {/* 20251215去除上传功能 */}
              {/* <Button
                icon={<UploadOutlined />}
                onClick={() => {}}
                style={{
                  border: "1px solid #EEEEEE",
                  color: "#2A2A2A",
                  position: "relative",
                  boxShadow: "none"
                }}
              >
                <input
                  type="file"
                  accept=".docx,.doc"
                  className="w-full h-full absolute top-0 left-0 opacity-0"
                  onChange={handleFileChange}
                  // 通过key处理两次选择一样的文件，不触发onChange的问题
                  key={fileRefresh}
                />
                上传
              </Button> */}
            </div>

            {/* <Search
            style={{ width: "240px", marginRight: "16px" }}
            placeholder="输入名称搜索"
            onSearch={onSearch}
            className="inputSearch border-solid border-[1px] hover:border-[#ABC3F5] rounded-[4px] h-[32px] leading-[32px]"
          /> */}
            <div className="flex gap-[12px]">
              {/* <Select
                className="w-[110px] h-[32px]"
                options={stateSelectOptions}
                value={listPostData.taskState}
                onChange={stateSelectValueChange}
                suffixIcon={
                  <CaretDownOutlined
                    rotate={stateSelectOpen ? 180 : 0}
                    style={{ color: "#888" }}
                    onClick={handleStateSelectToggle}
                  />
                }
                open={stateSelectOpen}
                onClick={handleStateSelectToggle}
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
            </div>
          </Flex>
          <div className="mt-[16px] h-[calc(100%-112px)] overflow-y-auto">
            <Table
              columns={columns}
              size="small"
              rowKey={(record) => record.id}
              // dataSource={mockData}
              dataSource={listData}
              pagination={false}
              loading={loading || operationLoading}
              onRow={(record) => {
                if (record.id == Number(highlightId)) {
                  return {
                    className: "animated-background h-[32px]"
                  };
                } else {
                  return {
                    className: "h-[32px]"
                  };
                }
              }}
            />
          </div>
          <Pagination
            className="mt-[16px]"
            align="end"
            total={listPostData.totalCount}
            pageSize={10}
            current={listPostData.pageNo}
            onChange={onPageSizeChange}
            showSizeChanger={false}
          />
        </div>
      </CommonLayout>
      <DeleteConfirm
        isShowDeleteModal={showDeleteModal}
        confirmModal={confirmModal}
        closeModal={closeDeleteModal}
        loading={deleteLoading}
      />
      <Drawer
        width={800}
        onClose={closeTaskDetail}
        open={taskDetailOpen}
        title={null}
        styles={{
          header: {
            height: 0,
            width: 0,
            display: "none"
          },
          footer: {
            height: 0,
            width: 0,
            display: "none"
          },
          body: {
            padding: 0
          }
        }}
      >
        <TaskDetail
          item={docTaskItem}
          isOpen={taskDetailOpen}
          onClose={closeTaskDetail}
        />
      </Drawer>
    </>
  );
};

export default HistoryM;
