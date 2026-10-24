import React, { useEffect, useMemo, useRef, useState } from "react";
import { CloseOutlined, PlusOutlined } from "@ant-design/icons";
import type { InputRef } from "antd";
import { Input, message, Tag, theme } from "antd";
import VirtualWrap from "./VirtualWrap";
import { debounce } from "lodash";

const FONT_SIZE = 12;
const INPUT_WIDTH = 64;
const ADD_TAG_TYPE = "add_tab_20250208";

const canvas = document.createElement("canvas");
interface AutoTagInterface {
  wrapRef?: any;
  tags: string[];
  setTags: (arg: string[]) => void;
  disabled?: boolean;
  fuzzyNameOrId?: string;
  addLabel?: string;
}

const AutoTag = ({
  tags,
  setTags,
  disabled,
  fuzzyNameOrId,
  addLabel,
  wrapRef = null
}: AutoTagInterface) => {
  const { token } = theme.useToken();
  const [inputVisible, setInputVisible] = useState(false);
  const [editInputIndex, setEditInputIndex] = useState(-1);
  const [editInitVal, setEditInitVal] = useState<string>("");
  const inputRef = useRef<InputRef>(null);
  const editInputRef = useRef<InputRef>(null);
  const tagInputStyle: React.CSSProperties = {
    width: INPUT_WIDTH,
    height: 32,
    marginInlineEnd: 8,
    verticalAlign: "top",
    fontSize: FONT_SIZE,
    lineHeight: 30,
    minWidth: INPUT_WIDTH
  };
  const [containerHeight, setContainerHeight] = useState<number>(0);
  const [containerWidth, setContainerWidth] = useState<number>(0);
  const [canvasContext, setCanvasContext] = useState<any>(
    canvas.getContext("2d")
  );
  const [virtualList, setVirtualList] = useState<Array<any>>([]);

  useEffect(() => {
    setContainerRect();
  }, [wrapRef]);

  const handleClose = (removedTag: string) => () => {
    const newTags = tags.filter((tag) => tag.trim() !== removedTag);
    setTags(newTags);
  };

  const showInput = () => {
    setInputVisible(true);
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const getStrLenght = (str: string) => {
    let totalLength = 0;

    for (let i = 0; i < str.length; i++) {
      // 判断当前字符是字母还是数字
      if (/[a-zA-Z0-9]/.test(str[i])) {
        totalLength += 1.2; // 字母和数字长度为1
      } else {
        // 其他字符（比如汉字、emoji等）长度为2
        totalLength += 2;
      }
    }

    return (FONT_SIZE / 2) * totalLength + 30;
  };

  const handleInputConfirm = (e: any) => {
    const _value = e.target.value.trim();
    if (_value && !tags.includes(_value)) {
      setTags([...tags, _value.slice(0, 16)]);
    }
    setInputVisible(false);
  };

  const handleEditInputConfirm = (e: any) => {
    const _value = e.target.value.trim();
    if (_value) {
      const newTags = [...tags];
      newTags[editInputIndex] = _value.slice(0, 16);
      setTags(newTags);
      setEditInputIndex(-1);
    }
  };

  const tagPlusStyle: React.CSSProperties = {
    height: 32,
    background: token.colorBgContainer,
    borderStyle: "dashed",
    borderColor: "#D9D9D9",
    padding: "0 15px",
    lineHeight: "30px",
    fontSize: FONT_SIZE
  };

  const handleIptChange = debounce((e: React.ChangeEvent<HTMLInputElement>) => {
    const _value = e.target.value.trim();
    const editIpt = editInputRef.current;
    if (_value.length >= 16 && editIpt && editIpt.input) {
      message.warning("敏感词最多可输入16个字符!");
    }
  }, 300);

  const getTextWidth = (
    text: string,
    fontSize = 12,
    fontFamily = "PingFangSC,微软雅黑,Helvetic"
  ) => {
    canvasContext.font = `${fontSize}px ${fontFamily}`;
    return canvasContext.measureText(text).width;
  };

  const RenderRow = (props: any) => {
    const { item } = props;
    const { list } = item;
    return (
      <div className="mb-4">
        {list && list.length
          ? list.map((i: any, index: number) => (
              <span key={`tag_wrap_${index}`}>{renderTag(i)}</span>
            ))
          : null}
      </div>
    );
  };

  const editTag = (label: string, idx: number) => (e: any) => {
    if (disabled) return;
    setEditInputIndex(idx);
    setEditInitVal(label);
    e.preventDefault();
  };

  const setEditIptWidth = () => {
    const editIpt = editInputRef.current;
    if (editIpt && editIpt.input) {
      editIpt.input.style.width = `${getStrLenght(editIpt.input.value.slice(0, 16))}px`;
    }
  };
  const setAddIptWidth = () => {
    const addIpt = inputRef.current;
    if (addIpt && addIpt.input) {
      addIpt.input.style.width = `${getStrLenght(addIpt.input.value.slice(0, 16))}px`;
    }
  };

  const editIptOnInput = debounce(setEditIptWidth, 200);

  const addIptOnInput = debounce(setAddIptWidth, 200);

  const renderTag = (tagData: any) => {
    const { idx, label } = tagData;
    return editInputIndex === idx ? (
      <Input
        ref={editInputRef}
        key={`edit-ipt-${idx}`}
        maxLength={16}
        size="small"
        style={tagInputStyle}
        defaultValue={editInitVal}
        onInput={editIptOnInput}
        onBlur={handleEditInputConfirm}
        onPressEnter={handleEditInputConfirm}
        onChange={handleIptChange}
      />
    ) : label === ADD_TAG_TYPE ? (
      inputVisible ? (
        <Input
          ref={inputRef}
          type="text"
          size="small"
          maxLength={16}
          style={tagInputStyle}
          onInput={addIptOnInput}
          onBlur={handleInputConfirm}
          onPressEnter={handleInputConfirm}
          onChange={handleIptChange}
        />
      ) : (
        <Tag
          icon={<PlusOutlined />}
          color="processing"
          style={tagPlusStyle}
          onClick={showInput}
        >
          {addLabel || "添加"}
        </Tag>
      )
    ) : (
      <Tag
        key={`tag_${idx}`}
        style={{
          userSelect: "none",
          height: "32px",
          lineHeight: "30px",
          padding: "0 15px",
          fontSize: `${FONT_SIZE}px`,
          background: "white",
          borderColor: "#EBEBEB"
        }}
        closable={!disabled}
        onClose={handleClose(label)}
        closeIcon={<CloseOutlined />}
      >
        <span onDoubleClick={editTag(label, idx)}>{label}</span>
      </Tag>
    );
  };

  const setContainerRect = () => {
    if (wrapRef && wrapRef.current) {
      const { height, width } = wrapRef.current.getBoundingClientRect();
      setContainerHeight(height);
      setContainerWidth(width);
    }
  };

  const filterTags = useMemo(() => {
    return (tags || []).concat(ADD_TAG_TYPE).filter((tag) => {
      return fuzzyNameOrId ? tag.indexOf(fuzzyNameOrId) > -1 : true;
    });
  }, [tags, fuzzyNameOrId]);

  useEffect(() => {
    if (containerWidth && containerHeight && filterTags && filterTags.length) {
      fixRenderData();
    }
  }, [filterTags, containerHeight, containerWidth]);

  const resizeFn = debounce(() => {
    setContainerRect();
  }, 500);

  useEffect(() => {
    window.addEventListener("resize", resizeFn);
    return () => {
      window.removeEventListener("resize", resizeFn);
    };
  }, []);

  useEffect(() => {
    if (editInputIndex >= 0) {
      setEditIptWidth();
      setTimeout(() => {
        editInputRef.current?.focus();
      }, 100);
    }
  }, [editInputIndex]);

  const fixRenderData = () => {
    const _list: Array<any> = [];
    let _row: Array<any> = [];
    let len: number = 0;
    const tagMargin = 18;
    const fixWidth = 49 + tagMargin;
    // console.log("fixRenderData", containerWidth)
    filterTags.forEach((str: string, idx: number) => {
      const _str = str.trim();
      const strWidth = getTextWidth(_str);
      const tagWidth = strWidth + fixWidth;
      const obj = {
        idx,
        label: _str
      };
      if (len + tagWidth > containerWidth) {
        _list.push({ idx, list: [..._row] });
        _row = [{ ...obj }];
        len = tagWidth;
      } else {
        len = len + tagWidth;
        _row.push({ ...obj });
      }
    });
    _list.push({ idx: _list.length + 1, list: [..._row] });
    setVirtualList([..._list]);
  };

  const res = useMemo(() => {
    return virtualList.length ? (
      <VirtualWrap
        list={virtualList}
        itemHeight={22}
        paddingY={12}
        wrapPadding={32}
        wrapperRef={wrapRef}
        itemKey="idx"
      >
        <RenderRow />
      </VirtualWrap>
    ) : null;
  }, [virtualList, editInputIndex, inputVisible]);

  return <>{res}</>;
};

export default AutoTag;
