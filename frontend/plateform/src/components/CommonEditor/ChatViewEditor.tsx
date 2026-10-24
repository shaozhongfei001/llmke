/* eslint-disable react-refresh/only-export-components */
import { deserializeMd } from "@udecode/plate-markdown";
import { createPlateEditor } from "@udecode/plate-common/react";
import { displayerEditor } from "./plugins/displayer";
import { isMarkdownTableData, tableValue } from "./ui/tableValue";
import { Plate } from "@udecode/plate-common/react";
import { Editor } from ".";
import React, { useMemo } from "react";
import { CaretDownOutlined, CaretRightOutlined } from "@ant-design/icons";
import {
  contentARegex,
  replacedRetrive,
  replaceRetriveReg,
  RETRIVE_TAG,
  startARegex
} from "./constant";
import { useState } from "react";

let isTable = false;

export const validateAndFixNodes = (nodes: any) => {
  const fixNode = (node: any) => {
    if (node.children && node.children.length === 0) {
      node.children = [{ text: "" }];
    } else if (node.children) {
      node.children = node.children.map(fixNode);
    }
    return node;
  };

  return nodes.map(fixNode);
};

const traverseTreeTable = (tree: any[], answer: any, status: any) => {
  function traverseTreeNode(node: any) {
    if (node.children && node.children.length > 0) {
      node.children.forEach((child: any, index: any) => {
        if (child.text && status !== 1 && isMarkdownTableData(child.text)) {
          node.children[index] = tableValue(node.children[0].text)[0];
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

function traverseTableText(node: any, tempEditor: any) {
  if (node.children && node.children.length > 0) {
    node.children.forEach((child: any, index: any) => {
      if (child.text) {
        const res = deserializeMd(tempEditor, child.text);
        node.children[index] = res[0];
      } else {
        traverseTableText(child, tempEditor);
      }
    });
  }
}

const traverseTreeTableAndMd = (tempEditor: any, text: string, status: any) => {
  if (text && status !== 1 && isMarkdownTableData(text)) {
    const tData = tableValue(text)[0];
    isTable = true;
    if (tData.children?.length) {
      tData.children.forEach((node: any, index: number) => {
        traverseTableText(node, tempEditor);
      });
    }
    return tData;
  } else {
    let r = deserializeMd(tempEditor, text);
    r = validateAndFixNodes(r);
    return r;
  }
};

const traverseTreeRetrive = (
  tree: any[],
  answer: any,
  status: any,
  tempEditor: any
) => {
  const map = new Map();
  (answer?.reference || []).forEach((item: any) => {
    item.contents.forEach((c: any) => {
      map.set(c.id, { ...item, mark: c.mark });
    });
  });
  function traverseTreeNode(node: any) {
    if (node.children && node.children.length > 0) {
      const deleteA: number[] = [];
      node.children.forEach((child: any, index: any) => {
        if (!child.text) {
          traverseTreeNode(child);
          return;
        }
        if (
          child.text &&
          child.text.indexOf(RETRIVE_TAG) > -1 &&
          node.children[0].text !== undefined
        ) {
          const allText = node.children.reduce((pre: any, cur: any) => {
            if (cur.bold) {
              return `${pre}**${cur.text}**`;
            } else if (cur.type === "a") {
              if (cur?.children?.length) {
                return `${pre}[${cur.children[0].text}](${cur.url})`;
              }
              return `${pre}[${cur.url}](${cur.url})`;
            }
            return pre + cur.text;
          }, "");
          let dealedText = allText.replaceAll(
            replaceRetriveReg,
            replacedRetrive
          );
          dealedText = deserializeMd(tempEditor, dealedText);
          node.children = dealedText;
        } else if (
          child.text.indexOf("<retrive-tag") > -1 ||
          child.text === "</retrive-tag>"
        ) {
          deleteA.push(index);
        } else if (
          child.text.match(contentARegex) &&
          deleteA[deleteA.length - 1] === index - 1 &&
          node.children?.[0]?.text !== undefined
        ) {
          const text = child.text.match(contentARegex)[0];
          const regex = /\[(.*?)\]/;
          const match = text.match(regex);
          if (match) {
            const idRegex = /id="(\d+)"/;
            const matchId = node.children[index - 1].text.match(idRegex);
            if (matchId) {
              const id = matchId[1];
              const curR = map.get(id);
              node.children[index] = {
                type: "retrive-tag",
                id,
                curReferentce: curR || {},
                children: [{ text: curR?.mark || "" }]
              };
            }
          }
        }
        traverseTreeNode(child); // 递归遍历子节点
      });
      const c = node.children.filter((item: any, index: any) => {
        return !deleteA.includes(index);
      });
      if (c.length) {
        node.children = c;
      } else {
        node.type = "text";
        node.children = [{ text: "" }];
      }
    }
  }

  // 从根节点开始遍历整个树
  tree.forEach((node, index) => {
    traverseTreeNode(node);
  });
};

export function WithPlate(props: any) {
  const { data } = props;
  const { thinkContent, content, finish } = getContentAfterThinkTag(
    data.content || ""
  );

  return (
    <>
      {thinkContent && (
        <ThinkPlate {...props} content={thinkContent || ""} finish={finish} />
      )}
      {content && <SubPlate {...props} content={content || ""} />}
    </>
  );
}

const ThinkPlate = (props: any) => {
  const [open, setOpen] = useState(true);
  return (
    <div className="bg-[#F8F8F8] !text-[#808080] px-[8px] py-[8px] rounded-[4px] mb-[10px]">
      <div
        className="flex cursor-pointer"
        onClick={() => {
          setOpen(!open);
        }}
      >
        {open ? <CaretDownOutlined /> : <CaretRightOutlined />}
        <div className="ml-[8px]">
          {props.finish
            ? `已深度思考${
                props.data.respTime
                  ? `(用时${Math.round(props.data.respTime / 1000)}秒)`
                  : ""
              }`
            : "思考中..."}
        </div>
      </div>
      <div style={{ display: open ? "block" : "none" }}>
        <SubPlate
          {...props}
          className={`${props.className} bg-[#F8F8F8] !text-[#808080]`}
        />
      </div>
    </div>
  );
};

const SubPlate = ({
  id,
  data,
  content,
  clickIndexes,
  className,
  status,
  imgClassName
}: any) => {
  const tempEditor = createPlateEditor({
    plugins: [...displayerEditor({}).plugins]
  });
  const result = content
    .replace(/\n\n(\d+\.) /g, "\n$1 ")
    .replace(/\n - /g, "\n    - ");
  const splitDatas = (result || "").split("\n\n");
  const deserializedData: any = [];
  isTable = false;
  splitDatas.forEach((text: any) => {
    const r = traverseTreeTableAndMd(tempEditor, text, status);
    Array.isArray(r) ? deserializedData.push(...r) : deserializedData.push(r);
  });
  // let deserializedData = deserializeMd(tempEditor, content || "");
  // deserializedData = validateAndFixNodes(deserializedData);

  // traverseTreeTable(deserializedData, data, status);
  traverseTreeRetrive(deserializedData, data, status, tempEditor);
  traverseTreeRetrive(deserializedData, data, status, tempEditor);

  const editor = createPlateEditor({
    ...displayerEditor({ clickIndexes, imgClassName }),
    id,
    shouldNormalizeEditor: isTable,
    value: deserializedData
  });
  return (
    <Plate editor={editor}>
      <Editor readOnly className={className} />
    </Plate>
  );
};

function getContentAfterThinkTag(text: string) {
  if (text.indexOf("<think>") > -1) {
    if (text.indexOf("</think>") > -1) {
      const closedThinkRegex = /<think>([\s\S]*?)<\/think>([\s\S]*)/s;
      const match = text.match(closedThinkRegex);
      if (match) {
        return {
          thinkContent: match[1],
          content: match[2],
          finish: true
        };
      } else {
        return {
          thinkContent: "",
          content: text,
          finish: true
        };
      }
    } else {
      const closedThinkRegex2 = /<think>(.*?)(?=<|\s*$)/s;
      const match2 = text.match(closedThinkRegex2);
      return { thinkContent: match2?.[1] || "", content: "" };
    }
  } else {
    return {
      thinkContent: "",
      content: text
    };
  }
}
