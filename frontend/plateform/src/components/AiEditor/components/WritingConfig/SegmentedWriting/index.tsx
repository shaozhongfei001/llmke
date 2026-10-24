import { useCallback, useState, useMemo, useEffect, useRef } from "react";
import { v4 as uuid } from "uuid";
import {
  Button,
  Flex,
  Form,
  Select,
  message,
  Modal,
  Table,
  Tooltip,
  Popconfirm
} from "antd";
import type { TableProps } from "antd";
import { CellEditorTable, ProTable } from "@ant-design/pro-components";
import { BetaSchemaForm } from "@ant-design/pro-form";
import {
  CaretRightOutlined,
  PlusOutlined,
  DeleteOutlined,
  CaretDownOutlined,
  ExclamationCircleFilled,
  InfoCircleFilled,
  CaretRightFilled,
  CaretDownFilled,
  ControlOutlined,
  DatabaseOutlined
} from "@ant-design/icons";
import ProcessDrawer from "@root/src/components/progressDrawer";
import w2 from "../../../assets/icon/icon-upload-material.svg";
import w1 from "../../../assets/icon/icon-material-base.svg";
import plusBlue from "@root/src/assets/img/plusBlue.png";
import { useStateStore } from "@root/src/components/AiEditor/core/states/useStateStore";
import {
  api_queryMaterialType,
  api_getArticleById,
  api_retryParseMaterialUsing,
  api_getArticleMaterialList,
  api_getArticleTypeDetails,
  api_deleteSectionByIds,
  api_getDatabase,
  fetchKnowledgeBase
} from "@root/src/components/AiEditor/core/services/servers";
import useAiEditorOperators from "@root/src/components/AiEditor/core/operators/useAiEditorOperators";
import { createTemplateForm } from "@root/src/components/AiEditor/components/Sidebar/util";
import UploadFileType, {
  dealOptions,
  ChooseMaterialType,
  handleConfirmFiles,
  UPLOAD_TYPE
} from "@root/src/components/UploadFileType";
import ChooseMaterial from "../FullWriting/components/ChooseMaterial";

import { UPLOAD_EVENTS } from "@root/src/components/UploadFileType/UploadParse";
import SectionDrawer from "../../SectionDrawer/index.tsx";
import { EDITOR_EVENT_NAME, editorEventBus } from "../../../editorEventBus";
import RenderMaterialType from "./components/material.tsx";
import SelectKnowledgeBase from "./components/konwledgeBase.tsx";
import {
  ContentSourceType,
  OutlineType,
  MaterialItemType,
  MaterialType
} from "./type.ts";
import "./index.less";
import MaterialSelect from "./components/materialSelect.tsx";
import SelectMaterialModal from "@root/src/components/AiEditor/components/WritingConfig/components/SelectMaterialModal";
import { useNavigate } from "react-router-dom";

const { useForm } = Form;
const { confirm } = Modal;
interface ISegmentedWriting {
  open: boolean;
  onClose: () => void;
}
let spollingTimer: undefined | number | null = undefined;
enum ProcessType {
  BASIC_INFO = 1,
  GUIDELINES_MATERAILS = 2,
  GERNERATE_DOC = 3
}

const overlayInnerStyle = {
  color: "#2A2A2A"
};

