import { Button, Empty } from "antd";
import { useMemo, useState } from "react";
import { IconCollapseDown, IconCollapseUp } from "@/components/Icon";
import { fixTreeData } from "@/components/AiEditor/components/WritingConfig/components/MaterialTree";
import MaterialList from "@/components/AiEditor/components/WritingConfig/components/MaterialList";
import ActionTreeItem, { treeItemTypes } from "./ActionTreeItem";
import { stageTypes, sourceTypes } from "..";
import { chooseFileTypes } from ".";

interface Iprops {
  stageType: stageTypes;
  materialTreeData: any;
  materialList: any[];
  sceneContentSources: any[];
  sceneMaterialList: any[];
  isVersion?: boolean;
  chooseFileType?: chooseFileTypes;
  setOpenSelectModal: (sta: boolean) => void;
  delTreeNode: (list: any[], sourceType: sourceTypes) => void;
}
enum fileTabTypes {
  content = "content",
  template = "template",
  both = "both"
}
const fileTabItems = [
  {
    key: fileTabTypes.content,
    label: "切片检索"
  },
  {
    key: fileTabTypes.template,
    label: "全文引用"
  }
];

enum refEntityTypes {
  document = "document",
  table = "table"
}

export const MaterialFileItem = (props: Iprops) => {
  const {
    stageType,
    materialTreeData,
    materialList = [],
    sceneMaterialList,
    isVersion = false,
    chooseFileType = chooseFileTypes.myMaterials,
    setOpenSelectModal,
    delTreeNode
  } = props;
  const [curFileType, setCurFileType] = useState<fileTabTypes>(
    fileTabTypes.content
  );
  const [isAllExpand, setIsAllExpand] = useState<boolean>(false);
  const changeExpandSta = () => {
    setIsAllExpand(!isAllExpand);
  };

  const myMaterialNum = useMemo(() => {
    return materialList && materialList.length
      ? Array.from(
          new Set(
            materialList
              .filter((i) => i.refEntityType === refEntityTypes.document)
              .map((i) => i.refId)
          )
        ).length
      : 0;
  }, [materialList]);

  const curMaterialTree = useMemo(() => {
    return fixTreeData(
      materialTreeData,
      (materialList || []).filter(
        (i: any) =>
          i.refEntityType === refEntityTypes.document &&
          [fileTabTypes.both, curFileType].includes(i.usage)
      )
    );
  }, [materialList, curFileType, materialTreeData]);

  const curSceneMaterialList = useMemo(() => {
    return (sceneMaterialList || []).filter(
      (i: any) =>
        i.refEntityType === refEntityTypes.document &&
        [fileTabTypes.both, curFileType].includes(i.usage)
    );
  }, [curFileType, sceneMaterialList]);

  const handlerChooseFile = () => {
    setOpenSelectModal(true);
  };

  const fileTypeOnChangeHandler = (type: fileTabTypes) => () => {
    setCurFileType(type);
  };

  const delNode = (node: any) => {
    const { leafKeys, refId } = node;
    let refIds: string[] = [];
    if (leafKeys && leafKeys.length) {
      refIds = leafKeys.map((i: string | number) => String(i));
    } else {
      refIds.push(String(refId));
    }
    const list: any[] = [];
    (materialList || []).forEach((i: any) => {
      if (!refIds.includes(String(i.refId))) {
        list.push(i);
      } else {
        if (i.usage !== curFileType && i.usage === fileTabTypes.both) {
          list.push({
            ...i,
            usage:
              curFileType === fileTabTypes.content
                ? fileTabTypes.template
                : fileTabTypes.content
          });
        }
      }
    });
    delTreeNode(list, sourceTypes.knowledge_base);
  };

  return (
    <>
      <div className="rounded-lg w-full">
        <div className="text-center mb-3 pr-4">
          <Button
            disabled={
              isVersion || chooseFileType === chooseFileTypes.modelMaterials
            }
            type="link"
            className="h-11 w-full px-0"
            onClick={handlerChooseFile}
          >
            <div className="block w-full h-10 bg-white text-primary-color border-dashed border-[#d9d9d9] border-[1px] rounded leading-10 hover:opacity-75">
              选择文件
              {/* {stageType === stageTypes.scene && myMaterialNum ? (
                <span>（{myMaterialNum}）</span>
              ) : null} */}
            </div>
          </Button>
        </div>
        <div className="w-full pr-2">
          <div className="flex justify-between mb-2">
            <div className="text-text-color2 pt-1 leading-7">
              已选择的文件
              {chooseFileType === chooseFileTypes.myMaterials ? (
                <span
                  title={isAllExpand ? "收起" : "展开"}
                  className="text-[#888] cursor-pointer ml-1 relative top-[1px] hover:text-[#055aff]"
                  onClick={changeExpandSta}
                >
                  {isAllExpand ? (
                    <IconCollapseUp className="p-1 text-base" />
                  ) : (
                    <IconCollapseDown className="p-1 text-base" />
                  )}
                </span>
              ) : null}
            </div>
            <div className="mr-2">
              {fileTabItems.map((i: any, idx: number) => {
                return (
                  <Button
                    className={`ml-2 px-3 border-none ${curFileType === i.key ? " bg-[#e2e9ff] cursor-default hover:!bg-[#e2e9ff]  hover:!opacity-100" : "text-gray-2a bg-[#f5f5f5]"}`}
                    type="link"
                    key={`file-tab-${idx}`}
                    onClick={fileTypeOnChangeHandler(i.key)}
                  >
                    <span
                      className={`${curFileType === i.key ? "font-bold text-primary-color cursor-default " : "text-gray-2a hover:opacity-75"}`}
                    >
                      {i.label}
                    </span>
                  </Button>
                );
              })}
            </div>
          </div>
          {/* <div>{JSON.stringify(curMaterialList)}</div> */}
          {chooseFileType === chooseFileTypes.myMaterials ? (
            curMaterialTree.length ? (
              curMaterialTree.map((rootNode: any) => {
                return (
                  <ActionTreeItem
                    key={rootNode.key}
                    node={rootNode}
                    stageType={stageType}
                    isAllExpand={isAllExpand}
                    isVersion={isVersion}
                    treeItemType={treeItemTypes.material}
                    delNode={delNode}
                  />
                );
              })
            ) : (
              <div className="mt-10">
                <Empty className="mt-10" />
              </div>
            )
          ) : sceneMaterialList.length ? (
            <MaterialList
              listData={curSceneMaterialList}
              showDel={false}
              hasBoder={false}
              showRight={false}
            />
          ) : (
            <div className="mt-10">
              <Empty className="mt-10" />
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default MaterialFileItem;
