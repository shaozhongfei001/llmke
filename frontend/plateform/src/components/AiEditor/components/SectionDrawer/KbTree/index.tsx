import { Empty } from "antd";
import { useMemo, useEffect, useState } from "react";
import ActionTreeItem, {
  treeItemTypes
} from "@/components/AiEditor/components/WritingConfig/SegmentedWriting/components/Outline/SourceMaterial/ActionTreeItem";
import { fixTreeData } from "@/components/AiEditor/components/WritingConfig/components/MaterialTree";
import { fileTabTypes, refEntityTypes } from "../";

interface Iprops {
  curFileType: fileTabTypes;
  materialTreeData: any;
  materialList: any[];
  clsoeExceptCls?: string;
  panelCls?: string;
  closeTreeHandler: () => void;
}

export const KbTree = (props: Iprops) => {
  const {
    curFileType,
    materialTreeData,
    materialList = [],
    clsoeExceptCls = "",
    panelCls = "",
    closeTreeHandler
  } = props;
  const [isAllExpand, setIsAllExpand] = useState<boolean>(false);

  const changeExpandSta = () => {
    setIsAllExpand(!isAllExpand);
  };

  const clickListener = (e: any) => {
    const { target } = e;
    isCloseTree(target);
  };

  const isCloseTree = (el: any) => {
    const { tagName, nodeType, className, parentNode } = el;
    if (tagName === "BODY") {
      closeTreeHandler();
      return;
    }
    if (
      (nodeType === 1 &&
        className &&
        className.toString().includes(panelCls)) ||
      className.toString().includes(clsoeExceptCls)
    ) {
      return;
    }
    // console.log(parentNode);
    isCloseTree(parentNode);
  };

  const curMaterialTree = useMemo(() => {
    return fixTreeData(
      materialTreeData,
      (materialList || []).filter(
        (i: any) =>
          i.refEntityType === refEntityTypes.kb &&
          [fileTabTypes.both, curFileType].includes(i.usage)
      )
    );
  }, [materialList, curFileType, materialTreeData]);

  useEffect(() => {
    window.addEventListener("click", clickListener);
    return () => {
      window.removeEventListener("click", clickListener);
    };
  }, []);

  return (
    <>
      {curMaterialTree.length ? (
        curMaterialTree.map((rootNode: any) => {
          return (
            <ActionTreeItem
              key={rootNode.key}
              node={rootNode}
              isAllExpand={true}
              showAction={false}
              treeItemType={treeItemTypes.material}
            />
          );
        })
      ) : (
        <div className="w-full h-[60vh] min-h-52 flex items-center justify-center">
          <Empty />
        </div>
      )}
    </>
  );
};

export default KbTree;
