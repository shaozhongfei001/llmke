import {
  AlignCenterOutlined,
  AlignLeftOutlined,
  AlignRightOutlined,
  FontSizeOutlined,
  MinusOutlined,
  UploadOutlined
} from "@ant-design/icons";
// import {useEdito} from  '@udecode/plate-core'
import { ParagraphPlugin, useEditorState } from "@udecode/plate-common/react";
import { Button, Col, Divider, Flex, Row } from "antd";
import BlockButton from "./BlockButton";
import ColorPicker from "./ColorPicker";
import CustomSelect from "./CustomSelect";
import DividerButton from "./DividerButton";
import HistoryButton from "./HistoryButton";
import ListButton from "./ListButton";
import MarkButton from "./MarkButton";
import { cn } from "@udecode/cn";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  UndoIcon,
  RedoIcon,
  BoldIcon,
  ItalicIcon,
  UnderlineIcon,
  StrikethroughIcon,
  ColorIcon,
  BgcColorIcon,
  OrderedListIcon,
  UnorderedListIcon,
  AlignIcon,
  LineHeightIcon,
  CodeIcon,
  DividerIcon
} from "../icons";
import {
  HEADING_KEYS,
  HEADING_LEVELS,
  HeadingPlugin
} from "@udecode/plate-heading";
import { useGlobalOperators } from "../../core/operators/useGlobalOperators";
import { cva } from "class-variance-authority";
import { useStateStore } from "../../core/states/useStateStore";
import { EDITOR_EVENT_NAME, editorEventBus } from "../../editorEventBus";
import PartingLineSelect from "./PartingLineSelect";
import { Editor } from "slate";
import { EditorType } from "../../@types/sys";

const editorVariants = cva(
  cn(" bg-slate-50 !text-[#555555] box-border", " z-50"),
  {
    defaultVariants: {
      withCompareEditor: false
    },
    variants: {
      withCompareEditor: {
        true: " min-w-[460px] max-w-[580px]  h-[45px]",
        false: "relative w-full h-[45px] mx-auto"
      }
    }
  }
);
const alignOptions = [
  { value: "left", label: "左对齐", icon: <AlignLeftOutlined /> },
  { value: "center", label: "居中对齐", icon: <AlignCenterOutlined /> },
  { value: "right", label: "右对齐", icon: <AlignRightOutlined /> }
];

const headingOptions = [
  // HEADING_KEYS,HEADING_LEVELS
  { value: ParagraphPlugin.key, label: "正文" },
  { value: HEADING_LEVELS[0], label: "标题 1" },
  { value: HEADING_LEVELS[1], label: "标题 2" },
  { value: HEADING_LEVELS[2], label: "标题 3" },
  { value: HEADING_LEVELS[3], label: "标题 4" },
  { value: HEADING_LEVELS[4], label: "标题 5" }
];

const fontSizeOptions = [
  { value: 12, label: "12" },
  { value: 14, label: "14" },
  { value: 16, label: "16" },
  { value: 18, label: "18" },
  { value: 20, label: "20" },
  { value: 22, label: "22" }
];

const lineHeightOptions = [
  { value: 1, label: "1" },
  { value: 1.5, label: "1.5" },
  { value: 2, label: "2" },
  { value: 3, label: "3" }
];

const letterSpaceOptions = [
  { value: "2px", label: "1" },
  { value: "4px", label: "2" },
  { value: "6px", label: "3" },
  { value: "8px", label: "4" }
];

interface IToolbar {
  toolbarEvents?: () => any;
  className?: string;
  isScrolled?: boolean;
  dynamicWidth?: number;
}

