import {
  createPlatePlugin,
  PlatePlugin,
  useEditorState
} from "@udecode/plate/react";
import { useEffect, useState } from "react";
import { isEnd, Path, Range, Element, Node } from "slate";
import { ReactEditor } from "slate-react";
import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import { useStateStore } from "../../../../core/states/useStateStore";
import { EditorStatus, ModueEnum } from "../../../../@types/sys";
import { insertNodes, select } from "@udecode/plate";
import { useMouduleOperators } from "../../../../core/operators/useMouduleOperators";
import { uid } from "uid";
// import AiPhoto from "../../../assets/img/aiphoto.png";
import AiPhoto from "@/assets/img/aiRobit.png";
import { Divider, message } from "antd";
import copy from "copy-to-clipboard";

const isSelectionInTable = (editor: any, selection: Range | null): boolean => {
  if (!selection || Range.isCollapsed(selection)) {
    return false; // 如果没有选区或选区是折叠的，直接返回 false
  }

  // 定义表格相关的节点类型
  const tableNodeTypes = ["table", "tr", "td", "th", "thead", "tbody"];
  // 获取选区的起点和终点路径
  const { anchor, focus } = selection;
  const from =
    Path.compare(anchor.path, focus.path) === -1 ? anchor.path : focus.path; // 起点路径
  const to =
    Path.compare(anchor.path, focus.path) === 1 ? anchor.path : focus.path;
  // 遍历选区中的所有节点
  for (const [node, path] of Node.nodes(editor, { from, to })) {
    if (Element.isElement(node)) {
      // 如果当前节点是表格相关类型，直接返回 true
      if (tableNodeTypes.includes(node.type)) {
        return true;
      }

      // 递归向上检查祖先节点
      // let currentPath = path;
      // while (currentPath.length > 0) {
      //   currentPath = Path.parent(currentPath); // 获取父路径
      //   const parentNode = Node.get(editor, currentPath);
      //   if (
      //     Element.isElement(parentNode) &&
      //     tableNodeTypes.includes(parentNode.type)
      //   ) {
      //     return true; // 如果找到表格相关的祖先节点，返回 true
      //   }
      // }
    }
  }

  return false; // 如果遍历完没有找到表格相关节点，返回 false
};

enum Actions {
  Feedback = "feedback"
}

const getLastElementPathFromSelection = (editor) => {
  const { selection } = editor;

  if (!selection || Range.isCollapsed(selection)) {
    return null; // 如果没有选区或者选区是折叠的
  }

  let lastElementPath = null;
  // 遍历选区中的所有节点,找到选区最后的最内层element节点
  for (const [node, path] of editor.nodes({ at: selection, reverse: true })) {
    const isDeepNode =
      Element.isElement(node) &&
      node.children &&
      node.children.every((child) => !Element.isElement(child));

    if (isDeepNode) {
      lastElementPath = path; // 更新最后一个元素节点的路径
      break;
    }
  }

  return lastElementPath; // 返回选区中的最后一个元素节点的路径
};

export const SelectionMenuPlugin: PlatePlugin = createPlatePlugin({
  key: "selectionMenu",
  handlers: {
    onSelect: ({ editor }) => {
      const { selection } = editor;
      if (selection && !Range.isCollapsed(selection)) {
        // 显示菜单逻辑
        // 这里可以设置一个状态来控菜单的显示
      }
    }
  }
});

const getValidInsertPath = (editor, path) => {
  const isLastNode = Path.equals(path, [editor.children.length - 1]);
  if (isLastNode) return [editor.children.length];

  const nextPath = Path.next(path);
  const isVaildPath = Node.has(editor, nextPath);
  if (isVaildPath) {
    const node = Node.get(editor, nextPath);
    // 是否为元素节点
    if (Element.isElement(node)) {
      return nextPath; // 如果是元素节点，返回当前路径
    }

    // 如果不是元素节点，返回父节点的下一个路径
    return Path.next(Path.parent(nextPath));
  } else {
    return getValidInsertPath(editor, Path.parent(nextPath));
  }
};

