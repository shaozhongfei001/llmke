import { useCallback, useState, useMemo, useEffect, useRef } from "react";
import { v4 as uuid } from "uuid";
import { Button, Flex, Form, message, Modal, Spin, Tooltip } from "antd";
import type { TableProps } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { BetaSchemaForm } from "@ant-design/pro-form";
import {
  CaretRightOutlined,
  CaretDownOutlined,
  ExclamationCircleFilled,
  InfoCircleFilled,
  CaretRightFilled,
  CaretDownFilled,
  PlusOutlined
} from "@ant-design/icons";
import ProcessDrawer from "@/components/progressDrawer";
import { useStateStore } from "@/components/AiEditor/core/states/useStateStore";
import {
  api_getArticleById,
  api_getArticleTypeDetails,
  api_deleteSectionByIds,
  api_addArticleTask,
  api_putDependencyDetect
} from "@/components/AiEditor/core/services/servers";
import useAiEditorOperators from "@/components/AiEditor/core/operators/useAiEditorOperators";
import { createTemplateForm } from "@/components/AiEditor/components/Sidebar/util";

import SectionDrawer from "../../SectionDrawer/index.tsx";
import { EDITOR_EVENT_NAME, editorEventBus } from "../../../editorEventBus";
import { OutlineType } from "./type.ts";
import {
  classifyMaterialToRenderNew,
  getAllLeafNodeSectionIds,
  getTreeSnapshot,
  traversalTree
} from "./utils.ts";
import {
  api_editSectionById,
  api_addSection
} from "@/components/AiEditor/core/services/servers";

import "./index.less";
import { useNavigate } from "react-router-dom";
import OutlineCmp, { stageTypes, sourceTypes } from "./components/Outline";

const { useForm } = Form;
const { confirm } = Modal;
interface ISegmentedWriting {
  open: boolean;
  onClose: () => void;
}
enum ProcessType {
  BASIC_INFO = 1,
  GUIDELINES_MATERAILS = 2,
  GERNERATE_DOC = 3
}

const initOriginData = {
  kbs: [],
  folders: [],
  files: []
};

const drawerTitleList = [
  {
    key: ProcessType.BASIC_INFO,
    value: "场景基本信息"
  },
  {
    key: ProcessType.GUIDELINES_MATERAILS,
    value: "大纲及素材"
  },
  {
    key: ProcessType.GERNERATE_DOC,
    value: "生成文章"
  }
];

enum writeTypes {
  ONLINE,
  OFFLINE
}

