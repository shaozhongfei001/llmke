import { BetaSchemaForm } from "@ant-design/pro-form";
// R12：原写法 Icon-link.svg 在 Linux 大小写敏感文件系统上不存在，实际文件为 icon-link.svg
import IconLink from "@/assets/svg/icon-link.svg";
import SelectMaterialModal from "@root/src/components/AiEditor/components/WritingConfig/components/SelectMaterialModal";
import { useEffect, useState } from "react";
import { Form, Popover } from "antd";
import MaterialTree from "@root/src/components/AiEditor/components/WritingConfig/components/MaterialTree";
import RelatedTableModal from "@root/src/pages/HomePage/Writing/EditSegmentedTemplate/components/RelatedTableModal";
import DbTableTree from "./DbTableTree";
import { PrimaryBtn } from "@root/src/pages/HomePage/Writing/common/components/PrimaryBtn";

enum Usage {
  Template = "template",
  Content = "content"
}

interface IProps {
  formSchema: any[];
  submitFormData: (formData: any) => any;
  mouduleName: "SECTION" | "ANALYSIS";
}

const initOriginData = {
  kbs: [],
  folders: [],
  files: []
};

// 数据表转换为大纲ContentSources数据
const dbTableTreeToContentSources = (dbTableTree: any) => {
  if (!dbTableTree || dbTableTree.length === 0) return false;
  const contentSource = dbTableTree.reduce((pre: any, curDb: any) => {
    const curRefIds: any = [];
    const curRefNames: any = [];
    const curDbNames: any = [];
    if (curDb?.tables && curDb.tables.length > 0) {
      curDb?.tables.forEach((table: any) => {
        curRefIds.push(table.id);
        curRefNames.push(table.name);
        curDbNames.push(curDb.name);
      });
    }
    return {
      refIds: [...(pre.refIds || []), ...curRefIds],
      refNames: [...(pre.refNames || []), ...curRefNames],
      dbNames: [...(pre.dbNames || []), ...curDbNames],
      refEntityType: "table",
      sourceType: "database"
    };
  }, {});
  return JSON.stringify(contentSource) === "{}" ? false : contentSource;
};

// 素材转换为大纲ContentSources数据
const materialDataToContentSources = (materialData: any[]) => {
  if (!materialData || materialData.length === 0) return [];

  const classifyByUsage: any = {
    [Usage.Template]: {
      sourceType: "knowledge_base",
      refEntityType: "document",
      usage: "template",
      refIds: [],
      refNames: []
    },
    [Usage.Content]: {
      sourceType: "knowledge_base",
      refEntityType: "document",
      usage: "content",
      refIds: [],
      refNames: []
    }
  };

  materialData.forEach((item) => {
    if (item?.usage) {
      classifyByUsage[item.usage] = {
        ...classifyByUsage[item.usage],
        refIds: [...classifyByUsage[item.usage].refIds, item.refId],
        refNames: [...classifyByUsage[item.usage].refNames, item.refName]
      };
    }
  });

  let materialContentSourcesArr: any = [];
  if (classifyByUsage[Usage.Template].refIds.length)
    materialContentSourcesArr = [
      ...materialContentSourcesArr,
      classifyByUsage[Usage.Template]
    ];
  if (classifyByUsage[Usage.Content].refIds.length)
    materialContentSourcesArr = [
      ...materialContentSourcesArr,
      classifyByUsage[Usage.Content]
    ];
  return materialContentSourcesArr;
};