export const SelectionMenu = ({ open, setOpen, editorRef }) => {
  const editor = useEditorState();
  const { selection } = editor;
  const { projectData, editorManager } = useStateStore();
  const { openFeedback } = useMouduleOperators();
  const [mouseX, setMouseX] = useState(0);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const [timer, setTimer] = useState<any>(null);

  const handleOnFeedback = () => {
    if (!editor) return;
    const { selection } = editor;
    if (!selection || Range.isCollapsed(selection)) {
      return; // 如果没有选区，直接返回
    }
    const output = editor.string(selection as any);
    openFeedback({
      id: uid(8),
      source: output,
      errorType: null,
      // 反馈场景:0-写作1润色 2-扩写3-缩写 4-字词审核 5-敏感词审核
      scene: 4
    });
  };

  const handleOnAiWrit = () => {
    console.log("触发智写");
    if (!editor) return;

    const { selection } = editor;

    if (selection && !Range.isCollapsed(selection)) {
      if (isSelectionInTable(editor, selection)) {
        message.info("不支持对表格内容进行润色");
        return;
      }
      const selectedText = editor.string(selection);

      const path = getLastElementPathFromSelection(editor);
      if (!path) return;

      const { anchor, focus } = selection;

      const isAtBlockEnd = isEnd(
        editor as unknown as any,
        Range.isBackward(selection) ? anchor : focus,
        path
      );

      if (!isAtBlockEnd) {
        // Range.isBackward(selection) 返回true表示 focus 在 anchor 的前面（即选区是向后的），false相反
        editor.splitNodes({ at: Range.isBackward(selection) ? anchor : focus }); // 从选区的尾部进行切割
      }
      console.log();
      insertNodes(
        editor,
        {
          type: "aiwriter",
          children: [],
          isDone: false, // 添加 isDone 属性
          attributes: {
            insertInline: !isAtBlockEnd,
            sourceText: selectedText,
            selection: editor.selection
          }
        },
        { at: getValidInsertPath(editor, path) }
      );
      editor.select(editor.end([]));
      editor.onChange();
    }
  };

  const handleOnCut = () => {
    console.log("触发cut");
    if (!editor) return;

    const { selection } = editor;
    if (!selection || Range.isCollapsed(selection)) {
      return; // 如果没有选区，直接返回
    }
    if (selection && !Range.isCollapsed(selection)) {
      const selectedText = editor.string(selection);
      editor.delete({ at: selection });
      copy(selectedText);
    }
  };
  const handleOnCopy = () => {
    console.log("触发copy");
    if (!editor) return;

    const { selection } = editor;
    if (!selection || Range.isCollapsed(selection)) {
      return; // 如果没有选区，直接返回
    }
    if (selection && !Range.isCollapsed(selection)) {
      const selectedText = editor.string(selection);
      copy(selectedText);
    }
  };

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      setMouseX(event.clientX); // 更新鼠标的 x 坐标
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  useEffect(() => {
    if (
      editorManager.status === EditorStatus.GeneratingFullText ||
      editorManager.status === EditorStatus.ReviewingFullText
    ) {
      return;
    }
    if (!editor) return;
    const { selection } = editor;
    if (selection && !Range.isCollapsed(selection)) {
      if (timer) {
        clearTimeout(timer);
      }
      const newTimer = setTimeout(() => {
        const domRange = ReactEditor.toDOMRange(
          editor as unknown as any,
          selection
        );
        const rect = domRange.getBoundingClientRect();
        const editorRect = editorRef.current.getBoundingClientRect();
        const scrollTop = editorRef.current.scrollTop; // 获取滚动位置
        setPosition({
          top:
            Math.floor(rect.top - editorRect.top) + // 相对于 editorRef 的顶部
            Math.floor(rect.height) + // 减去100的偏移
            Math.floor(scrollTop) -
            120, // 加上滚动位置
          left: mouseX
        });
        setOpen(true);
      }, 380); // 延迟300毫秒
      setTimer(newTimer);
    } else {
      if (timer) {
        clearTimeout(timer);
      }
      setOpen(false);
    }
  }, [editor.selection, editorManager.status]);

  return (
    <DropdownMenuPrimitive.Root open={open} onOpenChange={setOpen}>
      <DropdownMenuPrimitive.Trigger asChild>
        <button
          className="rounded-full opacity-0"
          style={{
            position: "absolute",
            top: position.top,
            left: position.left
          }}
          aria-label="Customise options"
        ></button>
      </DropdownMenuPrimitive.Trigger>
      <DropdownMenuPrimitive.Portal>
        <DropdownMenuPrimitive.Content
          className="min-w-[170px] flex bg-white shadow-[0px_10px_38px_-10px_rgba(22,_23,_24,_0.35),_0px_10px_20px_-15px_rgba(22,_23,_24,_0.2)] will-change-[opacity,transform] data-[side=top]:animate-slideDownAndFade data-[side=right]:animate-slideLeftAndFade data-[side=bottom]:animate-slideUpAndFade data-[side=left]:animate-slideRightAndFade"
          sideOffset={5}
        >
          {projectData.currentModule === ModueEnum.Writing && (
            <DropdownMenuPrimitive.Item className="group text-[14px] text-gray-600 border-none pl-3 py-2 outline-none">
              <div className="flex items-center justify-start">
                <img src={AiPhoto} alt="AI Photo" className="w-5 h-5 mr-2" />
                <span
                  className="p-0 cursor-pointer leading-[22px] hover:bg-[#F2F2F2]"
                  onClick={handleOnAiWrit}
                >
                  智能编辑
                </span>
                <Divider
                  type="vertical"
                  style={{
                    border: "1px solid #dedede"
                  }}
                />
              </div>
            </DropdownMenuPrimitive.Item>
          )}
          {projectData.currentModule === ModueEnum.Review && (
            <DropdownMenuPrimitive.Item className="group text-[14px] text-gray-600 border-none pl-3 py-2 outline-none">
              <div className="flex items-center justify-start">
                <img src={AiPhoto} alt="AI Photo" className="w-5 h-5 mr-2" />
                <span
                  className="p-0 cursor-pointer leading-[22px] hover:bg-[#F2F2F2]"
                  onClick={handleOnFeedback}
                >
                  反馈意见
                </span>
                <Divider
                  type="vertical"
                  style={{
                    border: "1px solid #dedede"
                  }}
                />
              </div>
            </DropdownMenuPrimitive.Item>
          )}
          <DropdownMenuPrimitive.Item className="cursor-pointer group text-[14px] text-gray-600 hover:text-gray-900 py-2 border-none outline-none">
            <span
              onClick={handleOnCopy}
              className="cursor-pointer leading-[22px] hover:bg-[#F2F2F2]"
            >
              复制
            </span>
            <Divider
              type="vertical"
              style={{
                border: "1px solid #dedede"
              }}
            />
          </DropdownMenuPrimitive.Item>
          <DropdownMenuPrimitive.Item className="cursor-pointer group text-[14px] text-gray-600 hover:text-gray-900 pr-3 py-2 border-none outline-none">
            <span
              onClick={handleOnCut}
              className="cursor-pointer leading-[22px] hover:bg-[#F2F2F2]"
            >
              剪切
            </span>
          </DropdownMenuPrimitive.Item>
        </DropdownMenuPrimitive.Content>
      </DropdownMenuPrimitive.Portal>
    </DropdownMenuPrimitive.Root>
  );
};
