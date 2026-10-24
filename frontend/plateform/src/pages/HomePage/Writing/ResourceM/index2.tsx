import {
  Input,
  Button,
  Flex,
  Tag,
  Modal,
  Tabs,
  ConfigProvider,
  message,
  Table,
  Pagination
} from "antd";
import { SearchOutlined, UploadOutlined } from "@ant-design/icons";
import FileViewCec from "@root/src/components/FileViewCec";
import useController from "./common/useController";
import DeleteConfirm from "../common/components/DeleteModal";
import ResourceUploadModal from "./common/ResourceUploadModal";
import {
  sceneTagMap,
  styleTagMap,
  tabItems,
  modalStyles
} from "./common/constans";
import "./index.less";

const { Search } = Input;

const ResourceM = () => {
  const {
    columns,
    showUploadModal,
    handleEvent,
    showDeleteModal,
    deleteLoading,
    confirmModal,
    showPreviewModal,
    curFileInfo,
    listData,
    listPostData,
    onSearch,
    activeTabKey,
    selectedSenceTags,
    handleSenceTagChange,
    selectedStyleTags,
    handleStyleTagChange,
    previewGoWrite,
    onPageSizeChange,
    searchValueRef
  }: any = useController();

  console.log("--------4", listPostData);

  return (
    <div className="h-full relative overflow-hidden">
      <Flex
        justify="space-between"
        align="center"
        className="mb-[16px] ml-[12px]"
      >
        <div className="text-[16px] text-text-color1 font-bold">素材管理</div>
      </Flex>
      <div className="bg-white h-[calc(100%-56px)] rounded-[8px] overflow-y-auto overflow-x-hidden px-[20px] resource-box">
        <Tabs
          activeKey={activeTabKey}
          items={tabItems}
          onChange={(key: string) => handleEvent("tabChange", key)}
        />
        <Flex justify="space-between">
          <Button
            icon={<UploadOutlined />}
            type="primary"
            onClick={() => handleEvent("openUploadModal")}
            style={{
              background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
              color: "#fff",
              border: "none"
            }}
          >
            上传
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
        <div className="material mt-[16px]">
          {activeTabKey == "demoLib" && (
            <Flex>
              <div className="font-bold w-[50px] h-[32px] leading-[32px]">
                文体
              </div>
              <div>
                {styleTagMap.map<React.ReactNode>((tag) => (
                  <Tag.CheckableTag
                    key={tag.key}
                    checked={selectedStyleTags.includes(tag.label)}
                    onChange={(checked) =>
                      handleStyleTagChange(tag.label, checked)
                    }
                    className="bg-[#F5F6FA] hover:text-[#055AFF] hover:bg-[#E2E9FF] text-[14px] mb-[12px] h-[32px] leading-[32px]"
                  >
                    {tag.label}
                  </Tag.CheckableTag>
                ))}
              </div>
            </Flex>
          )}

          {(activeTabKey == "lawLib" || activeTabKey == "demoLib") && (
            <Flex>
              <div className="font-bold w-[50px] h-[32px] leading-[32px]">
                场景
              </div>
              <div>
                {sceneTagMap.map<React.ReactNode>((tag) => (
                  <Tag.CheckableTag
                    key={tag.key}
                    checked={selectedSenceTags.includes(tag.label)}
                    onChange={(checked) =>
                      handleSenceTagChange(tag.label, checked)
                    }
                    className="bg-[#F5F6FA] hover:text-[#055AFF] hover:bg-[#E2E9FF] text-[14px] mb-[12px] h-[32px] leading-[32px]"
                  >
                    {tag.label}
                  </Tag.CheckableTag>
                ))}
              </div>
            </Flex>
          )}
        </div>
        <div
          // className="h-[calc(100%-28px)] overflow-y-hidden overflow-x-hidden mt-[16px]"
          id="cec-material-table"
        >
          <Table
            columns={columns}
            rowKey={(record) => record.id}
            dataSource={listData}
            pagination={false}
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
      <ResourceUploadModal
        isShowCreateModal={showUploadModal}
        cb={handleEvent}
        closeModal={() => handleEvent("closeUploadModal")}
        type={activeTabKey}
      />
      <DeleteConfirm
        isShowDeleteModal={showDeleteModal}
        confirmModal={confirmModal}
        closeModal={() => handleEvent("closeDeleteModal")}
        loading={deleteLoading}
      />
      <ConfigProvider
        modal={{
          styles: modalStyles
        }}
      >
        <Modal
          destroyOnClose={true}
          open={showPreviewModal}
          onCancel={() => {
            handleEvent("closePreviewModal");
          }}
          width={900}
          height={742}
          closable={false}
          maskClosable={false}
          footer={
            <Flex
              className="h-[68px] pr-6"
              align="center"
              justify="flex-end"
              gap={16}
            >
              {/* <Button
                onClick={() => {
                  handleE("close");
                }}
              >
                关闭
              </Button> */}
              {activeTabKey !== "lawLib" && (
                <Button
                  style={{
                    background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                    color: "#fff",
                    border: "none"
                  }}
                  onClick={() => {
                    previewGoWrite(curFileInfo);
                  }}
                  disabled={
                    !["doc", "docx"].includes(curFileInfo.fileSuffix) ||
                    !curFileInfo.htmlUrl
                  }
                >
                  去写作
                </Button>
              )}
            </Flex>
          }
        >
          <div className="h-[600px] overflow-y-auto">
            <FileViewCec
              curFileInfo={curFileInfo}
              handleEvent={() => handleEvent("closePreviewModal")}
            />
          </div>
        </Modal>
      </ConfigProvider>
    </div>
  );
};
export default ResourceM;
