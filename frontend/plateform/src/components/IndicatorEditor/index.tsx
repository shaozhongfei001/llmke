import React, { useEffect, useMemo, useRef, useState } from "react";
import "./indicatorTag.css";
import { useQuery } from "@tanstack/react-query";
import axios$ from "@root/src/apis";
import {
  autoAddSpaceForOperator,
  extractFormulaFromHtml,
  flattenTree,
  formatFormulaWithDetail,
  formulaToHtml,
  insertSpaces
} from "./util";
import ReactDOM from "react-dom";
import IndicatorCard from "../IndicatorCard";
import { message, Popover, Tooltip } from "antd";
import {
  useSplitLayout,
  EventTypes
} from "@/components/SplitLayout/SplitLayoutContext";

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
  "}",
  "÷"
];
interface Iprops {
  indicators: string[];
}
const IndicatorEditor = ({ indicators }: Iprops) => {
  const editorRef = React.useRef<HTMLDivElement>(null);

  const queryAllIndicator = useQuery({
    queryKey: ["queryIndicatorDetail"],
    queryFn: () => axios$.get(`/cecProxy/dw/indicator`).then((res) => res?.data)
  });

  const allIndicator = useMemo(() => {
    if (!queryAllIndicator.data) return [];
    return flattenTree(queryAllIndicator.data, "subIndicators");
  }, [queryAllIndicator.data]);

  // 新增：下拉选中索引
  const [selectedIndex, setSelectedIndex] = React.useState(0);

  // 下拉框状态
  const [dropdown, setDropdown] = React.useState<{
    visible: boolean;
    options: any[];
    position: { left: number; top: number };
  }>({
    visible: false,
    options: [],
    position: { left: 0, top: 0 }
  });

  // hover到指标上面
  const [hoveredTag, setHoveredTag] = React.useState<{
    item: any;
    position: { right: number; top: number };
  } | null>(null);

  const initDropdown = () => {
    setDropdown({
      visible: false,
      options: [],
      position: { left: 0, top: 0 }
    });
  };

  // 获取光标位置的辅助函数
  const getCaretPosition = () => {
    const selection = window.getSelection();
    if (!selection || !editorRef.current) return { left: 0, top: 0 };
    const range = selection.getRangeAt(0).cloneRange();
    const rects = range.getClientRects();
    if (rects.length > 0) {
      const rect = rects[0];
      return { left: rect.left, top: rect.bottom };
    }
    // fallback: 编辑器左上角
    const editorRect = editorRef.current.getBoundingClientRect();
    return { left: editorRect.left, top: editorRect.bottom };
  };

  // 键盘事件,用于进行提示指标的选取
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const selection = window.getSelection();
    if (!selection || !editorRef.current) return;

    // 新增：下拉菜单键盘操作
    if (dropdown.visible && dropdown.options.length > 0) {
      if (e.key === "ArrowDown") {
        setSelectedIndex((prev) => (prev + 1) % dropdown.options.length);
        e.preventDefault();
        return;
      }
      if (e.key === "ArrowUp") {
        setSelectedIndex(
          (prev) =>
            (prev - 1 + dropdown.options.length) % dropdown.options.length
        );
        e.preventDefault();
        return;
      }
      if (e.key === "Enter") {
        insertIndicatorTagAtCursor(dropdown.options[selectedIndex]);
        setDropdown({ ...dropdown, visible: false });
        e.preventDefault();
        return;
      }
    }

    // 判断当前选中节点是否为 Operator
    const anchorNode = selection.anchorNode;
    switch (e.key) {
      case "Backspace":
      case "Delete":
        if (
          anchorNode &&
          anchorNode.parentElement?.getAttribute("data-operator") === "true"
        ) {
          // 删除整个 Operator 节点
          anchorNode.parentElement.remove();
          e.preventDefault();
        }
        break;
      default:
        break;
    }
  };

  // 编辑onChange事件，给出智能提示
  const handleInput = (e: React.FormEvent<HTMLDivElement>) => {
    // 获取当前光标位置前的内容
    const selection = window.getSelection();
    if (!selection || !selection.anchorNode) {
      initDropdown();
      return;
    }

    // 获取编辑器内容
    let cursorPos = selection.anchorOffset;
    let node = selection.anchorNode;

    // 只处理文本节点
    if (node.nodeType !== Node.TEXT_NODE) {
      node = node.childNodes[0];
      cursorPos = 0;
    }

    // 如果刚输入了运算符并已插入空格，直接退出，不再走下拉提示
    // if (autoAddSpaceForOperator(node)) {
    //   initDropdown(); // 也可根据需要隐藏下拉
    //   return;
    // }

    const text = e.currentTarget.innerText;
    if (operators.includes(text)) {
      initDropdown();
    } else {
      // 获取当前文本内容
      const textContent = node.textContent || "";
      // 向前查找最近的运算符
      let lastOpIndex = -1;
      for (let i = cursorPos - 1; i >= 0; i--) {
        if (operators.includes(textContent[i]) || textContent[i] == " ") {
          lastOpIndex = i;
          break;
        }
      }
      // 获取从上一个运算符到当前光标的内容
      let searchText = textContent.slice(lastOpIndex + 1, cursorPos).trim();
      searchText = searchText.trim();
      if (searchText.length > 0) {
        // 搜索 allIndicator
        const matched = allIndicator.filter((item) =>
          (item.indicatorName || "--").includes(searchText)
        );
        if (matched.length > 0) {
          setDropdown({
            visible: true,
            options: matched,
            position: getCaretPosition()
          });
          setSelectedIndex(0);
        } else {
          initDropdown();
        }
      } else {
        initDropdown();
      }
    }
  };

  // 插入占位 span 到光标处，替换上一个运算符到光标之间的内容,智能替换
  const insertIndicatorTagAtCursor = (item: any) => {
    const selection = window.getSelection();
    if (!selection || !editorRef.current) return;
    let node = selection.anchorNode;
    let cursorPos = selection.anchorOffset;

    // 只处理文本节点
    if (
      node &&
      node.nodeType !== Node.TEXT_NODE &&
      node.childNodes.length > 0
    ) {
      node = node.childNodes[0];
      cursorPos = 0;
    }
    if (!node || node.nodeType !== Node.TEXT_NODE) return;

    const textContent = node.textContent || "";
    // 查找上一个运算符
    let lastOpIndex = -1;
    for (let i = cursorPos - 1; i >= 0; i--) {
      if (operators.includes(textContent[i])) {
        lastOpIndex = i;
        break;
      }
    }
    const start = lastOpIndex + 1;
    const end = cursorPos;

    // 拆分文本节点
    const range = selection.getRangeAt(0);

    // 替换目标文本为IndicatorTag占位span
    range.setStart(node, start);
    range.setEnd(node, end);
    range.deleteContents();

    // 创建占位span
    const tagSpan = document.createElement("span");
    tagSpan.setAttribute("data-indicator", "true");
    tagSpan.setAttribute("data-indicator-id", item.id); // 新增
    tagSpan.setAttribute("data-cur-index", String(formulaDetail.length)); // 新增
    tagSpan.contentEditable = "false";
    tagSpan.className = "indicator-tag cursor-pointer";
    tagSpan.innerText = item.indicatorName;
    range.insertNode(tagSpan);

    // 插入后恢复光标
    range.setStartAfter(tagSpan);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
    setFormulaDetail((p) => {
      return [
        ...p,
        {
          id: item.id,
          timeRange: ""
        }
      ];
    });

    // 触发input事件，保证状态同步
    editorRef.current.dispatchEvent(new Event("input", { bubbles: true }));
  };

  // 事件委托，整体添加所有指标TAG的hover事件
  // useEffect(() => {
  //   const editor = editorRef.current;
  //   if (!editor) return;

  //   const handleMouseEnter = (e: MouseEvent) => {
  //     const target = e.target as HTMLElement;
  //     if (target.classList.contains("indicator-tag")) {
  //       const rect = target.getBoundingClientRect();
  //       const id = target.getAttribute("data-indicator-id");
  //       const curIndex = target.getAttribute("data-cur-index");
  //       const item = allIndicator.find((i) => String(i.id) === id);

  //       const allWidth = window.innerWidth;
  //       if (item) {
  //         if (curIndex) {
  //           item.curIndex = Number(curIndex);
  //         }
  //         console.log("触发hover事件", item);
  //         setHoveredTag({
  //           item,
  //           position: { right: allWidth - rect.right, top: rect.bottom }
  //         });
  //       }
  //     }
  //   };

  //   // 事件委托，捕获阶段
  //   editor.addEventListener("mouseenter", handleMouseEnter, true);

  //   return () => {
  //     editor.removeEventListener("mouseenter", handleMouseEnter, true);
  //   };
  // }, [editorRef, allIndicator]);

  // // 事件委托，整体添加所有指标TAG的hover事件
  // useEffect(() => {
  //   if (!hoveredTag) return;

  //   const handleMove = (e: MouseEvent) => {
  //     const path = e.composedPath?.() || [];
  //     const isOver = path.some(
  //       (el: any) =>
  //         el?.getAttribute &&
  //         el.getAttribute("data-indicator-id") === String(hoveredTag.item.id)
  //     );
  //     if (!isOver) {
  //       console.log("取消hover事件", isOver, path);
  //       setHoveredTag(null);
  //     }
  //   };

  //   window.addEventListener("mousemove", handleMove);
  //   return () => window.removeEventListener("mousemove", handleMove);
  // }, [hoveredTag]);

  // 用一个ref保存当前hover的tag和卡片
  const hoverAreaRef = useRef<{
    tag: HTMLElement | null;
    card: HTMLElement | null;
  }>({ tag: null, card: null });

  // 监听tag的mouseenter
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    const handleMouseEnter = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.classList.contains("indicator-tag")) {
        const rect = target.getBoundingClientRect();
        const id = target.getAttribute("data-indicator-id");
        const curIndex = target.getAttribute("data-cur-index");
        const item = allIndicator.find((i) => String(i.id) === id);

        if (item) {
          if (curIndex) item.curIndex = Number(curIndex);
          setHoveredTag({
            item,
            position: {
              right: window.innerWidth - rect.right,
              top: rect.bottom
            }
          });

          // 保存当前hover的tag
          hoverAreaRef.current.tag = target;
        }
      }
    };

    editor.addEventListener("mouseenter", handleMouseEnter, true);
    return () =>
      editor.removeEventListener("mouseenter", handleMouseEnter, true);
  }, [editorRef, allIndicator]);

  // 监听全局mousemove，判断鼠标是否在tag或卡片内
  useEffect(() => {
    if (!hoveredTag) return;

    const handleMove = (e: MouseEvent) => {
      const { tag, card } = hoverAreaRef.current;
      const isOverTag = tag && tag.contains(e.target as Node);
      const isOverCard = card && card.contains(e.target as Node);

      if (!isOverTag && !isOverCard) {
        setHoveredTag(null);
        hoverAreaRef.current = { tag: null, card: null };
      }
    };

    window.addEventListener("mousemove", handleMove);
    return () => window.removeEventListener("mousemove", handleMove);
  }, [hoveredTag]);

  // 用于记录期初期末，近几年的数据
  // 时间点和事件范围timePoint，timeRange
  const [formulaDetail, setFormulaDetail] = useState<
    {
      id: number;
      timePoint?: string;
      timeRange?: string;
    }[]
  >([]);

  // 数据改变时刷新页面
  const changeFormulaDetail = ({ curIndex, obj }: any) => {
    setFormulaDetail((p: any) => {
      const newP = [...p];
      newP[curIndex] = { ...p[curIndex], ...obj };
      if (editorRef.current) {
        let str = extractFormulaFromHtml(editorRef.current?.outerHTML || "");
        str = formatFormulaWithDetail(str, newP);
        const { html, indicatorDetailMap } = formulaToHtml(str, allIndicator);
        setFormulaDetail(indicatorDetailMap);
        editorRef.current.innerHTML = html;
      }
      return newP;
    });
    if (!editorRef.current) return;
  };

  // 事件车，向外部发送公式数据
  const { publish, useSubscribe } = useSplitLayout();

  useSubscribe<number>(EventTypes.SAVE_CALCULATOR_CONFIRM, () => {
    let str = extractFormulaFromHtml(editorRef.current?.outerHTML || "");
    str = formatFormulaWithDetail(str, formulaDetail);
    // 去除所有空白字符（包括回车、换行、空格、制表符等），如果还有内容就不处理
    if (str.replace(/\s/g, "") === "") {
      message.warning("公式不能为空");
      return;
    }
    publish(EventTypes.SAVE_CALCULATOR, [str]);
  });

  // 初始化编辑器公式以及期初期末等变量
  useEffect(() => {
    if (
      !allIndicator.length ||
      !indicators ||
      !indicators.length ||
      !editorRef.current
    )
      return;
    const dispalyIndicators = indicators[0];
    const { html, indicatorDetailMap } = formulaToHtml(
      dispalyIndicators,
      allIndicator
    );
    setFormulaDetail(indicatorDetailMap);
    editorRef.current.innerHTML = html;
  }, [editorRef, allIndicator, indicators]);

  // 粘贴,自动识别指标
  const handlePaste = (e: React.ClipboardEvent<HTMLDivElement>) => {
    if (!editorRef.current) return;
    // 去除所有空白字符（包括回车、换行、空格、制表符等），如果还有内容就不处理
    if (editorRef.current.innerText.replace(/\s/g, "") !== "") return;
    e.preventDefault();
    const text = e.clipboardData.getData("text/plain");
    if (!text) return;

    // 公式解析：将匹配到的指标名替换为 $id
    let parsed = text;
    // 按长度倒序，避免短指标名影响长指标名
    const sortedIndicators = [...allIndicator].sort(
      (a, b) => (b.indicatorName?.length || 0) - (a.indicatorName?.length || 0)
    );
    sortedIndicators.forEach((item) => {
      if (item.indicatorName) {
        // 全局替换，避免多次出现
        const reg = new RegExp(
          item.indicatorName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
          "g"
        );
        parsed = parsed.replace(reg, `$${item.id}`);
      }
    });
    parsed = insertSpaces(parsed, operators);
    const { html, indicatorDetailMap } = formulaToHtml(parsed, allIndicator);
    setFormulaDetail(indicatorDetailMap);
    editorRef.current.innerHTML = html;
    message.success("识别完成");
    // 触发input事件，保证状态同步
    editorRef.current.dispatchEvent(new Event("input", { bubbles: true }));
  };

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div
        ref={editorRef}
        className="box-border w-full h-full border border-[#d9d9d9] border-solid rounded p-4 focus:outline-none focus:border-[#055AFF] leading-6 font-[14px]"
        contentEditable
        suppressContentEditableWarning
        tabIndex={0}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        onPaste={handlePaste} // 添加粘贴事件
      ></div>
      {dropdown.visible && dropdown.options.length > 0 && (
        <div
          style={{
            position: "fixed",
            left: dropdown.position.left,
            top: dropdown.position.top,
            zIndex: 1000,
            background: "#fff",
            border: "1px solid #d9d9d9",
            borderRadius: 4,
            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
            padding: 0,
            margin: 0,
            minWidth: 120
          }}
        >
          <div className="text-[#888888] border-0 border-b-[1px] border-[#EEEEEE] border-solid px-[12px] py-[4px]">
            匹配指标:
          </div>
          <ul
            style={{
              listStyle: "none",
              padding: "4px",
              margin: 0,
              maxHeight: "400px",
              overflowY: "auto"
            }}
          >
            {dropdown.options.map((item, idx) => (
              <Popover
                content={<IndicatorCard id={item.id} />}
                key={item.id}
                placement="right"
                arrow={false}
                styles={{
                  body: {
                    padding: 0,
                    boxSizing: "border-box",
                    borderRadius: "8px",
                    width: "364px"
                  }
                }}
              >
                <li
                  key={item.id}
                  style={{
                    padding: "5px 12px",
                    cursor: "pointer",
                    background: idx === selectedIndex ? "#e6f7ff" : undefined
                  }}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    insertIndicatorTagAtCursor(item);
                    setDropdown({ ...dropdown, visible: false });
                  }}
                  // 可加点击事件
                >
                  {item?.indicatorName || "--"}
                </li>
              </Popover>
            ))}
          </ul>
        </div>
      )}
      {hoveredTag &&
        ReactDOM.createPortal(
          <div
            style={{
              position: "fixed",
              right: hoveredTag.position.right,
              top: hoveredTag.position.top,
              zIndex: 2000
            }}
            data-indicator-id={hoveredTag.item.id}
            ref={(el) => (hoverAreaRef.current.card = el)}
          >
            <IndicatorCard
              id={hoveredTag.item.id}
              curIndex={hoveredTag.item.curIndex}
              type="editor"
              changeFormulaDetail={changeFormulaDetail}
              formulaDetail={formulaDetail}
            />
          </div>,
          document.body
        )}
    </div>
  );
};

export default IndicatorEditor;
