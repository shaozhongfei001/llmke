import React, { useState, useMemo, useEffect, useRef } from "react";
import { Button, Input, Tooltip, Switch, Spin, Modal, Tag, Flex } from "antd";
import type { InputRef } from "antd";
import {
  useSplitLayout,
  EventTypes
} from "@/components/SplitLayout/SplitLayoutContext";
import {
  DownOutlined,
  EllipsisOutlined,
  CaretDownOutlined,
  CaretRightOutlined,
  PlusOutlined,
  CloseOutlined
} from "@ant-design/icons";
import { FxIcon } from "@/components/Icon";
import {
  dataTypes,
  changeType,
  initialLitRow,
  initialTreeRow,
  editTypeObj,
  dataTypeList,
  indicatorTypeEnum,
  childrenKey
} from "./IndicatorDetail";
import { getIndicatorDetail } from "./common/useIndicatorsService";
import { useDrag, useDrop } from "react-dnd";
import { formulaToHtml } from "@/components/IndicatorEditor/util";
import "@/components/IndicatorEditor/indicatorTag.css";

const { TextArea } = Input;

const tagInputStyle: React.CSSProperties = {
  width: 100,
  height: 32,
  marginInlineEnd: 8,
  verticalAlign: "top"
};

const tagPlusStyle: React.CSSProperties = {
  height: 32,
  background: "#fff",
  borderStyle: "dashed"
};

interface ListItemProps {
  depth?: number;
  indicator: any;
  editListId: string | undefined;
  editType: string;
  indicatorType: indicatorTypeEnum;
  highLightNodeId: string | undefined;
  leftWidth: number;
  isAllExpand?: boolean;
  rowDataChange: (row: any, type: changeType, obj: any, cb?: any) => void;
  registerNodeRef: (id: string, element: HTMLDivElement | null) => void;
  onDrop: (dragNode: any, targetId: string, position: DropPosition) => void;
  resetEdit?: () => void;
}

export enum DropPosition {
  before = "before",
  after = "after",
  child = "child"
}

const cls = {
  [DropPosition.before]: "tip-before",
  [DropPosition.after]: "tip-after",
  [DropPosition.child]: "tip-child"
};

const subPadding = 24;

export const sourceList = [
  "合并资产负载表",
  "合并利润表",
  "合并现金流量表",
  "财务报表附注"
  // "其他"
];

const nodeTypes = ["selfNode"];

