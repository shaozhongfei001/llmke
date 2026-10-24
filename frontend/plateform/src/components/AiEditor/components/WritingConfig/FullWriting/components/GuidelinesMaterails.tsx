import { useState, useMemo } from "react";
import { Button, Tabs, Empty, Spin } from "antd";
import SelectMaterialModal from "@/components/AiEditor/components/WritingConfig/components/SelectMaterialModal";
import { fixTreeData } from "@/components/AiEditor/components/WritingConfig/components/MaterialTree";
import { ChooseFileIcon } from "@/components/Icon";
import { sourceTypes } from "../newIndex";
import ActionTreeItem, {
  treeItemTypes
} from "@/components/AiEditor/components/WritingConfig/SegmentedWriting/components/Outline/SourceMaterial/ActionTreeItem";

enum usageTypes {
  TEMPLATE = "template",
  CONTENT = "content",
  BOTH = "both"
}

enum refEntityTypes {
  document = "document"
}

enum stageTypes {
  scene = "scene"
}

enum tabTypes {
  TEMPLATE = "template",
  CONTENT = "content"
}

const tabItems = [
  {
    key: tabTypes.CONTENT,
    label: "切片检索"
  },
  {
    key: tabTypes.TEMPLATE,
    label: "全文引用"
  }
];

const initOriginData = {
  kbs: [],
  folders: [],
  files: []
};

interface Iprops {
  idDocLoading: boolean;
  materialData: any[];
  setMaterialData: (data: any[]) => void;
}

const GuidelinesMaterails = (props: Iprops) => {
  const { idDocLoading = false, materialData = [], setMaterialData } = props;
  const [openSelectModal, setOpenSelectModal] = useState(false);
  const [activeTab, setActiveTab] = useState<tabTypes>(tabTypes.CONTENT);
  const [materialTreeData, setMaterialTreeData] = useState<any>({
    ...initOriginData
  });
  const [isMaterialApisFetching, setIsMaterialApisFetching] =
    useState<boolean>(false);

  const materialConfiem = (list: any[], sourceType: sourceTypes) => {
    console.log("new material list:", list, materialData);
    const _list = materialData.filter((i: any) => i.sourceType !== sourceType);
    const newList = [..._list, ...list];
    setMaterialData([...newList]);
  };

  const getAllFilesCb = (originData: any) => {
    console.log("originData:", originData);
    setMaterialTreeData({ ...originData });
  };

  const handleTabChange = (key: any) => {
    if (key !== activeTab) {
      setActiveTab(key);
    }
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
        if (i.usage !== activeTab && i.usage === usageTypes.BOTH) {
          list.push({
            ...i,
            usage:
              activeTab === tabTypes.CONTENT
                ? usageTypes.TEMPLATE
                : usageTypes.CONTENT
          });
        }
      }
    });
    materialConfiem(list, sourceTypes.knowledge_base);
  };

  const materialList = useMemo(() => {
    return (materialData || []).filter((i: any) =>
      activeTab === tabTypes.CONTENT
        ? [usageTypes.CONTENT, usageTypes.BOTH].includes(i.usage)
        : [usageTypes.TEMPLATE, usageTypes.BOTH].includes(i.usage)
    );
  }, [activeTab, materialData]);

  const curMaterialTree = useMemo(() => {
    return fixTreeData(
      materialTreeData,
      (materialList || []).filter(
        (i: any) =>
          i.refEntityType === refEntityTypes.document &&
          [usageTypes.BOTH, activeTab].includes(i.usage)
      )
    );
  }, [materialList, activeTab, materialTreeData]);

  return (
    <>
      <div className="mb-2">
        <b className="text-base text-gray-2a ">选择文件</b>
      </div>
      <div className="border border-[#D9D9D9] border-dashed bg-[#F9FAFC] rounded-sm flex items-center flex-col py-3 mb-6">
        <Button
          size="large"
          icon={<ChooseFileIcon />}
          className="border-[#eeeeee] rounded h-10 text-primary-color text-sm px-7"
          onClick={() => setOpenSelectModal(true)}
        >
          <span className="flex items-center h-full">选择文件</span>
        </Button>
      </div>
      <div className="">
        <Tabs
          defaultActiveKey="chunking"
          items={[...tabItems]}
          activeKey={activeTab.toString()}
          onChange={handleTabChange}
        />
      </div>
      {/* <div>{JSON.stringify(materialData)}</div> */}
      <Spin spinning={idDocLoading || isMaterialApisFetching}>
        {curMaterialTree.length ? (
          curMaterialTree.map((rootNode: any) => {
            return (
              <ActionTreeItem
                key={rootNode.key}
                node={rootNode}
                stageType={stageTypes.scene}
                isAllExpand={true}
                isVersion={false}
                treeItemType={treeItemTypes.material}
                delNode={delNode}
              />
            );
          })
        ) : (
          <div className="mt-10">
            <Empty className="mt-10" />
          </div>
        )}
      </Spin>
      <SelectMaterialModal
        openSelectModal={openSelectModal}
        initSelectedArr={materialData}
        isMaterialApisFetching={isMaterialApisFetching}
        setIsMaterialApisFetching={setIsMaterialApisFetching}
        setOpenSelectModal={setOpenSelectModal}
        getAllMertail={materialConfiem}
        getAllFilesCb={getAllFilesCb}
      />
    </>
  );
};

export default GuidelinesMaterails;