const initialSectionInfo = {
  visible: false,
  row: {}
};
export const SegmentedWriting = ({ open, onClose }: ISegmentedWriting) => {
  const { serverInfo, projectData, setProjectData, setWritingSettingOpen } =
    useStateStore();
  const articleDataRef = useRef<any>({});
  const navigator = useNavigate();

  const { articleSettingSave } = useAiEditorOperators();
  const [curItemKey, setCurItemKey] = useState(ProcessType.BASIC_INFO);
  const [isShowRepeatCheckModal, setIsShowRepeatCheckModal] =
    useState<boolean>(false);
  const [repeatList, setRepeatList] = useState<Array<any>>([]);
  // ========================基本信息========================
  const [form] = useForm();
  const [formSchema, setFormSchema] = useState<any>([]); // 存储表单的 schema
  const [originDoc, setOriginDoc] = useState<any>({});
  const [title, setTitle] = useState("");
  // =====================素材及大纲========================
  const [outlines, setOutlines] = useState<OutlineType[]>([]);
  const outlinesRef = useRef<OutlineType[]>([]);
  // 分段写作封面
  const coverRef = useRef();
  //选择 后的素材列表,前端展示
  const [materialList, setMaterialList] = useState<any[]>([]);
  const [sectionData, setSectionData] = useState<any>({
    ...initialSectionInfo
  });

  //=====================文章生成=====================
  const [selectedRowKeys, setSelectedRowKeys] = useState<any[]>([]);

  const [materialTreeData, setMaterialTreeData] = useState<any>({
    ...initOriginData
  });
  const newMaterialListRef = useRef<any[]>([]);
  const [sceneContentSources, setSceneContentSources] = useState<any[]>([]);

  const getMaterialTree = (originData: any) => {
    console.log("originData:", originData);
    setMaterialTreeData({ ...originData });
  };

  const rowSelection: TableProps<OutlineType>["rowSelection"] = {
    selectedRowKeys,
    onChange: (selectedRowKeys: React.Key[]) => {
      setSelectedRowKeys([...selectedRowKeys]);
    }
  };

  // 整体loading
  const [articleTypeLoading, setArticleTypeLoading] = useState<boolean>(false);
  //获取模版详情
  const getTemplateDetail = async () => {
    try {
      setArticleTypeLoading(true);
      const res = await api_getArticleTypeDetails({
        data: {
          id: projectData.article_type || ""
        },
        config: serverInfo
      });
      setArticleTypeLoading(false);
      const { paramsSchema, name, contentSources } = res;
      setSceneContentSources(contentSources || []);
      const temp_schema = JSON.parse(paramsSchema)?.uiSchema || [];
      const schema = createTemplateForm(temp_schema);
      setFormSchema(schema);
      setTitle(name);
    } catch (e) {
      setArticleTypeLoading(false);
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
          title: data?.title || "",
          outlines: {
            ...originDoc.outlines,
            paragraphs:
              outlines?.length > 0
                ? outlinesConvertToApi(outlines)
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
      if (!originDoc.contentSources || originDoc.contentSources.length === 0) {
        console.log("lost,saveBasicInfo");
      }
      delete params.taskType;
      const settingRes = await articleSettingSave(params);
      const { id, articleTypeId, articleTypeVersionId, articleType } =
        settingRes;

      setProjectData((p) => {
        return {
          ...p,
          id
        };
      });

      articleDataRef.current = {
        id,
        articleTypeId,
        articleTypeVersionId,
        articleType
      };

      const docData = await api_getArticleById({
        data: {
          articleId: settingRes?.id
        },
        config: serverInfo
      });
      console.log(originDoc);
      setOriginDoc(docData);
      setCurItemKey(ProcessType.GUIDELINES_MATERAILS);

      //处理大纲数据
      const selKeys: string[] = [];
      const newOutLines = outlinesConvertToRender(
        docData?.outlines?.paragraphs || [],
        selKeys
      );

      const mList: any[] = classifyMaterialToRenderNew(docData.contentSources);
      setMaterialList(mList);
      newMaterialListRef.current = [...mList];

      coverRef.current = (docData?.outlines || {})?.coverPage;
      setOutlines([...newOutLines]);
      outlinesRef.current = [...newOutLines];
      setSelectedRowKeys([...selKeys]);
    });
  };

  // 大纲数据转换 增加id, children
  const outlinesConvertToRender = (data: any[], selectRowKey: string[]) => {
    return data.map((item) => {
      const id = uuid();
      if (item.contentOperation == "1") {
        // 回填第三步大纲选中
        selectRowKey.push(id);
      }
      const newItem: OutlineType = {
        ...item,
        id
      };

      if (item.subParagraphs && item.subParagraphs?.length > 0) {
        newItem.children = outlinesConvertToRender(
          item.subParagraphs,
          selectRowKey
        );
      }

      return newItem;
    });
  };

  // 前端渲染的大纲数据处理成接口需要的数据，提交到接口
  const outlinesConvertToApi = (data: any[]) => {
    return data.map((item: OutlineType) => {
      if (selectedRowKeys?.includes(item.id)) {
        item.contentOperation = "1";
      } else {
        item.contentOperation = "0";
      }
      const {
        title,
        section,
        sectionId,
        contentSources,
        contentOperation,
        dependency,
        useCustomDB,
        useCustomKb
      } = item;

      const newItem: any = {
        title,
        section,
        sectionId,
        contentOperation,
        contentSources,
        useCustomDB,
        useCustomKb
      };
      // 取出 sourceType == "knowledge_base"
      // const newContentSources = (contentSources || []).filter(
      //   (c) => c.sourceType == "knowledge_base"
      // );
      // 子节点才有contentsource

      if (dependency && dependency.length) {
        newItem.dependency = [...dependency];
      }

      // if (!item.children || item.children?.length == 0) {
      //   if (contentSources && contentSources?.length > 0) {
      //     newItem.contentSources = classifyMaterialToApi(contentSources);
      //   } else {
      //     newItem.contentSources = contentSources || null;
      //   }
      // }

      if (item.extraInfo) {
        newItem.extraInfo = item.extraInfo;
      }

      if (item.children) {
        newItem.subParagraphs = outlinesConvertToApi(item.children);
      }
      return newItem;
    });
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
      } else if (item.children) {
        item.children = loopDataSourceAdd(item.children, id, level + 1);
      }
      return item;
    });
  };

  const addRow = () => {
    const newOutLines = [...outlines, { id: uuid() }];
    setOutlines([...newOutLines]);
    outlinesRef.current = [...newOutLines];
  };

  const getText = (record: any, key: string) => {
    const { section, title } = record;
    return section && section[key] ? <b>{title}</b> : <span>{title}</span>;
  };

  const renderTitle = (record: any, key: string) => {
    return (
      <>
        {record?.title?.trim()?.length > 0 ? (
          <span
            className={`outline-title-${key}`}
            style={{
              paddingLeft: `${
                record.children && record.children.length > 0 ? "" : `${22}px`
              }`
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

  const stopPropagation = (e: any) => {
    e.stopPropagation();
  };

  //section 新增/编辑完后
  const changeSection = async (
    sectionInfo: any,
    oLines: any[],
    nodeId: string | number,
    updates: any
  ) => {
    console.log("section confirm:", sectionInfo, oLines, nodeId, updates);
    const { sectionPrompt } = sectionInfo;
    if (!sectionPrompt) {
      // 配置大纲章节时，修改内容要求为空，则此章节在生成文章中已勾选，应取消勾选
      setSelectedRowKeys([...selectedRowKeys.filter((i) => i !== nodeId)]);
    }

    if (!oLines.length || !nodeId) {
      console.log("error: 丢失outlines");
      return;
    }

    const api = sectionInfo.id ? api_editSectionById : api_addSection;
    const articleData = articleDataRef.current;
    const _data: any = {
      articleId: articleData.id,
      params: {
        ...sectionInfo,
        outlines: {
          paragraphs: [...oLines]
        }
      }
    };
    if (sectionInfo.id) {
      _data.id = sectionInfo.id;
    }

    const section = await api({
      data: _data,
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
            title: section.sectionTitle,
            sectionId: section.id,
            section: {
              materialType: section.materialType,
              hasSectionPrompt: !!section.sectionPrompt?.length,
              hasContent: !!node?.section?.hasContent
            }
          };
        }
        if (children) {
          newNode.children = traverse(children);
        }
        return newNode;
      });
    }

    const _outlines = traverse(outlinesRef.current);
    console.log("edit end:", serverInfo, section, oLines, outlines, _outlines);
    setOutlines([..._outlines]);
    outlinesRef.current = [..._outlines];
    setSectionData({ ...initialSectionInfo });
  };

  const deleteSection = async (record: OutlineType) => {
    const sectionIds: number[] = [];
    const articleData = articleDataRef.current;
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
      const otls = outlinesConvertToApi(newOutlines);
      const res = await api_deleteSectionByIds({
        data: {
          ids: sectionIds.join(","),
          articleId: articleData.id,
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
    }
    return true;
  };

  const validateMaterial = async () => {
    let isValidTitles = 0;
    function traverse(paragraphs: any[]) {
      paragraphs.some((p: any) => {
        if (!p.title) {
          //校验标题不为空
          ++isValidTitles;
        } else if (p.title && p.title.trim().length == 0) {
          ++isValidTitles;
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
    } else {
      const saveRes = await saveOutlines();
      if (saveRes) {
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
    const articleData = articleDataRef.current;
    setTimeout(() => {
      articleData.id && navigator(`/docWriting/docs/${articleData.id}`);
      editorEventBus.emit(EDITOR_EVENT_NAME.START_WRITE, "");
    }, 0);
    setWritingSettingOpen(false);
  };

  const saveOutlines = async (dropOutlines?: any, writeType?: writeTypes) => {
    const _outlines = dropOutlines || outlines || [];
    console.log(materialList, originDoc, outlines);
    const otls = outlinesConvertToApi(_outlines);
    const _originDoc = originDoc as any;

    // const newMsource = classifyMaterialToApi(mList || materialList);
    // const otherContentSources = (_originDoc.contentSources || []).filter(
    //   (c:any) => !Object.keys(sourceTypes).includes(c.sourceType)
    // );

    const _contentSources = _originDoc.contentSources || [];
    const _extraParams = _originDoc.extraParams || {};
    const newOutlines = _originDoc.outlines || {};

    if (!_contentSources || _contentSources.length === 0) {
      console.log("lost:saveOutlines");
    }

    const { id, articleTypeId, articleTypeVersionId, articleType } =
      articleDataRef.current;

    const params: any = {
      // taskType: writeType && writeType === writeTypes.OFFLINE ? 1 : 0,
      articleType,
      articleTypeId,
      articleTypeVersionId,
      extraParams: {
        ..._extraParams
      },
      // contentSources: [...otherContentSources, ...newMsource],
      contentSources: [..._contentSources],
      title: _originDoc?.title || "",
      id,
      outlines: {
        ...newOutlines,
        coverPage: coverRef.current,
        paragraphs: otls
      }
    };
    if (Object.prototype.toString.call(writeType) === "[object Number]") {
      params.taskType = writeType === writeTypes.OFFLINE ? 1 : 0;
    }

    const settingRes = await articleSettingSave(params);
    return settingRes;
  };

  const onLineGenerate = async () => {
    // const sectionIds = getCheckedSectionIds(outlines, selectedRowKeys);
    // const data = {
    //   articleId: articleDataRef.current.id,
    //   sectionIds
    // };
    // const res: any = await api_putDependencyDetect({
    //   data,
    //   config: serverInfo
    // });

    // const { success } = res;
    // if (success) {
    //   generate(writeTypes.ONLINE);
    //   // } else {
    //   //   message.error("勾选章节的依赖章节未全部Ready");
    // }
    generate(writeTypes.ONLINE);
  };

  const getCheckedSectionIds = (
    treeData: any[],
    targetIds: string[]
  ): string[] | number[] => {
    const result: string[] = [];

    const dfs = (node: any) => {
      if (!node.children?.length && targetIds.includes(node.id)) {
        result.push(node.sectionId);
        return;
      }

      if (node.children) {
        node.children.forEach(dfs);
      }
    };

    treeData.forEach(dfs);
    return result;
  };

  const generate = async (writeType?: writeTypes) => {
    const settingRes = await saveOutlines(null, writeType);
    if (settingRes) {
      toGenerate();
    }
  };
  // 立即生成 校验
  const checkDataIsHasContent = async () => {
    const isPass = await dependencyVerification({ outlines, selectedRowKeys });
    if (!isPass) {
      return;
    }
    const hasContentTree = filterTreeWithContent(outlines, selectedRowKeys);
    if (hasContentTree.length) {
      setRepeatList([...hasContentTree]);
      setIsShowRepeatCheckModal(true);
    } else {
      onLineGenerate();
    }
  };

  const closeRepeatCheckModal = () => {
    setIsShowRepeatCheckModal(false);
  };

  const filterTreeWithContent = (nodes: any[], filterKeys?: any[]): any[] => {
    const _filterKeys = filterKeys || [];
    if (!nodes || !nodes.length) {
      return [];
    }
    return nodes
      .map((node) => {
        const newNode = { ...node };
        const { children, section, id } = newNode;
        let hasValidChild = false;

        // 递归处理子节点
        if (children && children.length) {
          const filteredChildren = filterTreeWithContent(children, _filterKeys);
          hasValidChild = filteredChildren.length > 0;
          newNode.children = filteredChildren;
        }

        // 判断是否保留当前节点
        const isLeaf = !children || children.length === 0;
        if (isLeaf) {
          return section && section.hasContent && _filterKeys.includes(id)
            ? newNode
            : null;
        } else {
          return hasValidChild ? newNode : null;
        }
      })
      .filter(Boolean);
  };

  const renderRepeatItem = (item: any, level: number) => {
    const { children, title, id, isShowChild } = item;
    return (
      <div key={`item_${id}`}>
        <div
          className="h-6 leading-6 py-3 box-content overflow-hidden select-none"
          style={{ borderBottom: "1px solid #eee" }}
        >
          <span
            className={`inline-block h-6 box-content w-[${
              level === 0 && !children ? 1 * 20 : level * 20
            }px]`}
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

  const setOutlinesHandler = (oLines: any[]) => {
    setOutlines([...oLines]);
    outlinesRef.current = [...oLines];
  };

  const getLeafNodes = (node: any) => {
    if (!node.children || node.children.length === 0) {
      return [node.id];
    }

    return node.children.flatMap((child: any) => getLeafNodes(child));
  };

  const allLeafNodes = useMemo(() => {
    return (outlines || []).flatMap((root) => getLeafNodes(root));
  }, [outlines]);

  const getSelectNum = () => {
    let num = 0;
    selectedRowKeys.forEach((key: string) => {
      if (allLeafNodes.find((i: string) => i === key)) {
        num++;
      }
    });
    return num;
  };

  const renderProcess = useCallback(() => {
    switch (curItemKey) {
      case ProcessType.BASIC_INFO:
        return (
          <div className="form-basic-wrap pt-5">
            <BetaSchemaForm
              className="w-1/2 m-auto"
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
          <OutlineCmp
            outlines={outlines}
            stageType={stageTypes.write}
            treeList={materialList}
            sceneContentSources={sceneContentSources}
            setOutlines={setOutlinesHandler}
            deleteSection={deleteSection}
            loopDataSourceDelete={loopDataSourceDelete}
            setSectionData={setSectionData}
            materialConfiem={materialConfiem}
            saveDropResult={saveOutlines}
            getMaterialTree={getMaterialTree}
          >
            <div className="flex">
              <span className="w-[1px] bg-[#eee] mr-2 -ml-[2px] h-6 mt-1"></span>
              <Button
                className="border-[#EEE] px-3"
                icon={
                  <PlusOutlined
                    className={`text-base text-primary-color pt-[2px]`}
                  />
                }
                onClick={addRow}
              >
                添加标题
              </Button>
            </div>
          </OutlineCmp>
        );
      case ProcessType.GERNERATE_DOC:
        return (
          <div className="outlines pt-4 pr-4">
            <b className="text-gray-2a">选择模块</b>
            <ProTable
              className="mt-2"
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
                getCheckboxProps: (record) => ({
                  // disabled: !record.sectionId
                  disabled:
                    (!record.subParagraphs || !record.subParagraphs.length) &&
                    (!record.sectionId ||
                      !record.section ||
                      (record.section && !record.section.hasSectionPrompt))
                }),
                checkStrictly: false,
                renderCell: (checked, record, index, originNode) => {
                  const { children, section } = record;
                  if (
                    (!record.subParagraphs || !record.subParagraphs.length) &&
                    (!record.sectionId ||
                      !record.section ||
                      (record.section && !record.section.hasSectionPrompt))
                  ) {
                    return (
                      <Tooltip title="该模块未填写内容要求，暂不可选择">
                        <span style={{ opacity: 0.5, cursor: "not-allowed" }}>
                          {originNode}
                        </span>
                      </Tooltip>
                    );
                  }
                  return originNode;
                }
              }}
              tableAlertRender={() => {
                return <span>已选 {getSelectNum()} 项</span>;
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
                }
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
    materialList,
    selectedRowKeys,
    materialTreeData,
    sceneContentSources
  ]);

  const prevStep = (step: ProcessType) => async () => {
    const saveRes = await saveOutlines();
    if (saveRes) {
      setCurItemKey(step);
    }
  };

  const getOfflineGenerateParams = () => {
    const otls = outlinesConvertToApi(outlines);
    const treeSnapshot = getTreeSnapshot(
      otls,
      "subParagraphs",
      (node: any) => node.contentOperation === "1"
    );
    const sectionIds = getAllLeafNodeSectionIds(treeSnapshot, "subParagraphs");

    return {
      sectionIds
      // outlinesSnapshot: { paragraphs: treeSnapshot }
    };
  };

  // 依赖校验，放行返回true,拒绝返回false
  const [dependencyModal, setDependencyModal] = useState<boolean>(false);
  const [dependencySnapshot, setDependencySnapshot] = useState([]);
  const closeDependencyModal = () => {
    setDependencyModal(false);
    setDependencySnapshot([]);
  };
  const dependencyVerification = async ({ outlines, selectedRowKeys }: any) => {
    const sectionIds = getCheckedSectionIds(outlines, selectedRowKeys);
    const data = {
      articleId: articleDataRef.current.id,
      sectionIds
    };
    const res: any = await api_putDependencyDetect({
      data,
      config: serverInfo
    });
    if (res && res.data) {
      if (res.data.isDependReady) {
        // 依赖没问题放行
        return true;
      } else {
        // 依赖有问题，给出弹窗提示
        const { sections } = res.data;
        const ids = sections.map((i: { id: any }) => i.id);
        const snapshot = getTreeSnapshot(
          outlines,
          "subParagraphs",
          (node: any) => ids.includes(node?.sectionId)
        );
        const snapshotTree = traversalTree(
          snapshot,
          "subParagraphs",
          (node) => {
            const obj = {
              isShowChild: true,
              title: node.title,
              id: node.sectionId || node.id
            };
            return obj;
          }
        );
        setDependencySnapshot(snapshotTree);
        setDependencyModal(true);
        return false;
      }
    } else {
      return false;
    }
  };
  const [offGenLoading, setOffGenLoading] = useState(false);
  const offlineGenerate = async () => {
    const isPass = await dependencyVerification({ outlines, selectedRowKeys });
    if (!isPass) {
      return;
    }
    const settingRes = await saveOutlines(null, writeTypes.OFFLINE);
    if (settingRes) {
      setOffGenLoading(true);
      try {
        const params = getOfflineGenerateParams();
        if (!articleDataRef.current || !articleDataRef.current.id) {
          message.error("文章id不存在");
          return;
        }
        const res: any = await api_addArticleTask({
          data: {
            articleId: articleDataRef.current.id,
            ...params
          },
          config: serverInfo
        });
        if (!res || !res.success) {
          return;
        }
        message.loading("文档已开始离线生成，可在我的文档中查看进度", 3, () => {
          setOffGenLoading(false);
          navigator(
            `/docWriting/history?highlightId=${articleDataRef.current.id}`
          );
        });
      } catch (e) {
        setOffGenLoading(false);
        console.log(e);
      }
    }
  };

  const renderFooter = useCallback(() => {
    const step =
      curItemKey === ProcessType.BASIC_INFO
        ? ProcessType.BASIC_INFO
        : curItemKey === ProcessType.GERNERATE_DOC
          ? ProcessType.GUIDELINES_MATERAILS
          : ProcessType.BASIC_INFO;
    switch (curItemKey) {
      case ProcessType.BASIC_INFO:
        return (
          <Flex align="center" justify="flex-end" gap={16}>
            <Button
              className="text-text-color2 rounded px-4"
              onClick={saveBasicInfo}
            >
              下一步
            </Button>
          </Flex>
        );
      case ProcessType.GERNERATE_DOC:
      case ProcessType.GUIDELINES_MATERAILS:
        return (
          <Flex align="center" justify="flex-end" gap={16}>
            <Button
              className="rounded"
              style={{
                border: "1px solid #ebebeb",
                color: "#555"
              }}
              onClick={prevStep(step)}
              disabled={offGenLoading}
            >
              上一步
            </Button>
            {curItemKey === ProcessType.GERNERATE_DOC && (
              <Tooltip
                title={
                  <span className="text-gray-2a">流式输出，实时查看进度</span>
                }
                color="#fff"
              >
                <Button
                  className="text-primary-color rounded px-3 online-btn"
                  onClick={checkDataIsHasContent}
                  disabled={offGenLoading || !selectedRowKeys.length}
                >
                  在线生成
                </Button>
              </Tooltip>
            )}
            {curItemKey === ProcessType.GERNERATE_DOC ? (
              <Tooltip
                placement="topRight"
                title={
                  <span className="text-gray-2a">
                    后台异步生成，可在文档列表查看进度
                  </span>
                }
                color="#fff"
              >
                <Button
                  className="text-white rounded border-0 px-2"
                  style={{
                    color: "#fff",
                    background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`
                  }}
                  disabled={!selectedRowKeys.length}
                  loading={offGenLoading}
                  onClick={offlineGenerate}
                >
                  离线生成
                </Button>
              </Tooltip>
            ) : (
              <Button
                className="text-text-color2 rounded px-4"
                loading={offGenLoading}
                onClick={validateMaterial}
              >
                下一步
              </Button>
            )}
          </Flex>
        );
      default:
        return null;
    }
  }, [
    curItemKey,
    originDoc,
    selectedRowKeys,
    outlines,
    materialList,
    offGenLoading
  ]);

  const materialConfiem = (list: any[], sourceType: sourceTypes) => {
    console.log("new material list:", list);
    const _list = materialList.filter((i: any) => i.sourceType !== sourceType);
    const newList = [..._list, ...list];
    setMaterialList([...newList]);
    newMaterialListRef.current = [...newList];
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

    list?.forEach((tb: any) => {
      if (sourceType === sourceTypes.database) {
        dbSource.refIds.push(tb.refId),
          dbSource.refNames.push(tb.refName),
          dbSource.dbNames.push(tb.dbName);
      }
      if (sourceType === sourceTypes.knowledge_base) {
        switch (tb.usage) {
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
          case "both":
            kbTemplateSource.refIds.push(tb.refId),
              kbTemplateSource.refNames.push(tb.refName),
              (kbTemplateSource.usage = tb.usage);
            kbContentSource.refIds.push(tb.refId),
              kbContentSource.refNames.push(tb.refName),
              (kbContentSource.usage = tb.usage);
            break;
        }
      }
    });

    // 按照接口需要的方式保存contentSources
    setOriginDoc((pre: any) => {
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

  useEffect(() => {
    if (open && projectData.article_type) {
      getTemplateDetail();
      if (projectData?.id) {
        getDocDetail(projectData?.id as unknown as number);
      }
    }
  }, [open, projectData?.id, projectData.article_type]);

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

  return (
    <div className="w-full h-full relative z-10">
      <Flex vertical className="rounded-t-xl relative box-border">
        {formSchema && (
          <ProcessDrawer
            curItemKey={curItemKey as any}
            onClose={onClose}
            subTitle={title}
            list={drawerTitleList}
            renderFooter={renderFooter()}
          >
            <Spin spinning={articleTypeLoading}>{renderProcess()}</Spin>
          </ProcessDrawer>
        )}

        <SectionDrawer
          open={sectionData.visible}
          row={sectionData.node}
          serverInfo={serverInfo}
          outlines={outlines}
          stageType={stageTypes.write}
          treeList={materialList}
          materialTreeData={materialTreeData}
          onClose={changeSection}
        />
      </Flex>
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
              onClick={onLineGenerate}
              className="mr-2"
            />
            <Button
              children="取消"
              style={{
                border: "1px solid #ebebeb",
                color: "#555"
              }}
              onClick={closeRepeatCheckModal}
              className="mr-2"
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
      <Modal
        open={dependencyModal}
        title={
          <div className="-ml-1">
            <InfoCircleFilled style={{ color: "#faad14" }} />
            <b className="text-base ml-3">被依赖模块未勾选</b>
          </div>
        }
        width="400px"
        height="428px"
        closable={true}
        onCancel={closeDependencyModal}
        footer={null}
      >
        <div className="ml-6 text-sm text-[#2a2a2a] mb-3">
          以下模块被依赖，请进行勾选
        </div>
        <div className="ml-6 h-80 overflow-y-auto text-[#2a2a2a] text-sm">
          {(dependencySnapshot || []).map((item: any) =>
            renderRepeatItem(item, 0)
          )}
        </div>
      </Modal>
    </div>
  );
};

export default SegmentedWriting;
