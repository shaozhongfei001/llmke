import { throttle } from "lodash";
import React, { useState, useEffect, useRef } from "react";
import { Input, message } from "antd";
const { TextArea } = Input;
interface Iprops {
  initValue?: string;
  save: (val: string, type: "prompt" | "example") => void;
  valueType: "prompt" | "example";
  setSection: React.Dispatch<React.SetStateAction<any>>;
}
const AutoSaveInput = ({
  initValue = "",
  save,
  valueType,
  setSection
}: Iprops) => {
  const [value, setValue] = useState(initValue);
  const [active, setActive] = useState(false);
  const saveRef = useRef(null);

  useEffect(() => {
    // 创建节流保存函数
    saveRef.current = throttle(
      async (val) => {
        save(val, valueType);
      },
      1000,
      { leading: true, trailing: true }
    );

    return () => {
      saveRef.current?.cancel();
    };
  }, []);

  const handleChange = (e, valueType: "prompt" | "example") => {
    const val = e.target.value;
    const newPartSeciton = {
      [valueType == "prompt" ? "sectionPrompt" : "sectionContentExample"]: val
    };
    setSection &&
      setSection((p: any) => {
        return {
          ...p,
          ...newPartSeciton
        };
      });

    setValue(val);

    if (!active && val) {
      setActive(true);
    }
  };

  useEffect(() => {
    if (active) {
      // if (valueType == "prompt" && (!value || value?.trim().length == 0)) {
      //   message.error("内容要求不能为空");
      //   return;
      // }
      saveRef?.current(value);
    }
  }, [value, active]);

  return (
    <TextArea
      value={value}
      onChange={(e) => handleChange(e, valueType)}
      onBlur={() => setActive(false)}
      onFocus={() => value && setActive(true)}
      placeholder="请输入"
      maxLength={10000}
      style={{ height: "calc(100% - 32px)", resize: "none" }}
    ></TextArea>
  );
};

export default AutoSaveInput;
