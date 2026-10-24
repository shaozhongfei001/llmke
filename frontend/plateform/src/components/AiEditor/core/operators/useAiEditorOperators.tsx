import { deserializeHtml } from "@udecode/plate";
import { useStateStore } from "../states/useStateStore";
import {
  EditorStatus,
  ModueEnum,
  ModuleStatus,
  ProjectStatus
} from "../../@types/sys";
import {
  api_completeArticle,
  api_saveArticleSetting,
  api_reviewArticleByContentRule,
  TYPE_api_completeSection,
  api_completeSection,
  api_editSectionById,
  api_completeChart,
  api_storeFiles
} from "../services/servers";
import { redTitleHtml } from "../configs/red_head_temp";
import { message } from "antd";
import { cloneDeep } from "lodash";
import {
  completionHtml,
  extractRetrieveTagId,
  genInfoInsertTemp,
  getMermaidStr,
  handleMermaidString,
  delThinkTag,
  replaceContentClassTags,
  replaceDivWithP,
  replaceSpanWithP,
  setCurParagraph
} from "./help/utils";
import {
  articleContentSave,
  changeId2Uuid,
  customSerializeHtml,
  customSerializeMd,
  getTitleNode,
  handleOutlines,
  handleReqOrder,
  insertFormDataToTemp,
  renderParagraph
} from "./help";
import { Editor, Node, Path, Text, Transforms, select } from "slate";
import { MARK_SELECTION_UNDERLINE } from "../../components/editor/plugins/customPlugin/selectionUnderLinePlugin";
import { MARK_SELECTION_DELETE } from "../../components/editor/plugins/customPlugin/selectonDeletePligin";
import { MARK_REPLACE_PARAGRAPH } from "../../components/editor/plugins/customPlugin/replaceParagraph";
import dayjs from "dayjs";
import { useRef } from "react";
import mermaid from "mermaid";
import { uniqueId } from "lodash";

export enum LLMStatus {
  Normal = 1,
  Success,
  Error
}

type DataPayload = {
  articleId: string | number;
  sectionId: string | number;
  title: string | number;
};

const redTitleObj = {
  title: "通知标题",
  target: "主送机关",
  publisher: "发文机关",
  publishDate: "发文时间",
  documentNumber: "发文字号"
};

// 记录知识库哪些有溯源，用于删除参考文档
let orderNumList: any = [];

// 全文生成
let totalHtml = "";

