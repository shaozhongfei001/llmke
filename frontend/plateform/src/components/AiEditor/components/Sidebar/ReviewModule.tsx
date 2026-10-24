import { useEffect, useState, useMemo, useCallback } from "react";
import { UnorderedListOutlined } from "@ant-design/icons";
import { Button, Flex, message, Tabs, Tag, Tooltip } from "antd";
import loadingGif from "@/components/AiEditor/assets/img/loading.gif";
import init_bg from "@/components/AiEditor/assets/icon/review_init_bg.svg";
import useAiEditorOperators from "../../core/operators/useAiEditorOperators";
import { EditorStatus, ModueEnum } from "../../@types/sys";
import arrowhead from "@/components/AiEditor/assets/img/arrowhead.png";
import Confirm from "@/components/AiEditor/assets/icon/confirm.svg";
import Neglect from "@/components/AiEditor/assets/icon/neglect.svg";
import { useStateStore } from "../../core/states/useStateStore";
import { Editor, Node, Text } from "slate";
import { MARK_SELECTION_UNDERLINE } from "../editor/plugins/customPlugin/selectionUnderLinePlugin";
import { MARK_REPLACE_PARAGRAPH } from "../editor/plugins/customPlugin/replaceParagraph";
import { MARK_SELECTION_DELETE } from "../editor/plugins/customPlugin/selectonDeletePligin";
import {
  api_markSensitiveWord,
  api_doReviewing,
  api_articleFeedback
} from "../../core/services/servers";
import ReviewFeedback from "../ReviewFeedback";
import { useMouduleOperators } from "../../core/operators/useMouduleOperators";
import StyledTitle from "../common/StyledTitle";
import { EDITOR_EVENT_NAME, editorEventBus } from "../../editorEventBus";

/**
 * 去除字符串中的所有换行符 \n
 */
export const removeNewLines = (str: string): string => str.replace(/\n/g, "");

interface ReviewItem {
  id: string | number;
  targetContent: string;
  errorContent: string;
  errorContext: {
    errorContent: string;
    targetContent: string;
  };
  displayTargetContent: string;
  displayErrorContent: string;
  tips?: string;
  errorType: number;
}
interface ApproveParams {
  type: "all" | "item";
  item?: ReviewItem;
  allData?: ReviewItem[];
  reviewType?: ReviewType;
}

interface ReviewMode {
  "1": "result" | "review" | "loading";
  "2": "result" | "review" | "loading";
}

enum ReviewType {
  Corrigendum = "1",
  SensitiveWords = "2"
}

const errorTypeObj: any = {
  1: "错别字",
  2: "文法错误",
  3: "标点不当",
  4: "字词冗余",
  5: "缺字",
  6: "序号错误",
  7: "段落重复",
  8: "口语化表达",
  0: "其他"
};

const removeMarksFromEditor = (editor, markType) => {
  Editor.withoutNormalizing(editor, () => {
    // 获取所有包含mark的文本节点
    const nodes = Array.from(
      Editor.nodes(editor, {
        at: [],
        match: (n) => Text.isText(n) && n[markType]
      })
    );

    // 从后向前遍历节点，避免路径变化导致的跳过问题
    for (let i = nodes.length - 1; i >= 0; i--) {
      const [_, path] = nodes[i];
      editor.select(path);
      editor.delete();
    }

    editor.select(editor.end([]));
  });
};

