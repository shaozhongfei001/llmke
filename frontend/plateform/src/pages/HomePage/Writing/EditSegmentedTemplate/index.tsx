import { useCallback, useState, useMemo, useEffect, useRef } from "react";
import { Button, Flex, Modal } from "antd";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { ExclamationCircleFilled, PlusOutlined } from "@ant-design/icons";
import { v4 as uid } from "uuid";
import {
  api_deleteSectionByIds,
  api_applyOutlines
} from "@/components/AiEditor/core/services/servers";
import { useAppPassport } from "@root/src/core/helps";
import Right from "@/components/AiEditor/assets/img/right.png";
import SectionDrawer from "@/components/AiEditor/components/SectionDrawer";
import EditTemplate from "../EditTemplate/index";
import { useServices } from "../TemplateM/common/useServices";
import { useTServices } from "../EditTemplate/common/useTServices";
import { useServices as useServicesEdit } from "./service.ts";
import IconArrowLeft from "@/assets/svg/icon-arrow-left.svg";
import {
  api_editArticleTypeSectionById,
  api_addArticleTypeSection,
  api_applySection
} from "@/components/AiEditor/core/services/servers";
import OutlineCmp, {
  sourceTypes,
  fixRelationsObj,
  findNodesByIds
} from "@/components/AiEditor/components/WritingConfig/SegmentedWriting/components/Outline";
import { OutlineType } from "@/components/AiEditor/components/WritingConfig/SegmentedWriting/type.ts";
import { classifyMaterialToRenderNew } from "@/components/AiEditor/components/WritingConfig/SegmentedWriting//utils.ts";
import "./index.less";

const { confirm } = Modal;
enum ProcessType {
  BASIC_INFO = 1,
  GUIDELINES_MATERAILS = 2
}
const drawerTitleList = [
  {
    key: ProcessType.BASIC_INFO,
    value: "场景基本信息"
  },
  {
    key: ProcessType.GUIDELINES_MATERAILS,
    value: "大纲及素材"
  }
];

