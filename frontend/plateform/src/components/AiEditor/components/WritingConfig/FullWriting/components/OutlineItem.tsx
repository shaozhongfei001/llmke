import { Button, Input, Tooltip } from "antd";
import { useState, useRef, useEffect } from "react";
import { DeleteOutlined, EditOutlined } from "@ant-design/icons";
import { outlineChangeTypes } from "./Outlines";
import "./style.less";

interface Iprops {
  node: any;
  depth?: number;
  editNodeId: string | undefined;
  isVersion?: boolean;
  onOutlinesChangeHandler: (type: outlineChangeTypes, node: any) => void;
  editNodeIdChangeHandler: (id: string | undefined) => void;
}

const subPadding = 24;
const OutLineItem = (props: Iprops) => {
  const {
    node,
    depth = 0,
    editNodeId,
    isVersion = false,
    onOutlinesChangeHandler,
    editNodeIdChangeHandler
  } = props;
  const [title, setTitle] = useState<string | undefined>(undefined);
  const iptRef = useRef<any>(null);

  const delNode = (node: any) => () => {
    onOutlinesChangeHandler(outlineChangeTypes.delNode, { node });
  };

  const configSection = (node: any) => () => {
    onOutlinesChangeHandler(outlineChangeTypes.configSection, { node });
  };

  const editNodeTitle = (nodeId: string) => (e: any) => {
    e.stopPropagation();
    if (editNodeId !== nodeId) {
      editNodeIdChangeHandler(nodeId);
    }
    setTimeout(() => {
      if (iptRef.current && iptRef.current.focus) {
        iptRef.current.focus();
      }
    }, 200);
  };

  const nodeTitleChange = (e: any) => {
    const target = e.target;
    if (target) {
      const _title = target.value.trim();
      setTitle(_title);
      onOutlinesChangeHandler(outlineChangeTypes.editTitle, {
        node,
        title: _title
      });
    }
  };

  const fixSyncTitle = () => {
    if (editNodeId === node.id && title !== node.title) {
      setTitle(node.title || "");
    }
    if (editNodeId !== node.id && title !== node.title && title !== undefined) {
      onOutlinesChangeHandler(outlineChangeTypes.editTitle, { node, title });
    }
  };

  useEffect(() => {
    if (!editNodeId || (editNodeId && editNodeId === node.id)) {
      fixSyncTitle();
    }
  }, [editNodeId, node]);

  return (
    <div
      className={`tree-row flex px-3 relative w-full h-[52px] py-1 leading-[44px] box-border border-0 border-b border-solid border-b-[#eee] hover:bg-[#f5f5f5]`}
      style={{
        paddingLeft: `${depth * subPadding + 4}px`
      }}
    >
      <div className="flex-1 min-w-0 overflow-hidden">
        {editNodeId === node.id ? (
          <Input
            className="node-title-ipt min-w-[400px] w-11/12"
            value={title}
            placeholder="请输入标题"
            ref={iptRef}
            onChange={nodeTitleChange}
            allowClear
          />
        ) : (
          <div className={`relative h-11`}>
            {!node.title ? (
              <span
                className="text-[#FF4D4F] px-2 py-[6px] cursor-pointer rounded h-6 border-[#d9d9d9] hover:border-solid hover:border hover:px-[7px] hover:py-[5px]"
                onClick={isVersion ? undefined : editNodeTitle(node.id)}
              >
                未填写标题
              </span>
            ) : (
              <div className="w-full ml-1 h-11 overflow-hidden">
                <span className="w-full inline-block overflow-hidden whitespace-nowrap text-ellipsis">
                  <span
                    className="select-none px-2 py-[6px] cursor-pointer rounded h-6 border-[#d9d9d9] hover:border-solid hover:border hover:px-[7px] hover:py-[5px]"
                    title={title || node.title}
                    onClick={isVersion ? undefined : editNodeTitle(node.id)}
                  >
                    {depth === 0 ? <b>{title || node.title}</b> : node.title}
                  </span>
                </span>
              </div>
            )}
          </div>
        )}
      </div>
      <div className="w-28 pl-3 box-border">
        <div className="action-cell hidden">
          <Tooltip
            title={<span className="text-gray-2a">配置</span>}
            color="#fff"
          >
            <Button
              disabled={!(node.title && node.title.trim().length > 0)}
              className="mr-1"
              onClick={configSection(node)}
              type="link"
              icon={
                <EditOutlined className="text-[#555] p-1 text-base cursor-pointer rounded hover:text-primary-color hover:bg-white" />
              }
            />
          </Tooltip>
          <Tooltip
            title={<span className="text-gray-2a">删除</span>}
            color="#fff"
          >
            <Button
              disabled={isVersion}
              onClick={delNode(node)}
              type="link"
              icon={
                <DeleteOutlined className="text-[#555] p-1 text-base cursor-pointer rounded hover:text-primary-color hover:bg-white" />
              }
            />
          </Tooltip>
        </div>
      </div>
    </div>
  );
};

export default OutLineItem;
