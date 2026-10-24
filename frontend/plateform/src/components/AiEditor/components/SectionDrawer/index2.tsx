import React, { useEffect, useState, useMemo } from "react";
import { Divider, Drawer, Flex, Input, Tree } from "antd";
import type { TreeDataNode, TreeProps } from "antd";
import { CloseOutlined, PlusCircleOutlined } from "@ant-design/icons";
import { useStateStore } from "@root/src/components/AiEditor/core/states/useStateStore";
import {
  api_querySectionById,
  api_editSectionById,
  api_editArticleTypeSectionById,
  api_addArticleTypeSection,
  api_addSection
} from "@root/src/components/AiEditor/core/services/servers";
import File from "@/assets/img/loseFile.png";
import { debounce } from "lodash";

const close = (cb) => {
  cb();
};
const debounceClose = debounce(close, 300);

const { TextArea } = Input;

interface Iprops {
  open: boolean;
  sectionId?: number;
  id: number | string;
  onClose: (section: any) => void;
  serverInfo: any;
  materialTypes: any[];
  title?: string;
  isTemplate?: boolean;
}

interface MaterialType {
  id: number;
  name: string;
  parentID: number;
  gmtCreate: string;
  subTypeList?: MaterialType[];
}

interface MarticleTreeType {
  key: number;
  title: string;
  parentID: number;
  gmtCreate: string;
  children?: MaterialType[];
  checkable?: boolean;
}