const useAiEditorOperators = () => {
  const {
    setProjectData,
    serverInfo,
    projectData,
    modules,
    setModules,
    mainEditor,
    setEditorManager,
    sseController,
    useTemp,
    setReqSchedule,
    setBaseInfo,
    baseInfo
  } = useStateStore();
  const sourceObjRef = useRef<any>({});

  // ==========================工具类====================
  const setProjectStatus = (status: ProjectStatus) => {
    setProjectData((p) => ({
      ...p,
      status: status
    }));
  };

  const setModuleStatus = (status: ModuleStatus, moduleVale: string) => {
    const index = modules.findIndex((i) => i.value === moduleVale);
    const newModule = cloneDeep(modules);
    newModule[index] = { ...newModule[index], status: status };
    setModules(newModule);
  };

  const setCurrentModule = (module: ModueEnum) =>
    setProjectData((pre) => ({ ...pre, currentModule: module }));

  // 获得当前编辑器字数
  const getArticleTotalNum = (editor: any) => {
    if (!editor) return;
    const total = editor.children.reduce((pre: number, cur: any) => {
      return pre + Node.string(cur).length;
    }, 0);
    setProjectData((p) => ({
      ...p,
      total
    }));
  };

  // 清除编辑器
  const clearEditorAllValue = () => {
    const editor = mainEditor.current;
    editor?.select({
      anchor: editor.start([]),
      focus: editor.end([])
    });
    editor?.delete();
  };

  // 用户自己编辑的文章保存前需要先调用保存配置接口
  const saveBeforeReview = async () => {
    try {
      let curId: string;
      if (projectData?.id) {
        await articleContentSave({
          id: projectData.id,
          baseInfo,
          projectData,
          serverInfo,
          mainEditor
        });
        curId = projectData?.id;
      } else {
        const settingRes = await api_saveArticleSetting({
          data: {
            params: {
              title: projectData?.title || "未命名标题",
              articleType: projectData.article_type_mode,
              articleTypeId: projectData.article_type
            }
          },
          config: serverInfo
        });
        curId = settingRes?.id;
        setProjectData((p) => ({
          ...p,
          id: curId
        }));
        await articleContentSave({
          id: curId,
          baseInfo,
          projectData,
          serverInfo,
          mainEditor
        });
      }

      return curId;
    } catch (e) {
      console.log("error------>保存问题", e);
    }
  };

  // 取消生成，取消请求
  const cancelGenerate = () => {
    sseController.current.abort();
    setEditorManager((p) => ({ ...p, status: EditorStatus.Waiting }));
    articleContentSave({
      id: projectData.id,
      baseInfo,
      projectData,
      serverInfo,
      mainEditor
    });
    sseController.current = new AbortController();
  };

  // ==========================工具类end====================

  // ==========================全文生成相关====================
  // 将表单value插入模板中
  const insertDataToTemp = (
    editor: any,
    allValues: any,
    newHtmlString: string,
    titleObj: any
  ) => {
    for (const key in allValues) {
      if (allValues[key]) {
        if (
          titleObj[key]?.indexOf &&
          titleObj[key].indexOf("时间") > -1 &&
          allValues[key].toString()?.indexOf &&
          allValues[key].toString().indexOf("年") == -1
        ) {
          allValues[key] = dayjs(allValues[key]).format("YYYY[年]MM[月]DD[日]");
        }
        newHtmlString = newHtmlString.replace(
          new RegExp(`{${titleObj[key]}}`, "g"),
          allValues[key]
        );
      }
    }
    setEditorManager((p) => ({
      ...p,
      parsed_data: editor.api.html.deserialize({ element: newHtmlString })
    }));
  };

  // 保存文章配置
  const articleSettingSave = async (params: any) => {
    const res = await api_saveArticleSetting({
      data: { params },
      config: serverInfo
    });
    return res;
  };

  // 全文生成的处理，包含html与md的处理，格式模板的处理
  const writing = ({ formData, curMsg, outputFormat }: any) => {
    // 全文生成情况下的html
    totalHtml = totalHtml + curMsg;
    const useHtml = delThinkTag(totalHtml);
    // 部分生成情况下的html,手动补充模板
    let tempHtml = "";
    let articleHtml = "";
    if (projectData.customized_style?.enable) {
      let temp = "";
      let formSchemaMap = {};
      // 最原先前端内置的红头通知，已经没用，只是做历史文档兼容
      if (projectData.article_type_mode?.toString() === "1") {
        temp = redTitleHtml;
        formSchemaMap = redTitleObj;
      }
      if (projectData.customized_style?.enable) {
        temp = projectData.customized_style?.htmlSchema;
        formSchemaMap = projectData.customized_style.formSchemaMap;
      }
      tempHtml = insertFormDataToTemp(formData, temp, formSchemaMap);
      const contentHtml = completionHtml(useHtml);

      // 请示含摘要
      if (projectData.articleTypeKey === "request_with_summary") {
        const parser = new DOMParser();
        const doc = parser.parseFromString(tempHtml, "text/html");
        const allModelgenDom = doc.querySelectorAll(".modelgen");
        for (let i = 0; i < allModelgenDom.length; i++) {
          const element = allModelgenDom[i]; // 获取第一个匹配的元素
          element.parentNode && element.parentNode.removeChild(element); // 删除它
        }
        tempHtml = doc.body.innerHTML;
        articleHtml = tempHtml.replace(`<p></p>`, `<p></p>${contentHtml}`);
      } else {
        if (tempHtml.includes(`<p class="content">[content]</p>`)) {
          articleHtml = tempHtml.replace(
            `<p class="content">[content]</p>`,
            `<div class="content">${contentHtml}</div>`
          );
        } else if (
          tempHtml.includes(`<span class="content">[content]</span>`)
        ) {
          articleHtml = tempHtml.replace(
            `<span class="content">[content]</span>`,
            `<div class="content">${contentHtml}</div>`
          );
        } else if (
          tempHtml.includes(`<span class="content">\n  <p class="custom-span">`)
        ) {
          // 红头会议纪要
          articleHtml = tempHtml.replace(
            `<span class="content">\n  <p class="custom-span"><span>时间：</span></p>\n  <p class="custom-span"><span>地点：</span></p>\n  <p class="custom-span"><span>主持：</span></p>\n  <p class="custom-span"><span>出席：</span></p>\n  <p class="custom-span"><span>列席：</span></p>\n  <p class="custom-span"><span>记录：</span></p>\n  <p class="custom-span"><span>内容：</span></p>\n</span>`,
            `<div class="content">${contentHtml}</div>`
          );
        } else {
          // 会出现多余P标签的情况
          const parser = new DOMParser();
          const doc = parser.parseFromString(tempHtml, "text/html");
          const contentDom: any = doc.querySelector(".content");
          contentDom.innerHTML = contentHtml;
          articleHtml = doc.body.innerHTML;
        }
      }
    } else {
      if (!outputFormat) {
        articleHtml = completionHtml(useHtml);
      } else {
        // articleHtml = customDeserializeMd(mainEditor, totalHtml);
        articleHtml = useHtml;
      }
    }
    setProjectData((p) => ({
      ...p,
      article_content: articleHtml
    }));
  };

  // 全文审核松审片段处理
  const reviewArticle = async (id: string | number) => {
    const contentSpan = replaceContentClassTags(
      projectData.article_content as string
    );
    try {
      const res = await api_reviewArticleByContentRule({
        config: serverInfo,
        data: {
          articleId: id,
          signal: sseController.current.signal,
          content: contentSpan
        }
      });
      const newString = replaceSpanWithP(res.document);
      setEditorManager((p) => ({ ...p, status: EditorStatus.Success }));
      setProjectData((p) => {
        return {
          ...p,
          article_content: replaceDivWithP(
            p.article_content as string,
            newString
          ),
          content_review: {
            document: res.document,
            errors: res.errors
          }
        };
      });
    } catch (e) {
      console.log(e);
      setEditorManager((p) => ({ ...p, status: EditorStatus.Waiting }));
    }
  };

  // 全文生成完成后的后续流程处理，全文审核
  const stopLLMWriting = async (
    id: string | number,
    projectData: any,
    mainEditor: any,
    serverInfo: any
  ) => {
    if (!id) return;
    setModuleStatus(ModuleStatus.Waiting, ModueEnum.Writing);
    setProjectStatus(ProjectStatus.Waiting);
    if (projectData.article_content) {
      await articleContentSave({
        id,
        useProjectData: true,
        projectData,
        mainEditor,
        serverInfo
      });
      setEditorManager((p) => ({ ...p, status: EditorStatus.Waiting }));
    } else {
      return;
    }

    // 非空白文稿开始全文审核
    const { article_type_mode, contentRule } = projectData;
    if (
      article_type_mode === "1" ||
      (article_type_mode === "2" && contentRule)
    ) {
      setEditorManager((p) => ({
        ...p,
        status: EditorStatus.ReviewingFullText
      }));
      try {
        await reviewArticle(id);
        setEditorManager((p) => ({ ...p, status: EditorStatus.Success }));
      } catch (e) {
        setEditorManager((p) => ({ ...p, status: EditorStatus.Waiting }));
      }
    } else {
      setEditorManager((p) => ({ ...p, status: EditorStatus.Success }));
    }
  };

  // 全文生成
  const fullWriting = (outputFormat: any) => {
    // 处理状态
    setModuleStatus(ModuleStatus.Process, ModueEnum.Writing);
    setProjectStatus(ProjectStatus.Process);
    setProjectData((p) => ({
      ...p,
      files: [],
      sourceList: []
    }));
    // 全文写作
    startLLMWriting({
      id: projectData.id,
      useTemp: useTemp,
      formData: projectData.extraParams,
      outputFormat: outputFormat
    });
  };

  // 全文生成的流式请求函数
  const startLLMWriting = ({ id, useTemp, formData, outputFormat }: any) => {
    orderNumList = (projectData.sourceList || []).map((i) => i.order_num);
    totalHtml = "";
    setEditorManager((p) => ({
      ...p,
      status: EditorStatus.GeneratingFullText
    }));
    api_completeArticle({
      config: serverInfo,
      data: {
        signal: sseController.current.signal,
        articleId: id,
        isHtml: useTemp,
        onmessage: async ({ data }) => {
          const curRes = JSON.parse(data);
          if (curRes.status === LLMStatus.Success) {
            // 请示特殊处理，否则会有样式问题，content也不包裹生成的内容，造成审核问题
            if (projectData.articleTypeKey === "request_with_summary") {
              const temp = projectData.customized_style?.htmlSchema;
              const formSchemaMap = projectData.customized_style.formSchemaMap;
              let tempHtml = insertFormDataToTemp(
                formData,
                temp,
                formSchemaMap
              );
              const parser = new DOMParser();
              const doc = parser.parseFromString(tempHtml, "text/html");
              const allModelgenDom = doc.querySelectorAll(".modelgen");
              for (let i = 0; i < allModelgenDom.length; i++) {
                const element = allModelgenDom[i]; // 获取第一个匹配的元素
                element.parentNode && element.parentNode.removeChild(element); // 删除它
              }
              tempHtml = doc.body.innerHTML;
              const finallyHtml = tempHtml.replace(
                `<p></p>`,
                `<p></p>${totalHtml}`
              );
              setProjectData((p) => ({
                ...p,
                article_content: finallyHtml
              }));
            }
            // 处理参考文档
            if (curRes?.matchList || curRes?.docs) {
              let _allFiles: any = [];
              if (curRes?.matchList) {
                _allFiles = curRes.matchList;
              }
              if (curRes?.docs) {
                let _docs: any = curRes?.docs;
                if (typeof _docs === "string") {
                  _docs = JSON.parse(_docs);
                }
                // 对rag溯源过滤,没有用到的不要出现在参考文档
                const _ragFile = _docs.filter((i: any) =>
                  orderNumList.includes(i.order_num)
                );
                _allFiles = [..._allFiles, ..._ragFile];
                // 处理溯源文档
                setProjectData((p) => ({
                  ...p,
                  sourceList: [...(p?.sourceList || []), ..._docs]
                }));
              }
              // 处理参考文档
              setProjectData((p) => ({
                ...p,
                files: [...(p.files || []), ..._allFiles]
              }));
            }
          } else if (curRes.status === LLMStatus.Error) {
            message.error(curRes.reply.content);
            setEditorManager((p) => ({ ...p, status: EditorStatus.Waiting }));
          } else {
            // 对使用到的rag知识库溯源到的文件进行一个记录
            if (curRes.reply.content.includes("source='rag'")) {
              const _id = extractRetrieveTagId(curRes.reply.content);
              orderNumList.push(_id);
            }
            // 处理文章内容
            writing({
              formData,
              curMsg: curRes.reply.content,
              outputFormat
            });
            // 处理溯源文件
            if (curRes?.match) {
              setProjectData((p) => ({
                ...p,
                sourceList: [...(p?.sourceList || []), curRes?.match]
              }));
            }
          }
        },
        onerror: (err) => {
          console.log(err);
          message.error("请求出错，请稍后再试");
          setEditorManager((p) => ({ ...p, status: EditorStatus.Waiting }));
          orderNumList = [];
          throw err;
        },
        onclose: () => {
          totalHtml = "";
          orderNumList = [];
          setProjectData((p) => ({
            ...p,
            saveArticle: Math.random()
          }));
        }
      }
    });
  };

  //==========================全文生成end====================

  // =============================审核相关=======================
  // 带删除的下划线,用于审核标记
  const handleShowDeleteLine = (resultData: any) => {
    const editor: any = mainEditor.current;
    if (!resultData || resultData.length === 0) return;
    for (const [node, path] of Node.descendants(editor)) {
      if (Text.isText(node)) {
        const text = Node.string(node);
        resultData.forEach((item: any) => {
          // 判断是否使用判断信息
          const flagString =
            (item.errorContent || "").length > 12
              ? item.errorContent
              : item?.errorContext?.errorContent;

          const index = text.indexOf(flagString);
          if (index !== -1) {
            const realIndex = text.indexOf(item?.errorContent, index);

            const range = {
              anchor: { path, offset: realIndex },
              focus: { path, offset: realIndex + item?.errorContent.length }
            };
            select(editor as any, range);
            editor.addMark(MARK_SELECTION_DELETE, item.id);
          }
        });
      }
    }
    editor.select(editor.end([]));
  };

  // 标记内容勘误,用于审核标记
  const handleShowUnderLine = (resultData: any) => {
    const editor: any = mainEditor.current;
    if (!resultData || resultData.length === 0) return;
    // 将节点文本拼接成完整字符串
    const fullText = Array.from(Node.texts(editor))
      .map(([node]) => Node.string(node))
      .join("");

    // 使用withoutNormalizing批量操作，避免slate规范带来的path偏移问题
    // editor.withoutNormalizing(() => {
    // 找到位置进行标记
    resultData.forEach((item: any) => {
      const startIndex =
        item?.errorContent.length > 12
          ? fullText.indexOf(item?.errorContent)
          : fullText.indexOf(item.errorContext?.errorContent) +
            item.errorContext?.errorContent.indexOf(item?.errorContent);
      const endIndex = startIndex + item?.errorContent.length;
      if (fullText.indexOf(item.errorContext?.errorContent) !== -1) {
        let curIndex = 0;
        let markedLength = 0; // 跟踪已标记长度
        for (const [node, path] of Node.descendants(editor)) {
          if (Text.isText(node)) {
            const text = Node.string(node);
            const curNodeStartIndex = curIndex;
            const curNodeEndIndex = curIndex + text.length;

            // 确定当前节点内有部分需要标记的内容
            if (startIndex < curNodeEndIndex && endIndex > curNodeStartIndex) {
              // 确定标记的起点和终点在当前节点的相对偏移
              const markStart = Math.max(startIndex - curNodeStartIndex, 0);
              const markEnd = Math.min(
                endIndex - curNodeStartIndex,
                text.length
              );

              const range = {
                anchor: { path, offset: markStart },
                focus: { path, offset: markEnd }
              };

              // 选择范围并添加标记
              Transforms.select(editor, range);
              editor.addMark(MARK_SELECTION_DELETE, item.id);
              // 更新已标记的长度
              markedLength += markEnd - markStart;
              if (markedLength >= item.errorContent.length) break;
            }
            // 更新偏移量
            curIndex += text.length;
            // 检查是否完成标记
            if (curIndex >= endIndex) break;
          }
        }
      } else {
        console.log("在原文中没有找到的", item);
      }
    });
    // });

    editor.select(editor.end([]));
  };

  // 标记敏感词,用于审核标记
  const handleCensor = (resultData: any) => {
    const editor: any = mainEditor.current;
    if (!resultData || resultData.length === 0) return;
    // 1. 收集所有节点的文本及其路径
    const nodes = Array.from(Node.texts(editor));
    const fullText = nodes.map(([node]) => Node.string(node)).join(""); // 将节点文本拼接成完整字符串

    // 找到位置进行标记
    resultData.forEach((item: any) => {
      const startIndex =
        fullText.indexOf(item.context) + item.context.indexOf(item.word);
      const endIndex = startIndex + item.word.length;

      if (fullText.indexOf(item.context) !== -1) {
        let curIndex = 0;
        for (const [node, path] of Node.descendants(editor)) {
          if (Text.isText(node)) {
            const text = Node.string(node);
            const curNodeStartIndex = curIndex;
            const curNodeEndIndex = curIndex + text.length;
            if (startIndex < curNodeEndIndex && endIndex > curNodeStartIndex) {
              // 确定标记的起点和终点在当前节点的相对偏移
              const markStart = Math.max(startIndex - curNodeStartIndex, 0);
              const markEnd = Math.min(
                endIndex - curNodeStartIndex,
                text.length
              );

              const range = {
                anchor: { path, offset: markStart },
                focus: { path, offset: markEnd }
              };

              // 选择范围并添加标记
              Transforms.select(editor, range);
              editor.addMark(MARK_SELECTION_UNDERLINE, item.id);
            }
            // 更新偏移量
            curIndex += text.length;
            // 检查是否完成标记
            if (curIndex >= endIndex) break;
          }
        }
      }
    });
    editor.select(editor.end([]));
  };

  // 清除所有mark,用于审核
  const clearAllMark = (editor: any) => {
    select(editor as any, {
      anchor: Editor.start(editor as any, []),
      focus: Editor.end(editor as any, [])
    });
    editor.removeMark(MARK_SELECTION_UNDERLINE);
    editor.removeMark(MARK_SELECTION_DELETE);
    editor.removeMark(MARK_REPLACE_PARAGRAPH);
    editor.select(editor.end([]));
  };
  // =================================审核相关end=======================

  // ============================模板变量修改相关==========================
  // 根据变量修改模板内的内容，表单与编辑器联动需求
  const modifyTextNode = (editor: any, path: Path, newText: string) => {
    // 先获取要修改的节点
    const node: any = Node.get(editor, path);

    if (node && Editor.isBlock(editor, node)) {
      // 获取节点的文本长度
      const textLength = Node.string(node).length;

      // 删除原有文本内容
      if (textLength) {
        Transforms.delete(editor, {
          at: {
            anchor: { path, offset: 0 },
            focus: { path, offset: textLength }
          }
        });
      }
      // 插入新文本内容
      Transforms.insertText(editor, newText, { at: path });
    }
  };

  // 编辑器内容修改，涉及到变量，需要保存配置，用于格式模板
  const addFormData = (editor: any) => {
    const parentPath = editor.selection.anchor?.path;
    if (!parentPath || projectData.article_type_mode === "0") return;
    const curChangeNode = editor.parent(parentPath)[0];

    let formKeys: any[] = [];
    if (projectData.article_type_mode === "1") {
      formKeys = Object.keys(redTitleObj);
    } else {
      formKeys = Object.keys(projectData.customized_style.formSchemaMap);
    }
    if (!curChangeNode.class) return;
    // 获取当前change的节点
    const needChangeNodeClass = curChangeNode.class
      .split(" ")
      .find((i: string) => formKeys.includes(i));
    // 对于格式模板,判断是不是变量,对于普通的分段,有手动添加的标题
    if (
      !curChangeNode ||
      (!needChangeNodeClass && !curChangeNode.class.includes("title"))
    )
      return;
    if (curChangeNode.children && curChangeNode.children[0]) {
      const curText = curChangeNode.children[0].text;
      const _baseInfo: any = {
        ...baseInfo,
        [needChangeNodeClass || "title"]: curText
      };

      for (const [node, path] of Node.descendants(editor)) {
        if (
          Text.isText(node) &&
          editor.parent(path) &&
          editor.parent(path)[0] &&
          editor.parent(path)[0].class &&
          editor.parent(path)[0].class.includes(needChangeNodeClass)
        ) {
          const itemText = Node.string(node);
          // 避免无限递归
          if (itemText !== curText) {
            modifyTextNode(editor, path, curText);
          }
        }
      }
      return _baseInfo;
    }
  };
  // ============================模板变量修改相关end==========================

  // ============================分段写作相关==========================

  const globelPlateData = useRef("");
  const currentIndex = useRef(0);
  // 缓冲数据，流式数据的节流处理，保证渲染性能
  const allParagraphBuffer = useRef<{ [key: string]: any }>({});
  // 定时器引用，用于同步缓冲区的数据
  const syncIntervalRef = useRef<number | null>(null);
  // 启动定时器，每 300 毫秒同步一次缓冲数据
  const startSyncBuffer = (cover: any) => {
    syncIntervalRef.current = setInterval(() => {
      // 定时渲染章节
      if (String(allParagraphBuffer.current) !== "{}") {
        renderParagraph({
          allParagraph: allParagraphBuffer.current,
          setEditorManager,
          globelPlateData: globelPlateData.current,
          mainEditor,
          cover
        });
      }
    }, 300);
  };

  // 清除定时器并同步剩余数据
  const stopSyncBuffer = (cover: any) => {
    if (syncIntervalRef.current) {
      clearInterval(syncIntervalRef.current);
      syncIntervalRef.current = null;
    }
    // 最后渲染一次
    if (String(allParagraphBuffer.current) !== "{}") {
      // 定时渲染章节
      renderParagraph({
        allParagraph: allParagraphBuffer.current,
        setEditorManager,
        globelPlateData: globelPlateData.current,
        mainEditor,
        cover
      });
    }
  };
  // 单独保存某个段落的请求
  const saveSectionContent = async ({ sectionId, articleId, params }: any) => {
    const data = await api_editSectionById({
      config: serverInfo,
      data: {
        params,
        id: sectionId,
        articleId,
        updateContent: true
      }
    });
  };
  // 分段写作每次拿到切片的详细处理
  const write = ({ curRes, sectionId, cover }: any) => {
    // 将当前切片插入到对应的段落中
    if (allParagraphBuffer.current[sectionId]) {
      allParagraphBuffer.current = {
        ...allParagraphBuffer.current,
        [sectionId]:
          allParagraphBuffer.current[sectionId] + curRes.reply.content
      };
    } else {
      allParagraphBuffer.current = {
        ...allParagraphBuffer.current,
        [sectionId]: curRes.reply.content
      };
    }
  };

  // 将 SVG 转换为 PNG 图片
  const convertSvgToPng = async (svg: string) => {
    // const canvas = document.createElement("canvas");
    // canvas.width = width;
    // canvas.height = height;

    // const ctx = canvas.getContext("2d");
    // canvas.width = 500;
    // canvas.height = 500;
    // const v = await Canvg.from(ctx, svg, {
    //   ignoreDimensions: true,
    //   enableRedraw: true, // 允许动态重绘
    //   ignoreAnimation: true, // 忽略动画
    // });

    // // 渲染 SVG 到 Canvas
    // await v.render();
    // return new Promise((resolve) => {
    //   canvas.toBlob((blob) => {
    //     resolve(blob); // 返回 PNG Blob
    //   }, "image/png");
    // });

    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;

        const ctx = canvas.getContext("2d");
        ctx && ctx.drawImage(img, 0, 0);

        canvas.toBlob(
          (blob) => {
            resolve(blob);
          },
          "image/png",
          1
        );
      };
      const parser = new DOMParser();
      const svgDoc = parser.parseFromString(svg, "image/svg+xml");
      const svgElement = svgDoc.documentElement;

      svgElement.setAttribute("width", "1000"); // 设置宽度
      // svgElement.setAttribute("height", "2500"); // 设置高度

      const updatedSvg = new XMLSerializer().serializeToString(svgElement);
      img.src =
        "data:image/svg+xml;charset=utf-8," + encodeURIComponent(updatedSvg);
    });
  };

  // 将流程图转化为img,并且将图片上传至服务器
  const mermaidStrToImg = async (mermaidStr: string, name?: string) => {
    // return new Promise((resolve, reject) => {
    //   // 渲染 Mermaid 图表为 SVG
    //   const svg = await mermaid.render("graphDiv", mermaidCode);
    //   return svg;
    // });
    // 渲染 Mermaid 图表为 SVG
    mermaid.initialize({
      startOnLoad: true,
      securityLevel: "loose"
    });
    const { svg } = await mermaid.render("graphDiv", mermaidStr);
    const blob = await convertSvgToPng(svg);
    // const blob = new Blob([svg], { type: "image/svg+xml" });
    const file = new File(
      [blob as BlobPart],
      name || `${projectData.id}-股权结构图.png`,
      {
        type: "image/png"
      }
    );
    const formData: any = new FormData();
    formData.append("file", file);
    const url = await api_storeFiles({
      config: serverInfo,
      data: {
        file: formData
      }
    });
    return url;
  };

  // 处理含有图表的段落
  const handleMermaidParagraph = async ({
    sectionId,
    content,
    articleId
  }: any) => {
    const mermaidStrArr = getMermaidStr(content);
    const len = mermaidStrArr.length;
    for (let i = 0; i < len; i++) {
      const curChartString: string = mermaidStrArr[i].middlePart;
      if (!curChartString) continue;
      // curChartString = handleMermaidString(curChartString);
      const imgName = `${articleId}-${sectionId}-${uniqueId()}.png`;
      const imgUrl = await mermaidStrToImg(curChartString, imgName);
      mermaidStrArr[i].middlePart = `\n\n![${imgName}](${imgUrl})\n\n`;
    }
    const newContent = mermaidStrArr.reduce((pre, cur) => {
      pre = pre + cur.beforePart + cur.middlePart + cur.afterPart;
      return pre;
    }, "");
    allParagraphBuffer.current[sectionId] = newContent;
    // 保存段落
    await saveSectionContent({
      sectionId,
      articleId,
      params: {
        content: newContent
      }
    });
  };

  // 保存段落
  const handleParagraph = async ({ sectionId, articleId, params }: any) => {
    if ((allParagraphBuffer.current[sectionId] || "").includes("%%%mermaid=")) {
      // 对于有图表的段落，先转化为图片再上传图片再保存段落
      await handleMermaidParagraph({
        sectionId,
        content: allParagraphBuffer.current[sectionId] || "",
        articleId
      });
    } else {
      // 对于没有图表的段落直接保存
      await saveSectionContent({
        sectionId,
        articleId,
        params
      });
    }
  };

  // 将mermaidArr转成图片并上传
  const handleChartObj = async (mermaidArr: any[], chartReqArr: any[]) => {
    if (!mermaidArr.length) return {};
    const resObj: any = {};
    for (let i = 0; i < chartReqArr.length; i++) {
      const mermaidStr = handleMermaidString(mermaidArr[i]?.chart || "");
      const imgUrl = await mermaidStrToImg(mermaidStr);
      resObj[chartReqArr[i].sectionId] = `\n\n![股权结构图](${imgUrl})`;
    }
    return resObj;
  };

  // 分段写作完成，处理特殊的图表请求
  const stopSegmentedWriting = async ({
    chartReqLen,
    chartReqArr,
    cover,
    dataPayloads
  }: any) => {
    if (chartReqLen) {
      const arr = chartReqArr.map((item: any) => {
        return api_completeChart({
          config: serverInfo,
          data: {
            articleId: projectData.id,
            sectionId: item.sectionId
          }
        });
      });
      try {
        const chatRes = await Promise.all(arr);
        if (chatRes && chatRes.length) {
          const chartObj = await handleChartObj(chatRes, chartReqArr);
          allParagraphBuffer.current = {
            ...allParagraphBuffer.current,
            ...chartObj
          };
          // 处理图表数据，并渲染文章
          renderParagraph({
            allParagraph: allParagraphBuffer.current,
            setEditorManager,
            globelPlateData: globelPlateData.current,
            mainEditor,
            cover
          });
          setReqSchedule({
            total: dataPayloads.length + chartReqArr.length,
            cur: dataPayloads.length + chartReqArr.length
          });
          // 分段保存图表
          await Promise.all(
            chartReqArr.map((item: any) => {
              return api_editSectionById({
                config: serverInfo,
                data: {
                  params: {
                    sectionTitle: item.title,
                    content: allParagraphBuffer.current[item.sectionId]
                  },
                  id: item.sectionId,
                  articleId: projectData.id
                }
              });
            })
          );
        }
      } catch (e) {
        console.log(e);
      }
    }
  };

  // 分段写作状态重置，包括初始化变量，清除状态，请求偏移量设置等
  const resetSegmentedStatus = ({
    setReqSchedule,
    setEditorManager,
    state
  }: any) => {
    // 分段请求队列完成，初始化变量，改变当前状态
    setReqSchedule({
      total: 0,
      cur: 0
    });

    allParagraphBuffer.current = {};
    globelPlateData.current = "";
    currentIndex.current = 0;
    orderNumList = [];
    setEditorManager((p: any) => ({
      ...p,
      status: state || EditorStatus.Success
    }));
  };

  // 分段写作出错的处理
  const handleSegmentedError = (curRes: any) => {
    message.error(curRes.reply.content);
    resetSegmentedStatus({
      setReqSchedule,
      setEditorManager,
      state: EditorStatus.Waiting
    });
    setReqSchedule({
      total: 0,
      cur: 0
    });
    throw curRes.reply.content;
  };

  // 处理当前段落请求成功后的操作
  const handleCurParagraphSuccess = async ({
    curRes,
    dataPayload,
    dataPayloads,
    chartReqLen,
    chartReqArr,
    cover
  }: any) => {
    // 用于获取需要保存的数据，避免setState异步造成的数据获取不到的问题
    // 溯源
    let saveSourceList: any[] = [];
    // 参考文档
    let saveFiles: any[] = [];

    // 处理内容来源跟参考文档
    if (curRes?.matchList || curRes?.docs) {
      let _allFiles: any = [];
      if (curRes?.matchList) {
        _allFiles = curRes.matchList;
      }
      if (curRes?.docs) {
        let _docs: any = curRes?.docs;
        if (typeof _docs === "string") {
          _docs = JSON.parse(_docs);
        }
        // 对rag溯源过滤,没有用到的不要出现在参考文档
        const _ragFile = _docs.filter((i: any) =>
          orderNumList.includes(i.order_num)
        );
        _allFiles = [..._allFiles, ..._ragFile];
        // 处理溯源文档
        setProjectData((p) => {
          saveSourceList = [...(p?.sourceList || []), ..._docs];
          return {
            ...p,
            sourceList: saveSourceList
          };
        });
      }
      // 处理参考文档
      setProjectData((p) => {
        saveFiles = [...(p.files || []), ..._allFiles];
        return { ...p, files: saveFiles };
      });
    }

    // 每次写作完成，单独保存当前段落
    await handleParagraph({
      sectionId: dataPayload.sectionId,
      articleId: dataPayload.articleId,
      params: {
        sectionTitle: dataPayload.title,
        content: delThinkTag(allParagraphBuffer.current[dataPayload.sectionId])
      }
    });
    // 整体保存文章内容
    const data = genInfoInsertTemp(
      globelPlateData.current,
      allParagraphBuffer.current,
      mainEditor.current
    );
    await articleContentSave({
      id: projectData.id,
      useProjectData: false,
      section: customSerializeMd(mainEditor.current as any, data),
      baseInfo,
      projectData,
      serverInfo,
      mainEditor,
      files: saveFiles,
      sourceList: saveSourceList
    });

    currentIndex.current += 1;

    // 分段请求进度条
    setReqSchedule((p: any) => ({
      ...p,
      cur: currentIndex.current
    }));
    startRequests(
      dataPayloads,
      curRes.matchList,
      chartReqLen,
      chartReqArr,
      cover
    );
  };

  // 分段写作，获取到当前切片的操作
  const handleCurParagraphChunk = ({
    curRes,
    matchList,
    dataPayload,
    cover
  }: any) => {
    // 替换uuid
    if (curRes.match) {
      changeId2Uuid(curRes, matchList.length);
      setProjectData((p) => ({
        ...p,
        sourceList: [...(p?.sourceList || []), curRes.match]
      }));
    }
    // 对使用到的rag知识库溯源到的文件进行一个记录
    if (curRes.reply.content.includes("source='rag'")) {
      const _id = extractRetrieveTagId(curRes.reply.content);
      orderNumList.push(_id);
    }
    // 将段落数据加入到缓存中
    write({
      curRes,
      sectionId: dataPayload.sectionId,
      cover
    });
  };

  // 分段写作请求
  const startRequests = async (
    dataPayloads: DataPayload[],
    matchList: any,
    chartReqLen: number,
    chartReqArr: any[],
    cover: any
  ) => {
    // 分段流式数据请求完成
    if (currentIndex.current >= dataPayloads.length) {
      // 请求完成后的处理
      await stopSegmentedWriting({
        chartReqLen,
        chartReqArr,
        cover,
        dataPayloads
      });
      // 重置状态
      resetSegmentedStatus({ setReqSchedule, setEditorManager });
      return;
    }

    const dataPayload = dataPayloads[currentIndex.current];
    // 开始请求,开始定时渲染文章
    startSyncBuffer(cover);
    const completeSectionPayload: TYPE_api_completeSection = {
      config: serverInfo,
      data: {
        ...dataPayload,
        params: {
          historyMatches: matchList
        },
        signal: sseController.current.signal,

        onmessage: async (ev: any) => {
          const curRes = JSON.parse(ev.data);
          switch (curRes.status) {
            case LLMStatus.Error:
              stopSyncBuffer(cover);
              handleSegmentedError(curRes);
              break;
            case LLMStatus.Normal:
              handleCurParagraphChunk({
                curRes,
                matchList,
                dataPayload,
                cover
              });
              break;
            case LLMStatus.Success:
              stopSyncBuffer(cover);
              // 处理当前段落请求成功后的操作
              handleCurParagraphSuccess({
                curRes,
                dataPayload,
                dataPayloads,
                chartReqLen,
                chartReqArr,
                cover
              });
              break;
            default:
              break;
          }
        },

        onerror: (err: any) => {
          stopSyncBuffer(cover);
          resetSegmentedStatus({
            setReqSchedule,
            setEditorManager,
            state: EditorStatus.Waiting
          });
          getArticleTotalNum(mainEditor.current);
          setReqSchedule({
            total: 0,
            cur: 0
          });
          throw err;
        },
        onclose: async () => {
          // stopSyncBuffer(cover);
        }
      }
    };
    api_completeSection(completeSectionPayload);
  };

  // 分段写作处理封面
  const handleCover = async ({ extraParams, coverPage }: any) => {
    if (
      projectData.customized_style &&
      projectData.customized_style.htmlSchema &&
      projectData.customized_style.formSchemaMap
    ) {
      const coverHtml = insertFormDataToTemp(
        extraParams,
        projectData.customized_style.htmlSchema,
        projectData.customized_style.formSchemaMap
      );

      const nodes = deserializeHtml(mainEditor.current as any, {
        element: coverHtml
      });

      if (coverPage) {
        await saveSectionContent({
          sectionId: coverPage.sectionId,
          articleId: projectData.id,
          params: {
            content: customSerializeHtml(mainEditor.current, nodes as any)
          }
        });
      }
      return nodes;
    } else {
      const nodes = getTitleNode(extraParams.title);
      // await saveSectionContent({
      //   sectionId: coverPage.sectionId,
      //   articleId: projectData.id,
      //   params: {
      //     content: serializeHtml(mainEditor.current, nodes as any)
      //   }
      // });
      return nodes;
    }
  };

  // 分段写作流程
  const segmentedWriting = async ({
    outlines,
    extraParams,
    coverPage
  }: any) => {
    // 加载动画
    setEditorManager((p) => ({
      ...p,
      status: EditorStatus.GeneratingPartialText
    }));
    // 有封面的情况下先保存封面
    const cover: any = await handleCover({ extraParams, coverPage });
    // 处理状态
    setModuleStatus(ModuleStatus.Process, ModueEnum.Writing);
    setProjectStatus(ProjectStatus.Process);

    // 初始化全局数据
    currentIndex.current = 0;
    globelPlateData.current = "";
    sourceObjRef.current = {};
    orderNumList = (projectData.sourceList || []).map((i) => i.order_num);

    // 获取需要请求的大纲数据，以及文章框架，为后续请求与插入做准备
    const { plateData, reqArr, chartReqArr, hasDependency } =
      handleOutlines(outlines);
    // 根据依赖项处理请求顺序
    const newReqArr = handleReqOrder(reqArr, hasDependency);
    globelPlateData.current = plateData;
    // 先将现有的所有内容插入，再将需要生成的内容清空
    allParagraphBuffer.current = setCurParagraph(
      outlines,
      newReqArr.map((i: any) => Number(i.sectionId))
    );
    // 请求进度条
    setReqSchedule({
      total: newReqArr.length + chartReqArr.length,
      cur: 0
    });

    // 开始请求
    startRequests(
      newReqArr.map((item: any) => ({
        sectionId: item.sectionId,
        articleId: projectData.id,
        title: item.title
      })),
      [],
      chartReqArr.length,
      chartReqArr,
      cover
    );

    // 如果没有请求列表,直接修改状态
    if (!chartReqArr.length && !newReqArr.length) {
      setEditorManager((p) => ({
        ...p,
        parsed_data: cover,
        status: EditorStatus.Waiting
      }));
    }
  };
  // ============================分段写作相关end==========================

  return {
    handleShowDeleteLine,
    articleSettingSave,
    setCurrentModule,
    insertDataToTemp,
    startLLMWriting,
    saveBeforeReview,
    cancelGenerate,
    handleShowUnderLine,
    handleCensor,
    clearEditorAllValue,
    stopLLMWriting,
    clearAllMark,
    fullWriting,
    segmentedWriting,
    addFormData
  };
};
export default useAiEditorOperators;
