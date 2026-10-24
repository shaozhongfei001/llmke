import React, {
  useEffect,
  useState,
  useCallback,
  useRef,
  useMemo
} from "react";
import { Drawer, Input, message, Radio, Tooltip, Button, Tabs } from "antd";
import type { RadioChangeEvent } from "antd";
import { CloseOutlined, QuestionCircleOutlined } from "@ant-design/icons";
import { AnalysisLinkIcon } from "@/components/Icon";
import {
  api_querySectionById,
  api_getSectionByVersionId
} from "@/components/AiEditor/core/services/servers";
import AnalysisCmpTree from "./AnalysisCmpTree";
import { debounce } from "lodash";
import {
  TreeNode,
  stageTypes,
  sourceTypes
} from "@/components/AiEditor/components/WritingConfig/SegmentedWriting/components/Outline";
import RelatedTableModal from "@/pages/HomePage/Writing/EditSegmentedTemplate/components/RelatedTableModal";
import DbTree from "./DbTree";
import KbTree from "./KbTree";
import "./style.less";
import SelectMaterialModal, {
  writingTypes
} from "@/components/AiEditor/components/WritingConfig/components/SelectMaterialModal";

const { TextArea } = Input;

enum analysisType {
  auto = "auto",
  customize = "customize"
}
const analysisTypeItems = [
  {
    value: analysisType.auto,
    label: "大模型自动配置"
  },
  {
    value: analysisType.customize,
    label: "自定义配置"
  }
];

const cfgRadioItems = [
  {
    value: false,
    label: "默认配置"
  },
  {
    value: true,
    label: "自定义配置"
  }
];

const judgeKeys = {
  db: "useCustomDB",
  kb: "useCustomKb"
};

export const refEntityTypes = {
  db: "table",
  kb: "document"
};

export enum fileTabTypes {
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

const analysisBtnCls = "show-analysis-btn";
const dbBtnCls = "show-db-btn";
const kbBtnCls = "show-kb-btn";
const analysisCls = "analysis-cmp-wrap";
const dbPanelCls = "db-tree-wrap";
const kbPanelCls = "kb-tree-wrap";

interface Iprops {
  open: boolean;
  serverInfo: any;
  materialTreeData?: any;
  analysisTreeOrigin?: any[];
  isVersion?: boolean;
  articleTypeId?: string;
  versionId?: string;
  stageType?: stageTypes;
  outlines: any[];
  treeList: any[];
  row: any;
  onClose: (
    section: any,
    list: any[],
    nodeId: string | number,
    updates: any,
    cmps?: any[]
  ) => void;
}

const SectionDrawer = (props: Iprops) => {
  const {
    serverInfo,
    open,
    materialTreeData = {
      kbs: [],
      folders: [],
      files: []
    },
    analysisTreeOrigin = [],
    isVersion = false,
    articleTypeId,
    versionId,
    stageType = stageTypes.scene,
    outlines,
    treeList,
    row = {
      id: undefined,
      sectionId: 0,
      title: "",
      isLeaf: false,
      [judgeKeys.kb]: false,
      [judgeKeys.db]: false
    },
    onClose
  } = props;

  const sectionInfoRef = useRef<any>(null);
  const rowRef = useRef<any>(null);
  const outlinesRef = useRef<any[]>([]);
  const [sectionPrompt, setSectionPrompt] = useState<string>("");
  const [sectionContentExample, setSectionContentExample] =
    useState<string>("");
  const [cfgAnalysis, setCfgAnalysis] = useState<analysisType>(
    analysisType.auto
  );
  const cfgAnalysisRef = useRef<analysisType>(analysisType.auto);
  const [analysisComponents, setAnalysisComponents] = useState<any[]>([]);
  const analysisComponentsRef = useRef<any[]>([]);
  const [isAnalysisTreeShow, setIsAnalysisTreeShow] = useState<boolean>(false);
  const [customKb, setCustomKb] = useState<boolean>(false);
  const customKbRef = useRef<boolean>(false);
  const [customDB, setCustomDB] = useState<boolean>(false);
  const customDBRef = useRef<boolean>(false);
  const [isKbTreeShow, setIsKbTreeShow] = useState<boolean>(false);
  const [isDbTreeShow, setIsDbTreeShow] = useState<boolean>(false);
  const [isRelationModalShow, setIsRelationModalShow] =
    useState<boolean>(false);
  // 模态框选择的数据表数据
  const [dbTreeData, setDbTreeData] = useState<any>([]);
  const customizeDbTablesRef = useRef<any[]>([]);
  const customizeKbTablesRef = useRef<any[]>([]);
  const [curFileType, setCurFileType] = useState<fileTabTypes>(
    fileTabTypes.content
  );
  const [openSelectModal, setOpenSelectModal] = useState(false);
  const [isMaterialApisFetching, setIsMaterialApisFetching] =
    useState<boolean>(false);

  const filterDbFn =
    (isInclude = true) =>
    (i: any) =>
      isInclude
        ? i.sourceType === sourceTypes.database
        : i.sourceType !== sourceTypes.database;

  const filterKbFn =
    (isInclude = true) =>
    (i: any) =>
      isInclude
        ? i.sourceType === sourceTypes.knowledge_base
        : i.sourceType !== sourceTypes.knowledge_base;

  // 获取章节详情
  const getSectionInfo = async () => {
    try {
      const api = isVersion ? api_getSectionByVersionId : api_querySectionById;
      const _params: any = isVersion
        ? {
            sectionId: String(row.sectionId),
            versionId,
            articleTypeId
          }
        : {
            id: String(row.sectionId)
          };
      const res = await api({
        data: { ..._params },
        config: serverInfo
      });
      const { data } = res;
      sectionInfoRef.current = { ...data };
      setSectionPrompt(data.sectionPrompt);
      setSectionContentExample(data.sectionContentExample);
    } catch (e) {
      console.log("getSectionInfo ------->", e);
    }
  };

  const onSectionPromptChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setSectionPrompt(e.target.value.trim());
  };

