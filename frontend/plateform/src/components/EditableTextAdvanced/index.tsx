import {
  useEffect,
  useState,
  useRef,
  forwardRef,
  useImperativeHandle,
  memo
} from "react";
import { Input, message, Spin } from "antd";
import type { InputRef } from "antd/es/input";

type EditableTextProps = {
  initialValue: string;
  onSave: (value: string) => Promise<void>;
  canEmpty: boolean;
  color?: string;
};

export type EditableTextHandle = {
  startEditing: () => void;
};

const EditableTextAdvanced = forwardRef<EditableTextHandle, EditableTextProps>(
  ({ initialValue, onSave, canEmpty = true, color }, ref) => {
    const [isEditing, setIsEditing] = useState(false);
    const [value, setValue] = useState(initialValue);
    const [isSaving, setIsSaving] = useState(false);
    const inputRef = useRef<InputRef>(null);

    useEffect(() => {
      setValue(initialValue);
    }, [initialValue]);

    // 暴露方法给父组件
    useImperativeHandle(ref, () => ({
      startEditing: () => {
        setIsEditing(true);
      }
    }));

    // 双击事件处理
    const handleDoubleClick = () => {
      setIsEditing(true);
    };

    // 自动聚焦
    useEffect(() => {
      if (isEditing && inputRef.current) {
        inputRef.current.focus();
        // 可选：选中全部文本
        inputRef.current.select();
      }
    }, [isEditing]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === "Enter") handleSave();
      if (e.key === "Escape") {
        setValue(initialValue); // 恢复原文本
        setIsEditing(false);
      }
    };

    const handleSave = async () => {
      if (!canEmpty && value.trim() === "") {
        message.error("内容不能为空");
        return;
      }

      try {
        setIsSaving(true);
        await onSave(value);
        setIsEditing(false);
      } catch (error) {
        message.error("保存失败");
      } finally {
        setIsSaving(false);
      }
    };

    return isEditing ? (
      <div style={{ display: "flex", alignItems: "center", width: "100%" }}>
        <Input
          ref={inputRef}
          style={{
            width: "100%",
            paddingLeft: 0 // 去除缩进
          }}
          value={value}
          onChange={(e) => {
            e.stopPropagation();
            setValue(e.target.value);
          }}
          onClick={(e) => e.stopPropagation()}
          onBlur={handleSave}
          onKeyDown={handleKeyDown}
          disabled={isSaving}
        />
        {isSaving && <Spin size="small" style={{ marginLeft: 8 }} />}
      </div>
    ) : (
      <div
        className="w-full break-words text-ellipsis  line-clamp-1"
        title={value}
        onDoubleClick={handleDoubleClick}
        style={{
          color: color || "#2A2A2A"
        }}
      >
        {value || "-"}
      </div>
    );
  }
);

export default memo(EditableTextAdvanced);