export const SegmentedWriting = ({ open, onClose }: ISegmentedWriting) => {
  const { serverInfo, projectData, setProjectData, setWritingSettingOpen } =
    useStateStore();
  const navigator = useNavigate();

  const { articleSettingSave } = useAiEditorOperators();
  const [curItemKey, setCurItemKey] = useState(ProcessType.BASIC_INFO);
  const [drawerTitleList, setDrawerTitleList] = useState([
    {
      key: ProcessType.BASIC_INFO,
      value: "场景基本信息",
      isEdit: false
    },
    {
      key: ProcessType.GUIDELINES_MATERAILS,
      value: "大纲及素材",
      isEdit: false
    },
    {
      key: ProcessType.GERNERATE_DOC,
      value: "生成文章",
      isEdit: false
    }
  ]);
  const [isShowRepeatCheckModal, setIsShowRepeatCheckModal] =
    useState<boolean>(false);
  const [repeatList, setRepeatList] = useState<Array<any>>([]);

  // ========================基本信息========================
  const [form] = useForm();
  const [formSchema, setFormSchema] = useState<any>([]); // 存储表单的 schema
  const [originDoc, setOriginDoc] = useState({});
  const [title, setTitle] = useState("");

  // =====================素材及大纲========================
  const [expandedRowKeys, setExpandedRowKeys] = useState<any[]>();
  const [outlines, setOutlines] = useState<OutlineType[]>([]);
  // 分段写作封面
  const coverRef = useRef();

  const [materialTypes, setMaterialTypes] = useState<any[]>([]);

  //上传｜选择 后的素材列表,前端展示
  const [materialList, setMaterialList] = useState<any[]>([]);

  const [uploadModalOpen, setUploadModalOpen] = useState<boolean>(false);

  const [allExpand, setAllExpand] = useState<boolean>(false);

  // 从素材库选择素材时modal控制
  const [materialLibraryModalOpen, setMaterialLibraryModalOpen] = useState<{
    materialLibraryVisible: boolean;
    materialSelectTypeVisible: boolean;
    materialSelectList: any[];
  }>({
    materialLibraryVisible: false,
    materialSelectTypeVisible: false,
    materialSelectList: []
  });

  const [sectionDrawer, setSectionDrawer] = useState<{
    visible: boolean;
    sectionId?: number;
    id?: string;
    title?: string;
  }>({
    visible: false,
    sectionId: undefined,
    id: undefined
  });

  const [databaseModal, setDatabseModal] = useState<{
    visible: boolean;
    tableList: any[];
    companyName?: string;
  }>({
    visible: false,
    tableList: []
  });

  const [selectKonwledgeBaseOptions, setSelectKonwledgeBaseOptions] = useState(
    []
  );

  //=====================文章生成=====================
  const [selectedRowKeys, setSelectedRowKeys] = useState<any[]>([]);
  const [generateExpandedRowKeys, setGenerateExpandedRowKeys] = useState<any[]>(
    []
  );
  const rowSelection: TableProps<OutlineType>["rowSelection"] = {
    selectedRowKeys,
    onChange: (selectedRowKeys: React.Key[]) => {
      setSelectedRowKeys([...selectedRowKeys]);
    }
  };

  useEffect(() => {
    (async () => {
      await getMaterialType(); //获取素材类型
      const options = await fetchKnowledgeBase(); //获取知识库列表
      setSelectKonwledgeBaseOptions(options);
    })();
    return () => {
      spollingTimer && clearInterval(spollingTimer);
    };
  }, []);

  useEffect(() => {
    if (open && projectData.article_type) {
      getTemplateDetail();
      if (projectData?.id) {
        getDocDetail(projectData?.id as unknown as number);
      }
    }
  }, [open, projectData?.id, projectData.article_type]);

  //获取模版详情
  const getTemplateDetail = async () => {
    try {
      const res = await api_getArticleTypeDetails({
        data: {
          id: projectData.article_type
        },
        config: serverInfo
      });
      const { paramsSchema, name } = res;
      const temp_schema = JSON.parse(paramsSchema)?.uiSchema || [];
      const schema = createTemplateForm(temp_schema);
      setFormSchema(schema);
      setTitle(name);
    } catch (e) {
      console.log("getTemplateDetail------> e");
    }
  };

  // 获取文章详情
  const getDocDetail = async (id: number) => {
    const docDetail = await api_getArticleById({
      data: {
        articleId: id
      },
      config: serverInfo
    });
    if (docDetail) {
      if (!form) return;
      form.setFieldsValue({
        ...docDetail.extraParams
      });
      setOriginDoc(docDetail);
    }
  };

  // 基本信息保存
  const saveBasicInfo = async () => {
    form.validateFields().then(async (data) => {
      let params: any = {};
      if (projectData?.id) {
        params = {
          ...originDoc,
          extraParams: {
            ...data
          },
          outlines: {
            ...originDoc.outlines,
            paragraphs:
              outlines?.length > 0
                ? outlinesTransform(outlines)
                : originDoc?.outlines?.paragraphs
          }
        };
      } else {
        params = {
          extraParams: {
            ...data
          },
          title: data?.title || "",
          articleTypeId: projectData.article_type,
          articleTypeVersionId: projectData.article_type_version,
          outlineGenType: 3,
          articleType: projectData.article_type_mode
        };
      }
      const settingRes = await articleSettingSave(params);

      setProjectData((p) => {
        return {
          ...p,
          id: settingRes.id
        };
      });

      const docData = await api_getArticleById({
        data: {
          articleId: settingRes?.id
        },
        config: serverInfo
      });
      setOriginDoc(docData);
      recordStepStatus();
      setCurItemKey(ProcessType.GUIDELINES_MATERAILS);

      //处理大纲数据
      const selKeys: string[] = [];
      const newOutLines = outlinesConvert(
        docData?.outlines?.paragraphs || [],
        selKeys
      );

      coverRef.current = (docData?.outlines || {})?.coverPage;
      setOutlines(newOutLines);
      setSelectedRowKeys([...selKeys]);
      // 处理素材初始化数据
      const materialInDocs = extractMertailIdsFromDocDetail(
        docData?.outlines?.paragraphs || []
      );
      materialInDocs?.size > 0 &&
        getMaterialListByIds(materialInDocs, true, newOutLines);
    });
  };

  // 数据回填时，处理materialList,
  // 返回素材 idList
  const extractMertailIdsFromDocDetail = (paragraphs: any[]): any => {
    const uniqueRef = new Map(); // 使用 Set 来存储唯一的 refIds

    function traverse(paragraphs: any[]) {
      paragraphs.forEach((p: any) => {
        // 如果有子段落，递归调用
        if (p.subParagraphs) {
          traverse(p.subParagraphs);
        }
        // 如果当前节点有 contentSources，遍历其中的 refIds
        if (p.contentSources) {
          p.contentSources.forEach((source: any) => {
            if (source.sourceType == "materials" && source.refIds?.length > 0) {
              source.refIds.forEach((refId: any, index: number) => {
                if (!uniqueRef.has(refId)) {
                  uniqueRef.set(Number(refId), {
                    name: source.refNames[index],
                    type: [source.materialTypeIds[index]]
                  });
                }
              });
            }
          });
        }
      });
    }

    traverse(paragraphs);
    return uniqueRef; // 将 Set 转换为数组并返回
  };

  // 根据ids查询素材列表，去重塞入素材列表
  // isOrigin == true 来自文档素材，不需要填充到大纲中
  const getMaterialListByIds = async (
    ids: any,
    isOrigin = false,
    newOutLines?: any
  ) => {
    try {
      const id = isOrigin ? Array.from(ids.keys()) : ids;
      const res = await api_getArticleMaterialList({
        data: {
          id: id.join(","),
          pageSize: 999,
          pageNo: 1
        },
        config: serverInfo
      });
      if (res?.details) {
        const deleteFiles = [];
        let list = (res?.details || []).map((m: any) => {
          const { id, fileName, state, materialType } = m;
          return {
            id,
            fileName,
            state,
            material_type: materialType
          };
        });
        if (isOrigin) {
          for (const [key, value] of ids) {
            if (!list.map((li) => li.id).includes(key)) {
              deleteFiles.push({
                id: key,
                fileName: value.name,
                state: 6, //删除，丢失
                material_type: value.type
              });
            }
          }
          list = [...list, ...deleteFiles];
          if (deleteFiles?.length > 0) {
            const idList = deleteFiles.map((li) => li.id);
            removeDeletedMertial(idList, newOutLines);
          }
        } else {
          // 上传或选择素材后，填充到outline
          const insertM = list.filter((l) => l.state == 3);
          setNewMaterialInOutline(insertM);
        }
        const ll = upsertMaterials(materialList, list);
        setMaterialList([...ll]);
      }
    } catch (error) {
      console.log("getMaterialListByIds err --->", error);
    }
  };
  // 删除已丢失的素材
  const removeDeletedMertial = (ids: number[], newOutLines: any) => {
    function traverse(paragraphs: OutlineType[]) {
      paragraphs.forEach((p: OutlineType) => {
        if (p.relatedMaterials) {
          for (const [key, value] of p.relatedMaterials) {
            const newVal = value.filter((v) => !ids.includes(v.fileId));
            p.relatedMaterials.set(key, newVal);
          }
        }

        // 如果有子段落，递归调用
        if (p.children) {
          traverse(p.children);
        }
      });
    }
    traverse(newOutLines);
    setOutlines([...newOutLines]);
  };

  //上传完成后，将解析成功的素材数据填充到大纲
  const setNewMaterialInOutline = (list: MaterialItemType[]) => {
    function traverse(paragraphs: OutlineType[]) {
      paragraphs.forEach((p: OutlineType) => {
        if (p.relatedMaterials) {
          list.forEach((li: MaterialItemType) => {
            li.material_type.forEach((t: number) => {
              if (p.relatedMaterials?.has(t)) {
                const file = p.relatedMaterials.get(t) || [];
                const newFile = file
                  ?.filter((f) => f.fileId !== li.id)
                  .concat({
                    fileId: Number(li.id),
                    fileName: li.fileName
                  });
                p.relatedMaterials.set(t, newFile);
              }
            });
          });
        }
        if (p.children) {
          traverse(p.children);
        }
      });
    }
    traverse(outlines);
    setOutlines((pre) => [...pre]);
  };

  // 素材列表更新素材
  const upsertMaterials = (
    materialList: MaterialItemType[],
    newList: MaterialItemType[]
  ) => {
    const materialMap = new Map();

    // 将 materialList 中的材料以 id 为键存入 Map 中
    materialList.forEach((item: MaterialItemType) => {
      materialMap.set(item.id, item);
    });

    // 遍历newList，根据是否存在于 Map 中来替换或插入
    newList.forEach((item: MaterialItemType) => {
      materialMap.set(item.id, item); // 替换或插入
    });

    // 将 Map 转回数组
    return Array.from(materialMap.values());
  };

  // 传素材类型id，在素材类型里查对应的素材IdItem
  const findMaterialItemById = (id: number) => {
    let type: any;
    const traverse = (materialType: MaterialType[]) => {
      materialType.some((m: MaterialType) => {
        if (m.id == id) {
          type = m;
          return true;
        }
        if (m.subTypeList) {
          traverse(m.subTypeList);
        }
      });
    };
    traverse(materialTypes);
    return type;
  };

  // 大纲数据转换 增加id, children，relatedMaterials
  const outlinesConvert = (data: any[], selectRowKey: string[]) => {
    return data.map((item) => {
      const id = uuid();
      let relatedMaterials;
      if (item.contentOperation == "1") {
        // 回填第三步大纲选中
        selectRowKey.push(id);
      }
      if (item?.section?.materialType?.length > 0) {
        //处理原始数据中 关联素材
        relatedMaterials = relatedMaterialsFromOutlineContentSources(
          item?.section?.materialType,
          item.contentSources
        );
      }
      const newItem: OutlineType = {
        ...item,
        id,
        relatedMaterials,
        children: item.subParagraphs
          ? outlinesConvert(item.subParagraphs, selectRowKey)
          : [] // 重命名并递归处理子节点
      };
      return newItem;
    });
  };

  //将接口中大纲字段的ContentSources转换为relatedMaterials
  // relatedMaterials?: Map<
  //   number,
  //   {
  //     fileId: number;
  //     fileName: string;
  //   }[]
  //  >;
  const relatedMaterialsFromOutlineContentSources = (
    materialTypes: number[],
    contentSources: ContentSourceType[]
  ) => {
    const relatedM = new Map();
    materialTypes.forEach((m: number) => {
      const files: {
        fileId: number;
        fileName: string;
      }[] = [];
      if (contentSources && contentSources?.length > 0) {
        contentSources.forEach((source: ContentSourceType) => {
          if (source.sourceType == "materials") {
            (source?.materialTypeIds || []).forEach(
              (s: number, index: number) => {
                if (s == m) {
                  files.push({
                    fileId: Number(source.refIds[index]),
                    fileName: source.refNames[index]
                  });
                }
              }
            );
          }
        });
      }
      relatedM.set(m, files);
    });
    return relatedM;
  };

  // 删除大纲
  const loopDataSourceDelete = (
    data: OutlineType[],
    id: React.Key | undefined
  ): OutlineType[] => {
    return data
      .map((item) => {
        if (item.id !== id) {
          if (item.children) {
            const newChildren = loopDataSourceDelete(item.children, id);
            return {
              ...item,
              children: newChildren.length > 0 ? newChildren : undefined
            };
          }
          return item;
        }
        return null;
      })
      .filter(Boolean) as OutlineType[];
  };

  // 增加大纲
  const loopDataSourceAdd = (
    data: OutlineType[],
    id: React.Key | undefined,
    level: number = 0
  ): OutlineType[] => {
    return data.map((item) => {
      if (item.id == id) {
        item.children = item.children || [];
        item.children.push({
          id: uuid()
        });
        // if (level < 2) {
        //   item.children = item.children || [];
        //   item.children.push({
        //     id: uuid()
        //   });
        // } else {
        //   message.info("大纲最多只支持三级"); // 提示用户
        // }
      } else if (item.children) {
        item.children = loopDataSourceAdd(item.children, id, level + 1);
      }
      return item;
    });
  };

  const addRow = () => {
    setOutlines((pre: any) => {
      return [...pre, { id: uuid() }];
    });
  };

  const allOutlineIds = useMemo(() => {
    const ids: string[] = [];
    const traverse = (data: any[]) => {
      data.forEach((item: OutlineType) => {
        const { id } = item;
        ids.push(id);
        if (item.children) {
          traverse(item.children);
        }
      });
    };
    traverse(outlines);

    return ids;
  }, [outlines]);

  const selectOptions = useMemo(() => {
    return (
      materialList
        .filter((m: MaterialItemType) => m.state == 3)
        .map((li: MaterialItemType) => {
          return {
            label: li.fileName,
            value: li.id
          };
        }) || []
    );
  }, [materialList]);

  // 可编辑大纲 cols
  const columns: any[] = useMemo(() => {
    return [
      {
        title: "标题",
        dataIndex: "title",
        width: "600px",
        render: (_: string, record: OutlineType) =>
          renderTitle(record, "hasSectionPrompt")
      },
      {
        title: "关联素材",
        dataIndex: "materials",
        editable: false,
        maxWidth: "300px",
        render: (_: any, record: OutlineType) => {
          const { children, relatedMaterials, section } = record;
          const obj = {} as any;
          if (relatedMaterials) {
            const entriesArray = Array.from(relatedMaterials.entries()) as any;
            entriesArray.forEach(
              ([key, value]: [key: number, value: Array<any>]) => {
                obj[key] = [...value];
              }
            );
          }
          const relations = JSON.parse(JSON.stringify(obj));
          return (
            <div className="material-select-wrap">
              <MaterialSelect
                record={record}
                options={selectOptions}
                relations={relations}
                findMaterialItemById={findMaterialItemById}
                selectMaterials={selectMaterials}
              />
            </div>
          );
        }
      },
      {
        title: "关联知识库",
        dataIndex: "konwledgeBase",
        editable: false,
        maxWidth: "300px",
        render: (_: any, record: OutlineType) => {
          const { children, contentSources } = record;
          const knowledge_base = (contentSources || []).filter(
            (c) => c.sourceType == "knowledge_base"
          );
          if (!(children && children.length > 0)) {
            return (
              <SelectKnowledgeBase
                className="relateMaterials"
                id={record.id}
                knowledge_base={knowledge_base}
                options={selectKonwledgeBaseOptions}
                setOutlines={setOutlines}
              />
            );
          }
          return <div className="relateMaterials"></div>;
        }
      },
      {
        title: "操作",
        dataIndex: "操作",
        width: "150px",
        align: "left",
        editable: false,
        render: (_: string, record: OutlineType) => {
          const { contentSources, title } = record;
          const itemHaveDatabase = (contentSources || []).filter(
            (c) => c.sourceType == "database"
          );
          return [
            <Flex
              className="relateMaterials"
              gap={"20px"}
              justify="start"
              align="center"
            >
              <Tooltip
                title="添加子标题"
                color="#fff"
                overlayInnerStyle={overlayInnerStyle}
              >
                <PlusOutlined
                  className="text-[#555555] hover:text-[#055AFF]"
                  onClick={() => {
                    setOutlines(loopDataSourceAdd(outlines, record.id, 0));
                  }}
                />
              </Tooltip>

              {!(record.children && record.children.length > 0) &&
                title &&
                title.trim().length > 0 && (
                  <Tooltip
                    title="配置"
                    color="#fff"
                    overlayInnerStyle={overlayInnerStyle}
                  >
                    <ControlOutlined
                      className="text-[#555555] hover:text-[#055AFF]"
                      onClick={() => {
                        setSectionDrawer({
                          visible: true,
                          sectionId: record.sectionId,
                          title: title,
                          id: record.id
                        });
                      }}
                    />
                  </Tooltip>
                )}
              {itemHaveDatabase?.length > 0 && (
                <Tooltip
                  title="查看数据表"
                  color="#fff"
                  overlayInnerStyle={overlayInnerStyle}
                >
                  <DatabaseOutlined
                    className="text-[#555555] hover:text-[#055AFF]"
                    onClick={() => viewDataBase(itemHaveDatabase)}
                  />
                </Tooltip>
              )}
              <Popconfirm
                title="删除"
                description="是否确认删除"
                onConfirm={async () => {
                  const res = await deleteSection(record);
                  if (res) {
                    setOutlines(loopDataSourceDelete(outlines, record.id));
                  }
                }}
                okText="确认"
                cancelText="取消"
                cancelButtonProps={{
                  style: {
                    borderRadius: "4px",
                    color: "#555",
                    borderColor: "#EEEEEE"
                  }
                }}
                okButtonProps={{
                  style: {
                    background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                    color: "#fff",
                    border: "none",
                    borderRadius: "4px"
                  }
                }}
                overlayInnerStyle={{
                  width: "224px"
                }}
                disabled={!(record?.title && record?.title?.trim()?.length > 0)}
                placement="topLeft"
              >
                <Tooltip
                  title="删除"
                  color="#fff"
                  overlayInnerStyle={overlayInnerStyle}
                >
                  <DeleteOutlined
                    className=" text-[#555555] hover:text-[#055AFF]"
                    onClick={async (e) => {
                      if (
                        !(record?.title && record?.title?.trim()?.length > 0)
                      ) {
                        e.stopPropagation();
                        const res = await deleteSection(record);
                        if (res) {
                          setOutlines(
                            loopDataSourceDelete(outlines, record.id)
                          );
                        }
                      }
                    }}
                  />
                </Tooltip>
              </Popconfirm>
            </Flex>
          ];
        }
      }
    ];
  }, [materialTypes, outlines, materialList, originDoc]);

  const databaseCol = useMemo(() => {
    return [
      {
        title: "客户名称",
        dataIndex: "queryKey",
        key: "queryKey"
      },
      {
        title: `${databaseModal.companyName}`,
        dataIndex: "queryValue",
        key: "queryValue"
      }
    ];
  }, [databaseModal]);

  const viewDataBase = async (itemHaveDatabase: any) => {
    console.log("------ori", originDoc, itemHaveDatabase);
    try {
      const res = await api_getDatabase({
        data: {
          params: {
            companyName: originDoc?.extraParams?.companyName,
            indexNames: itemHaveDatabase[0].refIds
          }
        },
        config: serverInfo
      });
      if (res) {
        const list = Object.keys(res).map((key) => {
          return {
            queryKey: key,
            queryValue: res[key]
          };
        });

        setDatabseModal({
          visible: true,
          tableList: list,
          companyName: originDoc?.extraParams?.companyName || ""
        });
      }
    } catch (e) {
      console.log("get database error--------->");
    }
  };

  const getMaxTagTextLength = (len: number) => {
    return len <= 1 ? 21 : 9;
  };

  const getText = (record: any, key: string) => {
    const { section, title } = record;
    return section && section[key] ? <b>{title}</b> : <span>{title}</span>;
  };

  const renderTitle = (record: any, key: string) => {
    const level = getLevel(record, outlines, 0) || 0;
    return (
      <>
        {record?.title?.trim()?.length > 0 ? (
          <span
            className={`outline-title-${key}`}
            style={{
              paddingLeft: `${record.children && record.children.length > 0 ? "" : `${22}px`}`
            }}
          >
            {getText(record, key)}
          </span>
        ) : (
          <span className="text-[#FF4D4F] outline-title">未填写标题</span>
        )}
      </>
    );
  };

  const getLevel = (record: any, items: Array<any>, level: number) => {
    let list = [] as any;
    if (items && items.length) {
      if (items.some((i: any) => i.id === record.id)) {
        record.level = level;
        return level;
      } else {
        items.forEach((i: any) => {
          if (i.children) {
            list = list.concat(i.children);
          }
        });
        return getLevel(record, list, level + 1);
      }
    }
    return level;
  };

  const stopPropagation = (e) => {
    e.stopPropagation();
  };

  useEffect(() => {
    // 禁用关联素材table cell的双击事件
    if (curItemKey == ProcessType.GUIDELINES_MATERAILS) {
      document.querySelectorAll(".relateMaterials").forEach((cell) => {
        const parent = cell.parentElement;
        parent?.addEventListener("dblclick", stopPropagation);
      });
    }
    return () => {
      document.querySelectorAll(".relateMaterials").forEach((cell) => {
        const parent = cell.parentElement;
        parent?.removeEventListener("dblclick", stopPropagation);
      });
    };
  }, [curItemKey, outlines]);

  // console.log("++++++outlines", outlines);

  // 选择关联素材
  const selectMaterials = (
    selValues: any[],
    record: OutlineType,
    material: any
  ) => {
    function traverse(paragraphs: OutlineType[]) {
      paragraphs.forEach((p: OutlineType) => {
        if (p.id == record.id && p.relatedMaterials) {
          const files = selValues.map((sel) => {
            return {
              fileId: sel.value,
              fileName: sel.label
            };
          });
          p.relatedMaterials.set(material, files);
        }

        // 如果有子段落，递归调用
        if (p.children) {
          traverse(p.children);
        }
      });
    }
    traverse(outlines);
    setOutlines([...outlines]);
  };

  // 获取素材类型
  const getMaterialType = async () => {
    const res = await api_queryMaterialType({
      data: {},
      config: serverInfo
    });
    setMaterialTypes(res?.data);
  };

  useEffect(() => {
    if (curItemKey !== ProcessType.GUIDELINES_MATERAILS) {
      spollingTimer && clearInterval(spollingTimer);
      return;
    }
    if (materialList?.length) {
      if (spollingTimer) {
        clearInterval(spollingTimer);
        startSpolling(materialList);
      } else {
        startSpolling(materialList);
      }
    }
  }, [materialList, curItemKey]);

  const startSpolling = (curData: any[]) => {
    spollingTimer = setInterval(() => {
      const ids = curData
        .filter(
          (item: any) => item.state === 1 || item.state === 2 || !item.state
        )
        .map((item: any) => item.id);
      if (ids.join(",")) {
        getMaterialListByIds(ids);
      } else {
        spollingTimer && clearInterval(spollingTimer);
        spollingTimer = null;
      }
    }, 5000);
  };

  const handleUploadEvents = (action: string, payload: any) => {
    console.log("action============", action);
    console.log("payload", payload);
    switch (action) {
      case UPLOAD_TYPE.MODAL_CLOSE:
        {
          // todo  上传组件返回给我一堆素材id
          // 根据id获取素材列表，轮询直到所有state == 3
          const ids = payload.map((p) => p.id);
          getMaterialListByIds(ids);
          setUploadModalOpen(false);
        }

        break;
      case UPLOAD_EVENTS.MODAL_ONLY_CLOSE:
        setUploadModalOpen(false);
        break;
      case UPLOAD_TYPE.CONFIRM: {
        const fileList: any[] = payload.map((f) => {
          const { id, fileName, state, materialType } = f;
          return {
            id,
            uid: id,
            fileName,
            name: fileName,
            state,
            material_type: materialType,
            chooseType:
              materialType?.length > 0
                ? materialType.map((t) => {
                    const ids = findParentIdById(materialTypes, t);
                    return ids ? [ids, t] : [t];
                  })
                : []
          };
        });
        setMaterialLibraryModalOpen({
          materialLibraryVisible: false,
          materialSelectTypeVisible: true,
          materialSelectList: fileList
        });
      }
    }
  };
  // 给每个从素材库选中的文件，素材类型 加上parentId，用于数据回填
  const findParentIdById = (data, targetId): any => {
    for (const item of data) {
      console.log("+++++++", item, targetId);
      if (item.id === targetId) {
        return item.parentId; // 找到目标id，返回parentId
      }
      if (item.subTypeList) {
        const parentId = findParentIdById(item.subTypeList, targetId);
        if (parentId !== undefined) {
          return parentId; // 在子节点中找到，返回parentId
        }
      }
    }
    return undefined; // 如果没有找到，返回undefined
  };

  // 素材删除
  const deleteMertial = (id: number) => {
    setMaterialList((pre: any) => {
      return pre.filter((v: any) => v.id !== id);
    });
    // 删除掉大纲中关联的当前id的素材
    function traverse(paragraphs: OutlineType[]) {
      paragraphs.forEach((p: OutlineType) => {
        // 节点的关联素材也要被删掉
        if (p.relatedMaterials) {
          for (const [key, value] of p.relatedMaterials) {
            const newVal = value.filter((v) => v.fileId !== id);
            p.relatedMaterials.set(key, newVal);
          }
        }
        // 如果有子段落，递归调用
        if (p.children) {
          traverse(p.children);
        }
      });
    }
    traverse(outlines);
    setOutlines([...outlines]);
  };

  // 素材重新解析
  const retryParse = async (id: number) => {
    const res = await api_retryParseMaterialUsing({
      data: { id },
      config: {
        ...serverInfo,
        enableMock: false
      }
    });
    if (res) {
      // todo 如果解析中，轮询
      setMaterialList((pre: any[]) => {
        const cur = pre.find((item) => item.id === id);
        cur.state = 2;
        const data = [...pre];
        return data;
      });
    }
  };

  //section 新增/编辑完后
  const changeSection = (section: any) => {
    function traverse(paragraphs: OutlineType[]) {
      paragraphs.forEach((p: OutlineType) => {
        //更新section
        if (sectionDrawer.id == p.id) {
          p.sectionId = section.id;
          p.section = {
            id: section.id,
            materialType: section.materialType,
            hasSectionPrompt: section.sectionPrompt?.length > 0 ? true : false,
            hasContent: p?.section?.hasContent ? p?.section?.hasContent : false
          };

          //更新素材
          if (section.materialType?.length > 0) {
            const tempMap = new Map();
            section.materialType.forEach((type) => {
              if (p.relatedMaterials) {
                if (p.relatedMaterials?.has(type)) {
                  //section中有原类型，素材搬过去
                  const val = p.relatedMaterials.get(type);
                  tempMap.set(type, val);
                } else {
                  //没有的话，放个空数组
                  tempMap.set(type, []);
                }
              } else {
                tempMap.set(type, []);
              }
            });
            p.relatedMaterials = tempMap;
          } else {
            // 素材类型为空，删除所有关联素材
            delete p.relatedMaterials;
          }
        }
        if (p.children) {
          traverse(p.children);
        }
      });
    }
    traverse(outlines);
    setOutlines([...outlines]);
    setSectionDrawer({
      visible: false,
      sectionId: undefined,
      title: undefined,
      id: undefined
    });
  };

  const deleteSection = async (record: OutlineType) => {
    const sectionIds: number[] = [];
    if (record?.sectionId) {
      sectionIds.push(record?.sectionId);
    }
    function traverse(paragraphs: OutlineType[]) {
      paragraphs.forEach((p: OutlineType) => {
        if (p?.sectionId) {
          sectionIds.push(p.sectionId);
        }
        // 如果有子段落，递归调用
        if (p.children) {
          traverse(p.children);
        }
      });
    }
    if (record?.children) {
      traverse(record?.children);
    }
    if (sectionIds.length > 0) {
      const newOutlines = loopDataSourceDelete(outlines, record.id);
      const otls = outlinesTransform(newOutlines);
      const res = await api_deleteSectionByIds({
        data: {
          ids: sectionIds.join(","),
          articleId: projectData.id,
          type: "article",
          params: {
            outlines: {
              ...originDoc.outlines,
              coverPage: coverRef.current,
              paragraphs: otls
            }
          }
        },
        config: serverInfo
      });
      return res;
    } else {
      return true;
    }
  };

  // 点击下一步之后，记录前面步骤已编辑状态
  const recordStepStatus = () => {
    setDrawerTitleList(
      drawerTitleList.map((d) => {
        if (d.key == curItemKey) {
          d.isEdit = true;
        }
        return d;
      })
    );
  };

  const validateMaterial = async () => {
    const validateAllMaterialOfTitle: string[] = [];
    const validatePartMaterialOfTitle: {
      title: string;
      materialId: number;
    }[] = [];
    let isValidTitles = 0;
    function traverse(paragraphs: any[]) {
      paragraphs.some((p: any) => {
        if (!p.title) {
          //校验标题不为空
          ++isValidTitles;
        } else if (p.title && p.title.trim().length == 0) {
          ++isValidTitles;
        }
        if (p.relatedMaterials) {
          const values = p.relatedMaterials.values();
          if (values.some((v) => v.length == 0)) {
            validateAllMaterialOfTitle.push(p.title);
          }
          // if (values.every((v) => v.length == 0)) {
          //   // 如果每个类型素材列表都为空，弹出强提示，不能下一步
          //   validateAllMaterialOfTitle.push(p.title);
          // } else {
          //   // 如果只有一个类型素材列表都为空，弹出弱提示，可以继续
          //   for (const [key, value] of p.relatedMaterials) {
          //     if (value.length == 0) {
          //       validatePartMaterialOfTitle.push({
          //         title: p.title,
          //         materialId: key
          //       });
          //       return;
          //     }
          //   }
          // }
        }
        // 如果有子段落，递归调用
        if (p.children) {
          traverse(p.children);
        }
      });
    }
    traverse(outlines);

    let confrimParams:
      | {
          content: string;
          okText?: string;
          cancelText?: string;
          onOk?: () => void;
        }
      | undefined = undefined;
    if (isValidTitles) {
      confrimParams = {
        content: `检测到${isValidTitles}标题为空，请填写或者删除`
      };
    } else if (validateAllMaterialOfTitle.length > 0) {
      const validateInfo = validateAllMaterialOfTitle[0];
      confrimParams = {
        content: `${validateInfo} 缺少关联素材，缺失可能影响文章生成质量`,
        okText: "继续下一步",
        cancelText: "返回上传",
        onOk: async () => {
          const saveRes = await saveOutlines();
          if (saveRes) {
            recordStepStatus();
            setCurItemKey(ProcessType.GERNERATE_DOC);
          }
        }
      };
    }
    // else if (validatePartMaterialOfTitle.length > 0) {
    //   const validateInfo = validatePartMaterialOfTitle[0];
    //   const materialLabel = findMaterialItemById(validateInfo.materialId);
    //   confrimParams = {
    //     content: `${validateInfo.title} 缺少《${materialLabel?.name}》关联素材，缺失可能影响文章生成质量`,
    //     okText: "继续下一步",
    //     cancelText: "返回上传",
    //     onOk: async () => {
    //       const saveRes = await saveOutlines();
    //       if (saveRes) {
    //         recordStepStatus();
    //         setCurItemKey(ProcessType.GERNERATE_DOC);
    //       }
    //     }
    //   };
    // }
    else {
      const saveRes = await saveOutlines();
      if (saveRes) {
        recordStepStatus();
        setCurItemKey(ProcessType.GERNERATE_DOC);
      }
    }

    if (confrimParams) {
      confirm({
        title: "缺少关联素材",
        icon: <ExclamationCircleFilled />,
        okButtonProps: {
          style: {
            background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
            border: "none",
            color: "#fff"
          }
        },
        onCancel() {
          console.log("Cancel");
        },
        ...confrimParams
      });
    }
  };

  // 筛选大纲cols
  const generateColumns: any[] = useMemo(() => {
    return [
      {
        title: "标题",
        dataIndex: "title",
        render: (_: string, record: OutlineType) =>
          renderTitle(record, "hasContent")
      }
    ];
  }, []);

  const toGenerate = () => {
    setTimeout(() => {
      projectData.id && navigator(`/docWriting/docs/${projectData.id}`);
      editorEventBus.emit(EDITOR_EVENT_NAME.START_WRITE, "");
    }, 0);
    setWritingSettingOpen(false);
  };

  // 前端渲染的大纲数据处理成接口需要的数据，提交到接口
  const outlinesTransform = (data: any[]) => {
    return data.map((item: OutlineType) => {
      if (selectedRowKeys?.includes(item.id)) {
        item.contentOperation = "1";
      } else {
        item.contentOperation = "0";
      }
      const { title, section, sectionId, contentSources, contentOperation } =
        item;

      const newItem: OutlineType = {
        title,
        section,
        sectionId,
        contentOperation
      };
      // 先排除掉 sourceType == "materials"
      let newContentSources = (contentSources || []).filter(
        (c) => c.sourceType !== "materials"
      );
      // 针对 sourceType == "materials"，使用前端编辑的数据替换
      if (item.relatedMaterials) {
        const refIds: any[] = [];
        const refNames: string[] = [];
        const materialTypeIds: number[] = [];

        for (const [key, value] of item.relatedMaterials) {
          value.forEach((v) => {
            refIds.push(v.fileId);
            refNames.push(v.fileName);
            materialTypeIds.push(key);
          });
        }
        newContentSources = [
          ...newContentSources,
          {
            sourceType: "materials",
            refIds,
            refNames,
            materialTypeIds
          }
        ];
      }
      // 有就传，没有就不传，后端不希望 contentSources = []
      if (newContentSources?.length > 0) {
        newItem.contentSources = newContentSources;
      }

      if (item.extraInfo) {
        newItem.extraInfo = item.extraInfo;
      }

      if (item.children) {
        newItem.subParagraphs = outlinesTransform(item.children);
      }
      return newItem;
    });
  };

  const saveOutlines = async () => {
    const otls = outlinesTransform(outlines);

    const params = {
      articleType: projectData.article_type_mode,
      articleTypeId: projectData.article_type,
      articleTypeVersionId: projectData.article_type_version,
      extraParams: {
        ...originDoc.extraParams
      },
      title: originDoc?.title || "",
      id: projectData.id,
      outlines: {
        ...originDoc.outlines,
        coverPage: coverRef.current,
        paragraphs: otls
      }
    };
    console.log("-----final-", outlines, otls);
    const settingRes = await articleSettingSave(params);
    return settingRes;
  };

  const generate = async () => {
    const settingRes = await saveOutlines();
    if (settingRes) {
      recordStepStatus();
      toGenerate();
    }
  };
  // 立即生成 校验
  const checkDataIsHasContent = () => {
    const res = checkHasContent(outlines);
    if (res.length) {
      setRepeatList([...res]);
      setIsShowRepeatCheckModal(true);
    } else {
      generate();
    }
  };

  const closeRepeatCheckModal = () => {
    setIsShowRepeatCheckModal(false);
  };

  const checkHasContent = (items: Array<any>) => {
    function buildNewTree(nodes: Array<any>, selectedNodes: any) {
      return nodes
        .filter((node) => selectedNodes.has(node.id))
        .map((node) => {
          const newNode = { ...node, children: [] };
          if (node.children && Array.isArray(node.children)) {
            const _children = buildNewTree(node.children, selectedNodes);
            if (_children.length) {
              _children.forEach((i) => {
                if (i.children && i.children.length === 0) {
                  delete i.children;
                }
              });
            }
            newNode.children = _children;
          }
          if (newNode.children && newNode.children.length === 0) {
            delete newNode.children;
          }
          return newNode;
        });
    }
    const selectedNodes = new Set();
    retrieveCheck(items, selectedNodes);

    return buildNewTree(items, selectedNodes);
  };

  const dfs = (node: any, parent = null, selectedNodes = new Set()) => {
    const { section, id, children } = node;
    const { selectedRowKeys } = rowSelection;
    if (selectedRowKeys && selectedRowKeys.length) {
      if (
        (section && section.hasContent) ||
        (children &&
          children.some((child: any) => dfs(child, node, selectedNodes)))
      ) {
        if (selectedRowKeys.includes(id)) {
          selectedNodes.add(node.id);
        }
        return true;
      }
    }
    return false;
  };

  const retrieveCheck = (items: Array<any>, selectedNodes: any) => {
    items.forEach((i) => {
      dfs(i, null, selectedNodes);
      if (i.children && i.children.length) {
        retrieveCheck(i.children, selectedNodes);
      }
    });
  };

  const renderRepeatItem = (item: any, level: number) => {
    const { children, title, id, isShowChild } = item;
    return (
      <div key={`item_${id}`}>
        <div
          className="h-6 leading-6 py-3 overflow-hidden select-none"
          style={{ borderBottom: "1px solid #eee" }}
        >
          <span
            className={`inline-block h-6 w-[${level === 0 && !children ? 1 * 20 : level * 20}px]`}
          ></span>
          {children && children.length ? (
            <b>
              {level === 0 ? renderCaret(item) : null}
              {title.trim()}
            </b>
          ) : (
            <span>{title.trim()}</span>
          )}
        </div>
        {(isShowChild || level > 0) && children && children.length
          ? children.map((child: any) => {
              return renderRepeatItem(child, level + 1);
            })
          : null}
      </div>
    );
  };

  const renderCaret = (item: any) => {
    const { isShowChild } = item;

    return isShowChild ? (
      <CaretDownFilled
        className="text-[#888] cursor-pointer mr-1"
        onClick={showHideRepeatItem(item)}
      />
    ) : (
      <CaretRightFilled
        className="text-[#888] cursor-pointer mr-1"
        onClick={showHideRepeatItem(item)}
      />
    );
  };

  const showHideRepeatItem = (item: any) => () => {
    const _item = JSON.parse(JSON.stringify(item));
    _item.isShowChild = !_item.isShowChild;
    const _list = retrieveShowState(repeatList, _item);
    setRepeatList([..._list]);
  };

  const retrieveShowState = (items: any, newItem: any) => {
    const list = [] as any;
    items.forEach((item: any) => {
      const { id, children } = item;
      if (id === newItem.id) {
        item.isShowChild = newItem.isShowChild;
        list.push(item);
      } else {
        if (children && children.length) {
          list.push(
            Object.assign({}, item, {
              children: retrieveShowState(children, newItem)
            })
          );
        } else {
          list.push(item);
        }
      }
    });

    return list;
  };

  const onDoubleClick = () =>
    setTimeout(() => {
      const el = document.querySelector("Input.ant-input") as any;
      if (el && el.focus) {
        el.focus();
      }
    }, 0);

  const renderProcess = useCallback(() => {
    switch (curItemKey) {
      case ProcessType.BASIC_INFO:
        return (
          <div className="flex justify-content-center form-basic-wrap">
            <BetaSchemaForm
              className="w-[50%] m-auto"
              id="template-jindiao"
              layoutType="Form"
              form={form}
              columns={formSchema} // 动态根据选择渲染表单
              submitter={false}
            />
          </div>
        );
      case ProcessType.GUIDELINES_MATERAILS:
        return (
          <>
            <div>
              <span className="text-[#2A2A2A] font-bold">上传素材</span>
              <div className="border-[1px] border-[#D9D9D9] border-dashed h-[106px] w-full bg-[#F9FAFC] mt-[16px] rounded-[2px] flex items-center flex-col">
                <div className="mt-[16px]">
                  <Button
                    size="large"
                    icon={<img src={w2} />}
                    className="mr-[16px] border-[#eeeeee] w-[140px] text-sm rounded-[4px] text-[#055AFF]"
                    onClick={() => setUploadModalOpen(true)}
                  >
                    上传素材
                  </Button>
                  <Button
                    size="large"
                    icon={<img src={w1} />}
                    className="mr-[16px] border-[#eeeeee] w-[140px] text-sm rounded-[4px] text-[#055AFF]"
                    onClick={() =>
                      setMaterialLibraryModalOpen({
                        materialLibraryVisible: true,
                        materialSelectTypeVisible: false,
                        materialSelectList: []
                      })
                    }
                  >
                    从素材库选择
                  </Button>
                </div>
                <div className="text-[12px] text-[#999999] mt-[16px]">
                  支持单篇或批量上传，支持 doc、docx、excel、pdf、txt、ppt格式
                </div>
              </div>
              <Flex className="my-[10px]" wrap gap={6}>
                <RenderMaterialType
                  materialTypes={materialTypes}
                  materialList={materialList}
                  deleteMertial={deleteMertial}
                  retryParse={retryParse}
                  reUpload={() => setUploadModalOpen(true)}
                />
              </Flex>
            </div>
            <div className="mt-[20px] mb-[80px] outlines">
              <span className="text-[#2A2A2A] font-bold">
                大纲{" "}
                <Tooltip
                  title={`${allExpand ? "收起" : "展开"}所有大纲子节点`}
                  color="#fff"
                  overlayInnerStyle={overlayInnerStyle}
                >
                  <div
                    className="one-click-expanded"
                    onClick={() => {
                      if (allExpand) {
                        setExpandedRowKeys([]);
                      } else {
                        setExpandedRowKeys(allOutlineIds);
                      }
                      setAllExpand(!allExpand);
                    }}
                  >
                    {allExpand ? "一键收起" : "一键展开"}
                  </div>
                </Tooltip>
              </span>
              <CellEditorTable
                className="mt-[16px]"
                rowKey={"id"}
                columns={columns}
                value={outlines}
                controlled={true}
                onChange={(data) => {
                  setOutlines([...data]);
                }}
                bordered={false}
                recordCreatorProps={false}
                expandable={{
                  defaultExpandAllRows: true,
                  expandedRowKeys,
                  expandIcon: (expandedInfo) => {
                    const { expanded, record, onExpand } = expandedInfo;
                    if (record.children && record.children?.length > 0) {
                      return expanded ? (
                        <CaretDownOutlined
                          className="mr-1"
                          onClick={(e) => {
                            e.stopPropagation();
                            onExpand(record, e);
                          }}
                        />
                      ) : (
                        <CaretRightOutlined
                          className="mr-1"
                          onClick={(e) => {
                            e.stopPropagation();
                            onExpand(record, e);
                          }}
                        />
                      );
                    } else {
                      return <></>;
                    }
                  },
                  onExpandedRowsChange: (expandedRowKeys) =>
                    setExpandedRowKeys([...expandedRowKeys])
                }}
                onRow={() => ({
                  onDoubleClick
                })}
              />
              <Button
                size="small"
                className="text-text-color2 border-[#EEEEEE] mt-[10px] mb-[20px] w-[94px]"
                icon={<img src={plusBlue} className=" w-[14px] h-[14px]" />}
                onClick={addRow}
              >
                添加标题
              </Button>
            </div>
          </>
        );
      case ProcessType.GERNERATE_DOC:
        return (
          <div className="outlines">
            <span className="text-[#2A2A2A] font-bold">选择模块</span>
            <ProTable
              className="mt-[8px]"
              scroll={{
                x: 960
              }}
              rowKey={(r: any) => String(r.id)}
              search={false}
              columns={generateColumns}
              dataSource={outlines}
              bordered={false}
              rowSelection={{
                type: "checkbox",
                ...rowSelection,
                checkStrictly: false
              }}
              pagination={false}
              options={false}
              expandable={{
                // defaultExpandAllRows: true,
                // expandedRowKeys: generateExpandedRowKeys,
                expandIcon: (expandedInfo) => {
                  const { expanded, record, onExpand } = expandedInfo;
                  if (record.children && record.children?.length > 0) {
                    return expanded ? (
                      <CaretDownOutlined
                        className="mr-[8px]"
                        onClick={(e) => {
                          e.stopPropagation();
                          onExpand(record, e);
                        }}
                      />
                    ) : (
                      <CaretRightOutlined
                        className="mr-[8px]"
                        onClick={(e) => {
                          e.stopPropagation();
                          onExpand(record, e);
                        }}
                      />
                    );
                  } else {
                    return <></>;
                  }
                },
                onExpandedRowsChange: (expandedRowKeys) =>
                  setGenerateExpandedRowKeys([...expandedRowKeys])
              }}
            />
          </div>
        );
    }
  }, [
    curItemKey,
    formSchema,
    originDoc,
    outlines,
    form,
    expandedRowKeys,
    columns,
    generateColumns,
    // materialIdHover,
    materialList,
    selectedRowKeys,
    allExpand
  ]);

  const renderFooter = useCallback(() => {
    switch (curItemKey) {
      case ProcessType.BASIC_INFO:
        return (
          <Flex align="center" justify="flex-end" gap={16}>
            <Button
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                border: "none"
              }}
              onClick={() => {
                saveBasicInfo();
              }}
            >
              下一步
            </Button>
          </Flex>
        );
      case ProcessType.GERNERATE_DOC:
        return (
          <Flex align="center" justify="flex-end" gap={16}>
            <Button
              style={{
                border: "1px solid #ebebeb",
                borderRadius: "4px",
                color: "#555"
              }}
              onClick={async () => {
                const saveRes = await saveOutlines();
                if (saveRes) {
                  setCurItemKey(ProcessType.GUIDELINES_MATERAILS);
                }
              }}
            >
              上一步
            </Button>
            <Button
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                border: "none"
              }}
              onClick={checkDataIsHasContent}
            >
              开始生成
            </Button>
          </Flex>
        );
      default:
        return (
          <Flex align="center" justify="flex-end" gap={16}>
            <Button
              style={{
                border: "1px solid #ebebeb",
                borderRadius: "4px",
                color: "#555"
              }}
              onClick={async () => {
                const saveRes = await saveOutlines();
                if (saveRes) {
                  setCurItemKey(ProcessType.BASIC_INFO);
                }
              }}
            >
              上一步
            </Button>
            <Button
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                border: "none"
              }}
              onClick={() => {
                validateMaterial(); //校验
              }}
            >
              下一步
            </Button>
          </Flex>
        );
    }
  }, [curItemKey, originDoc, selectedRowKeys, outlines]);

  return (
    <div className="w-full h-full">
      <Flex
        vertical
        className="rounded-t-xl bg-white h-full relative box-border"
      >
        {formSchema && (
          <ProcessDrawer
            open={true}
            curItemKey={curItemKey as any}
            clickItem={(item) => {
              setCurItemKey(item.key);
            }}
            onClose={onClose}
            subTitle={title}
            list={drawerTitleList}
            renderFooter={renderFooter()}
          >
            {renderProcess()}
          </ProcessDrawer>
        )}

        <SectionDrawer
          open={sectionDrawer.visible}
          onClose={changeSection}
          sectionId={sectionDrawer.sectionId}
          id={projectData.id}
          title={sectionDrawer.title}
          materialTypes={materialTypes}
          serverInfo={serverInfo}
        />
        <UploadFileType
          open={uploadModalOpen}
          close={() => setUploadModalOpen(false)}
          uploadEvents={handleUploadEvents}
          options={dealOptions(materialTypes)}
        />
        <ChooseMaterial
          open={materialLibraryModalOpen.materialLibraryVisible}
          handleChooseEvent={handleUploadEvents}
          close={() =>
            setMaterialLibraryModalOpen({
              ...materialLibraryModalOpen,
              materialLibraryVisible: false
            })
          }
          defaultData={[]}
        />
        <ChooseMaterialType
          open={materialLibraryModalOpen.materialSelectTypeVisible}
          closeModal={() =>
            setMaterialLibraryModalOpen({
              ...materialLibraryModalOpen,
              materialSelectTypeVisible: false
            })
          }
          handleConfirm={() => {
            handleConfirmFiles(
              materialLibraryModalOpen.materialSelectList,
              serverInfo,
              () =>
                setMaterialLibraryModalOpen({
                  ...materialLibraryModalOpen,
                  materialSelectTypeVisible: false
                }),
              handleUploadEvents
            );
          }}
          fileList={materialLibraryModalOpen.materialSelectList}
          deleteFileFromlist2={(fileName: string) => {
            setMaterialLibraryModalOpen((pre) => {
              const { materialSelectList: preList } = pre;
              return {
                ...pre,
                materialSelectList: (preList || []).filter(
                  (f) => f.fileName !== fileName
                )
              };
            });
          }}
          options={dealOptions(materialTypes)}
          firstMaterialClassify={(checkFristMaterial: boolean) => {
            if (checkFristMaterial) {
              setMaterialLibraryModalOpen((pre) => {
                const { materialSelectList: preList } = pre;
                const curFile = preList[0];
                curFile &&
                  preList.forEach((item) => {
                    item.chooseType = curFile.chooseType;
                  });
                return {
                  ...pre
                };
              });
            }
          }}
          onChange={(value: string, f: any) => {
            setMaterialLibraryModalOpen((pre) => {
              const { materialSelectList: preList } = pre;
              const curFile = preList.find((item) => {
                return item.uid === f.uid;
              });
              curFile.chooseType = value;
              return {
                ...pre
              };
            });
          }}
        />
      </Flex>
      <Modal
        open={databaseModal.visible}
        className="writing-database-modal"
        title={"2024年集团固定资产年报数据表"}
        width="1000px"
        height="700px"
        onCancel={() =>
          setDatabseModal({
            visible: false,
            tableList: []
          })
        }
        footer={
          <Button
            children="关闭"
            style={{
              background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
              color: "#fff",
              border: "none"
            }}
            onClick={() =>
              setDatabseModal({
                visible: false,
                tableList: []
              })
            }
            className="mr-[8px]"
          />
        }
      >
        <div className="bg-[#F0F2F8] h-[600px] py-[20px] px-[60px] overflow-y-auto">
          <Table
            dataSource={databaseModal.tableList}
            className=""
            rowKey={uuid()}
            columns={databaseCol}
            pagination={false}
          />
        </div>
      </Modal>
      <Modal
        open={isShowRepeatCheckModal}
        title={
          <div className="-ml-1">
            <InfoCircleFilled style={{ color: "#faad14" }} />
            <b className="text-base ml-3">选择模块重复</b>
          </div>
        }
        width="400px"
        height="428px"
        closable={false}
        onCancel={closeRepeatCheckModal}
        footer={
          <div className="flex flex-row-reverse gap-4">
            <Button
              children="确认"
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                border: "none"
              }}
              onClick={generate}
              className="mr-[8px]"
            />
            <Button
              children="取消"
              style={{
                border: "1px solid #ebebeb",
                color: "#555"
              }}
              onClick={closeRepeatCheckModal}
              className="mr-[8px]"
            />
          </div>
        }
      >
        <div className="ml-6 text-sm text-[#2a2a2a] mb-3">
          以下模块上次已生成文章，生成的新内容将替换原有内容。
        </div>
        <div className="ml-6 h-80 overflow-y-auto text-[#2a2a2a] text-sm">
          {(repeatList || []).map((item: any) => renderRepeatItem(item, 0))}
        </div>
      </Modal>
    </div>
  );
};

export default SegmentedWriting;