  const onSectionContentExampleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setSectionContentExample(e.target.value.trim());
  };

  const fileTypeOnChangeHandler = (tabKey: any) => {
    setCurFileType(tabKey);
  };

  // 关闭章节配置抽屉后的执行代码
  const handleClose = async () => {
    const _row: any = rowRef.current || {};
    const _outlines = outlinesRef.current;
    const { id, title, isLeaf, sectionId, contentSources } = _row;
    console.log(row, _row);
    if (!isVersion && isLeaf && !sectionId && !sectionPrompt) {
      message.warning("内容要求必填");
      return;
    }
    let _contentSources: any[] = contentSources || [];
    // 保留contentSources中的其他数据
    const otherContentSources = (contentSources || []).filter(
      stageType === stageTypes.scene
        ? filterDbFn(false)
        : stageType === stageTypes.write
        ? filterKbFn(false)
        : null
    );

    // 场景自定义数据表
    if (stageType === stageTypes.scene && customDBRef.current) {
      console.log(customizeDbTablesRef.current, contentSources);
      const _dbConfirmData = getDbConfirmData(customizeDbTablesRef.current);
      _contentSources = [...otherContentSources, ...[_dbConfirmData]];
    }

    // 写作自定义素材表
    if (stageType === stageTypes.write && customKbRef.current) {
      console.log(customizeKbTablesRef.current, contentSources);
      const _kbConfirmData = getKbConfirmData(customizeKbTablesRef.current);
      _contentSources = [...otherContentSources, ..._kbConfirmData];
    }

    // const _outlines = updateTreeNode(outlines, [id], {
    //   contentSources: _contentSources,
    //   useCustomDB: customDBRef.current,
    //   useCustomKb: customKbRef.current
    // });

    const updates = {
      contentSources: _contentSources,
      useCustomDB: customDBRef.current,
      useCustomKb: customKbRef.current
    };

    const _oLines = fixOutlines(_outlines, id, { ...updates }, title);
    //提交数据
    const _sectionInfo = sectionInfoRef.current || {};
    const sectionInfo = {
      ..._sectionInfo,
      sectionTitle: title,
      sectionPrompt,
      sectionContentExample
    };
    // 场景编辑传入分析组件id数组，大纲编写传入素材数据
    const list =
      stageType === stageTypes.scene &&
      cfgAnalysisRef.current === analysisType.customize
        ? analysisComponentsRef.current
        : [];

    onClose && onClose(sectionInfo, _oLines, id, updates, list);

    if (stageType === stageTypes.scene) {
      setIsAnalysisTreeShow(false);
      setCfgAnalysis(analysisType.auto);
      cfgAnalysisRef.current = analysisType.auto;
    }
  };

  const fixOutlines = (
    nodes: any[],
    nodeId: string | number,
    updates: any,
    nodeTitle: string
  ) => {
    const sectionInfo = sectionInfoRef.current || {};
    return nodes.map((node: any) => {
      const {
        depth,
        title,
        useCustomDB,
        useCustomKb,
        contentSources,
        section,
        extraInfo,
        sectionId,
        id,
        contentOperation,
        children
      } = node;
      let newNode: any = {
        title,
        useCustomDB: depth === 1 ? true : !!useCustomDB,
        useCustomKb: !!useCustomKb,
        contentSources: contentSources || []
      };

      if (sectionId || nodeId === id) {
        newNode.sectionId = sectionId || 0;
        if (extraInfo) {
          newNode.extraInfo = extraInfo;
        }
        newNode.contentOperation = contentOperation || "0";
        const _section = section || {};
        newNode.section = {
          ..._section,
          materialType: sectionInfo?.materialType,
          hasSectionPrompt: !!sectionPrompt?.length,
          hasContent: !!sectionInfo?.hasContent
        };
        if (nodeId === id) {
          newNode = {
            ...newNode,
            ...updates,
            title: nodeTitle
          };
        }
      }

      if (children) {
        newNode.subParagraphs = fixOutlines(
          children,
          nodeId,
          updates,
          nodeTitle
        );
      }
      return newNode;
    });
  };

  // 路径克隆的深度更新
  const updateTreeNode: any = (
    nodes: any[],
    targetIds: Array<string | number>,
    updates: any
  ) => {
    const idSet = new Set(targetIds);
    return nodes.map((node) => {
      // 发现目标节点时创建新对象并合并更新
      if (idSet.has(node.id)) {
        return { ...node, ...updates };
      }

      // 递归处理子节点,保留未改变的引用
      if (node.children?.length) {
        const newChildren = updateTreeNode(node.children, targetIds, updates);
        return newChildren !== node.children
          ? { ...node, children: newChildren }
          : node;
      }
      return node;
    });
  };

  const debounceClose = useCallback(debounce(handleClose, 500), [
    sectionPrompt,
    sectionContentExample
  ]);

  const cfgAnalysisOnChange = (e: RadioChangeEvent) => {
    setCfgAnalysis(e.target.value);
    cfgAnalysisRef.current = e.target.value;
  };

  const cfgDbOnChange = (e: RadioChangeEvent) => {
    setCustomDB(e.target.value);
    customDBRef.current = e.target.value;
  };

  const cfgKbOnChange = (e: RadioChangeEvent) => {
    setCustomKb(e.target.value);
    customKbRef.current = e.target.value;
  };

  const toggleAnalysisTree = (sta: boolean) => () => {
    setIsAnalysisTreeShow(sta);
  };

  const toggleKbTree = (sta: boolean) => () => {
    setIsKbTreeShow(sta);
  };

  const toggleDbTree = (sta: boolean) => () => {
    setIsDbTreeShow(sta);
  };

  const handlerChooseFile = () => {
    setOpenSelectModal(true);
  };

  const analysisComponentsOnChange = (list: any[]) => {
    setAnalysisComponents([...list]);
    analysisComponentsRef.current = [...list];
  };

  const checkAnalysisSta = () => {
    if (sectionInfoRef.current) {
      const { component } = sectionInfoRef.current as any;
      if (component && component.length) {
        setCfgAnalysis(analysisType.customize);
        cfgAnalysisRef.current = analysisType.customize;
      }
    }
  };

  const toggoleRelationModal = (sta: boolean) => () => {
    setIsRelationModalShow(sta);
  };

  // 数据表确定后的执行代码
  const relatedTablesConfirm = ({ tableList, tableTree }: any) => {
    const list: any[] = [];
    const _sourceType = sourceTypes.database;
    (tableList || []).forEach((i: any) => {
      const { id, name, dbName } = i;
      list.push({
        customId: `db-${id}`,
        refId: id,
        refEntityType: refEntityTypes.db,
        refName: name,
        dbName,
        sourceType: _sourceType
      });
    });
    customizeDbTablesRef.current = [...list];
    // sectionConfiem(list, _sourceType);
    setIsRelationModalShow(false);
  };

  // 素材表确定后的执行代码
  const materialConfiem = (mList: any[]) => {
    customizeKbTablesRef.current = [...mList];
  };

  // 根据节点id，遍历向上寻找继承的节点
  const findParentWithCustomKey = (
    treeData: any[],
    nodeId: string | number,
    judgeKey: string
  ) => {
    let result = null;

    // 递归遍历函数（携带父级路径）
    const traverse = (nodes: any[], parentStack: any[] = []) => {
      for (const node of nodes) {
        // 找到目标节点时，反向遍历父级链
        if (node.id === nodeId) {
          for (let i = parentStack.length - 1; i >= 0; i--) {
            if (parentStack[i][judgeKey]) {
              result = parentStack[i].contentSources || [];
              break;
            }
          }
          return true; // 找到时提前终止遍历
        }
        // 递归遍历子节点，传递当前节点作为父级
        if (node.children && traverse(node.children, [...parentStack, node])) {
          return true;
        }
      }
      return false;
    };
    traverse(treeData);
    return result;
  };

  const getDbList = (contentSources: any[]) => {
    const list: any[] = [];
    if (!contentSources) {
      return list;
    }
    const _sourceType = sourceTypes.database;
    const _contentSources = contentSources.filter(filterDbFn());
    (_contentSources || []).forEach((i: any) => {
      const { refIds, refNames, dbNames } = i;
      (refIds || []).forEach((refId: any, idx: number) => {
        list.push({
          customId: `db-${refId}`,
          refId,
          refEntityType: refEntityTypes.db,
          refName: refNames[idx],
          dbName: dbNames[idx],
          sourceType: _sourceType
        });
      });
    });
    return list;
  };

  const getKbList = (contentSources: any[]) => {
    const list: any[] = [];
    if (!contentSources) {
      return list;
    }
    const _contentSources = contentSources.filter(filterKbFn());
    (_contentSources || []).forEach((i: any) => {
      const { refEntityType, refIds, refNames, sourceType, usage } = i;
      (refIds || []).forEach((refId: any, idx: number) => {
        list.push({
          customId: `kb-${refId}`,
          refId,
          refEntityType,
          refName: refNames[idx],
          usage,
          sourceType
        });
      });
    });
    return list;
  };

  const getDbConfirmData = (list: any[]) => {
    const dbSource = {
      refIds: [],
      refNames: [],
      dbNames: [],
      refEntityType: "table",
      sourceType: sourceTypes.database
    } as any;
    (list || []).forEach((i: any) => {
      dbSource.refIds.push(i.refId),
        dbSource.refNames.push(i.refName),
        dbSource.dbNames.push(i.dbName);
    });
    return dbSource;
  };

  const getKbConfirmData = (list: any[]) => {
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

    (list || []).forEach((tb: any) => {
      switch (tb.usage) {
        case fileTabTypes.both:
          kbTemplateSource.refIds.push(tb.refId),
            kbTemplateSource.refNames.push(tb.refName),
            (kbTemplateSource.usage = tb.usage);
          kbContentSource.refIds.push(tb.refId),
            kbContentSource.refNames.push(tb.refName),
            (kbContentSource.usage = tb.usage);
          break;
        case fileTabTypes.template:
          kbTemplateSource.refIds.push(tb.refId),
            kbTemplateSource.refNames.push(tb.refName),
            (kbTemplateSource.usage = tb.usage);
          break;
        case fileTabTypes.content:
          kbContentSource.refIds.push(tb.refId),
            kbContentSource.refNames.push(tb.refName),
            (kbContentSource.usage = tb.usage);
          break;
      }
    });
    const _list = [];
    if (kbTemplateSource.refIds.length) {
      _list.push({ ...kbTemplateSource });
    }
    if (kbContentSource.refIds.length) {
      _list.push({ ...kbContentSource });
    }
    return _list;
  };

  const getKbListByBoth = (list: any) => {
    const _list: any[] = [];
    (list || []).forEach((i: any) => {
      const { usage } = i;
      if (usage === fileTabTypes.both) {
        _list.push({ ...i, usage: fileTabTypes.content });
        _list.push({ ...i, usage: fileTabTypes.template });
      } else {
        _list.push({ ...i });
      }
    });
    return _list;
  };

  const getKbContentList = (list: any[]) => {
    return list.filter((i: any) => i.usage === fileTabTypes.content);
  };

  const getKbTemplateList = (list: any[]) => {
    return list.filter((i: any) => i.usage === fileTabTypes.template);
  };

  // 整个大纲选择的数据表列表
  const dbList = useMemo(() => {
    return !open ? [] : (treeList || []).filter(filterDbFn());
  }, [treeList, open]);

  // 整个大纲选择的素材列表
  const kbList = useMemo(() => {
    return !open ? [] : getKbListByBoth((treeList || []).filter(filterKbFn()));
  }, [treeList, open]);

  // 向上继承的数据表列表，如无则使用大纲选择的数据表列表
  const inheritDb = useMemo(() => {
    const _contentSources: any = findParentWithCustomKey(
      outlines,
      row.id,
      judgeKeys.db
    );
    return _contentSources ? getDbList(_contentSources) : dbList;
  }, [outlines, row, dbList]);

  // 向上继承的素材表列表，如无则使用大纲选择的数据表列表
  const inheritKb = useMemo(() => {
    const _contentSources: any = findParentWithCustomKey(
      outlines,
      row.id,
      judgeKeys.kb
    );
    return _contentSources ? getKbList(_contentSources) : kbList;
  }, [outlines, row, kbList]);

  // 自定义数据表列表
  const customizeDb = useMemo(() => {
    return customizeDbTablesRef.current || [];
  }, [customizeDbTablesRef.current]);

  // 自定义素材表列表
  const customizeKb = useMemo(() => {
    return customizeKbTablesRef.current || [];
  }, [customizeKbTablesRef.current]);

  // 当前选择的数据表列表
  const curDbList = useMemo(() => {
    return customDB ? customizeDb : inheritDb;
  }, [inheritDb, customizeDb, customDB]);

  // 当前的素材类型数据列表
  const curKbList = useMemo(() => {
    const list = customKb ? customizeKb : inheritKb;
    return curFileType === fileTabTypes.content
      ? getKbContentList(list)
      : getKbTemplateList(list);
  }, [curFileType, customKb, inheritKb, customizeKb]);

  const kbNum = useMemo(() => {
    return customKb ? customizeKb.length : inheritKb.length;
  }, [customKb, inheritKb, customizeKb]);

  // 展开自定义选择模态框时的默认选中数据表数据id列表
  const dbIdList = useMemo(() => {
    return (curDbList || []).map((i: any) => Number(i.refId));
  }, [curDbList]);

  // 展开时初始化数据
  useEffect(() => {
    if (open) {
      // 展开获取当前章节详情
      if (row && row.sectionId) {
        getSectionInfo();
      }
      if (row?.sectionPrompt || row?.contentAbstract) {
        setSectionPrompt(row?.sectionPrompt || row?.contentAbstract);
      }
      if (row && row.id) {
        rowRef.current = { ...row };
      }
      const { useCustomKb, useCustomDB, contentSources } = row;
      if (
        Object.prototype.toString.call(useCustomKb) === "[object Boolean]" &&
        useCustomKb !== customKb
      ) {
        setCustomKb(useCustomKb);
        customKbRef.current = useCustomKb;
      }
      if (
        Object.prototype.toString.call(useCustomDB) === "[object Boolean]" &&
        useCustomDB !== customDB
      ) {
        setCustomDB(useCustomDB);
        customDBRef.current = useCustomDB;
      }
      customizeDbTablesRef.current = contentSources
        ? getDbList(row.contentSources)
        : [];
      customizeKbTablesRef.current = contentSources
        ? getKbList(row.contentSources)
        : [];
    } else {
      setSectionPrompt("");
      setSectionContentExample("");
      rowRef.current = {};
      sectionInfoRef.current = {};
    }
  }, [row, open]);

  useEffect(() => {
    outlinesRef.current = outlines;
  }, [outlines]);

  // 场景配置中分析组件的初始化设置
  useEffect(() => {
    if (open && stageType === stageTypes.scene && sectionInfoRef.current) {
      checkAnalysisSta();
      if (isVersion) {
        const { component } = sectionInfoRef.current as any;
        if (component && component.length) {
          setIsAnalysisTreeShow(true);
        }
      }
    }
  }, [sectionInfoRef.current, isVersion, stageType, open]);

  return (
    <Drawer
      maskClosable={false}
      className="section-drawer-wrap"
      width={"450px"}
      title={
        <div className="flex justify-between">
          <span>写作配置</span>
          <CloseOutlined onClick={debounceClose} />
        </div>
      }
      onClose={() => {
        debounceClose();
      }}
      closable={false}
      destroyOnClose
      open={open}
    >
      {/* <div>{JSON.stringify(row)}</div> */}
      <div
        className="pb-4 w-full text-gray-2a mb-4"
        style={{ borderBottom: "1px solid #EEEEEE" }}
      >
        <b>{row.title}</b>
      </div>
      {row.isLeaf ? (
        <div className="mb-4 text-gray-2a">
          <b>内容要求</b>
          <TextArea
            className="section-drawer-textarea-wrap"
            disabled={isVersion}
            showCount
            maxLength={10000}
            value={sectionPrompt}
            onChange={onSectionPromptChange}
            placeholder="请输入内容要求"
            style={{ height: 140, resize: "none", marginTop: 8 }}
          />
        </div>
      ) : null}
      {row.isLeaf ? (
        <div className="mb-4 text-gray-2a">
          <b>参考示例</b>
          <TextArea
            className="section-drawer-textarea-wrap"
            disabled={isVersion}
            showCount
            maxLength={10000}
            value={sectionContentExample}
            onChange={onSectionContentExampleChange}
            placeholder="请输入参考示例"
            style={{ height: 140, resize: "none", marginTop: 8 }}
          />
        </div>
      ) : null}

      {/* 写作配置素材 begin */}
      {stageType === stageTypes.write && (
        <div className="mb-4">
          <div className="text-gray-2a mb-3 leading-6 flex justify-between">
            <b>配置关联素材</b>
            <Radio.Group
              disabled={isVersion}
              value={customKb}
              options={[...cfgRadioItems]}
              onChange={cfgKbOnChange}
            />
          </div>
          <div className={kbBtnCls}>
            <Button
              type="link"
              className="px-0 w-full h-8 border border-solid border-[#eee] rounded"
              icon={customKb ? <AnalysisLinkIcon /> : null}
              onClick={!customKb ? toggleKbTree(true) : handlerChooseFile}
            >
              <div className="text-center text-gray-2a hover:text-primary-color">
                {!customKb ? "查看" : ""}关联文件
                <span className="">（{kbNum}）</span>
              </div>
            </Button>
          </div>
          {!row.isLeaf && customKb ? (
            <div className="text-[#bbb] text-xs pt-1">
              当前关联的素材将同步应用于其子章节，子章节亦可自定义配置。
            </div>
          ) : null}
          {!customKb ? (
            <div
              className={`${kbPanelCls} fixed top-[5vh] right-[451px] h-[90vh] p-5 box-border rounded-lg bg-white overflow-x-hidden overflow-y-auto transition-[0.3s]`}
              style={{
                width: isKbTreeShow ? "400px" : "0px",
                opacity: isKbTreeShow ? "1" : "0"
              }}
            >
              <div className="material-tab-wrap relative mr-4 mb-4">
                <i className="inline-block h-[1px] w-full absolute bottom-0 border-0 border-b border-solid border-b-[#eee]"></i>
                <Tabs
                  items={fileTabItems}
                  onChange={fileTypeOnChangeHandler}
                  activeKey={curFileType}
                />
              </div>
              <KbTree
                curFileType={curFileType}
                materialTreeData={materialTreeData}
                materialList={curKbList}
                clsoeExceptCls={kbBtnCls}
                panelCls={kbPanelCls}
                closeTreeHandler={toggleKbTree(false)}
              />
            </div>
          ) : null}
        </div>
      )}
      {/* 写作配置素材 end */}

      {/* 场景配置数据表 begin */}
      {stageType === stageTypes.scene ? (
        <div className="mb-4">
          <div className="text-gray-2a mb-3 leading-6 flex justify-between">
            <b>配置关联数据表</b>
            {row.depth && row.depth > 1 ? (
              <Radio.Group
                disabled={isVersion}
                value={customDB}
                options={[...cfgRadioItems]}
                onChange={cfgDbOnChange}
              />
            ) : null}
          </div>

          <div className={dbBtnCls}>
            <Button
              type="link"
              className="px-0 w-full h-8 border border-solid border-[#eee] rounded"
              icon={customDB ? <AnalysisLinkIcon /> : null}
              onClick={
                !customDB || isVersion
                  ? toggleDbTree(true)
                  : toggoleRelationModal(true)
              }
            >
              <div className="text-center text-gray-2a hover:text-primary-color">
                {!customDB || isVersion ? "查看" : ""}关联数据表
                <span className="">（{dbIdList.length}）</span>
              </div>
            </Button>
          </div>
          {!row.isLeaf && customDB ? (
            <div className="text-[#bbb] text-xs pt-1">
              当前关联的素材将同步应用于其子章节，子章节亦可自定义配置。
            </div>
          ) : null}

          {!customDB ? (
            <div
              className={`${dbPanelCls} fixed top-[5vh] right-[451px] h-[90vh] p-5 box-border rounded-lg bg-white overflow-x-hidden overflow-y-auto transition-[0.3s]`}
              style={{
                width: isDbTreeShow ? "400px" : "0px",
                opacity: isDbTreeShow ? "1" : "0"
              }}
            >
              <DbTree
                dbTreeData={dbTreeData}
                dbList={curDbList}
                clsoeExceptCls={dbBtnCls}
                panelCls={dbPanelCls}
                closeTreeHandler={toggleDbTree(false)}
              />
            </div>
          ) : null}
        </div>
      ) : null}
      {/* 场景配置数据表 end */}

      {/* 场景配置分析组件 begin */}
      {stageType === stageTypes.scene && row.isLeaf ? (
        <div className="mb-4">
          <div className="flex justify-between">
            <div className="text-gray-2a mb-3 leading-6">
              <b>配置分析组件</b>
              <Tooltip title="配置分析组件可以提升模型写作效果，大模型可根据内容要求自动选择组件，用户也可以自定义配置组件。">
                <QuestionCircleOutlined className="text-base text-[#888] ml-1 hover:text-primary-color" />
              </Tooltip>
            </div>
            <div className="text-gray-2a mb-3">
              <Radio.Group
                disabled={isVersion}
                value={cfgAnalysis}
                options={[...analysisTypeItems]}
                onChange={cfgAnalysisOnChange}
              />
            </div>
          </div>
          {cfgAnalysis === analysisType.customize ? (
            <div className={analysisBtnCls}>
              <Button
                disabled={isVersion}
                type="link"
                className="px-0 w-full h-8 border border-solid border-[#eee] rounded "
                icon={<AnalysisLinkIcon />}
                onClick={toggleAnalysisTree(true)}
              >
                <div className="text-center text-gray-2a hover:text-primary-color">
                  关联分析组件
                  {analysisComponents.length ? (
                    <span className="">（{analysisComponents.length}）</span>
                  ) : null}
                </div>
              </Button>
            </div>
          ) : null}

          {cfgAnalysis === analysisType.customize ? (
            <div
              className={`${analysisCls} fixed top-[5vh] right-[451px] h-[90vh] p-5 box-border rounded-lg bg-white overflow-x-hidden overflow-y-auto transition-[0.3s]`}
              style={{
                width: isAnalysisTreeShow ? "400px" : "0px",
                opacity: isAnalysisTreeShow ? "1" : "0"
              }}
            >
              <AnalysisCmpTree
                sectionInfo={sectionInfoRef.current}
                analysisTreeOrigin={analysisTreeOrigin}
                clsoeExceptCls={analysisBtnCls}
                panelCls={analysisCls}
                isVersion={isVersion}
                closeTreeHandler={toggleAnalysisTree(false)}
                setAnalysisComponents={analysisComponentsOnChange}
              />
            </div>
          ) : null}
        </div>
      ) : null}
      {/* 场景配置分析组件 end */}
      {stageType === stageTypes.scene ? (
        <RelatedTableModal
          isModalOpen={isRelationModalShow}
          relationTables={dbIdList}
          isCustomize={customDB}
          onClose={toggoleRelationModal(false)}
          onConfirm={relatedTablesConfirm}
          setDbTreeData={setDbTreeData}
        />
      ) : null}

      {stageType === stageTypes.write ? (
        <SelectMaterialModal
          writingType={writingTypes.Segmented}
          openSelectModal={openSelectModal}
          initSelectedArr={customizeKb}
          isMaterialApisFetching={isMaterialApisFetching}
          initKbList={materialTreeData.kbs}
          setOpenSelectModal={setOpenSelectModal}
          setIsMaterialApisFetching={setIsMaterialApisFetching}
          getAllMertail={materialConfiem}
        />
      ) : null}
    </Drawer>
  );
};

export default SectionDrawer;
