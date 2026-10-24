/* eslint-disable react-refresh/only-export-components */
/* eslint-disable no-case-declarations */
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { useFaqController } from "../common/useFaqController";
import loading from "@/assets/gif/loading.gif";
import {
  Button,
  Checkbox,
  Empty,
  Input,
  message,
  Spin,
  Select,
  Pagination,
  Tooltip,
  Drawer,
  Radio,
  RadioChangeEvent,
  Popover
} from "antd";
import {
  PlusCircleOutlined,
  SearchOutlined,
  SyncOutlined
} from "@ant-design/icons";
import IconImport from "@/assets/knowledgebase/icon-import.svg";
import FaqUploadModal from "./FaqUploadModal";
import FaqRow, { FaqDrawerContent, SimilarDrawerContent } from "./FaqRow";
import RepeatFaq from "./RepeatFaq";
import "@/assets/styles/faq.less";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import { useServices } from "../service";

const FaqManageList = () => {
  const { knowledgeBaseId, id: fileId }: any = useParams();
  const navigator = useNavigate();
  const { state } = useLocation();
  const {
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
    faqInfo,
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
    goBack
  } = useFaqController({
    knowledgeBaseId,
    fileId,
    navigator,
    state
  });

  return (
    <div className="faq-edit-wrap">
      <div className="faq-nav-wrap">
        <div className="breadcrumb-wrap" onClick={goBack}>
          {faqInfo.title}
        </div>
      </div>
      <div className="faq-list-wrap">
        <Spin
          spinning={showSpin}
          indicator={
            <img
              src={loading}
              style={{
                width: "120px",
                height: "120px",
                transform: "translate(-50%,0)"
              }}
            />
          }
        >
          <div className="fat-header-btn-wrap">
            <div className="btn-left">
              {isFaqManage ? (
                <Button
                  style={{
                    background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                    color: "#fff"
                  }}
                  icon={<img src={IconImport} />}
                  onClick={() => setShowUploadModal(true)}
                  disabled={getBtnDisabled(FILE_BTN.ADD, faqInfo.permission)}
                >
                  导入
                </Button>
              ) : null}
              {isFaqManage ? (
                <Button
                  ghost
                  style={{ border: "1px solid #eee" }}
                  icon={<PlusCircleOutlined />}
                  type="primary"
                  disabled={
                    confirmLoading ||
                    getBtnDisabled(FILE_BTN.ADD, faqInfo.permission)
                  }
                  onClick={addNewQuestion}
                  className="border-none"
                >
                  新建
                </Button>
              ) : (
                <Button
                  style={{
                    background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                    color: "#fff"
                  }}
                  icon={<PlusCircleOutlined />}
                  disabled={
                    confirmLoading ||
                    getBtnDisabled(FILE_BTN.ADD, faqInfo.permission)
                  }
                  onClick={addNewQuestion}
                  className="border-none"
                >
                  新建
                </Button>
              )}
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
                  disabled={
                    confirmLoading ||
                    getBtnDisabled(FILE_BTN.ADD, faqInfo.permission)
                  }
                  onClick={repeatFaqCheck}
                >
                  重复问题检测
                </Button>
              ) : null}
            </div>
          </div>
          {/* <div className="check-all-wrap">
            <Checkbox
              checked={checkAll}
              indeterminate={indeterminate}
              onChange={onCheckAllChange}
            />
            <span className="check-all-txt">选择</span>
          </div> */}
          <div className="mb-[16px]">
            {/* onChange={(e: RadioChangeEvent) => {
                if (checkAll === e.target.value) {
                  setCheckAll(undefined);
                  return;
                }
                setCheckAll(e.target.value);
              }}
              value={checkAll} */}
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
          <div className="list-main-wrap">
            <div className="list-content-wrap">
              {!showSpin && !faqData.length ? (
                <div className="flex justify-center items-center h-full min-h-96">
                  <Empty />
                </div>
              ) : (
                <>
                  {faqData.map((item: any, idx: number) => (
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
                      kbInfo={faqInfo}
                    />
                  ))}
                </>
              )}
            </div>
            <div className="pt-5">
              <Pagination
                size="small"
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
            kbInfo={faqInfo}
          />
        )}
      </Drawer>
    </div>
  );
};
export default FaqManageList;
