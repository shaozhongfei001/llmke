import { useRef, useState } from "react";
import {
  CheckCircleOutlined,
  PlusOutlined,
  CheckOutlined,
  CloseOutlined
} from "@ant-design/icons";
import { uid } from "uid";
import { useDrag, useDrop, DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { Button, Tag, Select, Radio, AutoComplete, Tooltip } from "antd";
import type { RadioChangeEvent } from "antd";
import { ReactComponent as SplitIcon } from "@/assets/svg/split.svg";
import "./index.css";

const options = [
  { label: "分段符", value: "\\n\\n" },
  { label: "中文句号", value: "。" },
  { label: "英文句号", value: "." },
  { label: "中文感叹号", value: "！" },
  { label: "英文感叹号", value: "!" },
  { label: "中文问号", value: "？" },
  { label: "英文问号", value: "?" },
  { label: "中文逗号", value: "，" },
  { label: "英文逗号", value: "," }
];

// 类型定义
interface IdentifyTagItem {
  label?: string;
  value: string;
  id: string;
  pos: "before" | "after";
}

interface DraggableTagProps {
  id: string;
  name: string;
  index: number;
  pos: "before" | "after";
  moveTag: (from: number, to: number) => void;
  onClose: (id: string) => void;
}

const DraggableTag = ({
  id,
  name,
  index,
  pos,
  moveTag,
  onClose
}: DraggableTagProps) => {
  const ref = useRef<HTMLSpanElement | null>(null);

  const [, drop] = useDrop({
    accept: "TAG",
    hover(item: { id: string; index: number }) {
      if (item.index === index) return;
      moveTag(item.index, index);
      item.index = index;
    }
  });

  const [{ isDragging }, drag] = useDrag({
    type: "TAG",
    item: { id, index },
    collect: (monitor) => ({
      isDragging: monitor.isDragging()
    })
  });

  drag(drop(ref));

  return (
    <Tag
      ref={ref}
      closable
      onClose={(e) => {
        e.preventDefault();
        onClose(id);
      }}
      className="flex items-center h-[32px] bg-[#fff]"
      style={{
        opacity: isDragging ? 0.5 : 1,
        cursor: "pointer",
        marginRight: 8
      }}
    >
      <span className="flex items-center">
        {pos == "before" && <SplitIcon className="mr-[6px]" />}
        <div className="bg-[#ECECEC] px-[6px] leading-[18px] font-bold rounded-md text-center">
          {name}
        </div>
        {pos == "after" && <SplitIcon className="ml-[6px]" />}
      </span>
    </Tag>
  );
};

interface IdentifyTagProps {
  disabled: boolean;
  identifyList: IdentifyTagItem[];
  setIdentifyList: React.Dispatch<React.SetStateAction<IdentifyTagItem[]>>;
}

const IdentifyTag = ({
  identifyList,
  setIdentifyList,
  disabled
}: IdentifyTagProps) => {
  const [selIdentifyTag, setSelIdentifyTag] = useState<string>();
  const [position, setPosition] = useState<"before" | "after">();

  const moveTag = (from: number, to: number) => {
    const updated = [...identifyList];
    const [removed] = updated.splice(from, 1);
    updated.splice(to, 0, removed);
    setIdentifyList(updated);
  };

  const handleDelete = (value: string) => {
    setIdentifyList(
      identifyList.filter((tag: IdentifyTagItem) => tag.id !== value)
    );
  };

  const handleChange = (value: string) => {
    setSelIdentifyTag(value);
  };

  const handlePositionChange = (e: RadioChangeEvent) => {
    setPosition(e.target.value);
  };

  const selectOpt = options.map((props) => {
    const { label, value } = props;
    return {
      label: (
        <div className="h-full flex items-center">
          <div className="bg-[#ECECEC] px-[6px] leading-[18px] font-bold rounded-md text-center mr-[6px]">
            {value}
          </div>
          {label}
        </div>
      ),
      value
    };
  });

  return (
    <div>
      <div>
        <AutoComplete
          disabled={disabled}
          style={{ width: "70%" }}
          options={selectOpt}
          placeholder="选择或自定义输入正则表达式"
          onChange={handleChange}
          value={selIdentifyTag}
          filterOption={false} // 不自动过滤
          maxLength={200}
        />
        <Radio.Group
          disabled={disabled}
          className="ml-[12px]"
          options={[
            {
              label: "前",
              value: "before",
              title: "标识符前切分"
            },
            { label: "后", value: "after", title: "标识符后切分" }
          ]}
          onChange={handlePositionChange}
          value={position}
        />
        <Button
          type="text"
          icon={<CheckOutlined />}
          disabled={disabled}
          style={{
            marginLeft: 8,
            border: "none",
            color: "#fff",
            background:
              position && selIdentifyTag
                ? "linear-gradient(90deg,#075BFF,#AC96FF)"
                : "#E4E8F6"
          }}
          onClick={() => {
            // 对号按钮逻辑
            const tag = options.find((o) => selIdentifyTag == o.value);
            if (selIdentifyTag && position) {
              setIdentifyList((pre) => {
                return [
                  ...pre,
                  {
                    value: tag ? tag.value : selIdentifyTag,
                    id: uid(4),
                    pos: position
                  }
                ];
              });
              setPosition(undefined);
              setSelIdentifyTag(undefined);
            }
          }}
        />
        <Tooltip title="点击清空所选项">
          <Button
            type="text"
            icon={<CloseOutlined />}
            disabled={disabled}
            style={{
              marginLeft: 8,
              border: "none",
              color: "#555555",
              background: "#E4E8F6"
            }}
            onClick={() => {
              // 叉号按钮逻辑
              setPosition(undefined);
              setSelIdentifyTag(undefined);
            }}
          />
        </Tooltip>
      </div>
      <DndProvider backend={HTML5Backend}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            flexWrap: "wrap",
            marginTop: "10px"
          }}
        >
          {identifyList.map((item: IdentifyTagItem, idx: number) => (
            <DraggableTag
              key={item.id}
              id={item.id}
              name={item.value}
              pos={item.pos}
              index={idx}
              moveTag={moveTag}
              onClose={handleDelete}
            />
          ))}
        </div>
      </DndProvider>
    </div>
  );
};

export default IdentifyTag;
