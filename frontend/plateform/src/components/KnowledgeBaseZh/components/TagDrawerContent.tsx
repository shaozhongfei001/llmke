const TagDrawerContent = ({
  btnLoading,
  drawConfig,
  emitEvent,
  bizLabelList
}: any) => {
  const [tags, setTags] = useState<string[]>([]);
  const OLDTAGS = useMemo(() => {
    return drawConfig?.data?.tags || [];
  }, [drawConfig]);
  const [oldTags, setOldTags] = useState<string[]>(OLDTAGS || []);

  const handleCheck = (value: string, checked: boolean) => {
    if (checked) {
      const newTags = Array.from(new Set([...tags, value]));
      setTags(newTags);
    } else {
      setTags((prevTags: any) => {
        const newTags = prevTags.filter((tag: any) => tag !== value);
        return newTags;
      });
    }
  };

  const handleEvent = (type: string, data: any, originTag?: string) => {
    switch (type) {
      case "editTag":
        if (data != originTag) {
          const curTag5: any = oldTags.find(
            (tag: any) => tag.label === originTag
          );
          if (curTag5) {
            curTag5.checked = false;
          }

          const curTag6: any = oldTags.find((tag: any) => tag.label === data);
          if (curTag6) {
            curTag6.checked = true;
          }
          setOldTags([...oldTags]);
        }

        break;
      case "addTag":
        const curTag: any = oldTags.find((tag: any) => tag.label === data);
        if (curTag) {
          curTag.checked = true;
        }
        break;
      case "deleteTag":
        const curTag2: any = oldTags.find((tag: any) => tag.label === data);
        if (curTag2) {
          curTag2.checked = false;
          setOldTags([...oldTags]);
        }
        break;
    }
  };

  useEffect(() => {
    if (drawConfig.data.label) {
      setTags(drawConfig.data.label.split(","));
    } else {
      setTags([]);
    }
  }, [drawConfig]);

  useEffect(() => {
    if (bizLabelList) {
      const t = drawConfig?.data?.label ? drawConfig.data.label.split(",") : [];
      const o: any = _.uniqBy(bizLabelList, "label");
      setOldTags(
        o.map((item: any) => {
          return {
            ...item,
            checked: t.includes(item.label) ? true : false
          };
        })
      );
    }
  }, [bizLabelList, drawConfig]);

  return (
    <div className="h-full">
      <div className="text-[14px] text-[#666666] font-[400] leading-[20px] mb-[8px]">
        每个标签最多32个字符，支持中文，大小写英文字母，数字，下划线_，中划线-，首尾空格会自动截断
      </div>
      <div className="w-[485px] h-[224px] border-[1px] border-solid border-[#D9D9D9] bg-[#F6F6F6] rounded-[4px] p-[16px] overflow-y-auto">
        <AutoTag tags={tags} setTags={setTags} handleEvent={handleEvent} />
      </div>
      <div className="text-[#2A2A2A] mt-[20px] h-[calc(100%-300px)] overflow-y-auto overflow-x-hidden">
        已使用过标签<span className="text-[#666666]">（点击可添加）</span>
        <div className="mt-[10px]">
          {oldTags.map((tag: any, index: number) => {
            return (
              <Tag
                key={index}
                className=" bg-white cursor-pointer"
                style={{
                  margin: "4px 8px 4px 0",
                  border: tag.checked
                    ? "1px solid #EBF6FF"
                    : "1px solid #D9D9D9",
                  backgroundColor: tag.checked ? "#EBF6FF" : "#FFFFFF",
                  color: tag.checked ? "#1D70F5" : "#222222"
                }}
                onClick={() => {
                  setOldTags((prevTags: any) => {
                    const cur = prevTags.find(
                      (item: any) => item.label === tag.label
                    );
                    cur.checked = !cur.checked;
                    handleCheck(tag.label, cur.checked);
                    return [...prevTags];
                  });
                }}
              >
                {tag.label}
              </Tag>
            );
          })}
        </div>
      </div>
      <div
        className="flex justify-end h-[38px] pt-[16px]"
        style={{ borderTop: "1px solid #EBEBEB" }}
      >
        <Button
          style={{
            border: "1px solid #EBEBEB",
            color: "#555555",
            marginRight: "16px"
          }}
          onClick={() => {}}
        >
          取消
        </Button>
        <Button
          style={{
            border: "none",
            color: "#fff",
            background:
              "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
          }}
          onClick={() => {
            emitEvent("saveTags", tags);
          }}
          loading={btnLoading}
        >
          确认
        </Button>
      </div>
    </div>
  );
};