function FormContainer({ formSchema, submitFormData, mouduleName }: IProps) {
  // ================== 素材相关 ==================
  const [materailModalOpen, setMaterailModalOpen] = useState<boolean>(false);
  const [materialTreeData, setMaterialTreeData] = useState<any>({
    ...initOriginData
  });
  const [materialData, setMaterialData] = useState<any[]>([]);
  const [isMaterialApisFetching, setIsMaterialApisFetching] =
    useState<boolean>(false);

  const getAllFilesCb = (originData: any) => {
    setMaterialTreeData({ ...originData });
  };
  // ================== 素材相关end ==================

  // ================== 数据表相关 ==================
  const [relatedTable, setRelatedTable] = useState<{
    visible: boolean;
    relationTablesList?: any;
    relationTablesTree?: any;
  }>({
    visible: false,
    relationTablesList: [],
    relationTablesTree: []
  });

  const relatedTables = ({ tableList, tableTree }: any) => {
    // 将tables填充到大纲contentsource字段中
    console.log("成功拿到数据表数据tables:", tableList, tableTree);
    setRelatedTable({
      relationTablesList: tableList,
      relationTablesTree: tableTree,
      visible: false
    });
  };
  // ================== 数据表相关end ==================

  // ================== 表单数据提交 ===================
  const [form] = Form.useForm();
  const handleConfirm = () => {
    form.validateFields().then((values) => {
      const dbTableTreeContentSource = dbTableTreeToContentSources(
        relatedTable.relationTablesTree || []
      );

      const materialContentSourceArr = materialDataToContentSources(
        materialData || []
      );

      const contentSources = dbTableTreeContentSource
        ? [dbTableTreeContentSource, ...materialContentSourceArr]
        : materialContentSourceArr;

      const isChapter = mouduleName === "SECTION" ? true : false;
      const params = isChapter
        ? {
            inputs: values,
            contentSources,
            type: mouduleName
          }
        : {
            inputs: values,
            contentSources
          };

      submitFormData(params);
    });
  };
  // ================== 表单数据提交end ==================

  return (
    <div className="h-full">
      {/* 选择数据表 */}
      <RelatedTableModal
        isModalOpen={relatedTable.visible}
        relationTables={(relatedTable.relationTablesList || []).map(
          (i: any) => i.key
        )}
        onClose={() => {
          setRelatedTable((p) => ({ ...p, visible: false }));
        }}
        onConfirm={relatedTables}
      />
      {/* 选择知识库 */}
      <SelectMaterialModal
        openSelectModal={materailModalOpen}
        setOpenSelectModal={setMaterailModalOpen}
        initSelectedArr={materialData}
        isMaterialApisFetching={isMaterialApisFetching}
        setIsMaterialApisFetching={setIsMaterialApisFetching}
        getAllMertail={(list) => {
          setMaterialData(list);
        }}
        getAllFilesCb={getAllFilesCb}
      />
      {/* 表单 */}
      <div className="h-[calc(100%-50px)] overflow-y-auto">
        <BetaSchemaForm
          layoutType="Form"
          form={form}
          columns={formSchema.map((i) => ({
            ...i,
            formItemProps: {
              ...(i.formItemProps || {}),
              label: <span className="text-[#2a2a2a] font-bold">{i.title}</span>
            }
          }))}
          submitter={false}
        />

        <div>
          <span className="text-[#2a2a2a] font-bold">配置关联素材</span>
          <div className="flex justify-between items-center mt-2 gap-4">
            <Popover
              placement="top"
              content={
                <div className="w-[426px] h-[280px] box-border">
                  <MaterialTree
                    materialList={materialData}
                    materialTreeData={materialTreeData}
                    delBtnShow={false}
                    treeHeight={280}
                  />
                </div>
              }
              arrow={false}
            >
              <div
                className="bg-white w-full flex justify-center items-center h-[32px] rounded-[4px] cursor-pointer hover:border-[1px] hover:border-solid hover:border-[#055aff] box-border"
                onClick={() => setMaterailModalOpen(true)}
              >
                <img src={IconLink} alt="" className="mr-2" />
                关联文件（{(materialData || []).length}）
              </div>
            </Popover>
            <Popover
              placement="top"
              content={
                <div className="w-[426px] h-[280px] box-border overflow-y-auto">
                  <DbTableTree tree={relatedTable.relationTablesTree} />
                </div>
              }
              arrow={false}
            >
              <div
                className="bg-white w-full flex justify-center items-center h-[32px] rounded-[4px] cursor-pointer hover:border-[1px] hover:border-solid hover:border-[#055aff] box-border"
                onClick={() =>
                  setRelatedTable((p) => ({ ...p, visible: true }))
                }
              >
                <img src={IconLink} alt="" className="mr-2" />
                关联数据表（{(relatedTable?.relationTablesList || []).length}）
              </div>
            </Popover>
          </div>
        </div>
      </div>
      <PrimaryBtn className="absolute right-5 bottom-4" onClick={handleConfirm}>
        确定
      </PrimaryBtn>
    </div>
  );
}

export default FormContainer;
