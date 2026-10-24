import React, { useState, useCallback, useRef, useEffect } from "react";
import { Tooltip, Button, Input } from "antd";
import type { DataNode } from "antd/es/tree";
import { EllipsisOutlined, PlusOutlined } from "@ant-design/icons";
import { ITreeNode } from "../common/type.ts";
import type { InputRef } from "antd/es/input";
import "../common/style.less";
import { set } from "lodash";
interface Ipros {
  nodeType: "ANALYSIS" | "SECTION";
  node: DataNode;
  editingKey: string | null;
  // addingParentKey: string | null;
  clickNode: (key?: string) => void;
  addNode: () => void;
  deleteNode: () => void;
  renameNode: (key: string, name: string) => void;
  setEditingKey: (key: string | null) => void;
  duplicateNode?: (node: ITreeNode) => void;
}

function useClickHandler({ onClick, onDoubleClick, delay = 300 }) {
  const clickCountRef = useRef(0);
  const timerRef = useRef(null);

  return useCallback(
    (...args) => {
      clickCountRef.current += 1;

      if (clickCountRef.current === 1) {
        timerRef.current = setTimeout(() => {
          if (clickCountRef.current === 1 && onClick) {
            onClick(...args);
          }
          clickCountRef.current = 0;
        }, delay);
      } else {
        clearTimeout(timerRef.current);
        if (onDoubleClick) {
          onDoubleClick(...args);
        }
        clickCountRef.current = 0;
      }
    },
    [onClick, onDoubleClick, delay]
  );
}
const AnalysisTreeNode = ({
  node,
  nodeType,
  editingKey,
  // addingParentKey,
  clickNode,
  addNode,
  deleteNode,
  renameNode,
  setEditingKey,
  duplicateNode
}: Ipros) => {
  const [visible, setVisible] = useState(false);
  const inputRef = useRef<InputRef>(null);

  // 自动聚焦输入框
  useEffect(() => {
    if (editingKey && inputRef.current) {
      inputRef.current.focus();
    }
  }, [editingKey]);

  // 渲染节点操作菜单
  const renderMenu = useCallback(
    (nodeKey: string, node: DataNode) => {
      return (
        <>
          <div
            className="text-[#555555] hover:bg-[#F1F5FF] pl-[16px]"
            onClick={(e) => {
              e.stopPropagation();
              setEditingKey(nodeKey);
              setVisible(false);
            }}
          >
            重命名
          </div>
          {nodeType == "SECTION" && node.title !== "未命名章节" && (
            <div
              className="text-[#555555] hover:bg-[#F1F5FF] pl-[16px]"
              onClick={(e) => {
                e.stopPropagation();
                duplicateNode && duplicateNode(node);
                setVisible(false);
              }}
            >
              复制
            </div>
          )}
          <div
            className="text-[#555555] hover:bg-[#F1F5FF] pl-[16px]"
            onClick={(e) => {
              e.stopPropagation();
              deleteNode();
              setVisible(false);
            }}
          >
            删除
          </div>
        </>
      );
    },
    [addNode, deleteNode, duplicateNode, visible]
  );

  const renderTitleColor = (node: ITreeNode) => {
    if (nodeType == "SECTION" && node.title == "未命名章节") {
      return "#FF3A3A";
    }
    return "#2A2A2A";
  };
  const handleClick = useClickHandler({
    onClick: (e) => {
      if (!node.children || node?.children?.length == 0) {
        e.stopPropagation();
        clickNode(node.key as string);
      } else {
        return;
      }
    },
    onDoubleClick: () => setEditingKey(node.key as string)
  });

  return (
    <>
      {editingKey === node.key ? (
        <Input
          ref={inputRef}
          size="small"
          placeholder="请输入分类名称"
          style={{
            width: "100%",
            paddingLeft: 0 // 去除缩进
          }}
          defaultValue={node.title as string}
          onBlur={(e: any) => {
            const val = e.target.value;
            if (val?.trim().length > 0 && val == node.title) {
              setEditingKey(null);
            } else {
              renameNode(node.key as string, e.target.value);
            }
          }}
          onPressEnter={(e: any) => {
            if (e.target.value == node.title) {
              setEditingKey(null);
            } else {
              renameNode(node.key as string, e.target.value);
            }
          }}
          onClick={(e: any) => e.stopPropagation()}
        />
      ) : (
        <div
          className={`flex justify-between items-center chapter-tree-node`}
          onClick={(e) => {
            if (!node.children || node?.children?.length == 0) {
              e.stopPropagation();
              clickNode(node.key as string);
            } else {
              return;
            }
          }}
          onMouseEnter={(e) => {
            const parentOfParent = e.currentTarget.parentElement?.parentElement;
            if (parentOfParent) {
              parentOfParent.removeAttribute("title");
            }
          }}
        >
          <div
            title={node.title}
            className="break-words text-ellipsis line-clamp-1 w-[calc(100%-50px)]"
            style={{
              color: renderTitleColor(node)
            }}
            onDoubleClick={() => setEditingKey(node.key as string)}
          >
            {node.title}
          </div>
          <div
            className="tree-node-extends"
            style={{
              visibility: visible ? "visible" : "hidden"
            }}
          >
            <Tooltip
              placement="top"
              color={"#fff"}
              arrow={false}
              title={<span className="text-[#2A2A2A]">添加子分类</span>}
            >
              <Button
                type="text"
                size="small"
                className="operate-btn"
                icon={<PlusOutlined width={24} height={24} />}
                disabled={!!editingKey}
                onClick={(e) => {
                  e.stopPropagation();
                  addNode();
                }}
              />
            </Tooltip>
            <Tooltip
              placement="right"
              color={"#fff"}
              arrow={false}
              open={visible}
              onOpenChange={setVisible}
              overlayInnerStyle={{
                padding: 0
              }}
              title={
                <div
                  className="w-[96px] leading-[32px] cursor-pointer py-[8px]"
                  onMouseEnter={(e) => {
                    const parentOfParent =
                      e.currentTarget.parentElement?.parentElement;
                    if (parentOfParent) {
                      parentOfParent.removeAttribute("title");
                    }
                  }}
                >
                  {renderMenu(node.key as string, node)}
                </div>
              }
            >
              <Button
                type="text"
                size="small"
                className="operate-btn ml-[8px]"
                icon={<EllipsisOutlined width={24} height={24} />}
                onClick={(e) => e.stopPropagation()}
              />
            </Tooltip>
          </div>
        </div>
      )}
    </>
  );
};

export default AnalysisTreeNode;