export default TagDrawerContent;

import React, { useEffect, useMemo, useRef, useState } from "react";
import { PlusOutlined } from "@ant-design/icons";
import type { InputRef } from "antd";
import { Button, Flex, Input, Tag, theme, Tooltip } from "antd";
import _ from "lodash";

const tagInputStyle: React.CSSProperties = {
  width: 64,
  height: 22,
  marginInlineEnd: 8,
  verticalAlign: "top"
};

const AutoTag = (props: any) => {
  const { token } = theme.useToken();
  const { tags, setTags, handleEvent } = props;
  const [inputVisible, setInputVisible] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [editInputIndex, setEditInputIndex] = useState(-1);
  const [editInputValue, setEditInputValue] = useState("");
  const inputRef = useRef<InputRef>(null);
  const editInputRef = useRef<InputRef>(null);

  useEffect(() => {
    if (inputVisible) {
      inputRef.current?.focus();
    }
  }, [inputVisible]);

  useEffect(() => {
    editInputRef.current?.focus();
  }, [editInputValue]);

  const handleClose = (removedTag: string) => {
    const newTags = tags.filter((tag: string) => tag !== removedTag);
    console.log(newTags);
    setTags(newTags);
    handleEvent("deleteTag", removedTag);
  };

  const showInput = () => {
    setInputVisible(true);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleInputConfirm = () => {
    if (inputValue && !tags.includes(inputValue)) {
      handleEvent("addTag", inputValue);
      setTags([...tags, inputValue]);
    }
    setInputVisible(false);
    setInputValue("");
  };

  const handleEditInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEditInputValue(e.target.value);
  };

  const handleEditInputConfirm = () => {
    const newTags = [...tags];
    const originTag = newTags[editInputIndex];
    newTags[editInputIndex] = editInputValue;
    setTags(newTags);

    handleEvent("editTag", editInputValue, originTag);
    setEditInputIndex(-1);
    setEditInputValue("");
  };

  const tagPlusStyle: React.CSSProperties = {
    height: 22,
    background: "white",
    borderStyle: "dashed"
  };

  return (
    <Flex gap="4px 0" wrap>
      {tags.map((tag: string, index: number) => {
        if (editInputIndex === index) {
          return (
            <Input
              ref={editInputRef}
              key={tag}
              size="small"
              style={tagInputStyle}
              value={editInputValue}
              onChange={handleEditInputChange}
              onBlur={handleEditInputConfirm}
              onPressEnter={handleEditInputConfirm}
              maxLength={32}
            />
          );
        }
        const isLongTag = tag.length > 20;
        const tagElem = (
          <Tag
            key={tag}
            closable
            style={{ userSelect: "none" }}
            onClose={() => handleClose(tag)}
          >
            <span
              onDoubleClick={(e) => {
                setEditInputIndex(index);
                setEditInputValue(tag);
                e.preventDefault();
              }}
            >
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
          style={tagInputStyle}
          value={inputValue}
          onChange={handleInputChange}
          onBlur={handleInputConfirm}
          onPressEnter={handleInputConfirm}
          maxLength={32}
        />
      ) : (
        <Tag
          style={tagPlusStyle}
          icon={<PlusOutlined className="text-primary-color" />}
          className="text-primary-color"
          onClick={showInput}
        >
          添加
        </Tag>
      )}
    </Flex>
  );
};