const mockData = [
  { id: 1, name: "公司章程", parentId: 0, gmtCreate: "2024-12-04 18:54:39" },
  { id: 3, name: "财务报表", parentId: 0, gmtCreate: "2024-12-04 18:54:52" },
  { id: 4, name: "年度报告", parentId: 0, gmtCreate: "2024-12-04 18:55:07" },
  { id: 5, name: "招股说明书", parentId: 0, gmtCreate: "2024-12-04 18:55:22" },
  { id: 6, name: "银行流水", parentId: 0, gmtCreate: "2024-12-04 18:55:33" },
  { id: 7, name: "募集说明书", parentId: 0, gmtCreate: "2024-12-04 18:55:44" },
  { id: 8, name: "组织架构图", parentId: 0, gmtCreate: "2024-12-04 18:55:55" },
  {
    id: 9,
    name: "测试第一代",
    parentId: 0,
    gmtCreate: "2024-12-04 18:56:31",
    subTypeList: [
      {
        id: 10,
        name: "第2代",
        parentId: 9,
        gmtCreate: "2024-12-04 11:38:12",
        subTypeList: [
          {
            id: 11,
            name: "第3代",
            parentId: 10,
            gmtCreate: "2024-12-04 19:02:04"
          },
          {
            id: 12,
            name: "第3.1代",
            parentId: 10,
            gmtCreate: "2024-12-04 19:15:16"
          }
        ]
      }
    ]
  },
  { id: 13, name: "第3.1代", parentId: 0, gmtCreate: "2024-12-05 10:19:22" },
  { id: 14, name: "第3.1代", parentId: 0, gmtCreate: "2024-12-05 10:19:25" }
];
const SectionDrawer = (props: Iprops) => {
  const {
    open = false,
    sectionId,
    id,
    onClose,
    materialTypes,
    serverInfo,
    title,
    isTemplate
  } = props;
  const [sectionInfo, setSectionInfo] = useState({});
  const [showTree, setShowTree] = useState(false);
  const [contextValue, setContextValue] = useState<string>();
  const [exampleValue, setExampleValue] = useState<string>();
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
  const [checkedKeys, setCheckedKeys] = useState<React.Key[]>([]);
  const [autoExpandParent, setAutoExpandParent] = useState<boolean>(true);

  useEffect(() => {
    if (open && sectionId && id) {
      getSectionInfo(sectionId);
    }
  }, [open, sectionId, id]);

  const getSectionInfo = async (sectionId: number) => {
    try {
      const res = await api_querySectionById({
        data: {
          id: sectionId
        },
        config: serverInfo
      });
      const { data } = res;
      setSectionInfo(data);
      setCheckedKeys(data.materialType);
      setContextValue(data.sectionPrompt);
      setExampleValue(data.sectionContentExample);
    } catch (e) {
      console.log("getSectionInfo ------->", e);
    }
  };

  const checkNodeLabels: string[] = useMemo(() => {
    const checkedlabels: string[] = [];
    if (checkedKeys?.length > 0) {
      const traverse = (materialType: MaterialType[]) => {
        materialType.forEach((m: MaterialType) => {
          if (checkedKeys.indexOf(m.id) > -1) {
            checkedlabels.push(m.name);
          }
          if (m.subTypeList) {
            traverse(m.subTypeList);
          }
        });
      };
      traverse(materialTypes);
    }

    return checkedlabels;
  }, [checkedKeys, materialTypes]);

  const convertData = (data: MaterialType[]): MarticleTreeType[] => {
    return data.map((item) => {
      const newItem: MarticleTreeType = {
        key: item.id,
        title: item.name,
        parentID: item.parentID,
        gmtCreate: item.gmtCreate,
        checkable:
          item.subTypeList && item.subTypeList.length > 0 ? false : true
      };

      if (item.subTypeList && item.subTypeList.length > 0) {
        newItem.children = convertData(item.subTypeList);
      }
      return newItem;
    });
  };

  const treeData = useMemo(() => {
    const res = convertData(materialTypes);
    return res;
  }, [materialTypes]);

  const onExpand: TreeProps["onExpand"] = (expandedKeysValue) => {
    setExpandedKeys(expandedKeysValue);
    setAutoExpandParent(false);
  };

  const onCheck: TreeProps["onCheck"] = (checkedKeysValue, info) => {
    setCheckedKeys(checkedKeysValue as React.Key[]);
  };

  const onContextChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setContextValue(e.target.value);
  };

  const onExampleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setExampleValue(e.target.value);
  };

  const handleClose = async () => {
    //提交数据
    try {
      const data = {
        params: {
          ...sectionInfo,
          sectionPrompt: contextValue,
          sectionContentExample: exampleValue,
          materialType: checkedKeys
        }
      };
      let res;
      if (sectionId) {
        if (contextValue && contextValue?.trim()?.length > 0) {
          data.id = sectionId;
          if (isTemplate) {
            data.articleTypeId = id;
            res = await api_editArticleTypeSectionById({
              data,
              config: serverInfo
            });
          } else {
            data.articleId = id;
            res = await api_editSectionById({
              data,
              config: serverInfo
            });
          }
        } else {
          return;
        }
      } else {
        if (isTemplate) {
          data.articleTypeId = id;
          res = await api_addArticleTypeSection({
            data,
            config: serverInfo
          });
        } else {
          data.articleId = id;
          res = await api_addSection({
            data,
            config: serverInfo
          });
        }
      }
      if (res) {
        onClose && onClose(res);
      }
    } catch (e) {
      console.log("---------", e);
    } finally {
      setExampleValue("");
      setContextValue("");
      setCheckedKeys([]);
    }
  };
  const drawerClose = () => debounceClose(handleClose);
  return (
    <Drawer
      width={"430px"}
      title={
        <Flex justify="space-between">
          <span>写作配置</span>
          <CloseOutlined onClick={drawerClose} />
        </Flex>
      }
      onClose={drawerClose}
      closable={false}
      destroyOnClose
      open={open}
    >
      <div
        className="pb-[18px] w-full font-bold text-[#2A2A2A]"
        style={{ borderBottom: "1px solid #EEEEEE" }}
      >
        {title}
      </div>
      <div className="mt-[16px]">
        <label>内容要求</label>
        <TextArea
          showCount
          maxLength={10000}
          value={contextValue}
          onChange={onContextChange}
          placeholder="请输入内容要求"
          style={{ height: 140, resize: "none", marginTop: 8 }}
        />
      </div>
      <div className="mt-[16px]">
        <label>参考示例</label>
        <TextArea
          showCount
          maxLength={10000}
          value={exampleValue}
          onChange={onExampleChange}
          placeholder="请输入参考示例"
          style={{ height: 140, resize: "none", marginTop: 8 }}
        />
      </div>
      <Flex justify="space-between" className="mt-[30px]">
        <label>选择素材类型</label>

        <div className="text-[#305EBA] relative">
          <div
            className="cursor-pointer"
            onClick={() => setShowTree(!showTree)}
          >
            <PlusCircleOutlined className="mr-[4px]" />
            选择素材类型
          </div>
          <div className="absolute top-[26px] right-[-6px] w-[200px] shadow-lg">
            {showTree && (
              <Tree
                checkable
                onExpand={onExpand}
                expandedKeys={expandedKeys}
                autoExpandParent={autoExpandParent}
                onCheck={onCheck}
                checkedKeys={checkedKeys}
                treeData={treeData}
              />
            )}
          </div>
        </div>
      </Flex>
      {checkNodeLabels?.length > 0 &&
        checkNodeLabels.map((label) => {
          return (
            <div className="w-[350px] h-[32px] mt-[8px] border-[1px] border-solid border-[#eeeeee] px-[8px] flex items-center">
              <img src={File} width={14} height={14} className="mr-[8px]" />
              {label}
            </div>
          );
        })}
    </Drawer>
  );
};

export default SectionDrawer;
