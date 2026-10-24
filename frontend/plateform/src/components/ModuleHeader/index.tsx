import { EditOutlined } from "@ant-design/icons";
import { cn } from "@udecode/cn";
import { Input, message } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";

interface Iprops {
  name: string;
  systemPrompt: string;
  gmtModified: string;
  handleNameChange: (name: string) => void;
  type?: "chapter" | "analysis";
}

enum State {
  Success = 1,
  editing
}

const emptyName = ["", "未命名组件", "未命名标题", "未命名章节"];

const renderStateTip = (state: State) => {
  const isSuccess = state === State.Success;
  // const isSuccess = true;
  return (
    <div
      className={cn(
        `pl-4 relative before:content-[''] before:absolute before:w-[8px] before:h-[8px] before:rounded-full before:left-[0px] before:top-[4px]`,
        {
          "before:bg-[#34C759]": isSuccess,
          "before:bg-[#888]": !isSuccess
        }
      )}
      style={{ color: isSuccess ? "#34C759" : "#888" }}
    >
      {isSuccess ? "已完成" : "编辑中"}
    </div>
  );
};

const ModuleHeader = ({
  name,
  systemPrompt,
  gmtModified,
  handleNameChange,
  type
}: Iprops) => {
  const [displayNameInput, setDisplayNameInput] = useState(false);
  const [nameValue, setNameValue] = useState(name || "未命名组件");

  useEffect(() => {
    setNameValue(name);
  }, [name]);

  const curState = useMemo(() => {
    if (systemPrompt && !emptyName.includes(nameValue)) return State.Success;
    return State.editing;
  }, [nameValue, systemPrompt]);

  const warningMsg = useMemo(() => {
    if (!systemPrompt && emptyName.includes(nameValue)) {
      return `标题和${type === "chapter" ? "内容要求" : "系统提示词"}未填写`;
    }
    if (!systemPrompt) {
      return `${type === "chapter" ? "内容要求" : "系统提示词"}未填写`;
    }
    if (emptyName.includes(nameValue)) {
      return "标题未填写";
    }
  }, [nameValue, systemPrompt, type]);

  const handleSaveName = () => {
    if (!nameValue) {
      message.error("标题不能为空");
      return;
    }
    setDisplayNameInput(false);
    handleNameChange(nameValue);
  };

  return (
    <div className="w-full h-[41px] flex justify-center flex-col">
      {displayNameInput ? (
        <Input
          onBlur={handleSaveName}
          value={nameValue}
          className="w-[370px]"
          onChange={(e) => {
            setNameValue(e.target.value);
          }}
          autoFocus={true}
        />
      ) : (
        <div className="text-[16px] text-[#2a2a2a] font-bold mb-1">
          <span
            className="inline-block mr-2"
            onDoubleClick={() => {
              setDisplayNameInput(true);
            }}
          >
            {nameValue}
          </span>
          <EditOutlined
            style={{
              color: "#555",
              fontSize: "16px",
              cursor: "pointer"
            }}
            onClick={() => {
              setDisplayNameInput(true);
            }}
          />
        </div>
      )}
      <div className="flex text-[12px]">
        <div>{renderStateTip(curState)}</div>
        <div
          className="mx-2 px-2 text-[#888]"
          style={{
            borderLeft: "1px solid #EEE",
            borderRight: "1px solid #EEE"
          }}
        >
          最新保存&nbsp;{gmtModified}
        </div>
        {warningMsg && (
          <div className="text-[#FF9500] pl-4 relative before:content-[''] before:absolute before:w-[8px] before:h-[8px] before:bg-[#FF9500] before:rounded-full before:left-[0px] before:top-[4px]">
            {warningMsg}
          </div>
        )}
      </div>
    </div>
  );
};

export default ModuleHeader;
