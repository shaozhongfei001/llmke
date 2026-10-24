import { PlusCircleOutlined } from "@ant-design/icons";
import {
  Button,
  Checkbox,
  Divider,
  Flex,
  Form,
  Modal,
  Select,
  Switch,
  message,
  DatePicker
} from "antd";
import dayjs from "dayjs";
import { cn } from "@udecode/cn";
import { useEffect, useMemo, useState } from "react";
import { useStateStore } from "../../core/states/useStateStore";
import {
  BetaSchemaForm,
  ProFormCheckbox,
  ProFormSelect
} from "@ant-design/pro-form";
import { empty_mode_form_schema } from "../../core/configs/empty_mode_form_schema";
import {
  api_generateOutlines,
  api_getArticleTypeDetails
} from "../../core/services/servers";
import { notify_mode_form_schema } from "../../core/configs/notify_mode_form_schema";
import UpArrow from "@/components/AiEditor/assets/img/upArrow.png";
import DownArrow from "@/components/AiEditor/assets/img/downArrow.png";
import MaterialList from "./components/MaterialList/MaterialList";
import { useOutlinesDsigner } from "@/components/OutlineDesigner";
import { uid } from "uid";
import AiIconDisabled from "@/components/AiEditor/assets/icon/aiIconDisabled.svg";
import AiGene from "@/components/AiEditor/assets/icon/aiGene.svg";
import Empty1 from "@/components/AiEditor/assets/img/empty1.png";
import {
  addItemById,
  changeItemById,
  delItemById,
  moveItem,
  createTemplateForm
} from "./util";
import { useMouduleOperators } from "../../core/operators/useMouduleOperators";
import { Node } from "slate";
import {
  red_headed_mode_form_schema,
  redHeadInitValue
} from "../../core/configs/red_headed_mode_form_schema";
import useAiEditorOperators from "../../core/operators/useAiEditorOperators";
import { Loading } from "../Loading";
import {
  EditorStatus,
  ModueEnum,
  ModuleStatus,
  ProjectStatus
} from "../../@types/sys";
import { useGlobalOperators } from "../../core/operators/useGlobalOperators";
import { redTitleStyle } from "../MainEditor/default_style";
import { redTitleHtml } from "../../core/configs/red_head_temp";
import { EDITOR_EVENT_NAME, editorEventBus } from "../../editorEventBus";
import { articleContentSave } from "../../core/operators/help";

const redTitleObj = {
  title: "通知标题",
  target: "主送机关",
  publisher: "发文机关",
  publishDate: "发文时间",
  documentNumber: "发文字号"
};

const formItemLayout = {
  labelCol: { xs: { span: 24 }, sm: { span: 5 } }
};
interface MenuOption {
  label: JSX.Element;
  value: string;
}

interface MenuGroup {
  label: JSX.Element;
  title: string;
  options: MenuOption[];
}

enum ArticleType {
  OfficialDocument = "type_id=0&id=0&version=0",
  Announcement = "type_id=1&id=0&version=0"
}

const builtInSchema: any = {
  "0": empty_mode_form_schema,
  "1": notify_mode_form_schema
};

const modulesToMenuData = (modules_set: any[]): MenuGroup[] => {
  const systemOptions = modules_set
    .filter((m) => m.isSystem)
    .map((m) => ({
      label: <span>{m.name}</span>,
      value: `type_id=${m.type_id}&id=${m.id}&version=${m.version}`
    }));

  const customizedOptions = modules_set
    .filter((m) => !m.isSystem)
    .map((m) => ({
      label: <span>{m.name}</span>,
      value: `type_id=${m.type_id}&id=${m.id}&version=${m.version}&hasRedTemp=${true}&articleTypeKey=${m.articleTypeKey || ""}`
    }));
  return [
    {
      label: <span>系统模版</span>,
      title: "system",
      options: systemOptions
    },
    {
      label: <span>自定义模版</span>,
      title: "customized",
      options: customizedOptions
    }
  ];
};

const findInitialValue = (
  menuData: MenuGroup[],
  // 这是mode
  typeId: string,
  // 这是id
  id: string
): string | undefined => {
  const targetValue = `type_id=${typeId}&id=${id}`;
  for (const group of menuData) {
    const option = group.options.find((item) => {
      const itemArr = item.value.split("&");
      return (
        item.value.includes(targetValue) ||
        itemArr.includes(`articleTypeKey=${id}`)
      );
    });
    if (option) {
      return option.value;
    }
  }
  return undefined;
};

