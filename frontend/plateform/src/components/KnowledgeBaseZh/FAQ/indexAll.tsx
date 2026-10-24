/* eslint-disable react-refresh/only-export-components */
/* eslint-disable no-case-declarations */
import {
  Button,
  Empty,
  Input,
  Spin,
  Select,
  Pagination,
  Tooltip,
  Drawer,
  Radio,
  Popover,
  Modal,
  message,
  ConfigProvider
} from "antd";
import {
  CloseOutlined,
  PlusCircleOutlined,
  SearchOutlined,
  SyncOutlined
} from "@ant-design/icons";
import IconImport from "@/assets/knowledgebase/icon-import.svg";
import FaqUploadModal from "./FaqUploadModal";
import FaqRow, { FaqDrawerContent, SimilarDrawerContent } from "./FaqRow";
import RepeatFaq from "./RepeatFaq";
import "@/assets/styles/faqAll.less";
import { ICrumbs, useFaqController } from "../common/useFaqController";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import { useLocation, useParams } from "react-router-dom";
import IconCrumbs from "@/assets/knowledgebase/icon-crumbs.svg";
import FAQFolder from "./FAQFolder";
import { useServices } from "../service";
import TagDrawerContent from "../components/TagDrawerContent";
import FileFolderTransferContent from "../components/FileFolderTransferContent ";
import PermisssonConfig from "@root/src/pages/Components/PermissionConfig";

