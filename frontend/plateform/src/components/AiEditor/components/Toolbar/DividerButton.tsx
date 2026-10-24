import { insertNodes } from "@udecode/plate-common";
import { useEditorState } from "@udecode/plate-common/react";
import { HorizontalRulePlugin } from "@udecode/plate-horizontal-rule";
import { Button, Tooltip } from "antd";
import { createRedLineParagraph } from "../editor/plugins/customPlugin/partingLine/redLinePlugin";

// 分割线集合
const lineObj = {
  "red-line": createRedLineParagraph.key,
  hr: HorizontalRulePlugin.key,
  other: HorizontalRulePlugin.key,
};

const DividerButton = ({ format, icon, type }) => {
  const editor = useEditorState();
  const { selection } = editor;

  return (
    <Tooltip title={format}>
      <Button
        size="small"
        style={{ border: 0, background: "transparent", boxShadow: "none" }}
        icon={icon}
        onClick={(event) => {
          event.preventDefault();
          if (editor && selection) {
            insertNodes(editor, {
              type: lineObj[type] || lineObj.other,
              children: [{ text: "" }],
            });
          }
        }}
      />
    </Tooltip>
  );
};

export default DividerButton;