const ListItem: React.FC<ListItemProps> = (props) => {
  const {
    indicator,
    editListId,
    editType,
    depth = 0,
    indicatorType,
    highLightNodeId,
    leftWidth = 0,
    isAllExpand,
    rowDataChange,
    registerNodeRef,
    onDrop,
    resetEdit
  } = props;
  const [isExpand, setIsExpand] = useState<boolean>(true);
  const [isShowTip, setIsShowTip] = useState<boolean>(false);
  const nameIptRef = useRef<InputRef>(null);
  // const dscIptRef = useRef<InputRef>(null);
  // const aliasIptRef = useRef<InputRef>(null);
  const dragNodeRef = useRef<HTMLDivElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<DropPosition | null>(null);
  const [dragNodeId, setDragNodeId] = useState<string | null>(null);
  const positionRef = useRef<DropPosition | null>(null);
  const [indicatorDetail, setIndicatorDetail] = useState<any>(undefined);
  const [isFetching, setIsFetching] = useState<boolean>(false);
  const calculatorWrapRef = useRef<HTMLDivElement>(null);
  const [visibleDataType, setVisibleDataType] = useState(false);
  const dataTypeContentRef = useRef<HTMLDivElement>(null);
  const [visibleSourceType, setVisibleSourceType] = useState(false);
  const sourceTypeContentRef = useRef<HTMLDivElement>(null);
  const [isDscModalOpen, setIsDscModalOpen] = useState(false);
  const [editDescription, setEditDescription] = useState<string>("");
  const [isAliasModalOpen, setIsAliasModalOpen] = useState(false);
  const [editAlias, setEditAlias] = useState<string[]>([]);

  const [inputVisible, setInputVisible] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [editInputIndex, setEditInputIndex] = useState(-1);
  const [editInputValue, setEditInputValue] = useState("");
  const inputRef = useRef<InputRef>(null);
  const editInputRef = useRef<InputRef>(null);

  const { useSubscribe } = useSplitLayout();

  const sisActions = [
    {
      label: "复制",
      value: changeType.COPY
    },
    {
      label: "删除",
      value: changeType.DELETE
    }
  ];

  const originActions = [
    {
      label: "添加下级指标",
      value: changeType.ADD_CHILD
    },
    ...sisActions
  ];

  useSubscribe<number>(EventTypes.SAVE_CALCULATOR_ID, (id) => {
    if (id === indicator.id) {
      setIndicatorDetail(undefined);
    }
  });

  const [{ isDragging }, drag] = useDrag({
    type: nodeTypes[0],
    item: () => {
      if (
        indicator[childrenKey] &&
        indicator[childrenKey]?.length > 0 &&
        isExpand
      ) {
        setIsExpand(false);
      }
      return { ...indicator };
    },
    collect: (monitor) => ({
      isDragging: monitor.isDragging()
    })
  });

  const [{ isOver }, drop] = useDrop(() => ({
    accept: [...nodeTypes],
    hover: (draggedItem: any, monitor) => {
      if (!monitor.isOver({ shallow: true })) {
        return;
      }
      setDragNodeId(draggedItem.id);
      const _ref: any = dropZoneRef.current;
      if (_ref && _ref.getBoundingClientRect) {
        const rect = _ref.getBoundingClientRect();
        const clientOffset = monitor.getClientOffset();
        const clientY = clientOffset!.y;
        const clientX = clientOffset!.x;
        const offset = leftWidth + 50;
        const _position =
          clientX - offset > (rect.left + rect.width - offset) / 4
            ? DropPosition.child
            : clientY < rect!.top + rect!.height / 2
              ? DropPosition.before
              : DropPosition.after;

        if (_position !== positionRef.current) {
          // console.log("position:", _position, positionRef.current);
          positionRef.current = _position;
          setPosition(_position);
        }
      }
    },
    drop: (item: any) => {
      onDrop(item, indicator.id, positionRef.current || DropPosition.before);
      positionRef.current = null;
      setPosition(null);
      setDragNodeId(null);
    },
    collect: (monitor) => ({ isOver: monitor.isOver() })
  }));

  // drag(drop(dragNodeRef));
  drag(dragNodeRef);
  drop(dropZoneRef);

  const changeDataType = (val: string) => () => {
    if (String(indicator.dataType) !== val) {
      rowDataChange(indicator, changeType.DATA_TYPE_CHANGE, { dataType: val });
      setVisibleDataType(false);
    }
  };

  const changeSourceType = (val: string) => () => {
    if (String(indicator.sourceType) !== val) {
      rowDataChange(indicator, changeType.SOURCE_CHANGE, { sourceType: val });
      setVisibleSourceType(false);
    }
  };

  const configCalculator = (calculators: any[]) => () => {
    rowDataChange(indicator, changeType.CALCULATOR_CLICK, { calculators });
    setIsShowTip(false);
  };

  const handlerAbleChange = (checked: boolean) => {
    rowDataChange(indicator, changeType.DIS_ENABLE, { enable: checked });
  };

  const handlerAction = (type: changeType) => () => {
    rowDataChange(indicator, type, {});
  };

  const stopPropagation = (e: any) => {
    e.stopPropagation();
    e.preventDefault();
  };

  const handlerIptConfirm = (type: string) => (e: any) => {
    const val = e.target.value.trim();

    switch (type) {
      case editTypeObj.indicatorName:
        rowDataChange(
          indicator,
          isNew ? changeType.ADD_NODE : changeType.EDIT_ROW,
          {
            indicatorName: val
          }
        );
        break;
      // case editTypeObj.description:
      //   rowDataChange(indicator, changeType.EDIT_ROW, {
      //     description: val
      //   });
      //   break;
      // case editTypeObj.alias:
      //   rowDataChange(indicator, changeType.EDIT_ROW, {
      //     alias: val.split("，")
      //   });
      //   break;
    }
  };

  const editCell = (type: string, obj: any) => () => {
    rowDataChange(indicator, changeType.EDIT_INIT, {
      editIptType: type,
      ...obj
    });
  };

  const onToggleExpand = () => {
    setIsExpand(!isExpand);
  };

  const checkIsNeedExpand = (id: string) => {
    const _isExpand = nodeExists([indicator], id);
    if (_isExpand && !isExpand) {
      setIsExpand(true);
    }
  };

  const nodeExists = (treeData: any[], targetId: string) => {
    const stack = [...treeData];

    while (stack.length > 0) {
      const node = stack.pop();

      if (node.id === targetId) {
        return true;
      }

      if (node[childrenKey] && node[childrenKey].length > 0) {
        stack.push(...node[childrenKey]);
      }
    }

    return false;
  };

  const fetchIndicatorDetail = () => {
    setIsFetching(true);
    getIndicatorDetail(indicator.id)
      .then((res: any) => {
        setIndicatorDetail({ ...res });
      })
      .finally(() => {
        setIsFetching(false);
      })
      .catch((e) => {
        console.log(e);
        setIsFetching(false);
      });
  };

  const formatCalculatorHtml = () => {
    const { calculators, calculatorsIndicators } = indicatorDetail;
    const _html = formulaToHtml(calculators[0], calculatorsIndicators);
    const { html } = _html;
    if (html && calculatorWrapRef.current) {
      calculatorWrapRef.current.innerHTML = html;
    }
  };

  const showVisibleDataType = () => {
    setVisibleDataType(true);
  };

  const handleDataTypeMouseLeave = () => {
    setTimeout(() => {
      if (
        !document.activeElement ||
        !dataTypeContentRef.current ||
        !dataTypeContentRef.current.contains(document.activeElement)
      ) {
        setVisibleDataType(false);
      }
    }, 100);
  };

  const showVisibleSourceType = () => {
    setVisibleSourceType(true);
  };

  const handleSourceTypeMouseLeave = () => {
    setTimeout(() => {
      if (
        !document.activeElement ||
        !sourceTypeContentRef.current ||
        !sourceTypeContentRef.current.contains(document.activeElement)
      ) {
        setVisibleSourceType(false);
      }
    }, 100);
  };

  const handleShowDscModal = () => {
    setIsDscModalOpen(true);
  };

  const handleDscModalOk = () => {
    if (editDescription !== indicator.description) {
      setIsFetching(true);
      rowDataChange(
        indicator,
        changeType.EDIT_ROW,
        {
          description: editDescription
        },
        () => {
          setIsFetching(false);
          setIsDscModalOpen(false);
        }
      );
    } else {
      handleHideDscModal();
    }
  };

  const handleHideDscModal = () => {
    if (!isFetching) {
      setEditDescription("");
      resetEdit && resetEdit();
      setIsDscModalOpen(false);
    }
  };

  const editDescriptionChange = (e: any) => {
    const val = e.target.value.trim();
    setEditDescription(val);
  };

  const handleShowAliasModal = () => {
    setIsAliasModalOpen(true);
  };

  const handleHideAliasModal = () => {
    if (
      ((!indicator.alias || !indicator.alias.length) && editAlias.length) ||
      (indicator.alias && editAlias.toString() !== indicator.alias.toString())
    ) {
      setIsFetching(true);
      rowDataChange(
        indicator,
        changeType.EDIT_ROW,
        {
          alias: [...editAlias]
        },
        () => {
          setIsFetching(false);
          closeAliasModal();
        }
      );
    } else {
      closeAliasModal();
    }
  };

  const closeAliasModal = () => {
    setEditAlias([]);
    resetEdit && resetEdit();
    setIsAliasModalOpen(false);
  };

  const handleTagClose = (removedTag: string) => () => {
    const _editAlias = editAlias.filter((tag) => tag !== removedTag);
    // console.log(_editAlias);
    setEditAlias(_editAlias);
  };

  const showTagInput = () => {
    setInputVisible(true);
  };

  const handleTagInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleTagInputConfirm = () => {
    if (inputValue && !editAlias.includes(inputValue)) {
      setEditAlias([...editAlias, inputValue]);
    }
    setInputVisible(false);
    setInputValue("");
  };

  const handleTagEditInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEditInputValue(e.target.value);
  };

  const handleTagEditInputConfirm = () => {
    const _editAlias = [...editAlias];
    _editAlias[editInputIndex] = editInputValue;
    setEditAlias(_editAlias);
    setEditInputIndex(-1);
    setEditInputValue("");
  };

  const editAliasTag = (index: number, tag: string) => (e: any) => {
    setEditInputIndex(index);
    setEditInputValue(tag);
    stopPropagation(e);
  };

  // setEditAlias

  const isOriginal = useMemo(() => {
    return !!(indicatorType === indicatorTypeEnum.origin);
  }, [indicatorType]);

  const isStatistics = useMemo(() => {
    return !!(indicatorType === indicatorTypeEnum.statistics);
  }, [indicatorType]);

  const isNew = useMemo(() => {
    if (isStatistics) {
      return !!(String(indicator.id) === initialLitRow.id);
    } else if (isOriginal) {
      return !!(String(indicator.id) === initialTreeRow.id);
    }
    return false;
  }, [indicator, isOriginal, isStatistics]);

  const isDisabled = useMemo(() => {
    if (isStatistics) {
      return !!(!indicator.calculators || indicator.calculators.length === 0);
    } else if (isOriginal) {
      return !indicator.sourceType;
    }
    return false;
  }, [indicator, isOriginal, isStatistics]);

  const actions = useMemo(() => {
    if (isOriginal) {
      return originActions;
    }
    if (isStatistics) {
      return sisActions;
    }
    return [];
  }, [isOriginal, isStatistics]);

  const tipCls = useMemo(() => {
    // return "tip-before";
    return position && isOver && dragNodeId !== indicator.id
      ? cls[position]
      : "";
  }, [position, isOver, dragNodeId]);

  useEffect(() => {
    if (!isOver && dragNodeId) {
      setDragNodeId(null);
    }
  }, [isOver, dragNodeId]);

  useEffect(() => {
    if (dragNodeId && isOver && dragNodeId !== indicator.id && !isExpand) {
      setIsExpand(true);
    } else if (dragNodeId && dragNodeId === indicator.id && isExpand) {
      setIsExpand(false);
    }
  }, [dragNodeId, indicator, isExpand, isOver]);

  useEffect(() => {
    if (editListId && editListId === indicator.id) {
      switch (editType) {
        case editTypeObj.indicatorName:
          nameIptRef.current && nameIptRef.current.focus();
          break;
        case editTypeObj.description:
          // console.log(indicator);
          if (
            indicator.description &&
            indicator.description !== editDescription
          ) {
            setEditDescription(indicator.description);
          }
          handleShowDscModal();
          // dscIptRef.current.focus();
          break;
        case editTypeObj.alias:
          if (
            indicator.alias &&
            indicator.alias.length &&
            JSON.stringify(indicator.alias) !== JSON.stringify(editAlias)
          ) {
            setEditAlias([...indicator.alias.filter((i: string) => i)]);
          }
          handleShowAliasModal();
          //   aliasIptRef.current.focus();
          break;
      }
    }
  }, [editListId, editType, indicator]);

  useEffect(() => {
    if (highLightNodeId) {
      console.log(indicator, highLightNodeId);
      checkIsNeedExpand(highLightNodeId);
    }
  }, [highLightNodeId]);

  useEffect(() => {
    registerNodeRef(indicator.id, dragNodeRef.current);

    return () => {
      registerNodeRef(indicator.id, null);
    };
  }, [indicator.id, registerNodeRef]);

  useEffect(() => {
    if (isShowTip && !indicatorDetail) {
      fetchIndicatorDetail();
    }
  }, [isShowTip, indicatorDetail]);

  useEffect(() => {
    if (
      indicatorDetail &&
      indicatorDetail.calculators &&
      indicatorDetail.calculatorsIndicators
    ) {
      formatCalculatorHtml();
    }
  }, [indicatorDetail]);

  useEffect(() => {
    if (isAllExpand !== undefined && isAllExpand !== isExpand) {
      setIsExpand(isAllExpand);
    }
  }, [isAllExpand]);

  useEffect(() => {
    if (inputVisible) {
      inputRef.current?.focus();
    }
  }, [inputVisible]);

  useEffect(() => {
    editInputRef.current?.focus();
  }, [editInputValue]);

  return (
    <>
      <div
        className={`flex relative h-12 py-1 leading-10 box-border min-w-[950px] bg-white select-none hover:bg-[#f5f5f5]`}
        ref={dropZoneRef}
        style={{
          background:
            highLightNodeId && String(highLightNodeId) === String(indicator.id)
              ? "#f1f5ff"
              : "",
          borderBottom: "1px solid #e4e8f6"
        }}
      >
        <i
          className="inset-tip absolute h-[1px] left-12 right-0 border-0 border-b-2 border-solid border-b-primary-color"
          style={{
            display: tipCls ? "inline-block" : "none",
            // left: tipCls === "tip-child" ? "256px" : "56px",
            left: tipCls === "tip-child" ? "15%" : "5%",
            top: tipCls === "tip-before" ? "-1px" : "",
            bottom: tipCls === "tip-before" ? "" : "0px"
          }}
        >
          <b className="inline-block relative z-50 w-[10px] h-[10px] rounded-full bg-white -left-[10px] bottom-[19px] box-border border-2 border-solid border-primary-color"></b>
        </i>
        <div
          className={`pl-4 w-1/4 box-border min-w-60 flex ${
            isDragging ? "cursor-move" : "cursor-pointer"
          } `}
        >
          <div
            style={{
              width: `${
                indicatorType === indicatorTypeEnum.origin
                  ? depth * subPadding
                  : 0
              }px`
            }}
          >
            &nbsp;
          </div>
          {/* 指标名称 */}
          <div
            className={`${
              isOriginal ? "pl-4" : "pl-1"
            } flex-1 relative break-words text-ellipsis line-clamp-1`}
            ref={dragNodeRef}
          >
            {isOriginal &&
            indicator[childrenKey] &&
            indicator[childrenKey].length ? (
              isExpand ? (
                <CaretDownOutlined
                  className="text-[#888] absolute left-0 top-1/2 -mt-2"
                  title="关闭"
                  onClick={onToggleExpand}
                />
              ) : (
                <CaretRightOutlined
                  className="text-[#888] absolute left-0 top-1/2 -mt-2"
                  title="展开"
                  onClick={onToggleExpand}
                />
              )
            ) : null}
            {editListId === indicator.id &&
            editType === editTypeObj.indicatorName ? (
              <div className="w-full">
                <Input
                  defaultValue={indicator.indicatorName}
                  ref={nameIptRef}
                  placeholder="请输入指标名称"
                  allowClear
                  onClick={stopPropagation}
                  onBlur={handlerIptConfirm(editType)}
                  onPressEnter={handlerIptConfirm(editType)}
                />
              </div>
            ) : (
              <div className="relative px-1">
                <span
                  className="absolute top-1 bottom-1 right-0 left-0 border-0 z-10 select-none px-2 py-[6px] cursor-pointer rounded hover:border-[#d9d9d9] hover:border-solid hover:border"
                  title={indicator.indicatorName}
                  onClick={editCell(editTypeObj.indicatorName, {})}
                ></span>
                {indicator.indicatorName || "-"}
              </div>
            )}
          </div>
        </div>
        <div className="w-3/4 flex min-w-[710px]">
          {/* 数据类型 */}
          <div className="w-[17%] min-w-[120px] pl-3 flex box-border">
            {indicator.indicatorName ? (
              <Tooltip
                placement="rightTop"
                arrow={false}
                color="white"
                className="p-0"
                open={visibleDataType}
                title={
                  <div
                    className="text-gray-2a -my-1 -mx-2"
                    ref={dataTypeContentRef}
                    onMouseLeave={handleDataTypeMouseLeave}
                  >
                    {dataTypeList
                      .filter((d: any) => Number(d.value))
                      .map((d: any, idx: number) => {
                        return (
                          <div
                            className={`w-[52px] text-center rounded-lg h-8 leading-8 hover:bg-[#f1f5ff] select-none ${
                              d.value === String(indicator.dataType)
                                ? "bg-[#f1f5ff]"
                                : "cursor-pointer"
                            }`}
                            key={`data-type-${d.value}-${idx}`}
                            onClick={changeDataType(d.value)}
                          >
                            {d.label}
                          </div>
                        );
                      })}
                  </div>
                }
              >
                <Button
                  type="text"
                  className="px-1 mt-1 hover:!bg-[#E4E8F6] group"
                  iconPosition="end"
                  icon={
                    <DownOutlined
                      className={`${
                        visibleDataType ? "inline-block" : "hidden"
                      } w-3 text-black opacity-25 cursor-pointer group-hover:inline-block`}
                    />
                  }
                  onClick={showVisibleDataType}
                >
                  {dataTypes[indicator.dataType]}
                </Button>
              </Tooltip>
            ) : null}
          </div>
          {/* 描述 */}
          <div
            className={`${
              isOriginal ? "w-[27%] min-w-[180px]" : "w-[35%] min-w-[250px]"
            } pl-3 box-border break-words text-ellipsis line-clamp-1`}
          >
            {indicator.indicatorName ? (
              // editListId === indicator.id &&
              // editType === editTypeObj.description ? (
              //   <div className="w-full">
              //     <Input
              //       defaultValue={indicator.description}
              //       ref={dscIptRef}
              //       placeholder="请输入描述"
              //       allowClear
              //       onClick={stopPropagation}
              //       onBlur={handlerIptConfirm(editType)}
              //       onPressEnter={handlerIptConfirm(editType)}
              //     />
              //   </div>
              // ) :
              indicator.description ? (
                <Tooltip
                  placement="top"
                  color="white"
                  title={
                    <span className="text-gray-2a my-1 inline-block">
                      {indicator.description}
                    </span>
                  }
                >
                  <div className="relative px-1">
                    <span
                      className="absolute top-1 bottom-1 right-0 left-0 border-0 z-10 select-none px-2 py-[6px] cursor-pointer rounded hover:border-[#d9d9d9] hover:border-solid hover:border"
                      onClick={editCell(editTypeObj.description, {
                        description: indicator.description
                      })}
                    ></span>
                    {indicator.description}
                  </div>
                </Tooltip>
              ) : (
                <div className="relative px-1">
                  <span
                    className="absolute top-1 bottom-1 right-0 left-0 border-0 z-10 select-none px-2 py-[6px] cursor-pointer rounded hover:border-[#d9d9d9] hover:border-solid hover:border"
                    onClick={editCell(editTypeObj.description, {
                      description: ""
                    })}
                  ></span>
                  <span className="inline-block min-w-20">-</span>
                </div>
              )
            ) : null}
          </div>
          {/* 别名 */}
          <div
            className={`${
              isOriginal ? "w-[17%] min-w-32" : "w-[22%] min-w-40"
            } pl-3 box-border break-words text-ellipsis line-clamp-1`}
          >
            {indicator.indicatorName ? (
              // editListId === indicator.id && editType === editTypeObj.alias ? (
              //   <div className="w-full">
              //     <Input
              //       defaultValue={
              //         indicator.alias && indicator.alias.length
              //           ? indicator.alias[0]
              //           : ""
              //       }
              //       ref={aliasIptRef}
              //       placeholder="请输入别名"
              //       allowClear
              //       onClick={stopPropagation}
              //       onBlur={handlerIptConfirm(editType)}
              //       onPressEnter={handlerIptConfirm(editType)}
              //     />
              //   </div>
              // ) :
              indicator.alias &&
              indicator.alias.length &&
              indicator.alias.join("，") ? (
                <Tooltip
                  placement="top"
                  color="white"
                  title={
                    <span className="text-gray-2a my-1 inline-block">
                      {indicator.alias.join("，")}
                    </span>
                  }
                >
                  <div className="relative px-1">
                    <span
                      className="absolute top-1 bottom-1 right-0 left-0 border-0 z-10 select-none px-2 py-[6px] cursor-pointer rounded hover:border-[#d9d9d9] hover:border-solid hover:border"
                      onClick={editCell(editTypeObj.alias, {
                        alias: indicator.alias
                      })}
                    ></span>
                    {indicator.alias.join("，")}
                  </div>
                </Tooltip>
              ) : (
                <div className="relative px-1">
                  <span
                    className="absolute top-1 bottom-1 right-0 left-0 border-0 z-10 select-none px-2 py-[6px] cursor-pointer rounded hover:border-[#d9d9d9] hover:border-solid hover:border"
                    onClick={editCell(editTypeObj.alias, { alias: [] })}
                  ></span>
                  <span className="inline-block min-w-20">-</span>
                </div>
              )
            ) : null}
          </div>

          {isOriginal ? (
            // 来源
            <div className="w-[22%] min-w-40 pl-4 box-border">
              {indicator.indicatorName ? (
                <Tooltip
                  placement="bottom"
                  arrow={false}
                  color="white"
                  className="p-0"
                  open={visibleSourceType}
                  title={
                    <div
                      className="text-gray-2a -my-1 -mx-2"
                      ref={sourceTypeContentRef}
                      onMouseLeave={handleSourceTypeMouseLeave}
                    >
                      {sourceList.map((d: any, idx: number) => {
                        return (
                          <div
                            className={`w-[120px] px-2 rounded-lg h-8 leading-8 hover:bg-[#f1f5ff] select-none ${
                              d === String(indicator.sourceType)
                                ? "bg-[#f1f5ff]"
                                : "cursor-pointer"
                            }`}
                            key={`source-type-${d}-${idx}`}
                            onClick={changeSourceType(d)}
                          >
                            {d}
                          </div>
                        );
                      })}
                    </div>
                  }
                >
                  <Button
                    type="text"
                    className="px-1 mt-1 hover:!bg-[#E4E8F6] group"
                    iconPosition="end"
                    icon={
                      <DownOutlined
                        className={`${
                          visibleSourceType ? "inline-block" : "hidden"
                        } w-3 text-black opacity-25 cursor-pointer group-hover:inline-block`}
                      />
                    }
                    onClick={showVisibleSourceType}
                  >
                    <span
                      className={`${
                        !indicator.sourceType ? "text-[#bbb]" : ""
                      }`}
                    >
                      {indicator.sourceType || "请选择"}
                    </span>
                  </Button>
                </Tooltip>
              ) : null}
            </div>
          ) : null}
          {isStatistics ? (
            // 公式
            <div className="w-[9%] min-w-[60px] pl-3 box-border">
              {indicator.indicatorName ? (
                indicator.calculators &&
                indicator.calculators.length &&
                indicator.calculators.join("") !== "" ? (
                  <Tooltip
                    placement="top"
                    open={isShowTip}
                    zIndex={1}
                    color="white"
                    onOpenChange={setIsShowTip}
                    styles={{
                      root: {
                        maxWidth: 400
                      }
                    }}
                    title={
                      <Spin spinning={isFetching}>
                        <div className="text-gray-2a">
                          <div className="h-6 leading-6 mb-2">
                            <b>公式</b>
                          </div>
                          <div className="min-h-6" ref={calculatorWrapRef}>
                            &nbsp;
                          </div>
                        </div>
                      </Spin>
                    }
                  >
                    <Button
                      type="text"
                      className="px-0 hover:!bg-white"
                      icon={
                        <FxIcon
                          className={`"text-gray-2a cursor-pointer hover:text-[#0359FC]`}
                          onClick={configCalculator(indicator.calculators)}
                        />
                      }
                    />
                  </Tooltip>
                ) : (
                  <Tooltip
                    placement="top"
                    open={isShowTip}
                    zIndex={1}
                    onOpenChange={setIsShowTip}
                    color="white"
                    title={<div className="text-gray-2a">配置公式</div>}
                  >
                    <Button
                      type="text"
                      className="px-0 hover:!bg-white"
                      disabled={
                        indicator.id === initialLitRow.id ||
                        indicator.id === initialTreeRow.id
                      }
                      icon={
                        <FxIcon
                          className={`text-[#bbb] cursor-pointer hover:text-[#0359FC]`}
                          onClick={configCalculator([])}
                        />
                      }
                    />
                  </Tooltip>
                )
              ) : null}
            </div>
          ) : null}
          {/* 启用 */}
          <div className="w-[8.5%] min-w-[60px] pl-4 box-border">
            {indicator.indicatorName ? (
              <Switch
                defaultValue={!!(indicator.state && indicator.state === 1)}
                onChange={handlerAbleChange}
                disabled={
                  indicator.id === initialLitRow.id ||
                  indicator.id === initialTreeRow.id ||
                  isDisabled
                }
              />
            ) : null}
          </div>
          {/* 操作 */}
          <div className="w-[8.5%] min-w-[60px] pl-4 box-border">
            {indicator.indicatorName ? (
              <Tooltip
                placement="bottomRight"
                arrow={false}
                color="white"
                title={
                  <div className="text-gray-2a -my-1 -mx-2">
                    {actions.map((i: any, idx: number) => {
                      return (
                        <div
                          className={`${isOriginal ? "w-[100px] px-2 " : ""}${
                            isStatistics ? "w-[52px] text-center " : ""
                          }cursor-pointer h-8 leading-8 rounded-lg text-gray-2a hover:bg-[#f1f5ff]`}
                          key={`action-${indicator.id}-${i.value}-${idx}`}
                          onClick={handlerAction(i.value)}
                        >
                          {i.label}
                        </div>
                      );
                    })}
                  </div>
                }
              >
                <Button
                  type="text"
                  size="small"
                  disabled={
                    indicator.id === initialLitRow.id ||
                    indicator.id === initialTreeRow.id
                  }
                  className={`w-6 h-6 text-text-color2 hover:!text-primary-color hover:!bg-white`}
                  icon={<EllipsisOutlined />}
                />
              </Tooltip>
            ) : null}
          </div>
        </div>
      </div>

      {isExpand &&
        indicator[childrenKey]?.map((child: any) => {
          return (
            <ListItem
              {...props}
              key={child.id}
              indicator={child}
              depth={depth + 1}
            />
          );
        })}
      <Modal
        title="编辑描述"
        closable={{ "aria-label": "Custom Close Button" }}
        open={isDscModalOpen}
        footer={
          <div className="flex justify-end gap-4">
            <Button
              className="border-[#ebebeb] text-text-color2"
              disabled={isFetching}
              onClick={handleHideDscModal}
            >
              取消
            </Button>
            <Button
              type="primary"
              className="border-0 bg-[linear-gradient(99.9deg,#2B69FF,#8F91FF)]"
              onClick={handleDscModalOk}
              disabled={isFetching}
              loading={isFetching}
            >
              确认
            </Button>
          </div>
        }
        onCancel={handleHideDscModal}
      >
        <TextArea
          value={editDescription}
          onChange={editDescriptionChange}
          placeholder="请输入描述"
          className="h-40"
          style={{ resize: "none", height: "160px", borderColor: "#d9d9d9" }}
        />
      </Modal>
      <Modal
        title={
          <div className="flex justify-between leading-8">
            <div className="leading-8">编辑别名</div>
            <Button
              type="text"
              icon={<CloseOutlined />}
              disabled={isFetching}
              onClick={handleHideAliasModal}
            />
          </div>
        }
        closable={false}
        open={isAliasModalOpen}
        footer={false}
      >
        <Spin spinning={isFetching}>
          <div className="h-56 overflow-x-hidden overflow-y-auto">
            <Flex gap="12px 0" wrap>
              {editAlias.map<React.ReactNode>((tag, index) => {
                if (editInputIndex === index) {
                  return (
                    <Input
                      ref={editInputRef}
                      key={tag}
                      size="small"
                      style={tagInputStyle}
                      value={editInputValue}
                      onChange={handleTagEditInputChange}
                      onBlur={handleTagEditInputConfirm}
                      onPressEnter={handleTagEditInputConfirm}
                    />
                  );
                }
                const isLongTag = tag.length > 20;
                const tagElem = (
                  <Tag
                    key={tag}
                    className="border-[#eee] bg-white h-8 leading-6 px-3 py-1 box-border rounded text-gray-2a text-sm"
                    closable={true}
                    style={{ userSelect: "none" }}
                    onClose={handleTagClose(tag)}
                  >
                    <span onDoubleClick={editAliasTag(index, tag)}>
                      {isLongTag ? `${tag.slice(0, 20)}...` : tag}
                    </span>
                  </Tag>
                );
                return isLongTag ? (
                  <Tooltip title={tag} key={tag}>
                    {tagElem}
                  </Tooltip>
                ) : (
                  tagElem
                );
              })}
              {inputVisible ? (
                <Input
                  ref={inputRef}
                  type="text"
                  size="small"
                  style={{
                    ...tagInputStyle,
                    width: "160px"
                  }}
                  value={inputValue}
                  onChange={handleTagInputChange}
                  onBlur={handleTagInputConfirm}
                  onPressEnter={handleTagInputConfirm}
                />
              ) : (
                <Tag
                  className="border-[#d9d9d9] border-dashed bg-white h-8 leading-6 px-3 py-1 box-border rounded text-gray-2a text-sm"
                  icon={<PlusOutlined />}
                  onClick={showTagInput}
                >
                  自定义添加
                </Tag>
              )}
            </Flex>
          </div>
        </Spin>
      </Modal>
    </>
  );
};

export default ListItem;
