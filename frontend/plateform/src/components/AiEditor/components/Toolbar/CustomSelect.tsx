import { ArrowDownOutlined, CaretDownOutlined } from "@ant-design/icons";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  getAboveNode,
  setLineHeight,
  isElement,
  isBlock,
  isCollapsed,
  isNode,
} from "@udecode/plate";
import { AlignPlugin, setAlign } from "@udecode/plate-alignment";
// import { toggleNodeType } from '@udecode/plate-core';

import {
  ParagraphPlugin,
  PlateEditor,
  useEditorState,
} from "@udecode/plate-common/react";
import { Divider, Typography } from "antd";
import React, { useEffect, useState } from "react";
import {
  BaseEditor,
  Editor,
  Node,
  nodes,
  Path,
  Range,
  Transforms,
} from "slate";
// import { setLetterSpace } from './letterSpace';
// import './style.css';
const { Text } = Typography;
interface OptionType {
  value: string | number;
  label: string;
  icon?: React.ReactNode;
}

interface CustomSelectProps {
  options: OptionType[];
  onChange?: (value: string) => void;
  defaultValue?: string;
  width?: number;
  icon?: React.ReactNode;
  format: string;
}

const CustomSelect: React.FC<CustomSelectProps> = ({
  options,
  onChange,
  defaultValue,
  width = 42,
  format,
  icon,
}) => {
  const [selectedValue, setSelectedValue] = useState(options[0].value);
  const editor = useEditorState() as any;
  const { selection } = editor;

  const handleChange = (val: any) => {
    setSelectedValue(val.value);
    switch (format) {
      case "align":
        handleAlignChange(val);
        break;
      case "head":
        handleHeadChange(val);
        break;
      case "fontSize":
        handleFontSizeChange(val);
        break;
      case "lineHeight":
        handleLineHeightChange(val);
        break;
      case "letterSpace":
        handleLetterSpaceChange(val);
        break;
      default:
        onChange && onChange(val);
        return;
    }
  };

  const handleToolbar = () => {
    const nodes = getAboveNode(editor);
    const node = nodes && nodes[0];

    switch (format) {
      case "align":
        // eslint-disable-next-line no-prototype-builtins
        if (node?.hasOwnProperty("align")) {
          const { align }: any = node;
          setSelectedValue(align);
        } else {
          setSelectedValue(options[0].value);
        }
        break;
      case "head":
        // setSelectedValue('h1');
        // eslint-disable-next-line no-prototype-builtins
        if (node?.hasOwnProperty("type")) {
          const { type }: any = node;
          setSelectedValue(type);
        } else {
          setSelectedValue(options[0].value);
        }
        break;
      default:
        return;
    }
  };

  useEffect(() => {
    handleToolbar();
  }, [selection]);
  const handleAlignChange = (e: any) => {
    if (!editor) return;
    setAlign(editor, {
      key: AlignPlugin.key,
      value: e.value,
    });
  };

  const handleHeadChange = (e: any) => {
    if (!editor) return;

    const { selection } = editor;
    if (!selection) return;
    console.log(e);
    const blockType = e.value;

    // 获取选区上方的第一个块级节点
    const nodeEntry = Editor.above(editor, {
      at: selection,
      match: (n) => Editor.isBlock(editor, n),
    });

    if (nodeEntry) {
      const [node, path] = nodeEntry;

      if (selection && Range.isCollapsed(selection) === false) {
        const [startNode, startPath] = Editor.node(
          editor,
          selection.anchor.path
        );
        const [endNode, endPath] = Editor.node(editor, selection.focus.path);

        const startNodeRange = Editor.range(editor, startPath);
        const endNodeRange = Editor.range(editor, endPath);

        const startNodeText = Editor.string(editor, startNodeRange);
        const endNodeText = Editor.string(editor, endNodeRange);

        const selectedText = Editor.string(editor, selection);

        if (Path.equals(startPath, endPath)) {
          if (selectedText === startNodeText) {
            // 获取包含文本节点的块级节点
            const blockNodeEntry = Editor.above(editor, {
              at: startPath,
              match: (n) => Editor.isBlock(editor, n),
            });
            console.log("选区完全包含单个节点");
            console.log("startPath:", startPath, blockNodeEntry);
            if (blockNodeEntry) {
              const [blockNode, blockPath] = blockNodeEntry;
              console.log("Block node:", blockNode);
              // 设置块级节点的类型
              Transforms.setNodes(
                editor,
                { type: "heading" }, // 替换为你想要设置的类型
                { at: blockPath }
              );
            } else {
              console.log("未找到块级节点");
            }
          } else {
            console.log("选区在单个节点内，但不完全包含");
            //用这个选取建立一个新的element
          }
        } else {
          console.log("跨多个节点，无需更多判断");
        }
      } else {
        console.log("没有选中任何文本或选区是折叠的");
      }
      console.log(editor.children);
      // 如果是完整的节点，替换节点类型
      //Transforms.setNodes(editor, { type: blockType }, { at: path });

      // 如果不是完整的节点，插入一个新的标题节点
      // Transforms.insertNodes(editor, { type: blockType, children: [{ text: '' }] }, { at: path });

      // 如果没有找到上方的块级节点，插入一个新的标题节点
      //Transforms.insertNodes(editor, { type: blockType, children: [{ text: '' }] });
    }
  };

  const handleFontSizeChange = (e: any) => {
    if (!editor) return;
    const { selection } = editor;
    if (selection) {
      editor.addMark(`fontSize`, e.value);
    }
  };

  const handleLineHeightChange = (e: any) => {
    if (!editor) return;
    const { selection } = editor;
    if (selection) {
      setLineHeight(editor, {
        value: e.value,
      });
    }
  };

  const handleLetterSpaceChange = (e: any) => {
    if (!editor) return;
    console.log(e);
    // setLetterSpace(editor, {
    //   value: e.value,
    // });
  };

  const selectedOption =
    options.find((option) => option.value === selectedValue) ?? options[0];

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <div
          className="flex gap-x-[3px] h-[45px] cursor-pointer 
        items-center justify-start px-[3px] "
        >
          <div className="text-center truncate text-[12px]">
            {icon ? icon : selectedOption?.icon || selectedOption?.label}
          </div>
          {/* <ArrowDownOutlined size={10} className="text-[8px] font-light" /> */}
          <CaretDownOutlined className="text-[10px]" />
        </div>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="start"
          className="bg-white z-[99] shadow w-[120px]"
          sideOffset={-9}
          defaultValue={selectedValue}
        >
          {options &&
            options.map((i, index) => {
              return (
                <div key={index}>
                  <DropdownMenu.Item
                    className="flex cursor-pointer text-[12px] justify-between w-full px-3 box-border py-2  hover:bg-sky-100 hover:border-none hover:ring-none"
                    onSelect={() => handleChange(i)}
                    key={i.value}
                  >
                    <div className=" opacity-70 hover:opacity-100 ">
                      {i.label}
                    </div>
                    <div> {i.icon ? i.icon : ""} </div>
                  </DropdownMenu.Item>
                  {/* {index + 1 != options.length && (
                    <Divider
                      key={index}
                      style={{
                        margin: '0',
                        padding: '0 0',
                      }}
                    />
                  )} */}
                </div>
              );
            })}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
};

export default CustomSelect;
