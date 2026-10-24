import { displayerEditor } from "@root/src/components/AiChat/components/editor/plugins/displayer";
import { deserializeMd } from "@udecode/plate-markdown";
import { Editor } from "@root/src/components/AiChat/components/editor";
import { createPlateEditor, Plate } from "@udecode/plate-common/react";

import { Node } from "slate";
import {
  isMarkdownTableData,
  tableValue
} from "@root/src/components/CommonEditor/ui/tableValue";
import { validateAndFixNodes } from "@root/src/components/CommonEditor/ChatViewEditor";
export const serialize = (nodes: any) => {
  if (
    nodes.length === 1 &&
    nodes[0].children &&
    nodes[0].children.length === 1 &&
    nodes[0].children[0].type === "table"
  ) {
    const { children } = nodes[0].children[0];
    if (children.length) {
      return children
        .map((node: any, i: number) => {
          const str =
            "|" +
            node.children.map((n: any) => Node.string(n)).join("|") +
            " |\n";
          if (i === 0) {
            return (
              str +
              "|" +
              node.children.map((n: any) => " :---: ").join("|") +
              " |\n"
            );
          }
          return str;
        })
        .join("");
    }
    return "";
  }
  return nodes.map((n: any) => Node.string(n)).join("\n");
};

const traverseTree = (tree: any[]) => {
  function traverseTreeNode(node: any) {
    if (node.children && node.children.length > 0) {
      node.children.forEach((child: any, index: any) => {
        if (child.text) {
          if (isMarkdownTableData(child.text)) {
            node.children[index] = tableValue(node.children[0].text)[0];
          }
        }
        traverseTreeNode(child); // 递归遍历子节点
      });
    }
  }

  // 从根节点开始遍历整个树
  tree.forEach((node, index) => {
    traverseTreeNode(node);
  });
};

export function WithPlate({ id, data, className = "", type }: any) {
  const tempEditor = createPlateEditor({
    plugins: [...displayerEditor({}).plugins]
  });

  let deserializedData = deserializeMd(tempEditor, data || "");
  if (type === "table") {
    deserializedData = validateAndFixNodes(deserializedData);
    traverseTree(deserializedData);
  }

  const editor = createPlateEditor({
    ...displayerEditor({}),
    id: id,
    shouldNormalizeEditor: true,
    value: deserializedData
  });

  return {
    element: (
      <Plate editor={editor}>
        <Editor
          readOnly={false}
          className={className}
          maxLength={3000}
          curText={serialize(deserializedData)}
        />
      </Plate>
    ),
    editor
  };
}
