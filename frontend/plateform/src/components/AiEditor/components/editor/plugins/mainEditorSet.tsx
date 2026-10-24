import { withProps } from "@udecode/cn";
import {
  createPlatePlugin,
  ParagraphPlugin,
  PlateElement,
  PlateLeaf
} from "@udecode/plate-common/react";
import { BlockquotePlugin } from "@udecode/plate-block-quote/react";
import {
  CodeBlockPlugin,
  CodeLinePlugin,
  CodeSyntaxPlugin
} from "@udecode/plate-code-block/react";
import { HeadingPlugin } from "@udecode/plate-heading/react";
import { HorizontalRulePlugin } from "@udecode/plate-horizontal-rule/react";
import { LinkPlugin } from "@udecode/plate-link/react";
import { ImagePlugin, MediaEmbedPlugin } from "@udecode/plate-media/react";
import { ExcalidrawPlugin } from "@udecode/plate-excalidraw/react";
import { TogglePlugin } from "@udecode/plate-toggle/react";
import { ColumnPlugin, ColumnItemPlugin } from "@udecode/plate-layout/react";

import {
  MentionPlugin,
  MentionInputPlugin
} from "@udecode/plate-mention/react";
// import {
//   TablePlugin,
//   TableRowPlugin,
//   TableCellPlugin,
//   TableCellHeaderPlugin,
// } from "@udecode/plate-table/react";
import {
  BulletedListPlugin,
  ListItemPlugin,
  ListPlugin,
  NumberedListPlugin,
  TodoListPlugin
} from "@udecode/plate-list/react";
import { DatePlugin } from "@udecode/plate-date/react";
import {
  BoldPlugin,
  ItalicPlugin,
  UnderlinePlugin,
  StrikethroughPlugin,
  CodePlugin,
  SubscriptPlugin,
  SuperscriptPlugin
} from "@udecode/plate-basic-marks/react";
import {
  FontColorPlugin,
  FontBackgroundColorPlugin,
  FontSizePlugin
} from "@udecode/plate-font";
import { HighlightPlugin } from "@udecode/plate-highlight/react";
import { KbdPlugin } from "@udecode/plate-kbd/react";
import { AlignPlugin } from "@udecode/plate-alignment";
import { IndentPlugin } from "@udecode/plate-indent/react";
import { IndentListPlugin } from "@udecode/plate-indent-list/react";
import { LineHeightPlugin } from "@udecode/plate-line-height";
import { AutoformatPlugin } from "@udecode/plate-autoformat/react";

import { ExitBreakPlugin, SoftBreakPlugin } from "@udecode/plate-break/react";
import { NodeIdPlugin } from "@udecode/plate-node-id";
import { ResetNodePlugin } from "@udecode/plate-reset-node/react";
import { DeletePlugin } from "@udecode/plate-select";
import { TrailingBlockPlugin } from "@udecode/plate-trailing-block";
import { CommentsPlugin } from "@udecode/plate-comments/react";
import { DocxPlugin } from "@udecode/plate-docx";
import { CsvPlugin } from "@udecode/plate-csv";
import { MarkdownPlugin } from "@udecode/plate-markdown";
import { JuicePlugin } from "@udecode/plate-juice";
import { HEADING_KEYS } from "@udecode/plate-heading";
import { BlockquoteElement } from "../ui/blockquote-element";
import { CodeBlockElement } from "../ui/code-block-element";
import { CodeLineElement } from "../ui/code-line-element";
import { CodeSyntaxLeaf } from "../ui/code-syntax-leaf";
import { ExcalidrawElement } from "../ui/excalidraw-element";
import { HrElement } from "../ui/hr-element";
// import { ImageElement } from "../ui/image-element";
import { LinkElement } from "../ui/link-element";

