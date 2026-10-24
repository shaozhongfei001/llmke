import { useState, useMemo, useEffect } from "react";
import {
  Button,
  Checkbox,
  Input,
  Pagination,
  Popconfirm,
  Select,
  Switch,
  Tag
} from "antd";
import {
  CloseOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusCircleOutlined
} from "@ant-design/icons";
import Polish from "@/assets/img/polish.png";
import PolishDisabled from "@/assets/img/polishDisabled.png";
const { TextArea } = Input;
import "@/assets/styles/faq.less";
import Genera from "@/assets/gif/genera.gif";
import {
  faqBatchType,
  faqSimilarOptions,
  similarBatchType
} from "@root/src/const/knowledgebase";
import EditSimilarTable from "./EditSimilarTable";
import { uid } from "uid";
import { getFaqByRelatedPk } from "./service";
import { rowActionType } from "../common/useFaqController";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import { useLocation } from "react-router-dom";
import FolderSelect from "./FolderSelect";
import LabelCom from "../components/LabelCom";

interface IFaqRow {
  kbInfo: any;
  editQuestion: string;
  setEditQuestion: (arg: string) => void;
  editAnswer: string;
  setEditAnswer: (arg: string) => void;
  type: string;
  setType: (arg: string) => void;
  item: any;
  idx: number;
  confirmLoading: boolean;
  setOpenDrawer: (arg: boolean) => void;
  rowActionHandler: (actionType: rowActionType, data?: any) => void;
}

const FaqRow = (props: IFaqRow) => {
  const {
    item,
    idx,
    confirmLoading,
    rowActionHandler,
    setOpenDrawer,
    setType,
    setEditQuestion,
    setEditAnswer,
    kbInfo
  } = props;

  const editQa = () => {
    setType("edit");
    setOpenDrawer(true);
    const { pk, question, answer } = item;
    setEditQuestion(question);
    setEditAnswer(answer);
    rowActionHandler(rowActionType.EDIT_QA, { ...item, idx });
  };

  const changeStatusQa = (isChecked: boolean) => {
    rowActionHandler(rowActionType.CHANGE_STATUS_QA, {
      idx,
      isChecked,
      relatedPks: [item]
    });
  };

  const labels = useMemo(() => {
    if (item.label) {
      return item.label.split(",");
    } else {
      return [];
    }
  }, [item]);

  return (
    <div className="faq-row" key={item.pk || item.id}>
      <div className="question-row">
        <div className="question-wrap">
          <div className={`checkbox-cell`}>
            <Checkbox
              checked={item.isChecked}
              onChange={(v) =>
                rowActionHandler(rowActionType.CHECK_QA, {
                  idx,
                  isChecked: v.target.checked
                })
              }
            />
          </div>
          <div className="question-cell">
            <div className={`question-title`}>Q:</div>
            <div className="question-info">{item.question}</div>
          </div>
        </div>
        <div className={`flex items-center`}>
          <Tag
            className={`${getBtnDisabled(FILE_BTN.VIEW, item.permission) ? "cursor-not-allowed" : "cursor-pointer"}`}
            onClick={() => {
              if (getBtnDisabled(FILE_BTN.VIEW, item.permission)) {
                return;
              }
              rowActionHandler(rowActionType.OPEN_SIMILAR, item);
            }}
          >
            相似问
            <span className="text-primary-color">
              {item.similarQuestions?.length}
            </span>
          </Tag>
          {/* <LabelCom
            labels={labels}
            item={item}
            rowActionHandler={rowActionHandler}
          /> */}
          <Button
            type="link"
            size={"small"}
            disabled={getBtnDisabled(FILE_BTN.EDIT, item.permission)}
            onClick={() => {
              rowActionHandler(rowActionType.TRANSFER, item);
            }}
          >
            转移到
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            title="编辑"
            disabled={
              confirmLoading || getBtnDisabled(FILE_BTN.ADD, item.permission)
            }
            className=" text-[#333333]"
            onClick={editQa}
          />
          <Popconfirm
            title="删除问答对"
            disabled={confirmLoading}
            description="确认删除问答对吗？"
            okText="确认"
            cancelText="取消"
            onConfirm={() => {
              rowActionHandler(rowActionType.DELETE_QA, {
                relatedPks: [item.relatedPk],
                pks: [item.pk]
              });
            }}
          >
            <Button
              type="link"
              disabled={
                confirmLoading ||
                getBtnDisabled(FILE_BTN.DELETE, item.permission)
              }
              title="删除"
              icon={<DeleteOutlined />}
              className=" text-[#333333]"
            />
          </Popconfirm>
          <Switch
            disabled={
              confirmLoading || getBtnDisabled(FILE_BTN.ADD, item.permission)
            }
            checkedChildren="启用"
            unCheckedChildren="禁用"
            title={item.status === 1 ? "禁用" : "启用"}
            onChange={changeStatusQa}
            value={item.status === 1}
          />
        </div>
      </div>
      <div className="answer-row">
        <div className={`answer-title`}>A:</div>
        <div className="answer-info">{item.answer}</div>
      </div>
    </div>
  );
};
export default FaqRow;

