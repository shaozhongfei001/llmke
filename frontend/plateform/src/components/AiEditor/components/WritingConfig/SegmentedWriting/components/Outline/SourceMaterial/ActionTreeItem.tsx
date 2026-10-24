import { Button, Tooltip } from "antd";
import { useState, useEffect } from "react";
import {
  CaretRightOutlined,
  CaretDownOutlined,
  DeleteOutlined
} from "@ant-design/icons";
import { stageTypes } from "..";
import "./style.less";
import {
  getFileIcon,
  elementTypes
} from "@/components/AiEditor/components/WritingConfig/components/SelectMaterialModal";

interface Iprops {
  stageType?: stageTypes;
  node: any;
  isVersion?: boolean;
  treeItemType: treeItemTypes;
  isAllExpand: boolean;
  showAction?: boolean;
  delNode?: (node: any) => void;
}
export enum treeItemTypes {
  material = "material",
  dbTable = "dbTable"
}
const subPadding = 50;

export const ActionTreeItem = (props: Iprops) => {
  const {
    node = {},
    isVersion = false,
    isAllExpand = false,
    showAction = true,
    treeItemType = treeItemTypes.material,
    delNode
  } = props;
  const [isExpand, setIsExpand] = useState<boolean>(false);

  const getIcon = (item: any) => {
    const { elementType, fileName, name } = item;
    const _fileName = fileName || name || "";
    const type =
      treeItemType === treeItemTypes.material
        ? _fileName && elementType === elementTypes.FILE
          ? getFileSuffix(_fileName)
          : elementType === elementTypes.FOLDER
            ? "folder"
            : "kb"
        : treeItemType === treeItemTypes.dbTable
          ? "db"
          : undefined;
    return (
      <span className="pl-1 mt-[1px]">
        {type ? getFileIcon(type, item) : null}
      </span>
    );
  };

  const getFileSuffix = (fileName: string) => {
    const list = fileName.split(".");
    return list.length > 1 ? list[list.length - 1] : "";
  };

  const onToggle = () => {
    setIsExpand(!isExpand);
  };

  const delNodeHandler = (node: any) => () => {
    delNode && delNode(node);
  };

  useEffect(() => {
    if (isAllExpand !== isExpand) {
      setIsExpand(isAllExpand);
    }
  }, [isAllExpand]);

  return (
    <>
      <div
        className={`flex h-8 p-1 leading-6 rounded relative action-tree-item hover:bg-[#e8ebff]`}
        style={{
          paddingLeft: `${(node.depth - 1) * subPadding}px`
        }}
      >
        <div
          className={`${node.children && node.children.length ? "visible" : "invisible"}`}
        >
          {node.children && node.children.length ? (
            isExpand ? (
              <CaretDownOutlined
                className="p-1 text-base mr-1 text-[#888] hover:opacity-80"
                title="关闭"
                onClick={onToggle}
              />
            ) : (
              <CaretRightOutlined
                className="p-1 text-base mr-1 text-[#888] hover:opacity-80"
                title="展开"
                onClick={onToggle}
              />
            )
          ) : null}
        </div>
        {getIcon(node)}
        <div className="truncate pr-5" title={node.title}>
          {node.title}
        </div>
        {showAction && !isVersion ? (
          <Tooltip
            title={<span className="text-gray-2a">删除</span>}
            color="#fff"
          >
            <Button
              className="del-btn absolute right-0 top-0 hidden"
              onClick={delNodeHandler(node)}
              icon={
                <DeleteOutlined className="text-text-color2 p-1 rounded hover:bg-white hover:text-[#ff4d4f]" />
              }
              type="link"
            />
          </Tooltip>
        ) : null}
      </div>

      {isExpand &&
        node.children?.map((child: any) => {
          return <ActionTreeItem {...props} key={child.key} node={child} />;
        })}
    </>
  );
};

export default ActionTreeItem;