import { ToggleElement } from "../ui/toggle-element";
import { ColumnGroupElement } from "../ui/column-group-element";
import { ColumnElement } from "../ui/column-element";
import { HeadingElement } from "../ui/heading-element";
import { MediaEmbedElement } from "../ui/media-embed-element";
import { MentionElement } from "../ui/mention-element";
import { MentionInputElement } from "../ui/mention-input-element";
import { ParagraphElement } from "../ui/paragraph-element";
// import { TableElement } from "../ui/table-element";
// import { TableRowElement } from "../ui/table-row-element";
// import {
//   TableCellElement,
//   TableCellHeaderElement,
// } from "../ui/table-cell-element";
import { TodoListElement } from "../ui/todo-list-element";
import { DateElement } from "../ui/date-element";
import { CodeLeaf } from "../ui/code-leaf";
import { CommentLeaf } from "../ui/comment-leaf";
import { HighlightLeaf } from "../ui/highlight-leaf";
import { KbdLeaf } from "../ui/kbd-leaf";
import { autoformatRules } from "./autofomatRules";
import { HtmlReactPlugin } from "@udecode/plate/react";
import { SelectionMenuPlugin } from "./customPlugin/SelectionMenu";
import AiWriterPlugin, {
  AiWriterInput
} from "./customPlugin/aiWriter/aiWriter";
import {
  createSelectionDeleteLeafPlugin,
  SelectionDeleteLeaf
} from "./customPlugin/selectonDeletePligin";
import {
  createSelectionUnderLineLeafPlugin,
  SelectionUnderLineLeaf
} from "./customPlugin/selectionUnderLinePlugin";
import {
  createReplaceParagraphLeafPlugin,
  ReplaceParagraphLeaf
} from "./customPlugin/replaceParagraph";
import {
  createRedLineParagraph,
  RedLineParagraphElement
} from "./customPlugin/partingLine/redLinePlugin";
import {
  CreateIndexes,
  CREATEINDEXES,
  IndexesElement
} from "./customPlugin/createIndexes";
import { editorEventBus, EDITOR_EVENT_NAME } from "../../../editorEventBus";
import { ListElement } from "../ui/list-element";
import { SpanElement, SpanPlugin } from "./customPlugin/spanPlugin";
import { MermaidElement, mermaidPlugin } from "./customPlugin/mermaidPlugin";
import { CustomImgPlugin, ImgElement } from "./customPlugin/customImgPlugin";
import {
  PageBreakElement,
  PageBreakPlugin
} from "./customPlugin/pageBreakPlugin";
import {
  TableElement,
  tablePlugin
} from "./customPlugin/customTable/tablePlugin";
import {
  TheadElement,
  theadPlugin
} from "./customPlugin/customTable/theadPlugin";
import {
  TbodyElement,
  tbodyPlugin
} from "./customPlugin/customTable/tbodyPlgin";
import { TrElement, trPlugin } from "./customPlugin/customTable/trPlugin";
import { ThElement, thPlugin } from "./customPlugin/customTable/thPlugin";
import { TdElement, tdPlugin } from "./customPlugin/customTable/tdPlugin";
import {
  CustonAlignElement,
  CustonAlignPlugin
} from "./customPlugin/customAlignPlugin";
import { customDeserializeHtml } from "../../../core/operators/help";

// 块级操作按钮HOC
// const withButtonWrapper = (BaseComponent: any) => {
//   return (props: { [x: string]: any; children: any }) => {
//     const { children, ...rest } = props;
//     const { element, editor } = rest;
//     return (
//       <div style={{ position: "relative" }}>
//         {/* 在元素前添加按钮 */}
//         <button
//           onClick={(e) => {
//             const path = ReactEditor.findPath(editor, element);
//             e.stopPropagation(); // 防止冒泡
//             console.log(props, path, "当前的所有内容");
//           }}
//           style={{
//             position: "absolute",
//             top: "5px",
//             left: "-40px",
//             marginRight: "8px",
//             backgroundColor: "lightgray",
//             border: "none",
//             cursor: "pointer",
//           }}
//         >
//           点击
//         </button>
//         <BaseComponent {...rest}>{children}</BaseComponent>
//       </div>
//     );
//   };
// };

