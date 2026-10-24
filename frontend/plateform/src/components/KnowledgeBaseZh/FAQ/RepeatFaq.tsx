import {
  Modal,
  Input,
  Button,
  Spin,
  Popconfirm,
  Switch,
  message,
  ConfigProvider
} from "antd";
import { useParams } from "react-router-dom";
import { useEffect, useState, useMemo } from "react";
import "@/assets/styles/faq.less";
import {
  repeatCheck,
  deleteFaq,
  updateFaq,
  changeStatus
} from "../common/faqService";
import BgNoData from "@/assets/knowledgebase/bg-no-repeat-faq.svg";
import {
  DeleteOutlined,
  EditOutlined,
  CaretDownOutlined,
  CaretRightOutlined
} from "@ant-design/icons";
import FileViewCom from "../components/FileViewCom";
import {
  downloadByStream,
  fileViewTypes,
  getFileName,
  getFileType
} from "@root/src/core/helps";
import { set } from "lodash";
const { TextArea } = Input;
interface IRepeatFaq {
  isShow: boolean;
  repeatList: Array<any>;
  isBatchEnable: boolean;
  closeModal: (sta?: boolean) => void;
  [key: string]: any;
  fileId: string;
  knowledgeBaseId: string;
}

const RepeatFaq = (props: IRepeatFaq) => {
  const {
    isShow,
    repeatList,
    isBatchEnable,
    closeModal,
    fileId,
    knowledgeBaseId,
    faqData
  } = props;
  const [repeatFaqs, setRepeatFaqs] = useState<Array<any>>([]);
  const [expadnList, setExpandList] = useState<Array<boolean>>([]);
  const [statusObj, setStatusObj] = useState<any>({});
  const [editQuestion, setEditQuestion] = useState("");
  const [editAnswer, setEditAnswer] = useState("");
  const [curFileInfo, setCurFileInfo] = useState<any>({});
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [isDelete, setIsDelete] = useState(false);

  const isFaqManage = useMemo(() => {
    return fileId === "all";
  }, [fileId]);

  const isChanged = useMemo(() => {
    return (
      isDelete ||
      Object.keys(statusObj).some(
        (key) =>
          statusObj[key] &&
          statusObj[key]["origin"] !== statusObj[key]["change"]
      )
    );
  }, [statusObj, isDelete]);

  const close = () => {
    closeModal(isChanged);
    setTimeout(() => {
      resetData();
    }, 1000);
  };

  const resetData = () => {
    repeatFaqs.length && setRepeatFaqs([]);
    expadnList.length && setExpandList([]);
    editQuestion && setEditQuestion("");
    editAnswer && setEditAnswer("");
    !loading && setLoading(true);
  };

  const editQuestionOnChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setEditQuestion(e.target.value.trim());
  };

  const editAnswerOnChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setEditAnswer(e.target.value.trim());
  };

  const editRow = (groupIdx: number, itemIdx: number) => {
    const _repeatFaqs = editStaChange(repeatFaqs, groupIdx, itemIdx);
    setRepeatFaqs([..._repeatFaqs]);
  };

  const editStaChange = (
    list: Array<Array<any>>,
    groupIdx?: number,
    itemIdx?: number
  ) => {
    return list.map((g: any, gIdx: number) =>
      g.map((i: any, iIdx: number) => {
        if (gIdx === groupIdx && iIdx === itemIdx) {
          setEditQuestion(i.question);
          setEditAnswer(i.answer);
        }
        return Object.assign({}, i, {
          isEdit: gIdx === groupIdx && iIdx === itemIdx ? true : false
        });
      })
    );
  };

  const deleteQA = (
    relatedPks: Array<number>,
    groupIdx: number,
    itemIdx: number
  ) => {
    try {
      setConfirmLoading(true);
      deleteFaq({
        relatedPks,
        kbId: knowledgeBaseId
      }).then((res: any) => {
        if (res) {
          message.success("删除成功!");
          afterDelQA(groupIdx, itemIdx);
          !isDelete && setIsDelete(true);
        } else {
          message.error("删除失败!");
        }
        setConfirmLoading(false);
      });
    } catch (error) {
      setConfirmLoading(false);
      message.error("删除失败!");
    }
  };

  const afterDelQA = (groupIdx: number, itemIdx: number) => {
    const _repeatFaqs = [...repeatFaqs];
    const _group = [..._repeatFaqs[groupIdx]];
    _group.splice(itemIdx, 1);
    if (_group.length === 0) {
      _repeatFaqs.splice(groupIdx, 1);
    } else {
      _repeatFaqs[groupIdx] = _group;
    }
    _repeatFaqs[groupIdx] = _group;
    setRepeatFaqs([..._repeatFaqs]);
    if (_repeatFaqs.length === 0) {
      closeModal(true);
      message.info("重复问题已处理！");
    }
  };

  const initStatusObj = (list: Array<Array<any>>) => {
    const _list = list.flat(Infinity);
    const _obj = {} as any;
    _list.forEach((i: any) => {
      const { pk, relatedPk, status } = i;
      // 20241105状态接口改为接收relatedPk的数组
      _obj[String(relatedPk)] = {
        origin: status,
        change: status,
        ...i
      };
    });

    setStatusObj({ ..._obj });
  };

  const statusOnChange = (checked: boolean, pk: any, groupIdx: number) => {
    const _group = [...repeatFaqs[groupIdx]];
    const _obj = {
      [pk]: {
        ...statusObj[pk],
        change: checked === true ? 1 : 0
      }
    } as any;

    _group.forEach((i: any) => {
      // 20241105接口改为接收relatedPk的数组
      const _pk = i.relatedPk;
      if (_pk !== pk && checked === true) {
        _obj[_pk] = {
          ...statusObj[_pk],
          change: 0
        };
      }
    });

    setStatusObj({
      ...statusObj,
      ..._obj
    });
  };

  const editQA = (row: any, groupIdx: number, itemIdx: number) => {
    const { pk, relatedPk } = row;
    try {
      setConfirmLoading(true);
      updateFaq({
        fileId: isFaqManage ? undefined : fileId,
        kbId: knowledgeBaseId,
        faqs: [{ question: editQuestion, answer: editAnswer, pk, relatedPk }]
      }).then((res: any) => {
        if (res) {
          faqUpdateOnChange(
            groupIdx,
            itemIdx,
            {
              isEdit: false,
              question: editQuestion,
              answer: editAnswer
            },
            true
          );
          message.success("编辑问答对成功！");
        } else {
          message.error("编辑问答对失败！");
        }
        setConfirmLoading(false);
      });
    } catch (error) {
      setConfirmLoading(false);
      message.error("编辑问答对失败！");
    }
  };

  const faqUpdateOnChange = (
    groupIdx: number,
    itemIdx: number,
    newData: { [key: string]: any },
    judgeChange: boolean
  ) => {
    const _repeatFaqs = [...repeatFaqs];
    const _group = [..._repeatFaqs[groupIdx]];
    if (judgeChange && _group[itemIdx].question !== editQuestion) {
      setTimeout(() => {
        repeatList.length === 0 && fetchRepeatList();
      }, 1000);
    }
    const _item = Object.assign({}, _group[itemIdx], { ...newData });
    _group[itemIdx] = { ..._item };
    _repeatFaqs[groupIdx] = _group;

    setRepeatFaqs([..._repeatFaqs]);
  };

  const controllRepeatList = (res: any) => {
    initStatusObj(res);
    setRepeatFaqs([...editStaChange(res)]);
    const _expandList = [...new Array(res.length).fill(false)];
    _expandList[0] = true;
    setExpandList([..._expandList]);
  };

  const fetchRepeatList = () => {
    repeatCheck(knowledgeBaseId)
      .then((res) => {
        if (res) {
          controllRepeatList(res);
        }
      })
      .finally(() => {
        setTimeout(() => {
          setLoading(false);
        }, 1000);
      });
  };

  const expandRows = (gIdx: number, isExpand: boolean) => {
    const _expandList = [...expadnList];
    _expandList[gIdx] = isExpand;
    setExpandList([..._expandList]);
  };

  const getTIds = (checkedData: any[], type?: number) => {
    const fileIds = checkedData
      .filter((item: any) => {
        return item.dataType === 2;
      })
      .map((item: any) => item.fileId);
    const folderIds = checkedData
      .filter((item: any) => {
        return item.dataType === 1;
      })
      .map((item: any) => item.folderId);
    const relatedPks = checkedData
      .filter((item: any) => {
        return item.dataType === 3;
      })
      .map((item: any) => item.relatedPk);
    if (type === 1) {
      const enablePks = checkedData
        .filter((item: any) => {
          return item.dataType === 3;
        })
        .filter((i: any) => i.status === 1)
        .map((item: any) => item.relatedPk);
      const disablePks = checkedData
        .filter((item: any) => {
          return item.dataType === 3;
        })
        .filter((i: any) => i.status === 0)
        .map((item: any) => item.relatedPk);
      return { fileIds, folderIds, enablePks, disablePks, relatedPks };
    }
    return { fileIds, folderIds, relatedPks };
  };

  const confirmStatusChange = () => {
    const changeStaList = Object.keys(statusObj).map((key: string) => ({
      ...statusObj[key],
      pk: key,
      status: statusObj[key].change
    }));

    const status = 1;

    const { fileIds, folderIds, enablePks, disablePks }: any = getTIds(
      changeStaList,
      1
    );

    const allPks = [...enablePks, ...disablePks];
    const others = isBatchEnable
      ? []
      : (faqData || []).filter((item: any) => {
          return !allPks.includes(item.relatedPk) || !item.relatedPk;
        });
    const {
      fileIds: fileIds1,
      folderIds: folderIds1,
      relatedPks
    }: any = getTIds(others);
    // 20241106 全部启用与部分启用检测到的重复数据，调用不同的接口，使用不同的参数修改状态
    const params: any = isBatchEnable
      ? {
          kbId: knowledgeBaseId,
          disabledRelatedpks: disablePks,
          status
        }
      : {
          kbId: knowledgeBaseId,
          relatedpks: [...enablePks, ...relatedPks],
          disabledRelatedpks: disablePks,
          status
        };
    if (fileIds.length || fileIds1.length) {
      params.fileIds = [...fileIds, ...fileIds1];
    }
    if (folderIds.length || folderIds1.length) {
      params.folderIds = [...folderIds, ...folderIds1];
    }

    changeStatusList(params);
  };

  const changeStatusList = (params: any, cb?: any) => {
    changeStatus(params)
      .then((res: any) => {
        const { data, success } = res;
        if (success) {
          if (data && data.length) {
            message.error(`修改状态失败，有重复问题存在！`);
          } else {
            if (cb) {
              cb();
            } else {
              message.success(`修改状态成功！`);
              closeModal(true);
              setConfirmLoading(false);
            }
          }
        } else {
          message.error(`修改状态失败！`);
          setConfirmLoading(false);
        }
      })
      .catch((e) => {
        console.log(e);
        setConfirmLoading(false);
      });
  };

  useEffect(() => {
    if (isShow && knowledgeBaseId) {
      if (repeatList && repeatList.length) {
        controllRepeatList([...repeatList]);
        setLoading(false);
      } else {
        console.log("open");
        fetchRepeatList();
      }
    }
  }, [isShow, knowledgeBaseId, repeatList]);

  return (
    <Modal
      title={
        <span className="repeat-modal-title">
          {repeatList.length ? "重复问题处理" : "重复问题检测"}
        </span>
      }
      open={isShow}
      width={repeatFaqs.length ? 1100 : 480}
      footer={false}
      onCancel={close}
    >
      <div
        className="repeat-bottom-line"
        style={{ width: repeatFaqs.length ? "1100px" : "480px" }}
      ></div>
      {/* {JSON.stringify(isBatchEnable)} */}
      {repeatFaqs.length === 0 && !loading ? (
        <div className="no-repeat-list">
          <img src={BgNoData} width="120" height="88" />
          <div className="info-txt">未识别到完全重复的问题</div>
        </div>
      ) : (
        <Spin spinning={loading}>
          <div className="repeat-info">
            <span>
              以下<b>{repeatFaqs.length}</b>
              组问答的问题一样，每组只能选择一个启动使用。
            </span>
          </div>
          <div className="repeat-wrap">
            <div className="repeat-list-container">
              {repeatFaqs.map((row: any, groupIdx: number) => {
                return (
                  <div
                    className="repeat-row"
                    key={`repeat_group_${groupIdx}_${row.length}`}
                  >
                    <div
                      className={`${expadnList[groupIdx] ? "expand-row " : ""}group-title`}
                    >
                      <span>
                        {expadnList[groupIdx] ? (
                          <CaretDownOutlined
                            title="关闭"
                            onClick={() => {
                              expandRows(groupIdx, false);
                            }}
                          />
                        ) : (
                          <CaretRightOutlined
                            title="展开"
                            onClick={() => {
                              expandRows(groupIdx, true);
                            }}
                          />
                        )}
                      </span>
                      <b>第{groupIdx + 1}组</b>
                    </div>
                    {(row || []).map((item: any, itemIdx: number) => {
                      return (
                        <div
                          className={`${expadnList[groupIdx] ? "" : "hidden "}item-row`}
                          key={`repeat_group_item_${groupIdx}_${item.pk}`}
                        >
                          <div className="question-row">
                            <div className="question-wrap">
                              <div className="question-cell">
                                <div
                                  className={`${item.isEdit ? "editLine " : ""}question-title`}
                                >
                                  Q:
                                </div>
                                {item.isEdit ? (
                                  <div className="question-ipt">
                                    <TextArea
                                      value={editQuestion}
                                      style={{
                                        height: 42,
                                        resize: "none",
                                        lineHeight: "30px"
                                      }}
                                      onChange={editQuestionOnChange}
                                    />
                                  </div>
                                ) : (
                                  <div className="question-info">
                                    {item.question}
                                  </div>
                                )}
                              </div>
                            </div>
                            <div
                              className={`${item.isEdit ? "hidden " : ""}btn-group-cell`}
                            >
                              <Button
                                type="link"
                                icon={<EditOutlined />}
                                title="编辑"
                                disabled={confirmLoading}
                                className=" text-[#333333]"
                                onClick={() => editRow(groupIdx, itemIdx)}
                              />
                              <Popconfirm
                                title="删除问答对"
                                disabled={confirmLoading}
                                description="确认删除问答对吗？"
                                okText="确认"
                                cancelText="取消"
                                onConfirm={() =>
                                  deleteQA([item.relatedPk], groupIdx, itemIdx)
                                }
                              >
                                <Button
                                  type="link"
                                  disabled={confirmLoading}
                                  title="删除"
                                  icon={<DeleteOutlined />}
                                  className=" text-[#333333]"
                                />
                              </Popconfirm>
                              <Switch
                                disabled={confirmLoading}
                                checkedChildren="启用"
                                unCheckedChildren="禁用"
                                title={
                                  statusObj[item.relatedPk] &&
                                  statusObj[item.relatedPk].change === 1
                                    ? "禁用"
                                    : "启用"
                                }
                                onChange={(checked: boolean) => {
                                  statusOnChange(
                                    checked,
                                    item.relatedPk,
                                    groupIdx
                                  );
                                }}
                                value={
                                  statusObj[item.relatedPk] &&
                                  statusObj[item.relatedPk].change === 1
                                }
                              />
                            </div>
                          </div>
                          <div className="answer-row">
                            <div
                              className={`${item.isEdit ? "editLine " : ""}answer-title`}
                            >
                              A:
                            </div>
                            {item.isEdit ? (
                              <div className="answer-ipt">
                                <TextArea
                                  value={editAnswer}
                                  style={{
                                    height: 42,
                                    resize: "none",
                                    lineHeight: "30px"
                                  }}
                                  onChange={editAnswerOnChange}
                                />
                              </div>
                            ) : (
                              <div className="answer-info">{item.answer}</div>
                            )}
                          </div>
                          {item.isEdit ? (
                            <div className="add-edit-btn-group">
                              <Button
                                className="cancle-btn"
                                disabled={confirmLoading}
                                onClick={() => {
                                  faqUpdateOnChange(
                                    groupIdx,
                                    itemIdx,
                                    {
                                      isEdit: false
                                    },
                                    false
                                  );
                                }}
                              >
                                取消
                              </Button>
                              <Button
                                className="save-btn"
                                loading={confirmLoading}
                                disabled={!editAnswer || !editQuestion}
                                onClick={() => editQA(item, groupIdx, itemIdx)}
                              >
                                确认
                              </Button>
                            </div>
                          ) : null}
                          <div className="source-file-wrap">
                            <div className="source-url">
                              <span>来源文件：</span>
                              {item.sourceFile ? (
                                <Button
                                  type="link"
                                  disabled={!item.sourceFile}
                                  style={{ fontSize: "12px" }}
                                  onClick={() => {
                                    const fileType = getFileType(
                                      { metadata: { source: item.sourceFile } },
                                      item.sourceFile
                                    );
                                    if (fileViewTypes.includes(fileType)) {
                                      setCurFileInfo({
                                        url: item.sourceFile,
                                        filePath: item.sourceFile,
                                        pdfPages: item.pdfPages || 0
                                      });
                                      setShowPreviewModal(true);
                                    } else {
                                      downloadByStream({
                                        filePath: item.sourceFile,
                                        fileName: getFileName({
                                          metadata: { source: item.sourceFile }
                                        })
                                      });
                                    }
                                  }}
                                >
                                  {getFileName({
                                    metadata: { source: item.sourceFile }
                                  })}
                                </Button>
                              ) : (
                                <span className="no-file-path">
                                  {item.sourceFileName || "无"}
                                </span>
                              )}
                            </div>
                            <div className="modify-time">
                              修订时间：{item.reviseDate || "-"}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>
        </Spin>
      )}
      {repeatFaqs.length ? (
        <div className="repeat-btn-group">
          <Button
            className="cancle-btn"
            onClick={close}
            style={{
              borderColor: "#ebebeb"
            }}
          >
            取消
          </Button>
          <Button
            type="primary"
            loading={false}
            disabled={!isChanged}
            style={{
              color: "#fff",
              background:
                "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)",
              border: "none"
            }}
            onClick={confirmStatusChange}
          >
            确定
          </Button>
        </div>
      ) : (
        <div className="clost-btn-wrap">
          <Button
            style={{
              background:
                "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)",
              border: "none"
            }}
            onClick={close}
          >
            确认
          </Button>
        </div>
      )}
      <ConfigProvider
        modal={{
          styles: {
            header: {
              padding: "20px 24px",
              borderBottom: "1px solid #F0F0F0",
              margin: 0
            },
            body: { padding: 0 },
            mask: {},
            footer: { padding: 0, margin: 0 },
            content: { padding: 0 }
          }
        }}
      >
        <FileViewCom
          data={curFileInfo}
          showPreviewModal={showPreviewModal}
          setShowPreviewModal={setShowPreviewModal}
        />
      </ConfigProvider>
    </Modal>
  );
};

export default RepeatFaq;