export const Toolbar = (props: IToolbar) => {
  const { projectData, editorType } = useStateStore();
  const isPreview = useMemo(() => {
    return editorType === EditorType.Preview;
  }, [editorType]);
  // 处理上传
  const handleFileChange = (event: any) => {
    const file = event.target.files[0];
    editorEventBus.emit(EDITOR_EVENT_NAME.UPLOADFILE, file);
    setRefresh((refresh) => refresh + 1);
  };
  const [refresh, setRefresh] = useState(0);
  return (
    <div
      className={cn(
        "w-full h-[40px] absolute z-50",
        "bg-slate-50 !text-[#555555] box-border",
        {
          "cursor-not-allowed": isPreview
          // "opacity-50": isPreview
        }
      )}
      onClick={(event) => {
        if (isPreview) {
          // 阻止事件冒泡
          event.stopPropagation();
        }
      }}
    >
      <div className="editor-tools w-full overflow-x-hidden flex justify-center items-center gap-x-1">
        <Flex align="center" justify="center">
          {projectData.article_type === "0" ||
            (projectData.articleTypeKey === "normal" && (
              <Button
                size="small"
                type="link"
                className="text-[#555] cursor-pointer text-[12px]"
              >
                <input
                  type="file"
                  accept=".doc,.docx"
                  className="w-full h-full absolute top-0 left-0 opacity-0 cursor-pointer"
                  onChange={handleFileChange}
                  // 通过key处理两次选择一样的文件，不触发onChange的问题
                  key={refresh}
                />
                <UploadOutlined className="-mr-[6px] cursor-pointer" />
                <span className="mt-[2px]">上传</span>
              </Button>
            ))}
        </Flex>
        <Divider type="vertical" style={{ borderColor: "#dedede" }} />
        <HistoryButton format="undo" icon={<UndoIcon />} />
        <HistoryButton format="redo" icon={<RedoIcon />} />
        <Divider type="vertical" style={{ borderColor: "#dedede" }} />
        <MarkButton format="bold" title="加粗" icon={<BoldIcon />} />
        <MarkButton format="italic" title="斜体" icon={<ItalicIcon />} />
        <MarkButton
          format="underline"
          title="下划线"
          icon={<UnderlineIcon />}
        />
        <MarkButton
          format="strikethrough"
          title="删除线"
          icon={<StrikethroughIcon />}
        />
        <Divider type="vertical" style={{ borderColor: "#dedede" }} />
        <CustomSelect width={85} format="head" options={headingOptions} />
        <CustomSelect width={65} format="fontSize" options={fontSizeOptions} />
        <Divider type="vertical" style={{ borderColor: "#dedede" }} />

        <ColorPicker format="color" icon={<ColorIcon />} />
        <ColorPicker format="backgroundColor" icon={<BgcColorIcon />} />
        <Divider type="vertical" style={{ borderColor: "#dedede" }} />
        <ListButton format="ol" title="有序列表" icon={<OrderedListIcon />} />
        <ListButton format="ul" title="无序列表" icon={<UnorderedListIcon />} />
        <CustomSelect format="align" options={alignOptions} />
        {/* <IndentButton format="indent" icon={<MenuUnfoldOutlined />} />
        <IndentButton format="outdent" icon={<MenuFoldOutlined />} /> */}
        {/* <CustomSelect format="lineHeight" options={lineHeightOptions} icon={<LineHeightIcon />} /> */}
        <CustomSelect
          format="letterSpace"
          options={letterSpaceOptions}
          icon={<FontSizeOutlined />}
        />
        {/* <MarkButton format="highlight" icon={<HighlightOutlined />} /> */}
        <Divider type="vertical" style={{ borderColor: "#dedede" }} />
        {/* <BlockButton format="code" title="代码块" icon={<CodeIcon />} /> */}
        {/* 红头分割线 */}
        <PartingLineSelect />
        {/* <DividerButton
          format="红头文件分割线"
          type="red-line"
          icon={<MinusOutlined style={{ color: "red" }} />}
        /> */}
        <DividerButton format="分割线" type="hr" icon={<DividerIcon />} />
        <Divider type="vertical" style={{ borderColor: "#dedede" }} />
        {/* <BlockButton format="table" icon={<TableOutlined />} /> */}
      </div>
      {/* 遮罩，预览模式不让使用 */}
      {isPreview && (
        <div
          className={cn(
            "w-full h-[45px] absolute top-0 left-0 cursor-not-allowed bg-white",
            {
              "opacity-50": isPreview
            }
          )}
          onClick={(event) => {
            if (isPreview) {
              // 阻止事件冒泡
              event.stopPropagation();
            }
          }}
        ></div>
      )}
    </div>
  );
};