const ReviewModule = () => {
  const { clearAllMark, handleShowUnderLine, handleCensor } =
    useAiEditorOperators();
  const { closeFeedback, openFeedback } = useMouduleOperators();
  const {
    mainEditor,
    projectData,
    serverInfo,
    modules,
    setOpen,
    setProjectData,
    setEditorManager,
    baseInfo
  } = useStateStore();

  // 保存tab的状态
  const [reviewMode, setReviewMode] = useState<ReviewMode>({
    [ReviewType.Corrigendum]: "review",
    [ReviewType.SensitiveWords]: "review"
  });
  // 当前的tab
  const [activeKey, setActiveKey] = useState(ReviewType.Corrigendum);
  // 保存审核的结果
  const [resultData, setResultData] = useState({
    [ReviewType.Corrigendum]: [],
    [ReviewType.SensitiveWords]: []
  });

  // 保存文章
  const { saveBeforeReview } = useAiEditorOperators();

  // 反馈相关
  const feedback = useMemo(() => {
    return modules.find((i) => i.value === ModueEnum.Review)?.feedback;
  }, [modules]);

  // 反馈
  const handFeedback = async (data) => {
    if (!projectData.id) {
      message.warning("请先保存文章");
      return;
    }
    const { originData, formData } = data;
    console.log(originData, formData, "这是我需要的数据");
    const res = await api_articleFeedback({
      config: serverInfo,
      data: {
        articleId: projectData.id,
        errorType: Number(formData.errorType || originData.errorType),
        feedbackType: 0,
        userComment: formData.suggestion,
        targetContent: originData.source,
        scene: originData.scene
      }
    });
    if (res) {
      message.success("感谢您的反馈，我们会继续改进");
      closeFeedback();
    }
  };

  // 当前展示的状态
  const mode = useMemo(() => {
    return reviewMode[activeKey];
  }, [reviewMode, activeKey]);

  const handleSubTabChange = (val: string) => {
    setActiveKey(val as ReviewType);
  };

  // 离开审核时清空所有状态
  useEffect(() => {
    return () => {
      const editor: any = mainEditor.current;
      setResultData({
        [ReviewType.Corrigendum]: [],
        [ReviewType.SensitiveWords]: []
      });
      setReviewMode({
        [ReviewType.Corrigendum]: "review",
        [ReviewType.SensitiveWords]: "review"
      });
      clearAllMark(editor);
    };
  }, []);

  // 切换错误类型时清空所有状态
  useEffect(() => {
    const editor: any = mainEditor.current;
    clearAllMark(editor);
  }, [activeKey]);

  // 开始审核
  const startReview = async () => {
    setItemStatus({});
    setSensitiveWordsItemStatus({});
    setReviewMode((p) => {
      return { ...p, [activeKey]: "loading" };
    });
    setEditorManager((p) => ({
      ...p,
      status: EditorStatus.Reviewing
    }));
    const id = await saveBeforeReview();
    if (id) {
      // 字词审核与敏感词审核
      const hasSensitiveWords =
        projectData.sensitiveWords &&
        Object.keys(projectData.sensitiveWords).length > 0;
      const reqArr = hasSensitiveWords
        ? [
            api_doReviewing({
              config: serverInfo,
              data: {
                articleId: id
              }
            }),
            api_markSensitiveWord({
              config: serverInfo,
              data: {
                articleId: id
              }
            })
          ]
        : [
            api_doReviewing({
              config: serverInfo,
              data: {
                articleId: id
              }
            })
          ];
      setReviewMode((p) => {
        return {
          [ReviewType.Corrigendum]: "loading",
          [ReviewType.SensitiveWords]: "loading"
        };
      });
      Promise.all(reqArr)
        .then((res) => {
          const [corrigendumReviewData, sensitiveWordsReviewData] = res;
          setResultData((p) => ({
            // 所有返回内容，手动去掉 \n
            [ReviewType.SensitiveWords]: (sensitiveWordsReviewData || []).map(
              (i: any) => {
                return {
                  ...i,
                  context: removeNewLines(i?.context || ""),
                  word: removeNewLines(i?.word || "")
                };
              }
            ),
            [ReviewType.Corrigendum]: (corrigendumReviewData || []).map(
              (i: any) => {
                // 如果内容为空格取消或增加空格，使用display字段进行展示
                const isVoid = !i.errorContent.trim();
                const { errorContent, targetContent } = i.errorContext || {};
                // 用于列表展示的内容
                const displayObj = {
                  displayTargetContent: isVoid
                    ? (i?.errorContext || {})?.targetContent || ""
                    : i?.targetContent || "",
                  displayErrorContent: isVoid
                    ? (i?.errorContext || {})?.errorContent || ""
                    : i?.errorContent || ""
                };
                // 用于替换和高亮的内容
                const highlightObj = {
                  errorContent: removeNewLines(
                    isVoid ? errorContent || "" : i?.errorContent || ""
                  ),
                  targetContent: removeNewLines(
                    isVoid ? targetContent || "" : i?.targetContent || ""
                  )
                };

                return {
                  ...i,
                  ...highlightObj,
                  // 用于定位的内容
                  errorContext: {
                    errorContent: removeNewLines(
                      (i?.errorContext || {}).errorContent || ""
                    ),
                    targetContent: removeNewLines(
                      (i?.errorContext || {}).targetContent || ""
                    )
                  },
                  ...displayObj
                };
              }
            )
          }));
          setReviewMode((p) => {
            return {
              [ReviewType.Corrigendum]: "result",
              [ReviewType.SensitiveWords]: "result"
            };
          });
          setEditorManager((p) => ({
            ...p,
            status: EditorStatus.ReviewingSuccess
          }));
        })
        .catch((e) => {
          setReviewMode((p) => {
            return {
              [ReviewType.Corrigendum]: "result",
              [ReviewType.SensitiveWords]: "result"
            };
          });
          setEditorManager((p) => ({
            ...p,
            status: EditorStatus.ReviewingSuccess
          }));
        });
    }
  };

  // 监听审核事件
  useEffect(() => {
    const handleReview = () => {
      startReview();
    };
    editorEventBus.on(EDITOR_EVENT_NAME.START_REVIEW, handleReview);
    return () => {
      editorEventBus.off(EDITOR_EVENT_NAME.START_REVIEW, handleReview);
    };
  }, [
    serverInfo,
    projectData.id,
    projectData.extraParams,
    baseInfo,
    projectData.sensitiveWords
  ]);

  // 根据错误类型为当前文章打上标记
  useEffect(() => {
    try {
      if (
        mode === "result" &&
        resultData[ReviewType.Corrigendum].length &&
        activeKey === ReviewType.Corrigendum
      ) {
        const corrigendumData = resultData[ReviewType.Corrigendum];
        handleShowUnderLine(corrigendumData);
      } else if (
        mode === "result" &&
        resultData[ReviewType.SensitiveWords].length &&
        activeKey === ReviewType.SensitiveWords
      ) {
        handleCensor(resultData[ReviewType.SensitiveWords]);
      }
    } catch (e) {
      console.log(e, "我是错误");
    }
  }, [resultData, mode, activeKey]);

  // 字词审核的tag分类
  const classifyData = useMemo(() => {
    const errorType: any = {};
    (resultData[ReviewType.Corrigendum] || []).forEach((item: any) => {
      errorType[item.errorType] = errorType[item.errorType]
        ? [...errorType[item.errorType], item]
        : [item];
    });
    return errorType;
  }, [resultData[ReviewType.Corrigendum]]);

  // 当前点击的Tag
  const [curClickTag, setCurClickTag] = useState("");

  // 不同操作按钮的分组
  const [itemStatus, setItemStatus] = useState<any>({});
  // 采纳
  const accept = (params: ApproveParams) => {
    const editor: any = mainEditor.current;
    const { type, allData, item, reviewType } = params;
    // 采纳一个的情况
    if (type === "item" && item) {
      for (const [node, path] of Node.descendants(editor)) {
        if (
          node[MARK_SELECTION_UNDERLINE] === item.id ||
          node[MARK_SELECTION_DELETE] === item.id
        ) {
          editor.select(path);
          editor.delete();
          if (item?.targetContent) {
            editor.addMark(MARK_REPLACE_PARAGRAPH, item.id);
            editor.insertText(item.targetContent);
          }
        }
      }
      // 全部替换的情况
    } else if (type === "all" && allData) {
      // 内容勘误的全部接受

      if (!reviewType || reviewType === ReviewType.Corrigendum) {
        for (const [node, path] of Node.descendants(editor)) {
          const curItem = allData.filter((i) => {
            return (
              (i.id === node[MARK_SELECTION_UNDERLINE] ||
                i.id === node[MARK_SELECTION_DELETE]) &&
              //蜜度需求： 全部采纳时跳过 i.errorContent === i.targetContent这种情况
              i.errorContent !== i.targetContent
            );
          })[0];
          if (curItem) {
            editor.select(path);
            editor.delete();
            if (curItem && curItem.targetContent) {
              editor.addMark(MARK_REPLACE_PARAGRAPH, curItem.id);
              editor.insertText(curItem.targetContent);
            }
          }
        }
      } else if (reviewType === ReviewType.SensitiveWords) {
        removeMarksFromEditor(editor, MARK_SELECTION_UNDERLINE);
        removeMarksFromEditor(editor, MARK_SELECTION_DELETE);
      }
    }
    editor.select(editor.end([]));
  };

  // 忽略
  const ignore = (item) => {
    const editor: any = mainEditor.current;
    for (const [node, path] of Node.descendants(editor)) {
      if (
        node[MARK_SELECTION_UNDERLINE] === item.id ||
        node[MARK_SELECTION_DELETE] === item.id
      ) {
        editor.select(path);
        editor.removeMark(MARK_SELECTION_UNDERLINE);
        editor.removeMark(MARK_SELECTION_DELETE);
        editor.removeMark(MARK_REPLACE_PARAGRAPH);
      }
    }
    editor.select(editor.end([]));
  };

  const [isHoveredId, setIsHoveredId] = useState("");
  const renderReviewItem = (item: ReviewItem) => {
    const handleMouseEnter = (id) => {
      setIsHoveredId(id);
    };

    const handleMouseLeave = () => {
      setIsHoveredId("");
    };
    return (
      <div
        key={item.id}
        className="review-item cursor-pointer"
        onMouseEnter={() => handleMouseEnter(item.id)}
        onMouseLeave={handleMouseLeave}
      >
        <Flex
          style={{
            border: "1px solid #EBEBEB",
            // height: '50px',
            boxSizing: "border-box",
            width: "100%",
            padding: "12px",
            borderRadius: "4px"
          }}
          vertical
        >
          <Flex justify="space-between">
            {/* 蜜度需求 item?.targetContent === item.errorContent 时展示tips,同时不展示采纳和忽略 */}
            {item.displayTargetContent === item.displayErrorContent ? (
              <Flex gap={3} align="center" flex={1}>
                <span
                  style={{
                    borderBottom: "2px solid red"
                  }}
                >
                  {item.displayErrorContent}
                </span>
                {item?.displayTargetContent && (
                  <img src={arrowhead} alt="" width={16} height={16} />
                )}
                <span>{item.tips}</span>
              </Flex>
            ) : (
              <Flex gap={3} align="center" flex={1}>
                <span
                  style={{
                    borderBottom: "2px solid red"
                  }}
                >
                  {item?.displayTargetContent ? (
                    item.displayErrorContent
                  ) : (
                    <del
                      style={{
                        textDecorationColor: "red",
                        textDecorationThickness: "1px"
                      }}
                    >
                      {item.displayErrorContent}
                    </del>
                  )}
                </span>
                {item?.displayTargetContent && (
                  <img src={arrowhead} alt="" width={16} height={16} />
                )}
                {item?.displayTargetContent && (
                  <span>{item?.displayTargetContent}</span>
                )}
              </Flex>
            )}
            {item?.targetContent === item.errorContent ? null : (
              <>
                {!itemStatus[item.id] && (
                  <Flex gap={12} className="ml-[12px]">
                    <Tooltip title="采纳">
                      <img
                        src={Confirm}
                        width={16}
                        className="cursor-pointer"
                        onClick={() => {
                          accept({ type: "item", item });
                          setItemStatus((p) => ({
                            ...p,
                            [item.id]: "accept"
                          }));
                        }}
                      />
                    </Tooltip>
                    <Tooltip title="忽略">
                      <img
                        src={Neglect}
                        width={16}
                        className="cursor-pointer"
                        onClick={() => {
                          ignore(item);
                          setItemStatus((p) => ({
                            ...p,
                            [item.id]: "ignore"
                          }));
                        }}
                      />
                    </Tooltip>
                  </Flex>
                )}
                {itemStatus[item.id] === "accept" && (
                  <Flex className="text-[#15AD2C]">已采纳</Flex>
                )}
                {itemStatus[item.id] === "ignore" && (
                  <Flex
                    className="text-[#999] w-[120px]"
                    gap={12}
                    align="center"
                  >
                    <span>已忽略</span>
                    <Button
                      className="text-[#055AFF]"
                      size="small"
                      onClick={() => {
                        openFeedback({
                          id: item.id,
                          source: JSON.stringify(item),
                          errorType: item.errorType,
                          // 反馈场景:0-写作1润色 2-扩写3-缩写 4-字词审核 5-敏感词审核
                          scene: 4
                        });
                      }}
                    >
                      反馈
                    </Button>
                  </Flex>
                )}
              </>
            )}
          </Flex>
          {isHoveredId === item.id && (
            <Flex className="text-[#999] mt-[8px]">
              错误类型：{errorTypeObj[item.errorType]}
            </Flex>
          )}
        </Flex>
      </div>
    );
  };
  // 展开收起
  const [isUnfold, setIsUnfold] = useState(false);
  const handleClickTag = (key = "") => {
    setCurClickTag(key);
  };

  // 全部采纳
  const handleAccept = () => {
    if (activeKey === ReviewType.Corrigendum) {
      accept({
        allData: resultData[ReviewType.Corrigendum],
        type: "all"
      });
      setItemStatus((_) => {
        const _obj: any = {};
        resultData[ReviewType.Corrigendum].forEach((i: any) => {
          _obj[i.id] = "accept";
        });
        return _obj;
      });
    } else {
      accept({
        allData: resultData[ReviewType.SensitiveWords],
        type: "all",
        reviewType: ReviewType.SensitiveWords
      });
      setSensitiveWordsItemStatus((_) => {
        const _obj: any = {};
        resultData[ReviewType.SensitiveWords].forEach((i: any) => {
          _obj[i.id] = "accept";
        });
        return _obj;
      });
    }
  };
  // 全部忽略
  const handleIgnoreAll = (editor: any, curKey: ReviewType) => {
    editor && clearAllMark(editor);
    const handleFn =
      curKey === ReviewType.Corrigendum
        ? setItemStatus
        : setSensitiveWordsItemStatus;
    handleFn(() => {
      const _obj: any = {};
      resultData[activeKey].forEach((i: any) => {
        _obj[i.id] = "ignore";
      });
      return _obj;
    });
  };

  const operationButton = () => {
    return (
      <Flex justify="space-between" align="center">
        {activeKey === ReviewType.Corrigendum && (
          <span>
            共
            <span className="text-[#e6432e] font-bold mx-[5px]">
              {resultData[activeKey].length}
            </span>
            条建议
          </span>
        )}
        {activeKey === ReviewType.SensitiveWords && (
          <span>
            共发现
            <span className="text-[#FFA318] font-bold mx-[5px]">
              {resultData[activeKey].length}
            </span>
            处敏感词汇
          </span>
        )}

        <Flex gap={8}>
          <Button
            size="small"
            style={{
              color: "#305eba",
              border: "1px solid #eee",
              background: "white"
            }}
            onClick={handleAccept}
          >
            全部采纳
          </Button>
          <Button
            size="small"
            style={{
              color: "#305eba",
              border: "1px solid #eee",
              background: "white"
            }}
            onClick={() => handleIgnoreAll(mainEditor.current, activeKey)}
          >
            全部忽略
          </Button>
          <Button
            size="small"
            style={{
              color: "#305eba",
              border: "1px solid #eee",
              background: "white"
            }}
            onClick={startReview}
          >
            重新审核
          </Button>
        </Flex>
      </Flex>
    );
  };

  const renderCorrigendumEl = () => {
    return (
      <div className="h-[calc(100vh-240px)]">
        {resultData[ReviewType.Corrigendum].length > 0 && (
          <Flex vertical className="h-full" wrap key="1" gap={10}>
            {operationButton()}
            <Flex
              justify="space-between"
              className="w-[370px]"
              align="baseline"
            >
              <Flex
                wrap={isUnfold ? "wrap" : "nowrap"}
                flex={1}
                className="overflow-hidden w-[330px] gap-[8px] review-tag-box"
              >
                <Tag
                  key="all"
                  className={`cursor-pointer border-none  px-[12px] py-[5px] ${
                    !curClickTag
                      ? "bg-[#E2E9FF] text-[#055AFF]"
                      : "bg-[#F5F5F5] text-[#2A2A2A]"
                  }`}
                  // color={!curClickTag ? "#E2E9FF" : ""}
                  onClick={() => handleClickTag()}
                >
                  全部({resultData[ReviewType.Corrigendum].length})
                </Tag>
                {Object.keys(classifyData).map((key) => (
                  <Tag
                    className={`cursor-pointer border-none  px-[12px] py-[5px] ${
                      curClickTag === key
                        ? "bg-[#E2E9FF] text-[#055AFF]"
                        : "bg-[#F5F5F5] text-[#2A2A2A]"
                    }`}
                    key={errorTypeObj[key]}
                    onClick={() => handleClickTag(key)}
                  >
                    {errorTypeObj[key]}({classifyData[key].length})
                  </Tag>
                ))}
              </Flex>
              {Object.keys(classifyData).length > 3 && (
                <div
                  className="w-8 h-8 bg-[#f5f5f5] ml-2 flex align-middle justify-center cursor-pointer"
                  onClick={() => setIsUnfold(!isUnfold)}
                >
                  <UnorderedListOutlined
                    style={{
                      color: isUnfold ? "#055aff" : ""
                    }}
                  />
                </div>
              )}
            </Flex>
            <Flex
              vertical
              gap={12}
              flex={1}
              className="mt-[12px] overflow-y-auto"
            >
              {(curClickTag
                ? classifyData[curClickTag]
                : resultData[ReviewType.Corrigendum || []]
              ).map((item) => {
                return renderReviewItem(item);
              })}
            </Flex>
          </Flex>
        )}
        {!resultData[ReviewType.Corrigendum].length && (
          <Flex vertical gap={10} className="h-full box-border" key={"0"}>
            <Flex vertical flex={1} align="center" className="pt-[64px]">
              <img src={init_bg} width={160} height={120} alt="" className="" />
              <div className="text-[#333] text-[16px] mt-[16px]">
                您的文章非常完美
              </div>
              <div className="text-[#999] text-[14px] mt-2">没有任何问题</div>
            </Flex>
          </Flex>
        )}
      </div>
    );
  };

  const [sensitiveWordsItemStatus, setSensitiveWordsItemStatus] = useState<any>(
    {}
  );
  const renderSensitiveWordsItem = (item) => {
    return (
      <div key={item.id} className="review-item mt-2 cursor-pointer">
        <Flex
          style={{
            border: "1px solid #EBEBEB",
            height: "50px",
            boxSizing: "border-box",
            width: "100%",
            padding: "12px",
            borderRadius: "4px"
          }}
          justify="space-between"
        >
          <Flex gap={3} align="center">
            <span
              style={{
                borderBottom: "2px solid #FFA318"
              }}
            >
              {item.word}
            </span>
          </Flex>
          {!sensitiveWordsItemStatus[item.id] && (
            <Flex gap={12}>
              <Tooltip title="采纳">
                <img
                  src={Confirm}
                  width={16}
                  className="cursor-pointer"
                  onClick={() => {
                    accept({ type: "item", item });
                    setSensitiveWordsItemStatus((p) => ({
                      ...p,
                      [item.id]: "accept"
                    }));
                  }}
                />
              </Tooltip>
              <Tooltip title="忽略">
                <img
                  src={Neglect}
                  width={16}
                  className="cursor-pointer"
                  onClick={() => {
                    ignore(item);
                    setSensitiveWordsItemStatus((p) => ({
                      ...p,
                      [item.id]: "ignore"
                    }));
                  }}
                />
              </Tooltip>
            </Flex>
          )}
          {sensitiveWordsItemStatus[item.id] === "accept" && (
            <Flex className="text-[#15AD2C]">已采纳</Flex>
          )}
          {sensitiveWordsItemStatus[item.id] === "ignore" && (
            <Flex className="text-[#999] w-[130px]" gap={12} align="center">
              <span>已忽略</span>
              <Button
                className="text-[#055AFF]"
                onClick={() => {
                  openFeedback({
                    id: item.id,
                    source: JSON.stringify(item),
                    // 100为敏感词错误
                    errorType: 100,
                    // 反馈场景:0-写作1润色 2-扩写3-缩写 4-字词审核 5-敏感词审核
                    scene: 5
                  });
                }}
              >
                反馈
              </Button>
            </Flex>
          )}
        </Flex>
      </div>
    );
  };

  const renderSensitiveWordsEl = () => {
    return (
      <div className="h-[calc(100vh-240px)]">
        {resultData[ReviewType.SensitiveWords].length > 0 && (
          <Flex vertical className="h-full">
            {operationButton()}
            <Flex vertical gap={10} className="mt-[12px] overflow-y-auto">
              {resultData[ReviewType.SensitiveWords].map((item) => {
                return renderSensitiveWordsItem(item);
              })}
            </Flex>
          </Flex>
        )}
        {!resultData[ReviewType.SensitiveWords].length && (
          <Flex vertical gap={10} className="h-full box-border">
            <Flex vertical flex={1} align="center" className="pt-[64px]">
              <img src={init_bg} width={160} height={120} alt="" className="" />
              <div className="text-[#333] text-[16px] mt-[16px]">
                您的文章非常完美
              </div>
              <div className="text-[#999] text-[14px] mt-2">没有任何问题</div>
            </Flex>
          </Flex>
        )}
      </div>
    );
  };

  const renderLoadingEl = () => {
    return (
      mode === "loading" && (
        <Flex
          vertical
          gap={10}
          className="px-[16px] py-4 h-[calc(100vh-100px)] box-border"
          justify="center"
          align="center"
        >
          <img src={loadingGif} width={64} height={64} />
          <div className="text-sm text-[#1677ff]">审核中，请稍后...</div>
        </Flex>
      )
    );
  };

  const renderInitEl = () => {
    return (
      <Flex vertical gap={10} className="h-full box-border">
        <Flex vertical flex={1} align="center" className="pt-[84px]">
          <img src={init_bg} width={160} height={120} alt="" className="" />
          <div className="text-[#333] text-[16px] mt-[16px]">还未开始审核</div>
          <div className="text-[#999] text-[14px] mt-2">
            {activeKey === "1" ? "开始审核吧～" : "开始审核吧~"}
          </div>
        </Flex>
      </Flex>
    );
  };

  const closeSidebar = () => {
    setOpen(false);
    setProjectData((p) => ({
      ...p,
      currentModule: ModueEnum.Writing
    }));
  };

  const renderTabs = () => {
    const tabs = [
      {
        key: ReviewType.Corrigendum,
        label: "内容勘误",
        children:
          mode === "loading"
            ? renderLoadingEl()
            : mode == "result"
            ? renderCorrigendumEl()
            : renderInitEl()
      }
    ];
    if (
      projectData.sensitiveWords &&
      Object.keys(projectData.sensitiveWords).length > 0
    ) {
      tabs.push({
        key: ReviewType.SensitiveWords,
        label: "敏感词汇",
        children:
          mode === "loading"
            ? renderLoadingEl()
            : mode == "result"
            ? renderSensitiveWordsEl()
            : renderInitEl()
      });
    }
    return tabs;
  };
  return (
    <div className="h-full w-full relative">
      <StyledTitle title="审核" close={closeSidebar} />
      <ReviewFeedback
        open={feedback?.openModal || false}
        data={feedback?.data}
        handleClose={closeFeedback}
        handleOk={handFeedback}
      />
      <Tabs
        className="nlp-editor-review-tabs"
        items={renderTabs()}
        defaultActiveKey="1"
        activeKey={activeKey}
        onChange={handleSubTabChange}
        style={{ padding: "0 16px 16px 16px" }}
      ></Tabs>
    </div>
  );
};

export default ReviewModule;
