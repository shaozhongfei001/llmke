import React, { useState, useMemo, useRef, useEffect } from "react";
import { Button, Tooltip, Input } from "antd";
import { EllipsisOutlined, PlusOutlined } from "@ant-design/icons";
import { IndicatorFormIcon } from "@/components/Icon";
import { menuActionTypes } from "./CategoryTree";

interface TreeItemProps {
  node: any;
  editRowId: string;
  highLightNodeId: string | undefined;
  treeAction?: (type: string, node: any, categoryName?: string) => void;
}

const TreeItem: React.FC<TreeItemProps> = (props) => {
  const { node, editRowId, highLightNodeId, treeAction } = props;
  const [isShowMenu, setIsShowMenu] = useState(false);

  const iptRef = useRef<any>(null);

  const isFolder = useMemo(() => {
    return !!(node && node.categoryType === 0);
  }, [node]);

  const menuActions = [
    {
      label: "重命名",
      value: menuActionTypes.RENAME
    },
    {
      label: "删除",
      value: menuActionTypes.DELETE
    }
  ];

  const menuAddActions = [
    {
      label: "添加子分类",
      value: menuActionTypes.ADDNODE
    },
    {
      label: "添加指标表单",
      value: menuActionTypes.ADDFORM
    }
  ];

  const handlerRowClick = () => {
    treeAction && treeAction(menuActionTypes.CLICK, node);
  };

  const handlerMenuClick = (type: string) => () => {
    treeAction && treeAction(type, node);
  };

  const stopPropagation = (e: any) => {
    e.stopPropagation();
  };

  const handlerIptConfirm = (e: any) => {
    const val = e.target.value.trim();
    treeAction && treeAction(menuActionTypes.RENAMECONFIRM, node, val);
  };

  useEffect(() => {
    if (editRowId === node.id && iptRef.current) {
      iptRef.current.focus && iptRef.current.focus();
    }
  }, [editRowId, node, iptRef.current]);

  return (
    <div
      className={`h-10 box-border flex justify-between items-center ${highLightNodeId && highLightNodeId === node.id ? "bg-[#f1f5ff]" : ""}`}
      onClick={handlerRowClick}
    >
      {editRowId === node.id ? (
        <div className="w-full">
          <Input
            defaultValue={node.categoryName}
            ref={iptRef}
            placeholder="请输入分类名称"
            allowClear
            onClick={stopPropagation}
            onBlur={handlerIptConfirm}
            onPressEnter={handlerIptConfirm}
          />
        </div>
      ) : (
        <div
          title={node.categoryName}
          className="break-words text-ellipsis line-clamp-1 w-[calc(100%-50px)] text-gray-2a "
        >
          {!isFolder ? <IndicatorFormIcon className="mr-1" /> : null}
          {node.categoryName}
        </div>
      )}

      <div
        className={`tree-node-extend flex gap-2 ${editRowId === node.id ? "hidden" : ""}`}
      >
        {isFolder ? (
          <Tooltip
            placement="right"
            color={"#fff"}
            arrow={false}
            styles={{ body: { padding: 0 } }}
            title={
              <div className="py-2 w-32 rounded bg-white">
                {menuAddActions.map((i: any, idx: number) => {
                  return (
                    <div
                      className="pl-5 text-gray-2a h-8 leading-8 cursor-pointer hover:bg-[#f1f5ff]"
                      key={`${node.id}-menu-${idx}`}
                      onClick={handlerMenuClick(i.value)}
                    >
                      {i.label}
                    </div>
                  );
                })}
              </div>
            }
          >
            <Button
              type="text"
              size="small"
              className="w-6 h-6 text-text-color2 hover:!text-primary-color hover:!bg-white"
              icon={<PlusOutlined />}
              onClick={stopPropagation}
            />
          </Tooltip>
        ) : null}
        <Tooltip
          placement="right"
          color={"#fff"}
          arrow={false}
          open={isShowMenu}
          onOpenChange={setIsShowMenu}
          styles={{ body: { padding: 0 } }}
          title={
            <div className="w-20 py-2 rounded bg-white">
              {menuActions.map((i: any, idx: number) => {
                return (
                  <div
                    className="pl-5 text-gray-2a h-8 leading-8 cursor-pointer hover:bg-[#f1f5ff]"
                    key={`${node.id}-menu-${idx}`}
                    onClick={handlerMenuClick(i.value)}
                  >
                    {i.label}
                  </div>
                );
              })}
            </div>
          }
        >
          <Button
            type="text"
            size="small"
            className="w-6 h-6 text-text-color2 hover:!text-primary-color hover:!bg-white"
            icon={<EllipsisOutlined />}
            onClick={stopPropagation}
          ></Button>
        </Tooltip>
      </div>
    </div>
  );
};

export default TreeItem;