const initOriginData = {
  kbs: [],
  folders: [],
  files: []
};
const initialSectionInfo = {
  visible: false,
  row: {}
};
const SegmentedWritingTemplate = () => {
  const { id, version } = useParams();
  const modalType = id && id.indexOf("temp") > -1 ? "add" : "edit";
  const { getToken } = useAppPassport();
  const token: any = getToken();
  const navigator = useNavigate();
  const { queryTemplateById, getVersionInfoById }: any = useServices({});
  const isOnceIn = useRef<boolean>(true);

  const { createArticleType, updateArticleType } = useTServices({});
  const [curItemKey, setCurItemKey] = useState(ProcessType.BASIC_INFO);
  const [sectionData, setSectionData] = useState<any>({
    ...initialSectionInfo
  });
  const [materialTreeData, setMaterialTreeData] = useState<any>({
    ...initOriginData
  });

  const [outlines, setOutlines] = useState<OutlineType[]>([]);
  const [templateInfo, setTemplateInfo] = useState<any>({});
  const [applyLoading, setApplyLoading] = useState(false);
  const [materialList, setMaterialList] = useState<any[]>([]);
  const newMaterialListRef = useRef<any[]>([]);
  // 存储章节依赖关系数据
  const relationsRef = useRef<any>(null);
  const { getSceneAnalysisTree } = useServicesEdit();
  const [analysisTreeOrigin, setAnalysisTreeOrigin] = useState<any[]>([]);
  const editTemplateRef = useRef();

  const location = useLocation();
  const isVersion = useMemo(() => {
    return location.pathname.includes("/docWriting/template/version");
  }, [location]);

  const versionId = useMemo(() => {
    return version ? version.split("-")[0] : "";
  }, [version]);

  const versionTxt = useMemo(() => {
    return version ? version.split("-")[1] : 0;
  }, [version]);

  const serverInfo = useMemo(() => {
    return {
      token: token,
      baseURL: "/cecProxy/"
    };
  }, [token]);

  const getMaterialTree = (originData: any) => {
    console.log("originData:", originData);
    setMaterialTreeData({ ...originData });
  };

  const getTemplateById = async () => {
    try {
      const res = isVersion
        ? await getVersionInfoById.mutateAsync({
            id,
            versionId
          })
        : await queryTemplateById.mutateAsync(id);

      if (res) {
        setTemplateInfo(res);
        const mList: any[] = classifyMaterialToRenderNew(res.contentSources);
        setMaterialList(mList);
        newMaterialListRef.current = [...mList];
        const newOutLines = outlinesConvert(res?.outlines?.paragraphs || []);
        relationsRef.current = fixRelationsObj(newOutLines);
        if (newOutLines?.length == 0) {
          setOutlines([{ id: uid() }, { id: uid() }, { id: uid() }]);
        } else {
          setOutlines(newOutLines);
        }
      }
    } catch (e) {
      console.log("e", e);
    }
  };

  // 接口获取大纲后处理数据
  const outlinesConvert = (data: any[], depth: number = 0) => {
    return data.map((item) => {
      const id = item?.sectionId || uid();
      const newItem: OutlineType = {
        ...item,
        useCustomDB: depth === 0 ? true : !!item.useCustomDB,
        id,
        key: item.sectionId,
        children: item.subParagraphs
          ? outlinesConvert(item.subParagraphs, depth + 1)
          : [], // 重命名并递归处理子节点
        sectionPrompt: item?.sectionPrompt || item?.contentAbstract || ""
      };
      return newItem;
    });
  };

  // 增加一级大纲
  const addRow = () => {
    setOutlines((pre: any) => {
      return [...pre, { id: uid() }];
    });
  };
  // 删除section后，所有子节点的section同步删除，更新大纲数据
  const deleteSection = async (record: OutlineType) => {
    // 存储该大纲及子节点的所有sectionId
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
    //批量删除section
    if (sectionIds.length > 0) {
      const newOutlines = loopDataSourceDelete(outlines, record.id);
      const otls = outlinesTransform(newOutlines);
      const res = await api_deleteSectionByIds({
        data: {
          ids: sectionIds.join(","),
          articleId: templateInfo.id,
          type: "articleType",
          params: {
            outlines: {
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

  // 增加大纲子节点
  const loopDataSourceAdd = (
    data: OutlineType[],
    id: React.Key | undefined,
    level: number = 0
  ): OutlineType[] => {
    return data.map((item) => {
      if (item.id == id) {
        item.children = item.children || [];
        item.children.push({
          id: uid()
        });
      } else if (item.children) {
        item.children = loopDataSourceAdd(item.children, id, level + 1);
      }
      return item;
    });
  };

  const fixDependency = (nodes: any[], key: string = "children") => {
    const _relations = relationsRef.current || {};
    const hasDependencySections = Object.keys(_relations);
    return nodes.map((node: any) => {
      const { sectionId, title, extraInfo } = node;
      const keys = [
        "title",
        "section",
        "sectionId",
        "contentSources",
        "useCustomDB",
        "useCustomKb"
      ];
      const newNode: any = {
        title
      };
      if (sectionId) {
        keys.forEach((key: string) => {
          newNode[key] = node[key];
        });
      }
      if (extraInfo) {
        newNode.extraInfo = extraInfo;
      }

      if (hasDependencySections.includes(String(sectionId))) {
        console.log(_relations[String(sectionId)]);
        const dependencys = findNodesByIds(
          outlines,
          _relations[String(sectionId)],
          key
        );
        if (dependencys.length) {
          const refIds: Array<string | number> = [];
          const refNames: Array<string | number> = [];
          const sourceType = "section";
          (dependencys || []).map((d: any) => {
            refIds.push(d.sectionId);
            refNames.push(d.title);
          });
          newNode.dependency = [
            {
              refIds,
              refNames,
              sourceType
            }
          ];
        } else {
          console.log(sectionId, "没找到依赖节点：", _relations);
        }
      }

      if (node[key]) {
        newNode.subParagraphs = fixDependency(node[key], key);
      }
      return newNode;
    });
  };

  //section 新增/编辑完后大纲更新
  const changeSection = async (
    sectionInfo: any,
    paragraphs: any[],
    nodeId: string | number,
    updates: any,
    cmps: any[] = []
  ) => {
    console.log("section confirm:", sectionInfo, paragraphs, nodeId, updates);
    if (isVersion) {
      setSectionData({ ...initialSectionInfo });
      return;
    }
    const childrenKey = "subParagraphs";
    const newParagraphs = fixDependency(paragraphs, childrenKey);
    const api = sectionInfo.id
      ? api_editArticleTypeSectionById
      : api_addArticleTypeSection;

    const _data: any = {
      articleTypeId: templateInfo.id,
      params: {
        ...sectionInfo,
        outlines: {
          paragraphs: newParagraphs
        },
        component: cmps || []
      }
    };
    if (sectionInfo.id) {
      _data.id = sectionInfo.id;
    }
    const section = await api({
      data: {
        ..._data
      },
      config: serverInfo
    });

    function traverse(nodes: OutlineType[]) {
      return nodes.map((node: OutlineType) => {
        //更新section
        const { id, children } = node;
        let newNode = {
          ...node
        };
        if (id === nodeId) {
          newNode = {
            ...newNode,
            ...updates,
            contentSources: updates.contentSources || [],
            sectionId: section.id,
            section: {
              materialType: section.materialType
            }
          };
        }
        if (children) {
          newNode.children = traverse(children);
        }
        return newNode;
      });
    }
    if (section) {
      const _outlines = traverse(outlines);
      setOutlines([..._outlines]);
      setSectionData({ ...initialSectionInfo });
    }
  };

  const outlinesTransform = (data: any[]) => {
    return data.map((item: OutlineType) => {
      const {
        title,
        section,
        sectionId,
        contentSources,
        dependency,
        useCustomKb,
        useCustomDB
      } = item;
      const newItem: any = {
        title,
        section,
        sectionId,
        contentSources,
        dependency,
        useCustomKb,
        useCustomDB
      };
      if (item.extraInfo) {
        newItem.extraInfo = item.extraInfo;
      }
      if (item.children) {
        newItem.subParagraphs = outlinesTransform(item.children);
      }
      return newItem;
    });
  };

  // 保存模版
  const saveTemplate = async (dropOutlines?: any, isSlience?: boolean) => {
    const _outlines = dropOutlines || outlines;
    // 校验标题不为空
    let isValidTitles = 0;

    const traverse = (data: any[]) => {
      return data.forEach((item: OutlineType) => {
        const { title } = item;
        if (!title) {
          //校验标题不为空
          ++isValidTitles;
        } else if (title && title.trim().length == 0) {
          ++isValidTitles;
        }

        if (item.children) {
          traverse(item.children);
        }
      });
    };
    traverse(_outlines);
    if (isValidTitles > 0 && !dropOutlines) {
      // 拖拽改变顺序或新增章节组件时不提示章节未填写标题
      if (!isSlience) {
        confirm({
          title: "标题未填写",
          icon: <ExclamationCircleFilled />,
          content: `检测到${isValidTitles}个标题为空，请填写或者删除`,
          okButtonProps: {
            style: {
              background: "linear-gradient(#2867FF, #8789FF)",
              border: "none",
              color: "#fff"
            }
          },
          onCancel() {
            console.log("Cancel");
          }
        });
        return false;
      }
    }
    const newOutlines = fixDependency(_outlines);

    const params = {
      ...templateInfo,
      outlines: {
        paragraphs: newOutlines
      }
    };

    let res: any;
    if (templateInfo?.id) {
      params.id = templateInfo?.id;
      res = await updateArticleType.mutateAsync(params);
    } else {
      res = await createArticleType.mutateAsync(params);
    }

    return !!res?.success;
  };

  // 抽取大纲后应用
  const applyOutlines = async (extractRes: any) => {
    setApplyLoading(true);
    setOutlines([]);
    try {
      const res = await api_applyOutlines({
        data: {
          articleId: templateInfo?.id,
          params: {
            outlines: extractRes
          }
        },
        config: serverInfo
      });
      if (res) {
        setApplyLoading(false);
        const newOutLines = outlinesConvert(
          (res?.data || {})?.paragraphs || []
        );
        if (newOutLines?.length == 0) {
          setOutlines([{ id: uid() }, { id: uid() }, { id: uid() }]);
        } else {
          console.log(newOutLines);
          setOutlines(newOutLines);
        }
        return true;
      }
    } catch (e) {
      console.log("applyOutlines-------", e);
    }
  };

  const materialConfiem = (list: any[], sourceType: sourceTypes) => {
    console.log("new material list:", list);
    const _list = materialList.filter((i: any) => i.sourceType !== sourceType);
    const newList = [..._list, ...list];
    setMaterialList([...newList]);
    newMaterialListRef.current = [...newList];
    // contentSourceAfterMaterialList(newList, sourceType);
    contentSourceAfterMaterialList(list, sourceType);
  };

  const contentSourceAfterMaterialList = (
    list: any[],
    sourceType: sourceTypes
  ) => {
    const dbSource = {
      refIds: [],
      refNames: [],
      dbNames: [],
      refEntityType: "table",
      sourceType: sourceTypes.database
    } as any;
    const kbTemplateSource = {
      refIds: [],
      refNames: [],
      usage: "",
      refEntityType: "document",
      sourceType: sourceTypes.knowledge_base
    } as any;
    const kbContentSource = {
      refIds: [],
      refNames: [],
      usage: "",
      refEntityType: "document",
      sourceType: sourceTypes.knowledge_base
    } as any;

    (list || [])
      .filter((i: any) => i.sourceType === sourceType)
      .forEach((tb: any) => {
        if (tb.sourceType === sourceTypes.database) {
          dbSource.refIds.push(tb.refId),
            dbSource.refNames.push(tb.refName),
            dbSource.dbNames.push(tb.dbName);
        }
        if (tb.sourceType === sourceTypes.knowledge_base) {
          switch (tb.usage) {
            case "both":
              kbTemplateSource.refIds.push(tb.refId),
                kbTemplateSource.refNames.push(tb.refName),
                (kbTemplateSource.usage = tb.usage);
              kbContentSource.refIds.push(tb.refId),
                kbContentSource.refNames.push(tb.refName),
                (kbContentSource.usage = tb.usage);
              break;
            case "template":
              kbTemplateSource.refIds.push(tb.refId),
                kbTemplateSource.refNames.push(tb.refName),
                (kbTemplateSource.usage = tb.usage);
              break;
            case "content":
              kbContentSource.refIds.push(tb.refId),
                kbContentSource.refNames.push(tb.refName),
                (kbContentSource.usage = tb.usage);
              break;
          }
        }
      });
    // 按照接口需要的方式保存contentSources
    setTemplateInfo((pre: any) => {
      const _contentSources = [] as any;
      if (sourceType === sourceTypes.knowledge_base) {
        if (kbTemplateSource.refIds.length) {
          _contentSources.push({ ...kbTemplateSource });
        }
        if (kbContentSource.refIds.length) {
          _contentSources.push({ ...kbContentSource });
        }
      } else if (
        sourceType === sourceTypes.database &&
        dbSource.refIds.length
      ) {
        _contentSources.push({ ...dbSource });
      }

      const otherContentSources = (pre.contentSources || []).filter(
        (c: any) => c.sourceType !== sourceType
      );
      console.log("newContentSources:", [
        ...otherContentSources,
        ..._contentSources
      ]);

      return {
        ...pre,
        contentSources: [...otherContentSources, ..._contentSources]
        // contentSources: [..._contentSources]
      };
    });
  };

  const dropSection = async (sceneId: string | number) => {
    if (templateInfo && templateInfo.id) {
      const res: any = await api_applySection({
        data: {
          id: sceneId,
          params: {
            // articleId:,
            articleTypeId: templateInfo.id,
            scope: 0
          }
        },
        config: serverInfo
      });
      const { success, data } = res;
      if (success) {
        const newMiniOutline = outlinesConvert(data.paragraphs);
        console.log("new mini outline:", newMiniOutline);
        return newMiniOutline && newMiniOutline.length ? newMiniOutline[0] : {};
      }
      return null;
    }
    return null;
  };

  const fetchAnalysisTree = async () => {
    const res = await getSceneAnalysisTree();
    const list = res || [];
    setAnalysisTreeOrigin([...list]);
  };

  const editTemplateClickHandler = (isNext: boolean) => () => {
    const _ref = editTemplateRef.current as any;
    if (_ref && _ref.onFinish) {
      if (isNext) {
        _ref.onFinish(true);
      } else {
        _ref.onFinish();
      }
    }
  };

  const onNextHandler = (res: any, next: any) => {
    if (res) {
      if (isOnceIn.current) {
        isOnceIn.current = false;
      }
      setTemplateInfo(res);
      if (next) {
        setCurItemKey(ProcessType.GUIDELINES_MATERAILS);
      }
    } else {
      if (isVersion) {
        setCurItemKey(ProcessType.GUIDELINES_MATERAILS);
      }
    }
  };

  // 步骤渲染 第一步场景基本信息 第二步编辑大纲及素材
  const renderProcess = useCallback(() => {
    switch (curItemKey) {
      case ProcessType.BASIC_INFO:
        return (
          <EditTemplate
            ref={editTemplateRef}
            isSegment={true}
            templateId={templateInfo?.id}
            isOnceIn={isOnceIn}
            onNext={onNextHandler}
          />
        );
      case ProcessType.GUIDELINES_MATERAILS:
        return (
          <div className="h-[calc(100vh-200px)] pl-5 overflow-y-auto overflow-x-hidden">
            <OutlineCmp
              outlines={outlines}
              treeList={materialList}
              applyLoading={applyLoading}
              relationsRef={relationsRef}
              isVersion={isVersion}
              setOutlines={setOutlines}
              applyOutlines={applyOutlines}
              deleteSection={deleteSection}
              loopDataSourceDelete={loopDataSourceDelete}
              setSectionData={setSectionData}
              materialConfiem={materialConfiem}
              dropSection={dropSection}
              saveDropResult={saveTemplate}
              getMaterialTree={getMaterialTree}
            >
              <div className="flex">
                <span className="w-[1px] bg-[#eee] mr-2 -ml-[2px] h-6 mt-1"></span>
                <Button
                  disabled={isVersion}
                  className="border-[#EEE] px-3"
                  icon={
                    <PlusOutlined
                      className={`text-base ${
                        isVersion ? "" : "text-primary-color"
                      } pt-[2px]`}
                    />
                  }
                  onClick={addRow}
                >
                  添加标题
                </Button>
              </div>
            </OutlineCmp>
          </div>
        );
    }
  }, [curItemKey, outlines, templateInfo, isOnceIn.current]);

  const goBack = (key: number) => () => {
    navigator(key);
  };

  useEffect(() => {
    if (modalType == "edit" && curItemKey == ProcessType.GUIDELINES_MATERAILS) {
      if (!isVersion || String(versionId)) {
        getTemplateById();
      }
    }
    if (modalType == "add") {
      setOutlines([{ id: uid() }, { id: uid() }, { id: uid() }]);
    }
  }, [id, curItemKey, versionId, isVersion]);

  useEffect(() => {
    fetchAnalysisTree();
  }, []);

  return (
    <div className="h-full overflow-hidden w-full">
      <Flex justify="flex-start" align="center" className="mb-4">
        <img
          className="mr-2 pb-[2px] cursor-pointer"
          src={IconArrowLeft}
          onClick={goBack(-1)}
        />
        <b className="text-base text-text-color1">
          {isVersion
            ? `查看场景版本 - V1.${versionTxt}`
            : modalType === "edit"
              ? "编辑场景"
              : "新建场景"}
        </b>
      </Flex>
      <div className="w-[calc(100vw-112px)] h-[calc(100%-58px)] bg-white rounded-lg overflow-y-auto overflow-x-hidden flex flex-col">
        <Flex
          align="start"
          justify="space-between"
          className="h-14 px-5 py-3 leading-8"
          style={{ borderBottom: "1px solid #eee" }}
        >
          <Flex align="start">
            {drawerTitleList.map((item, index) => (
              <Flex align="center" key={`crumbs-step-${item.key}`}>
                <span
                  className="w-6 h-6 inline-block leading-6 text-center rounded-full mr-3 text-xs select-none"
                  style={{
                    background:
                      curItemKey > index
                        ? "linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%) "
                        : "#f2f2f2",
                    color: curItemKey > index ? "white" : "#888"
                  }}
                >
                  {item.key}
                </span>
                <span
                  className="mr-8 select-none"
                  style={{
                    fontWeight: item.key === curItemKey ? "700" : "400"
                  }}
                >
                  {item.value}
                </span>
                {item.key < drawerTitleList.length && (
                  <img src={Right} width={16} height={16} className="mr-8" />
                )}
              </Flex>
            ))}
          </Flex>

          {curItemKey == ProcessType.BASIC_INFO ? (
            <div>
              {!isVersion ? (
                <Button
                  type="primary"
                  onClick={editTemplateClickHandler(false)}
                  className="mr-3 rounded bg-white text-text-color2"
                  style={{
                    border: "1px solid #dedede"
                  }}
                >
                  保存
                </Button>
              ) : null}
              <Button
                ghost
                onClick={editTemplateClickHandler(true)}
                className="border-none"
                style={{
                  background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                  color: "#fff"
                }}
              >
                下一步
              </Button>
            </div>
          ) : null}

          {curItemKey == ProcessType.GUIDELINES_MATERAILS ? (
            <div>
              <Button
                className="mr-3 rounded bg-white text-text-color2"
                style={{
                  border: "1px solid #ebebeb"
                }}
                onClick={async () => {
                  if (!isVersion) {
                    await saveTemplate(null, true);
                  }
                  setCurItemKey(ProcessType.BASIC_INFO);
                }}
              >
                上一步
              </Button>
              {!isVersion ? (
                <Button
                  className="border-none"
                  style={{
                    background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                    color: "#fff"
                  }}
                  onClick={async () => {
                    const res = await saveTemplate();
                    if (res) {
                      navigator("/docWriting/template");
                    }
                  }}
                >
                  保存
                </Button>
              ) : null}
            </div>
          ) : curItemKey == ProcessType.BASIC_INFO ? null : null}
        </Flex>
        <div className="bg-white h-[calc(100%-56px)] overflow-hidden flex flex-col">
          {renderProcess()}
        </div>
      </div>
      {sectionData.visible ? (
        <SectionDrawer
          open={sectionData.visible}
          row={sectionData.node}
          articleTypeId={String(id)}
          versionId={String(versionId)}
          serverInfo={serverInfo}
          isVersion={isVersion}
          analysisTreeOrigin={analysisTreeOrigin}
          outlines={outlines}
          treeList={materialList}
          materialTreeData={materialTreeData}
          onClose={changeSection}
        />
      ) : null}
    </div>
  );
};

export default SegmentedWritingTemplate;