const WritingModule = () => {
  const isSimpleLoadingStatus = (status: EditorStatus) => {
    return [
      EditorStatus.WaitingForGen,
      EditorStatus.GeneratingFullText,
      EditorStatus.ReviewingFullText
    ].includes(status);
  };
  const {
    projectData,
    serverInfo,
    mainEditor,
    setProjectData,
    setEditorManager,
    editorManager,
    useTemp,
    setUseTemp,
    displayOriginTemp,
    setDisplayOriginTemp,
    baseInfo
  } = useStateStore();

  const { getSubmitFromData } = useMouduleOperators();

  const { setProjectStatus, setModuleStatus } = useGlobalOperators();

  const {
    insertDataToTemp,
    articleSettingSave,
    startLLMWriting,
    stopLLMWriting
  } = useAiEditorOperators();

  const [menuData, setMenuData] = useState<MenuGroup[]>([]); // 为 menuData 指定类型
  const [formSchema, setFormSchema] = useState<any>([]); // 存储表单的 schema
  const [showForm, setShowForm] = useState(true); //收起，展开

  const form = useMemo(() => {
    return projectData.form;
  }, [projectData.form]);

  // 下拉框的值
  const selectedOption = useMemo(() => {
    if (!projectData.supported_types) return;
    const menuDataResult = modulesToMenuData(projectData.supported_types);
    setMenuData(menuDataResult);
    const selectValue = findInitialValue(
      menuDataResult,
      projectData.article_type_mode ? projectData.article_type_mode : "0",
      projectData.article_type ? projectData.article_type : "0"
    );
    return selectValue;
  }, [
    projectData.supported_types,
    projectData.article_type,
    projectData.article_type_mode
  ]);

  // 大模型生成完后保存和审核文章
  // useEffect(() => {
  //   if (projectData.saveArticle === "init") return;
  //   stopLLMWriting(projectData.id);
  // }, [projectData.saveArticle, projectData.outputFormat]);

  // 表单变更插入初始值
  useEffect(() => {
    if (!form) return;
    if (projectData.article_type_mode === "1") {
      form.setFieldsValue(redHeadInitValue);
    }
  }, [formSchema, form]);

  const getSchemaForSelectedOption = async (
    selectedOption: string | undefined
  ) => {
    setModuleStatus(ModuleStatus.Process, ModueEnum.Writing);
    const params = new URLSearchParams(selectedOption);
    // 将其转换为对象
    const queryObject: Record<string, string> = {};
    params.forEach((value, key) => {
      queryObject[key] = value;
    });

    let form_schema: any = [];
    //只有解析后type_id===2（自定义）
    if (queryObject["type_id"] === "2") {
      const res = await api_getArticleTypeDetails({
        data: {
          id: queryObject.id
        },
        config: serverInfo
      });
      setProjectData((p) => ({
        ...p,
        outputFormat: res?.outputFormat,
        contentRule: res?.contentRule,
        sensitiveWords: res?.sensitiveWords
      }));
      form_schema = handleTemplateDetail(res, form_schema);
    } else {
      // 下拉框切换的时候清空模版和样式
      setProjectData((p) => ({
        ...p,
        customized_style: {
          enable: false,
          styles: {},
          htmlSchema: "",
          formSchemaMap: {},
          originHtmlSchema: ""
        }
      }));
      form_schema = builtInSchema[queryObject["type_id"]];
    }

    // 设置表单 schema（假设返回的 schema 是 `empty_mode_form_schema`）
    setFormSchema(form_schema);
    setModuleStatus(ModuleStatus.Waiting, ModueEnum.Writing);
  };

  /* 处理 formatTemplate, 
    1、 处理 paramsSchema.uiSchema 成为右侧表单数据 {dataIndex: title}
    2、将处理后数据的dataIndex 与 formatTemplate.htmlSchema 里{dataIndex}中数据匹配
    并且替换成为{title}
  */
  const handleTemplateDetail = (res: any, form_schema: any[]) => {
    const { paramsSchema, formatTemplate, supportMaterials, supportOutlines } =
      res;
    const temp_schema = JSON.parse(paramsSchema)?.uiSchema || [];
    // 表单增加校验, 不同类型的渲染
    form_schema = createTemplateForm(temp_schema);
    const form_schema_dataIndex: any = {}; //存放{dataIndex:title}映射
    form_schema.forEach((s: any) => {
      form_schema_dataIndex[s.dataIndex] = s.title;
    });

    // 如果有formatTemplate字段，说明有红头模版
    if (formatTemplate && formatTemplate?.length > 0) {
      const template = JSON.parse(formatTemplate);
      // 把接口返回的htmlSchema转换成前端编辑器展示的模版
      let newHtmlSchema = template.htmlSchema;
      for (const key in form_schema_dataIndex) {
        newHtmlSchema = newHtmlSchema.replace(
          new RegExp(`{${key}}`, "g"),
          `{${form_schema_dataIndex[key]}}`
        );
      }

      setProjectData((p) => ({
        ...p,
        supportMaterials,
        supportOutlines,
        customized_style: {
          enable: true,
          styles: JSON.parse(template.cssSchema),
          htmlSchema: newHtmlSchema,
          formSchemaMap: form_schema_dataIndex,
          originHtmlSchema: template.htmlSchema //存储接口返回的原始htmlSchema，saveSetting接口需要使用
        }
      }));
    } else {
      setProjectData((p) => ({
        ...p,
        supportMaterials,
        supportOutlines,
        customized_style: {
          enable: false,
          styles: {},
          htmlSchema: "",
          formSchemaMap: {},
          originHtmlSchema: ""
        }
      }));
    }
    return form_schema;
  };

  // 初始化将表单值填入
  useEffect(() => {
    if (!form) return;
    form.setFieldsValue({
      ...projectData.extraParams,
      contentAbstract:
        projectData?.contentAbstract ||
        projectData?.extraParams?.contentAbstract,
      lengthLimit: projectData?.lengthLimit,
      title: projectData.title === "未命名文档" ? "" : projectData.title
    });
  }, [projectData.contentAbstract, form, projectData.extraParams]);

  useEffect(() => {
    // 红头文件有内容，进来直接渲染,需要使用模版样式渲染
    if (projectData.customized_style.enable) {
      setEditorManager((p) => ({
        ...p,
        styles: projectData?.customized_style.styles
      }));
    } else if (projectData.article_type_mode == "1") {
      setEditorManager((p) => ({ ...p, styles: redTitleStyle }));
    }
  }, [projectData.id, projectData.customized_style.enable]);

  const handleModeTypeChanged = (value: string) => {
    const params = new URLSearchParams(value);

    // 将其转换为对象
    const queryObject: Record<string, string> = {};
    params.forEach((value, key) => {
      queryObject[key] = value;
    });
    // console.log(value, projectData, params, queryObject, modules)
    setProjectData((p) => ({
      ...p,
      article_type_mode: queryObject["type_id"],
      article_type: queryObject["id"]
    }));
    setUseTemp(false);
  };

  // useEffect(() => {
  //   if (form) {
  //     form.setFieldValue('title', projectData.title);
  //   }
  //   if (!useTemp || !form) return;
  //   if (selectedOption?.includes('type_id=1')) {
  //     insertDataToTemp(
  //       mainEditor.current,
  //       { ...form.getFieldsValue(), title: projectData.title },
  //       redTitleHtml,
  //       redTitleObj as any
  //     );
  //   }
  // }, [projectData.title, form]);

  // 监听 initialValue 或者 selectedOption 变化时请求数据
  useEffect(() => {
    if (selectedOption) {
      getSchemaForSelectedOption(selectedOption);
    }
  }, [selectedOption]);

  // 素材相关
  const [curMaterialList, setCurMaterialList] = useState<any>([]); //当前选择得素材
  const confirmSelect = (list: any) => setCurMaterialList(list);

  // 大纲相关
  const [useOutline, setUseOutline] = useState<boolean>(false);
  const [outlineData, setOutlineData] = useState<any>([]);

  useEffect(() => {
    if (projectData.outlines && projectData.outlines.length > 0) {
      setUseOutline(true);
    }
  }, [projectData.outlines]);

  // 大纲
  useEffect(() => {
    if (!projectData.outlines) return;
    setUseTemp(false);
    setOutlineData(projectData.outlines);
  }, [projectData.outlines]);

  const outlinesEventEmit = (title: string, data: any) => {
    switch (title) {
      case "outlines_changeItem":
        setOutlineData(
          changeItemById({
            tree: outlineData,
            value: data.value,
            key: data.key,
            id: data.itemData.id
          })
        );
        break;
      case "outlines_delItem":
        setOutlineData(delItemById(outlineData, data.id));
        break;
      case "outlines_addItem":
        setOutlineData(addItemById(outlineData, data.id));
        break;
      case "outlines_moveToTop":
        setOutlineData(
          moveItem("top", {
            tree: data.outlineData,
            dragItem: data.dragItem,
            dropItem: data.dropItem
          })
        );
        break;
      case "outlines_moveToBottom":
        setOutlineData(
          moveItem("bottom", {
            tree: data.outlineData,
            dragItem: data.dragItem,
            dropItem: data.dropItem
          })
        );

        break;
      default:
        break;
    }
  };

  const handleOutline = () => {
    setUseOutline(!useOutline);
    if (!useOutline) {
      setShowForm(false);
    }
  };

  const { OutlineElement } = useOutlinesDsigner({
    outlinesEventEmit,
    outlineData,
    limit: 1
  });

  // 新增段落
  const addOutline = () => {
    if (outlineData?.length >= 10) {
      message.warning("大纲段落不大于10个");
      return;
    }
    setOutlineData((p) => [
      ...p,
      {
        id: uid(32),
        title: "",
        contentAbstract: ""
      }
    ]);
  };

  // 生成大纲请求
  const [outlineLoading, setOutlineLoading] = useState<boolean>(false);
  const handleGenOutline = async () => {
    const formData = form.getFieldsValue();
    const { contentAbstract } = formData;
    if (!contentAbstract) {
      message.warning("请填写内容描述");
      return;
    }
    try {
      setOutlineLoading(true);
      let contentSources: any = [];
      if (curMaterialList.length) {
        const refIds: number[] = [];
        const refNames: string[] = [];
        curMaterialList.forEach((i: any) => {
          refNames.push(i.fileName);
          refIds.push(i.id);
        });
        contentSources = [
          {
            sourceType: "materials",
            refIds,
            refNames
          }
        ];
      }
      const outlines = await api_generateOutlines({
        config: serverInfo,
        data: {
          params: {
            contentAbstract,
            title: projectData.title,
            sources: contentSources
          }
        }
      });
      setOutlineLoading(false);
      if (outlines && outlines.paragraphs) {
        const allData = outlines.paragraphs.map((i) => ({
          title: i.title,
          id: uid(32),
          contentAbstract: i.contentAbstract
        }));
        setOutlineData(allData);
      }
    } catch (e) {
      console.log(e);
      setOutlineLoading(false);
    }
  };

  // 红头文件相关
  const [redHeadTipShow, setRedHeadTipShow] = useState<boolean>(false);

  useEffect(() => {
    if (projectData?.useTemplate) {
      setDisplayOriginTemp(false);
      setUseTemp(true);
    } else {
      // setDisplayOriginTemp(true);
      // setUseTemp(false);
    }
  }, [projectData.useTemplate]);

  useEffect(() => {
    const params = new URLSearchParams(selectedOption);
    // 将其转换为对象
    const queryObject: Record<string, string> = {};
    params.forEach((value, key) => {
      queryObject[key] = value;
    });
    if (queryObject["type_id"] === "1") {
      if (useTemp) {
        setFormSchema(red_headed_mode_form_schema);
        setTimeout(() => {
          displayOriginTemp &&
            setEditorManager((p) => ({ ...p, styles: redTitleStyle }));
          displayOriginTemp &&
            insertDataToTemp(
              mainEditor.current,
              {
                ...form.getFieldsValue()
              },
              redTitleHtml,
              redTitleObj
            );
        }, 0);
      } else {
        setFormSchema(notify_mode_form_schema);
      }
    }
    if (useTemp) {
      if (projectData.customized_style?.htmlSchema) {
        setTimeout(() => {
          displayOriginTemp &&
            setEditorManager((p) => ({
              ...p,
              styles: projectData.customized_style.styles
            }));
          displayOriginTemp &&
            insertDataToTemp(
              mainEditor.current,
              {
                ...form.getFieldsValue()
                // title: projectData.title,
              },
              projectData.customized_style?.htmlSchema,
              projectData.customized_style.formSchemaMap
            );
        }, 0);
      }
    }
  }, [useTemp, displayOriginTemp]);

  const handleConfirmRedHead = () => {
    setUseTemp(true);
    setRedHeadTipShow(false);
  };

  const handleCloseRedHead = () => {
    setRedHeadTipShow(false);
  };

  const onValuesChange = (formItem: { [x: string]: any }, allValues: any) => {
    const keys = Object.keys(formItem);
    if (keys[0] === "title") {
      setProjectData((p) => ({
        ...p,
        title: formItem["title"]
      }));
    }
    if (!useTemp) return;

    let temp;
    let formSchemaMap;
    if (selectedOption?.includes("type_id=1")) {
      temp = redTitleHtml;
      formSchemaMap = redTitleObj;
      setEditorManager((p) => ({ ...p, styles: redTitleStyle }));
    } else if (projectData.customized_style?.enable) {
      temp = projectData.customized_style?.htmlSchema;
      formSchemaMap = projectData.customized_style.formSchemaMap;
    }
    insertDataToTemp(
      mainEditor.current,
      { ...allValues },
      temp,
      formSchemaMap as any
    );
  };

  const handleGen = async () => {
    try {
      // 处理状态
      setModuleStatus(ModuleStatus.Process, ModueEnum.Writing);
      setProjectStatus(ProjectStatus.Process);
      setProjectData((p) => ({
        ...p,
        files: [],
        sourceList: []
      }));
      // 处理参数
      const params: any = await getSubmitFromData({
        outlineData,
        useOutline,
        form,
        selectedOption,
        curMaterialList,
        useTemp: useTemp
      });
      setEditorManager((p) => ({ ...p, status: EditorStatus.WaitingForGen }));
      // 保存配置
      const settingRes = await articleSettingSave(params);
      // 保存文章id
      setProjectData((p) => ({ ...p, id: settingRes.id.toString() }));

      // 根据id写作
      startLLMWriting({
        id: settingRes.id,
        useTemp: useTemp,
        formData: form.getFieldsValue(),
        selectedOption
      });
    } catch (e) {
      setEditorManager((p) => ({
        ...p,
        status: EditorStatus.Waiting
      }));
    }
  };

  // 用户不点击生成情况下的保存
  useEffect(() => {
    const handleSave = async (cb: () => void) => {
      // 处理参数
      const params: any = await getSubmitFromData({
        outlineData,
        useOutline,
        form,
        selectedOption,
        curMaterialList,
        useTemp
      });
      // 保存配置
      const settingRes = await articleSettingSave(params);
      setProjectData((p) => ({
        ...p,
        id: settingRes.id
      }));
      await articleContentSave({
        id: settingRes.id,
        baseInfo,
        projectData,
        serverInfo,
        mainEditor
      });
      cb();
    };
    editorEventBus.on(EDITOR_EVENT_NAME.CLICKSAVE, handleSave);
    return () => {
      editorEventBus.off(EDITOR_EVENT_NAME.CLICKSAVE, handleSave);
    };
  }, [
    outlineData,
    useOutline,
    form,
    selectedOption,
    curMaterialList,
    useTemp,
    projectData?.title,
    projectData.extraParams,
    baseInfo,
    projectData.files
  ]);

  return (
    <>
      <Modal
        open={redHeadTipShow}
        onOk={handleConfirmRedHead}
        onCancel={handleCloseRedHead}
      >
        <p className="mt-[25px] mb-[30px]">
          注意：使用格式模板，文章内容将被清空!
        </p>
      </Modal>
      <div className="h-full w-full relative">
        <div className={cn("flex px-3 py-2 justify-between items-center")}>
          <Flex className="section-title" style={{ width: "100%" }}>
            <div className="flex-1">文章简介</div>
            {projectData.supportOutlines == 1 && (
              <img
                src={showForm ? UpArrow : DownArrow}
                onClick={() => setShowForm(!showForm)}
                style={{ cursor: "pointer" }}
              />
            )}
          </Flex>
        </div>
        <div className="px-3">
          <Divider className="m-0 border-[#DBDBDB]" />
        </div>
        <div
          className="overflow-y-auto p-[15px] w-full"
          style={{
            height: "calc(100% - 100px)"
          }}
        >
          <div className={`${showForm ? "" : "hidden"}`}>
            <Select
              disabled
              className="w-full mb-5"
              options={menuData}
              onChange={handleModeTypeChanged}
              allowClear={false} // 禁用清除按钮
              value={selectedOption}
            />
            {(projectData?.customized_style?.enable ||
              selectedOption?.includes("type_id=1")) && (
              <div className="mb-5 text-[#555]">
                是否使用格式模板&emsp;
                <Checkbox
                  checked={useTemp}
                  onChange={(e) => {
                    setDisplayOriginTemp(true);
                    if (
                      e.target.checked &&
                      Node.string(mainEditor?.current as any)
                    ) {
                      setRedHeadTipShow(true);
                    } else {
                      setUseTemp(!useTemp);
                    }
                  }}
                />
              </div>
            )}
            <BetaSchemaForm
              layoutType="Form"
              form={form}
              columns={formSchema} // 动态根据选择渲染表单
              submitter={false}
              onValuesChange={onValuesChange}
            />
            {(selectedOption === ArticleType.OfficialDocument ||
              projectData.supportMaterials == 1) && (
              <MaterialList
                curMaterialList={curMaterialList}
                setCurMaterialList={setCurMaterialList}
                confirmSelect={confirmSelect}
                contentSources={projectData?.contentSources || []}
              />
            )}
          </div>

          {(selectedOption === ArticleType.OfficialDocument ||
            projectData.supportOutlines == 1) && (
            <>
              {/* 文章大纲 */}
              <Flex className="section-title mt-[20px]">
                <div className="flex w-[200px] items-center flex-1">
                  <div className="mr-[12px]">文章大纲</div>
                  <Switch checked={useOutline} onClick={handleOutline} />
                </div>
                {useOutline && (
                  <Flex gap={10}>
                    {!outlineData?.length && (
                      <Button
                        size="small"
                        ghost
                        icon={<PlusCircleOutlined />}
                        disabled={!useOutline}
                        onClick={addOutline}
                        type="primary"
                        style={{
                          color: `${!useOutline ? "#dedede" : "#055AFF"}`,
                          backgroundColor: "#fff",
                          borderRadius: "4px",
                          border: "1px solid #dedede"
                        }}
                      >
                        新建大纲
                      </Button>
                    )}
                    <Button
                      size="small"
                      disabled={!useOutline}
                      onClick={handleGenOutline}
                      // todo: 这里的loading记得处理
                      loading={outlineLoading}
                      ghost
                      icon={
                        <img
                          className="text-red-50"
                          src={useOutline ? AiGene : AiIconDisabled}
                        ></img>
                      }
                      style={{
                        color: `${!useOutline ? "#dedede" : "#055AFF"}`,
                        backgroundColor: "#fff",
                        borderRadius: "4px",
                        border: "1px solid #dedede"
                      }}
                    >
                      智能生成
                    </Button>
                  </Flex>
                )}
              </Flex>
              {useOutline && (
                <Flex vertical className="w-full">
                  {outlineLoading && <Loading />}
                  <Flex className="w-full">{OutlineElement}</Flex>
                  <Flex className="w-full">
                    {outlineData?.length ? (
                      <Button
                        size="small"
                        ghost
                        icon={<PlusCircleOutlined />}
                        disabled={!useOutline}
                        onClick={addOutline}
                        style={{
                          width: "100%",
                          color: `#555555`,
                          backgroundColor: "#fff",
                          borderRadius: "4px",
                          border: "1px dashed #dedede",
                          marginTop: "16px"
                        }}
                      >
                        添加段落
                      </Button>
                    ) : (
                      <div
                        className="flex flex-col justify-center items-center w-full"
                        style={{ marginTop: showForm ? "16px" : "100px" }}
                      >
                        <img src={Empty1} className="w-[106px] h-[91px]" />
                        <div className="text-[16px] text-[#222222] ml-[8px] mt-[16px]">
                          还没有文章大纲
                        </div>
                        <div className="text-[12px] text-[#999999] ml-[8px] mt-[8px]">
                          开始新建吧~
                        </div>
                      </div>
                    )}
                  </Flex>
                </Flex>
              )}
            </>
          )}
        </div>
        <div
          className={cn(
            "btn-container absolute bottom-0 shadow w-full",
            "px-5 py-4"
          )}
        >
          <Flex gap={15}>
            <Button
              type="primary"
              onClick={() => {
                handleGen();
              }}
              loading={isSimpleLoadingStatus(editorManager.status)}
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                border: "none",
                borderRadius: "4px"
              }}
            >
              立即生成
            </Button>
            <Button
              onClick={() => {
                console.log(mainEditor.current);
                // console.log(BlockSelectionPlugin?.options?.selectedIds);
                // BlockSelectionPlugin.options.selectedIds?.add("5");
                // console.log(BlockSelectionPlugin?.options?.selectedIds);
                form.resetFields();
                setCurMaterialList([]);
                setOutlineData([]);
              }}
              style={{
                color: `#555555`,
                backgroundColor: "#fff",
                borderRadius: "4px",
                border: "1px solid #dedede"
              }}
            >
              清空设置
            </Button>
          </Flex>
        </div>
      </div>
    </>
  );
};

export default WritingModule;