export const SimilarDrawerContent = ({
  data,
  setData,
  similarLoading,
  submitAddSimilar,
  deleteSimilarConfirm,
  submitUpdateSimilar,
  curItem,
  knowledgeBaseId,
  cancleEditQa,
  kbInfo
}: any) => {
  const { state } = useLocation();
  const [batchValue, setBatchValue] = useState(null);
  const [tableLoading, setTableLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const handleBatchMenu = (batchName: any) => {
    switch (batchName) {
      case similarBatchType.DELETE:
        deleteSimilarConfirm(selectedRowKeys);
        break;
    }
    setBatchValue(null);
  };
  const addNewSimilar = () => {
    setData((pre: any[]) => {
      return [
        {
          editable: true,
          similarQuestion: "",
          add: true,
          first: true,
          key: `add_${uid()}`
        },
        ...pre
      ];
    });
  };
  return (
    <div className="flex flex-col justify-between h-full overflow-hidden">
      <div
        className="faq_drawer_content px-[16px] py-[16px] font-bold text-text-color1 text-[16px] flex justify-between"
        style={{ borderBottom: "1px solid #EEEEEE" }}
      >
        <div>相似问</div>
        <CloseOutlined onClick={cancleEditQa} />
      </div>
      <div className="faq_drawer_content px-[16px] py-[16px] flex-1 h-full">
        <div className="flex items-center">
          <Button
            icon={<PlusCircleOutlined />}
            type="primary"
            className="border-none"
            style={{
              background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
              color: "#fff",
              marginRight: "16px"
            }}
            onClick={addNewSimilar}
            disabled={getBtnDisabled(FILE_BTN.ADD, curItem.permission)}
          >
            新建
          </Button>
          <Select
            allowClear
            placeholder="更多操作"
            style={{
              width: "120px",
              borderRadius: "10px",
              color: "#055aff"
            }}
            value={batchValue}
            onSelect={handleBatchMenu}
          >
            {faqSimilarOptions.map((i: any) => {
              return (
                <Select.Option
                  key={i.value}
                  value={i.value}
                  disabled={
                    i.disabled ||
                    selectedRowKeys.length === 0 ||
                    (i.value === faqBatchType.DELETE &&
                      getBtnDisabled(FILE_BTN.DELETE, curItem.permission))
                  }
                >
                  <div className="more-action-row">{i.label}</div>
                </Select.Option>
              );
            })}
          </Select>
        </div>
        <div className="mt-[16px] h-[calc(100%-150px)] overflow-y-auto">
          <EditSimilarTable
            data={data}
            setData={setData}
            similarLoading={similarLoading}
            submitAddSimilar={submitAddSimilar}
            deleteSimilarConfirm={deleteSimilarConfirm}
            submitUpdateSimilar={submitUpdateSimilar}
            tableLoading={tableLoading}
            selectedRowKeys={selectedRowKeys}
            setSelectedRowKeys={setSelectedRowKeys}
            kbInfo={kbInfo}
          />
        </div>
      </div>
    </div>
  );
};

export const FaqDrawerContent = ({
  submitQa,
  onCancel,
  type,
  editQuestion,
  editAnswer,
  editAnswerOnChange,
  editQuestionOnChange,
  confirmLoading,
  polishLoading,
  curPolishContent,
  polishContentList,
  polishContentPage,
  handlerPolish,
  knowledgeBaseId,
  openDrawer,
  setFolder
}: any) => {
  const isDisabled = useMemo(() => {
    return !(editQuestion && editAnswer);
  }, [editQuestion, editAnswer]);

  return (
    <div className="flex flex-col justify-between h-full">
      <div
        className="faq_drawer_content px-[20px] py-[16px] font-bold text-text-color1 text-[16px] flex justify-between"
        style={{ borderBottom: "1px solid #EEEEEE" }}
      >
        <div>{type === "add" ? "新建问答" : "编辑问答"}</div>
        <CloseOutlined onClick={onCancel} />
      </div>
      <div className="faq_drawer_content px-[20px] py-[16px] flex-1 overflow-y-auto">
        <div className="question-cell">
          {openDrawer && type === "add" && (
            <>
              <div className={` question-title mb-[8px] flex items-center`}>
                <div className="text-red-700 mr-[5px]">*</div>
                <div>文件夹</div>
              </div>
              <FolderSelect kbId={knowledgeBaseId} setValue={setFolder} />
            </>
          )}
          <div className={`editLine question-title mb-[8px]`}>Q问题</div>
          <div className="question-ipt">
            <TextArea
              style={{
                height: 80,
                resize: "none",
                lineHeight: "30px"
              }}
              value={editQuestion}
              onChange={editQuestionOnChange}
              placeholder="请输入问题"
            />
          </div>
        </div>
        <div className="answer-row mt-[20px]">
          <div className="flex justify-between items-center">
            <div className={`editLine answer-title mb-[8px]`}>A答案</div>
            <Button
              type="link"
              icon={
                <img
                  src={
                    type === "add" || polishLoading || polishContentList.length
                      ? PolishDisabled
                      : Polish
                  }
                />
              }
              size="small"
              className="px-0 gap-[4px]"
              onClick={() => handlerPolish("getPolish")}
              loading={!polishContentList.length && polishLoading}
              disabled={
                type === "add" || polishLoading || polishContentList.length
              }
            >
              润色
            </Button>
          </div>
          <div className="answer-ipt">
            <TextArea
              style={{
                height: 100,
                lineHeight: "30px"
              }}
              value={editAnswer}
              placeholder="请输入答案"
              onChange={editAnswerOnChange}
            />
          </div>
        </div>
        {polishLoading || polishContentList.length ? (
          <div
            className="mt-[8px] rounded-[4px]"
            style={{
              borderRadius: "4px",
              border: "2px solid #055AFF"
            }}
          >
            {!!curPolishContent && (
              <div className="px-[16px] py-[12px] max-h-[352px] overflow-y-auto">
                {curPolishContent}
              </div>
            )}
            {polishLoading ? (
              <div className="h-[46px] rounded-[4px] px-[16px] py-[12px] flex items-center justify-between">
                <div className="flex items-center">
                  <img
                    src={Genera}
                    width={16}
                    height={16}
                    className="mr-[8px]"
                  />
                  <div className="text-[#0C5FFF] ">生成中…</div>
                </div>
                <div
                  className="text-[#888888] cursor-pointer"
                  onClick={() => handlerPolish("stop")}
                >
                  停止生成
                </div>
              </div>
            ) : (
              <div className="flex justify-between items-center px-[16px] py-[12px]">
                <div>
                  <Pagination
                    size="small"
                    simple={{ readOnly: true }}
                    defaultCurrent={1}
                    total={polishContentList.length}
                    pageSize={1}
                    current={polishContentPage.pageNo}
                    disabled={polishLoading}
                    onChange={(pageNo, pageSize) =>
                      handlerPolish("polishPageChange", { pageNo, pageSize })
                    }
                  />
                </div>
                <div>
                  <Button
                    style={{
                      border: "1px solid #ebebeb",
                      color: "#555",
                      marginRight: "8px"
                    }}
                    onClick={() => handlerPolish("remove")}
                    disabled={polishLoading}
                  >
                    放弃
                  </Button>
                  <Button
                    style={{
                      border: "1px solid #ebebeb",
                      color: "#555",
                      marginRight: "8px"
                    }}
                    loading={polishLoading}
                    onClick={() => handlerPolish("reGenerate")}
                  >
                    再次生成
                  </Button>
                  <Button
                    style={{
                      background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                      color: isDisabled ? "#ddd" : "#fff",
                      border: "none"
                    }}
                    disabled={polishLoading}
                    onClick={() => handlerPolish("replace")}
                  >
                    替换
                  </Button>
                  {/* <Button
                    type="primary"
                    style={{
                      background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                      color: isDisabled ? "#ddd" : "#fff",
                      border: "none",
                    }}
                    loading={confirmLoading}
                    onClick={() => handlerPolish("insert")}
                    disabled={polishLoading}
                  >
                    插入下方
                  </Button> */}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
      <div
        className="faq_drawer_footer px-[20px] py-[16px] flex justify-end"
        style={{ borderTop: "1px solid #EEEEEE" }}
      >
        <Button
          style={{
            border: "1px solid #ebebeb",
            color: "#555",
            marginRight: "16px"
          }}
          onClick={onCancel}
        >
          取消
        </Button>
        <Button
          type="primary"
          style={{
            background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
            color: isDisabled ? "#ddd" : "#fff",
            border: "none"
          }}
          loading={confirmLoading}
          onClick={submitQa}
          disabled={isDisabled}
        >
          确定
        </Button>
      </div>
    </div>
  );
};