const FaqManageList = ({ knowledgeBaseId, fileId, kbInfo }: any) => {
  const params = useParams();
  const { state } = useLocation();

  const {
    setCurSimilarParentList,
    bizLabelList,
    drawConfig,
    btnLoading,
    drawerStyles,
    showSpin,
    isFaqManage,
    batchValue,
    confirmLoading,
    batch_operations,
    fuzzy,
    setCheckAll,
    faqData,
    editQaPk,
    editSimilarPk,
    expandSimilarQaPk,
    type,
    editQuestion,
    editAnswer,
    page,
    total,
    isBatchEnable,
    isCheckRepeatShow,
    repeatList,
    setPolishContentList,
    curSimilarList,
    similarLoading,
    curItem,
    polishLoading,
    curPolishContent,
    polishContentList,
    polishContentPage,
    polishBtnLoading,
    checkAll,
    showUploadModal,
    openDrawer,
    openDraw,
    setOpenDraw,
    setShowUploadModal,
    addNewQuestion,
    refreshList,
    changeBatch,
    repeatFaqCheck,
    handleBatchMenu,
    rowActionHandler,
    onCheckAllChange,
    setOpenDrawer,
    setType,
    setEditQuestion,
    setEditAnswer,
    onPageSizeChange,
    uploadDone,
    handleEvent,
    repeatFaqCheckDone,
    cancleEditQa,
    setCurPolishContent,
    setCurSimilarList,
    submitAddSimilar,
    deleteSimilarConfirm,
    submitUpdateSimilar,
    submitQa,
    editAnswerOnChange,
    editQuestionOnChange,
    handlerPolish,
    fuzzyOnChange,
    docKeyDown,
    addSimilarQaPk,
    crumbs,
    isCreateFolderShow,
    setIsCreateFolderShow,
    returnFolder,
    closeCreateFolder,
    editFolder,
    newFolderName,
    tableLoading,
    newFolderNameOnChange,
    createFolderConfirm,
    setEditFolder,
    isCreatFolder,
    setFolder
  } = useFaqController({ knowledgeBaseId, fileId, state, kbInfo, params });

  return (
    <>
      <div className="faq-list-wrap">
        <Spin size="large" spinning={showSpin}>
          <div className="fat-header-btn-wrap">
            <div className="btn-left">
              {isFaqManage ? (
                <Button
                  style={{
                    background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                    color: "#fff",
                    border: "none"
                  }}
                  icon={<img src={IconImport} />}
                  onClick={() => setShowUploadModal(true)}
                  disabled={getBtnDisabled(FILE_BTN.ADD, kbInfo.permission)}
                >
                  导入
                </Button>
              ) : null}
              <Button
                ghost
                style={{ border: "1px solid #eee" }}
                icon={<PlusCircleOutlined />}
                type="primary"
                onClick={addNewQuestion}
                className="border-none"
                disabled={
                  confirmLoading ||
                  getBtnDisabled(FILE_BTN.ADD, kbInfo.permission)
                }
              >
                新建问答
              </Button>
              <Button
                ghost
                style={{ border: "1px solid #eee" }}
                icon={<PlusCircleOutlined />}
                type="primary"
                onClick={() => {
                  setEditFolder(undefined);
                  setIsCreateFolderShow(true);
                }}
                className="border-none"
                disabled={
                  confirmLoading ||
                  getBtnDisabled(FILE_BTN.ADD, kbInfo.permission) ||
                  !isCreatFolder
                }
              >
                新建文件夹
              </Button>
              <Select
                allowClear
                disabled={confirmLoading}
                placeholder="更多操作"
                style={{
                  width: "120px",
                  borderRadius: "10px",
                  color: "#055aff"
                }}
                value={batchValue}
                onSelect={handleBatchMenu}
              >
                {batch_operations.map((i: any) => {
                  return (
                    <Select.Option
                      key={i.value}
                      value={i.value}
                      disabled={i.disabled}
                    >
                      <div className="more-action-row">{i.label}</div>
                    </Select.Option>
                  );
                })}
              </Select>
            </div>
            <div className="flex items-center">
              <Input
                value={fuzzy}
                disabled={confirmLoading}
                placeholder="搜索内容"
                style={{
                  width: "240px",
                  marginRight: "8px"
                  // border: "1px solid #ebebeb",
                }}
                suffix={
                  <div className="cursor-pointer" onClick={refreshList}>
                    <SearchOutlined style={{ color: "#999", fontSize: 12 }} />
                  </div>
                }
                onChange={fuzzyOnChange}
                onKeyDown={docKeyDown}
              />
              {!isFaqManage ? (
                <Tooltip
                  placement="top"
                  title={<span className="text-[#2A2A2A]">换一批</span>}
                  color="#fff"
                  className="text-text-color1"
                >
                  <Button icon={<SyncOutlined />} onClick={changeBatch} />
                </Tooltip>
              ) : (
                <></>
              )}
              {isFaqManage ? (
                <Button
                  style={{
                    color: "#055aff",
                    border: "1px solid #ebebeb"
                  }}
                  onClick={repeatFaqCheck}
                  disabled={
                    confirmLoading ||
                    getBtnDisabled(FILE_BTN.ADD, kbInfo.permission)
                  }
                >
                  重复问题检测
                </Button>
              ) : null}
            </div>
          </div>
          <div>
            <Radio
              checked={checkAll === 1}
              onClick={(e: any) => {
                if (checkAll === 1) {
                  setCheckAll(undefined);
                  onCheckAllChange(false);
                } else {
                  setCheckAll(1);
                  onCheckAllChange(true);
                }
              }}
            >
              选择当前页
            </Radio>
            <Popover
              placement="top"
              content="选择全部，将影响当前知识库所有问答对"
              color="#fff"
            >
              <Radio
                checked={checkAll === 2}
                onClick={(e: any) => {
                  if (checkAll === 2) {
                    setCheckAll(undefined);
                    onCheckAllChange(false);
                  } else {
                    setCheckAll(2);
                    onCheckAllChange(true);
                  }
                }}
              >
                选择全部
              </Radio>
            </Popover>
          </div>
          {crumbs.length > 1 ? (
            <div className="py-4 flex items-center">
              <img src={IconCrumbs} />
              <span className="ml-2 crumbs-wrap">
                {crumbs.map((c: ICrumbs, idx: number) => {
                  return (
                    <span
                      key={`crumbs_${c.id}_${idx}`}
                      className={`${idx === crumbs.length - 1 ? "" : "crumbs-link"}`}
                    >
                      <span onClick={() => returnFolder(c.id)}>
                        {c.name || "未命名文件夹"}
                      </span>
                    </span>
                  );
                })}
              </span>
            </div>
          ) : null}
          <div className="list-main-wrap">
            <div className="list-content-wrap">
              {!showSpin && !faqData.length ? (
                <div className="flex justify-center items-center h-full min-h-96">
                  <Empty />
                </div>
              ) : (
                <>
                  {faqData.map((item: any, idx: number) => (
                    <>
                      {item.dataType === 3 ? (
                        <FaqRow
                          key={item.pk || item.relatedPk || item.id}
                          item={item}
                          idx={idx}
                          confirmLoading={confirmLoading}
                          rowActionHandler={rowActionHandler}
                          setOpenDrawer={setOpenDrawer}
                          type={type}
                          setType={setType}
                          editQuestion={editQuestion}
                          setEditQuestion={setEditQuestion}
                          editAnswer={editAnswer}
                          setEditAnswer={setEditAnswer}
                          kbInfo={kbInfo}
                        />
                      ) : (
                        <FAQFolder
                          key={item.folderId || item.fileId || item.pk}
                          item={item}
                          idx={idx}
                          rowActionHandler={rowActionHandler}
                        />
                      )}
                    </>
                  ))}
                </>
              )}
            </div>
            <div className="py-[20px]">
              <Pagination
                align="end"
                total={total}
                pageSize={page.pageSize}
                current={page.pageNo}
                onChange={onPageSizeChange}
              />
            </div>
          </div>
        </Spin>
      </div>
      <Modal
        destroyOnClose={true}
        footer={null}
        open={isCreateFolderShow}
        width={620}
        onCancel={closeCreateFolder}
        title={`${editFolder && editFolder.id ? "重命名文件夹" : "新建文件夹"}`}
      >
        <div className="create-folder-ipt my-5">
          <Input
            value={newFolderName}
            disabled={tableLoading}
            placeholder="请输入文件夹名称"
            style={{
              height: "40px"
            }}
            onChange={newFolderNameOnChange}
          />
        </div>
        <div className="flex mt-5 gap-4 flex-row-reverse">
          <Button
            loading={tableLoading}
            disabled={!newFolderName}
            type="default"
            className="border-none"
            onClick={createFolderConfirm}
            style={{
              background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
              color: "#fff"
            }}
          >
            确认
          </Button>
          <Button
            disabled={tableLoading}
            style={{
              color: "#555",
              border: "1px solid rgb(235, 235, 235)"
            }}
            onClick={closeCreateFolder}
          >
            取消
          </Button>
        </div>
      </Modal>
      <FaqUploadModal
        isShowCreateModal={showUploadModal}
        closeModal={uploadDone}
        uploadEvents={handleEvent}
        knowledgeBaseId={knowledgeBaseId}
        uploadType="import"
      />

      <RepeatFaq
        isShow={isCheckRepeatShow}
        isBatchEnable={isBatchEnable}
        repeatList={repeatList}
        closeModal={repeatFaqCheckDone}
        fileId={fileId}
        knowledgeBaseId={knowledgeBaseId}
        faqData={faqData}
      />
      <Drawer
        closable
        destroyOnClose
        placement="right"
        open={openDrawer}
        width={840}
        styles={drawerStyles}
        onClose={cancleEditQa}
        forceRender
        getContainer={false}
        afterOpenChange={(open) => {
          if (!open) {
            setEditQuestion("");
            setEditAnswer("");
            setCurSimilarList([]);
            setCurSimilarParentList([]);
            setCurPolishContent("");
            setPolishContentList([]);
          }
        }}
      >
        {type === "similar" && (
          <SimilarDrawerContent
            setData={setCurSimilarList}
            data={curSimilarList}
            similarLoading={similarLoading}
            submitAddSimilar={submitAddSimilar}
            deleteSimilarConfirm={deleteSimilarConfirm}
            submitUpdateSimilar={submitUpdateSimilar}
            curItem={curItem}
            knowledgeBaseId={knowledgeBaseId}
            cancleEditQa={cancleEditQa}
            kbInfo={kbInfo}
          />
        )}
        {(type === "edit" || type === "add") && (
          <FaqDrawerContent
            type={type}
            data={curItem}
            onCancel={cancleEditQa}
            submitQa={submitQa}
            editQuestion={editQuestion}
            editAnswer={editAnswer}
            editAnswerOnChange={editAnswerOnChange}
            editQuestionOnChange={editQuestionOnChange}
            confirmLoading={confirmLoading}
            polishLoading={polishLoading}
            curPolishContent={curPolishContent}
            polishContentList={polishContentList}
            polishContentPage={polishContentPage}
            polishBtnLoading={polishBtnLoading}
            handlerPolish={handlerPolish}
            knowledgeBaseId={knowledgeBaseId}
            openDrawer={openDrawer}
            setFolder={setFolder}
          />
        )}
        {type === "tag" && (
          <TagDrawerContent
            drawConfig={drawConfig}
            btnLoading={btnLoading}
            emitEvent={rowActionHandler}
            bizLabelList={bizLabelList}
          />
        )}
      </Drawer>
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
              <div className="text-[16px] font-bold">
                {drawConfig.type === "permission"
                  ? "权限配置"
                  : drawConfig.type === "tag"
                    ? "标签"
                    : drawConfig.type === "transfer"
                      ? "转移到"
                      : ""}
              </div>
              <CloseOutlined
                className="cursor-pointer"
                onClick={() => setOpenDraw(false)}
              />
            </div>
          }
          closable={false}
          width={557}
          onClose={() => setOpenDraw(false)}
          open={openDraw}
          destroyOnClose
        >
          <div className="h-[calc(100vh-100px)] relative px-[20px] pt-[10px] pb-[20px]">
            {drawConfig.type === "tag" && (
              <TagDrawerContent
                drawConfig={drawConfig}
                btnLoading={btnLoading}
                emitEvent={rowActionHandler}
                bizLabelList={bizLabelList}
              />
            )}
            {drawConfig.type === "transfer" && (
              <FileFolderTransferContent
                drawConfig={{ ...drawConfig, data: drawConfig.data || {} }}
                handleEvent={handleEvent}
                btnLoading={btnLoading}
                fileListType={4}
                kbName={kbInfo.primitiveName}
              />
            )}
            {drawConfig.type === "permission" && (
              <PermisssonConfig
                drawConfig={drawConfig}
                subTitle={
                  drawConfig.data.dataType === 1
                    ? "文件夹公开范围"
                    : "文档公开范围"
                }
                bizType={drawConfig.bizType as any}
                type="docuRight"
              />
            )}
          </div>
        </Drawer>
      </ConfigProvider>
    </>
  );
};
export default FaqManageList;
