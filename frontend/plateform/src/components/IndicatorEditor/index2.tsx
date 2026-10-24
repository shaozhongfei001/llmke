import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createEditor, Descendant, Range, Editor, Node } from "slate";
import { Slate, Editable, withReact } from "slate-react";
import { LeafCb, renderElementCb } from "./renderElementAndLeaf";
import { myDecorator } from "./myDecorator";
import { insertIndicator, updateDropdownPosition } from "./util";
import { initialValue } from "./elemntAndLeafType";

const arr = [
  "营业收入",
  "净利润",
  "总资产",
  "净资产",
  "流动资产",
  "流动负债",
  "现金及现金等价物",
  "存货",
  "应收账款"
];

const operators = [
  "+",
  "-",
  "*",
  "/",
  "%",
  "=",
  "<",
  ">",
  "<=",
  ">=",
  "!=",
  "&&",
  "||",
  "!",
  "(",
  ")",
  "[",
  "]",
  "{",
  "}"
];

interface Iprops {
  getValue?: (value: any) => void;
}
const IndicatorEditor = ({ getValue }: Iprops) => {
  const editor = useMemo(() => withReact(createEditor()), []);
  const [value, setValue] = useState<Descendant[]>(initialValue);
  const editorRef = useRef<HTMLDivElement>(null); // 新增ref
  const [dropdown, setDropdown] = useState({
    visible: false,
    options: [] as string[],
    index: 0,
    position: { left: 0, top: 0 }
  });

  useEffect(() => {
    if (dropdown.visible) {
      updateDropdownPosition({
        editorRef,
        dropdown,
        setDropdown
      });
    }
  }, [dropdown.visible, value]);

  const renderElement = useCallback(renderElementCb, []);
  const Leaf = useCallback(LeafCb, []);

  const handleChange = (newValue: Descendant[]) => {
    console.log("value", newValue);
    setValue(newValue);
    const { selection } = editor;
    if (selection && Range.isCollapsed(selection)) {
      const [node] = Editor.node(editor, selection);
      const text = Node.string(node);
      // 获取光标前的内容
      const before = text.slice(0, selection.anchor.offset);
      // 模糊匹配
      const matched = arr.filter(
        (item) => item.includes(before) && before.length > 0
      );
      if (matched.length > 0) {
        // 计算弹窗位置（可用 DOM API 或 Slate API）
        setDropdown({
          visible: true,
          options: matched,
          index: 0,
          position: { left: 0, top: 0 } // 这里建议用 ref + getBoundingClientRect 计算
        });
      } else {
        setDropdown((d) => ({ ...d, visible: false }));
      }
    } else {
      setDropdown((d) => ({ ...d, visible: false }));
    }
  };

  useEffect(() => {
    console.log(value, "这是内容");
  }, [value]);

  return (
    <div className="relative h-full w-full" ref={editorRef}>
      <Slate editor={editor} initialValue={value} onChange={handleChange}>
        <Editable
          renderElement={renderElement}
          renderLeaf={Leaf}
          decorate={myDecorator}
          className="box-border w-full h-full border border-[#d9d9d9] border-solid rounded p-4 focus:outline-none focus:border-[#055AFF] leading-6 font-[14px]"
        />
      </Slate>
      {dropdown.visible && (
        <div
          className="dropdown"
          style={{
            position: "absolute",
            left: dropdown.position.left,
            top: dropdown.position.top,
            zIndex: 1000,
            background: "#fff",
            border: "1px solid #eee",
            borderRadius: 4,
            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
            minWidth: 120
          }}
        >
          {dropdown.options.map((item, idx) => (
            <div
              key={item}
              className={idx === dropdown.index ? "active" : ""}
              style={{
                padding: "4px 12px",
                background: idx === dropdown.index ? "#e6f7ff" : "#fff",
                cursor: "pointer"
              }}
              onMouseDown={(e) => {
                e.preventDefault();
                // 这里调用插入IndicatorTag的函数
                insertIndicator({ title: item, editor, setDropdown });
              }}
            >
              {item}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default IndicatorEditor;