export const mainEditorDefaultPlugins = [
  // BlockSelectionPlugin.configure({
  //   options: {
  //     query: {
  //       allow: ["p"],
  //     },
  //     isSelected: (id?: string) => {
  //       console.log("我又没有被执行");
  //       return Boolean(id);
  //     },
  //   },
  // }),
  // myPlugin,
  mermaidPlugin,
  // TablePlugin.configure({
  //   options: {
  //     initialTableWidth: 80,
  //     enableMerging: true,
  //     minColumnWidth: 10,
  //   },
  // }),
  HtmlReactPlugin,
  BlockquotePlugin,
  CodeBlockPlugin,
  ParagraphPlugin,
  HeadingPlugin.configure({
    options: {
      levels: [1, 2, 3, 4, 5, 6]
    }
  }),
  HorizontalRulePlugin,
  LinkPlugin.configure({}),
  // 所有序列化放在这个插件中去做
  MentionPlugin.configure({
    parsers: {
      html: {
        deserializer: {
          parse: customDeserializeHtml
        }
      }
    }
  }),
  BoldPlugin,
  ItalicPlugin,
  UnderlinePlugin,
  StrikethroughPlugin,
  CodePlugin,
  FontColorPlugin,
  FontBackgroundColorPlugin,
  FontSizePlugin,
  HighlightPlugin,
  AlignPlugin.configure({
    inject: { targetPlugins: ["p", "h1", "h2", "h3"] }
  }),
  IndentPlugin.configure({
    inject: { targetPlugins: ["p", "h1", "h2", "h3"] }
  }),
  IndentListPlugin.configure({
    inject: { targetPlugins: ["p", "h1", "h2", "h3"] }
  }),
  LineHeightPlugin.configure({
    inject: {
      nodeProps: {
        defaultNodeValue: 3,
        validNodeValues: [1, 1.2, 1.5, 2, 3]
      },
      targetPlugins: ["p", "h1", "h2", "h3"]
    }
  }),
  AutoformatPlugin.configure({
    options: {
      rules: autoformatRules,
      enableUndoOnDelete: true
    }
  }),
  ResetNodePlugin.configure({
    options: {
      rules: [
        // Usage: https://platejs.org/docs/reset-node
      ]
    }
  }),
  ExitBreakPlugin.configure({
    options: {
      rules: [
        {
          hotkey: "mod+enter"
        },
        {
          before: true,
          hotkey: "mod+shift+enter"
        },
        {
          hotkey: "enter",
          level: 1,
          query: {
            allow: ["li"],
            end: true,
            start: true
          },
          relative: true
        }
      ]
    }
  }),
  NodeIdPlugin,
  DeletePlugin,
  SoftBreakPlugin.configure({
    options: {
      rules: [
        { hotkey: "shift+enter" },
        {
          hotkey: "enter",
          query: {
            allow: [
              "h1",
              "h2",
              "h3",
              "h4",
              "h5",
              "h6",
              "blockquote",
              "td",
              "th"
            ]
          }
        }
      ]
    }
  }),
  TrailingBlockPlugin.configure({
    options: { type: "p" }
  }),
  DocxPlugin,
  CsvPlugin,
  MarkdownPlugin,
  JuicePlugin,
  ListPlugin,
  // ===============自定义插件==================
  // 红色删除线，用于审核删除
  createSelectionDeleteLeafPlugin,
  // 红色背景加下划线，用于审核替换
  createSelectionUnderLineLeafPlugin,
  // 替换后渐变的蓝色
  createReplaceParagraphLeafPlugin,
  // 自定义红线
  createRedLineParagraph,
  // 右键菜单插件
  SelectionMenuPlugin,
  // 润色插件
  AiWriterPlugin,
  // 需要点击的角标,溯源
  CreateIndexes,
  // span
  SpanPlugin,
  // 图片
  CustomImgPlugin,
  // 分页
  PageBreakPlugin,
  // 自定义表格
  tablePlugin,
  theadPlugin,
  tbodyPlugin,
  trPlugin,
  thPlugin,
  tdPlugin,
  CustonAlignPlugin
];
export const mainEditorDefaultComponents = {
  [BlockquotePlugin.key]: BlockquoteElement,
  [CodeBlockPlugin.key]: CodeBlockElement,
  [CodeLinePlugin.key]: CodeLineElement,
  [CodeSyntaxPlugin.key]: CodeSyntaxLeaf,
  [ExcalidrawPlugin.key]: ExcalidrawElement,
  [HorizontalRulePlugin.key]: HrElement,
  [LinkPlugin.key]: LinkElement,
  [TogglePlugin.key]: ToggleElement,
  [ColumnPlugin.key]: ColumnGroupElement,
  [ColumnItemPlugin.key]: ColumnElement,
  [HEADING_KEYS.h1]: withProps(HeadingElement, { variant: "h1" }),
  [HEADING_KEYS.h2]: withProps(HeadingElement, { variant: "h2" }),
  [HEADING_KEYS.h3]: withProps(HeadingElement, { variant: "h3" }),
  [HEADING_KEYS.h4]: withProps(HeadingElement, { variant: "h4" }),
  [HEADING_KEYS.h5]: withProps(HeadingElement, { variant: "h5" }),
  [HEADING_KEYS.h6]: withProps(HeadingElement, { variant: "h6" }),
  [MediaEmbedPlugin.key]: MediaEmbedElement,
  [MentionPlugin.key]: MentionElement,
  [MentionInputPlugin.key]: MentionInputElement,
  [ParagraphPlugin.key]: ParagraphElement,
  // [TablePlugin.key]: TableElement,
  // [TableRowPlugin.key]: TableRowElement,
  // [TableCellPlugin.key]: TableCellElement,
  // [TableCellHeaderPlugin.key]: TableCellHeaderElement,
  [TodoListPlugin.key]: TodoListElement,
  [DatePlugin.key]: DateElement,
  [BoldPlugin.key]: withProps(PlateLeaf, { as: "strong" }),
  [CodePlugin.key]: CodeLeaf,
  [CommentsPlugin.key]: CommentLeaf,
  [HighlightPlugin.key]: HighlightLeaf,
  [ItalicPlugin.key]: withProps(PlateLeaf, { as: "em" }),
  [KbdPlugin.key]: KbdLeaf,
  [StrikethroughPlugin.key]: withProps(PlateLeaf, { as: "s" }),
  [SubscriptPlugin.key]: withProps(PlateLeaf, { as: "sub" }),
  [SuperscriptPlugin.key]: withProps(PlateLeaf, { as: "sup" }),
  [UnderlinePlugin.key]: withProps(PlateLeaf, { as: "u" }),
  [BulletedListPlugin.key]: withProps(ListElement, { variant: "ul" }),
  [NumberedListPlugin.key]: withProps(ListElement, { variant: "ol" }),
  [ListItemPlugin.key]: withProps(PlateElement, { as: "li" }),
  [CustomImgPlugin.key]: ImgElement,
  [CustonAlignPlugin.key]: CustonAlignElement,
  // ========================自定义components=================
  // mermai语法支持
  [mermaidPlugin.key]: MermaidElement,
  // 需要点击的角标,溯源
  [CREATEINDEXES]: withProps(IndexesElement, {
    className:
      "w-[14px] h-[14px] bg-[#E1EBFF] rounded-full text-[#055AFF] text-[10px] cursor-pointer",
    onClick: (data) => {
      editorEventBus.emit(EDITOR_EVENT_NAME.CLICKRETRIEVE, data);
    }
  }),
  // 红色删除线，用于审核删除功能
  [createSelectionDeleteLeafPlugin.key]: SelectionDeleteLeaf,
  // 红色背景leaf用于审核替换功能
  [createSelectionUnderLineLeafPlugin.key]: SelectionUnderLineLeaf,
  // 替换后,渐变的蓝色
  [createReplaceParagraphLeafPlugin.key]: ReplaceParagraphLeaf,
  // 润色插件
  [AiWriterPlugin.key]: AiWriterInput,
  // 自定义红线
  [createRedLineParagraph.key]: RedLineParagraphElement,
  // span标签
  [SpanPlugin.key]: SpanElement,
  // 分页
  [PageBreakPlugin.key]: PageBreakElement,
  // 自定义表格相关
  [tablePlugin.key]: TableElement,
  [theadPlugin.key]: TheadElement,
  [tbodyPlugin.key]: TbodyElement,
  [trPlugin.key]: TrElement,
  [thPlugin.key]: ThElement,
  [tdPlugin.key]: TdElement
};
