import { Tabs, Button, Spin } from "antd";
import { useMemo, useState } from "react";
import "../style.less";
import { sourceTypes } from "..";
import { CloseOutlined } from "@ant-design/icons";
import MaterialFileItem from "./MaterialFileItem";
import DbTableItem from "./DbTableItem";
import RelatedTableModal from "@/pages/HomePage/Writing/EditSegmentedTemplate/components/RelatedTableModal";
import BgChooseDb from "./assets/bg-choose-db.svg";

interface Iprops {
  stageType: stageTypes;
  materialTreeData: any;
  materialList: any[];
  dbList: any[];
  sceneContentSources: any[];
  isVersion?: boolean;
  isLoading?: boolean;
  setOpenSelectModal: (sta: boolean) => void;
  materialConfiem: (list: any[], sourceType: sourceTypes) => void;
  closeDrawerHandler: () => void;
}
enum materialTypes {
  material = "material",
  dbTable = "dbTable"
}

enum stageTypes {
  scene = "scene",
  write = "write"
}

const tabItems = [
  {
    key: materialTypes.material,
    label: "选择文件",
    isShow: [stageTypes.scene, stageTypes.write]
  },
  {
    key: materialTypes.dbTable,
    label: "选择数据表",
    isShow: [stageTypes.scene]
  }
];

export enum chooseFileTypes {
  myMaterials = "myMaterials",
  modelMaterials = "modelMaterials"
}

const chooseFileTabItems = [
  {
    key: chooseFileTypes.myMaterials,
    label: "我选择的素材"
  },
  {
    key: chooseFileTypes.modelMaterials,
    label: "模版关联的素材"
  }
];
const initSceneContentSourcesInfo = {
  dbList: [],
  materialList: []
};

export const SourceMaterial = (props: Iprops) => {
  const {
    stageType,
    sceneContentSources,
    dbList = [],
    isVersion = false,
    isLoading = false,
    materialConfiem,
    closeDrawerHandler
  } = props;
  const [curTab, setCurTab] = useState<materialTypes>(materialTypes.material);
  const [curFileTypeTab, setCurFileTypeTab] = useState<chooseFileTypes>(
    chooseFileTypes.myMaterials
  );
  const [isRelationTablesShow, setIsRelationTablesShow] =
    useState<boolean>(false);
  const [dbTreeData, setDbTreeData] = useState<any>([]);

  const fileTypeTabOnChange = (tabKey: any) => {
    setCurFileTypeTab(tabKey);
  };

  const tabOnChange = (tabKey: any) => {
    setCurTab(tabKey);
  };

  const handleMaterialList = (materialListObj: any[], curSource: any) => {
    const { refIds, refNames, usage, refEntityType } = curSource;
    refIds.forEach((curId: any, index: number) => {
      // 如果出现两次，则认为这个素材即是内容来源，也是样本例文
      if (materialListObj[curId]) {
        materialListObj[curId] = { ...materialListObj[curId], usage: "both" };
      } else {
        materialListObj[curId] = {
          refId: curId,
          refName: refNames[index],
          usage: usage,
          refEntityType: refEntityType
        };
      }
    });
    return materialListObj;
  };

  const handleSceneContentSources = (sceneContentSources: any[]) => {
    const result = sceneContentSources.reduce(
      (pre: any, curSource) => {
        const { sourceType } = curSource;
        let { dbList, materialListObj } = pre;
        switch (sourceType) {
          case sourceTypes.knowledge_base:
            materialListObj = handleMaterialList(materialListObj, curSource);
            break;
          case sourceTypes.database:
            dbList = [...dbList, ...(curSource.refIds || [])];
            break;
          default:
            break;
        }
        pre = { dbList, materialListObj };
        return pre;
      },
      {
        dbList: [],
        materialListObj: {}
      }
    );
    return {
      dbList: result.dbList,
      materialList: Object.values(result.materialListObj)
    };
  };

  const closeDbModal = () => {
    setIsRelationTablesShow(false);
  };

  const sceneContentSourcesInfo = useMemo(() => {
    if (!sceneContentSources) {
      return initSceneContentSourcesInfo;
    }
    const res = handleSceneContentSources(sceneContentSources);
    return res;
  }, [sceneContentSources]);

  const relatedTablesConfirm = ({ tableList, tableTree }: any) => {
    const list: any[] = [];
    const _sourceType = sourceTypes.database;
    (tableList || []).forEach((i: any) => {
      const { id, name, dbName } = i;
      list.push({
        customId: `db-${id}`,
        refId: id,
        refEntityType: "table",
        refName: name,
        dbName,
        sourceType: _sourceType
      });
    });
    materialConfiem(list, _sourceType);
    setIsRelationTablesShow(false);
  };

  const dbIdList = useMemo(() => {
    return (dbList || []).map((i: any) => Number(i.refId));
  }, [dbList]);

  const curTabItems = useMemo(() => {
    return stageType
      ? tabItems.filter((i: any) => i.isShow.includes(stageType))
      : [];
  }, [stageType, tabItems]);

  return (
    <div className="bg-[#f1f5fc] rounded-lg h-full w-full relative">
      <Button
        type="link"
        title="关闭"
        className="absolute z-50 right-3 top-2"
        icon={
          <CloseOutlined className="text-[#666] scale-x-75 scale-y-75 hover:opacity-80" />
        }
        onClick={closeDrawerHandler}
      ></Button>
      <div className="material-tab-wrap relative mr-4">
        <i className="inline-block h-[1px] w-full absolute bottom-0 border-0 border-b border-solid border-b-[#eee]"></i>
        {curTabItems && curTabItems.length > 1 ? (
          <Tabs items={curTabItems} onChange={tabOnChange} activeKey={curTab} />
        ) : (
          <Tabs
            items={chooseFileTabItems}
            onChange={fileTypeTabOnChange}
            activeKey={curFileTypeTab}
          />
        )}
      </div>
      {curTab === materialTypes.material ? (
        <div
          className={`overflow-x-hidden overflow-y-auto scrollbar-thin py-2 h-[calc(100vh-252px)]`}
        >
          <Spin spinning={isLoading}>
            <MaterialFileItem
              {...props}
              sceneMaterialList={sceneContentSourcesInfo.materialList}
              chooseFileType={curFileTypeTab}
              delTreeNode={materialConfiem}
            />
          </Spin>
        </div>
      ) : (
        <div
          className={`overflow-x-hidden overflow-y-auto scrollbar-thin py-2 h-[calc(100vh-252px)]`}
        >
          {/* <Spin spinning={isLoading}>
            <DbTableItem
              {...props}
              dbTreeData={dbTreeData}
              sceneDbList={sceneContentSourcesInfo.dbList}
              setIsRelationTablesShow={setIsRelationTablesShow}
              delTreeNode={materialConfiem}
            />
          </Spin> */}
          <div className="flex w-full h-[calc(100vh-352px)] justify-center select-none">
            <img src={BgChooseDb} width={400} />
          </div>
        </div>
      )}
      <RelatedTableModal
        isModalOpen={isRelationTablesShow}
        relationTables={dbIdList}
        onClose={closeDbModal}
        onConfirm={relatedTablesConfirm}
        setDbTreeData={setDbTreeData}
      />
    </div>
  );
};

export default SourceMaterial;
