import { createPlateEditor, Plate } from "@udecode/plate-common/react";

import { TooltipProvider } from "../editor/ui/tooltip";
import { Editor } from "./Editor";
import { Toolbar } from "../Toolbar";
import {
  mainEditorDefaultComponents,
  mainEditorDefaultPlugins
} from "../editor/plugins/mainEditorSet";
import { useEffect, useMemo, useRef, useState } from "react";
import { useStateStore } from "../../core/states/useStateStore";
import {
  SelectionMenu,
  SelectionMenuPlugin
} from "../editor/plugins/customPlugin/SelectionMenu";
import { Transforms, BaseEditor, Node, Range } from "slate";
import { MentionPlugin } from "@udecode/plate";
import Catalogue from "../Catalogue";
import { EditorType, ModueEnum } from "../../@types/sys";
import {
  articleContentSave,
  customDeserializeMd,
  customSerializeMd,
  getTitleNode,
  handleOutlines,
  insertFormDataToTemp
} from "../../core/operators/help";
import { useGlobalOperators } from "../../core/operators/useGlobalOperators";
import useAiEditorOperators from "../../core/operators/useAiEditorOperators";
import { redTitleStyle } from "./default_style";
import { replaceBaseInfo } from "./util";
import { cloneDeep, debounce, throttle } from "lodash";
import { deserializeHtml, isElement } from "@udecode/plate-common";
import { api_editSectionById } from "../../core/services/servers";
import { coverTemp } from "./play";

const headingArr = ["h1", "h2", "h3", "h4", "h5"];

let allowChange = true;

// 如果修改的内容涉及到溯源, 则删除溯源角标;
const delRetrieveTag = (editor: any) => {
  try {
    const endStr = ["。", "！", "!", "?", "？"];
    if (!editor) return;
    const { selection } = editor;
    // 确保光标存在
    if (!selection) return;

    // 获取当前选区最后一个文本节点
    const [lastNode, lastNodePath] = editor.last(selection);

    if (lastNode && lastNode.text) {
      // 当前的offset到结尾有两个以句号，感叹号，问号则认为是上一句话合并的，不在此次溯源内容中
      if (Range.isCollapsed(editor.selection)) {
        const offset = selection.anchor.offset;
        if (!offset) return;
        const verifyStr = lastNode.text.slice(offset);
        let count = 0;
        for (let i = 0; i < verifyStr.length; i++) {
          if (endStr.includes(verifyStr[i])) {
            count++;
          }
        }
        if (count > 1) return;
      }

      // 当前改变的内容是以句号，感叹号，问号结尾并且下一个节点为retrieve-tag则删除
      const isEnd = endStr.some((i) => lastNode.text.endsWith(i));
      if (!isEnd) return;

      // 假设他的后面一个node是溯源标签
      const retrievePath = cloneDeep(lastNodePath);
      if (retrievePath.length === 0) return;
      retrievePath[retrievePath.length - 1] += 1;

      // 查看下一个节点是否存在，以及是否是溯源节点
      const nextNode: any = Node.get(editor, retrievePath);
      if (nextNode && nextNode["type"] === "retrieve-tag") {
        editor.removeNodes({
          at: retrievePath
        });
        // 避免removeNodes方法造成valueChange无限递归
        allowChange = false;
        setTimeout(() => {
          allowChange = true;
        }, 1500);
      }
    }
  } catch (e) {
    console.log(e);
  }
};

// 自动保存分段生成修改的内容
const autoSaveSection = ({ id, generateType, editor, serverInfo }: any) => {
  if (generateType !== 1) return;
  const { selection } = editor;
  if (!selection) return; // 确保光标存在

  try {
    // 获取当前光标所在的父级节点
    const parentEntry = editor.above({
      match: (n) =>
        isElement(n) &&
        typeof n.class === "string" &&
        n.class.includes("sectionId-")
    });
    if (!parentEntry) return;
    const [parentNode, path] = parentEntry;
    const sectionId = parentNode.id;
    let mdStr = "";
    const params: any = {};
    if (
      parentNode.children[0] &&
      headingArr.includes(parentNode.children[0].type)
    ) {
      mdStr = customSerializeMd(editor, parentNode.children.slice(1));
      // title暂不支持保存
      // params["sectionTitle"] = customSerializeMd(
      //   editor,
      //   parentNode.children[0].children
      // );
    } else {
      mdStr = customSerializeMd(editor, parentNode.children);
    }
    params["content"] = mdStr;

    api_editSectionById({
      config: serverInfo,
      data: {
        params,
        id: sectionId,
        articleId: id,
        updateContent: true
      }
    }).then((res) => {});
  } catch (e) {
    console.log(e, "分段保存失败");
  }
};

// 自动保存全文
const autoSaveContent = ({
  // 文章id,必传
  id,
  // 是否使用ProjectData中的数据作为文章数据保存
  useProjectData = false,
  // 部分内容,用于不保存全文的情况,例如分段生成不保存封面内容
  section = "",
  // 文章表单配置是否被更改，用于编辑器与表单数据同步，拥有格式模板时使用
  baseInfo = {},
  // 必传
  projectData,
  // 请求配置信息，token,是否使用mock等,必传
  serverInfo,
  // 编辑器Ref,必传
  mainEditor,
  editor
}: any) => {
  articleContentSave({
    id,
    useProjectData,
    section,
    baseInfo,
    projectData,
    serverInfo,
    mainEditor
  });
};

// 编辑器内容改变时
const valueChange = ({
  // 生成方式
  generateType,
  // 文章id,必传
  id,
  // 是否使用ProjectData中的数据作为文章数据保存
  useProjectData = false,
  // 部分内容,用于不保存全文的情况,例如分段生成不保存封面内容
  section = "",
  // 参考文档,必传
  matchList = "",
  // 文章表单配置是否被更改，用于编辑器与表单数据同步，拥有格式模板时使用
  baseInfo = {},
  // 必传
  projectData,
  // 请求配置信息，token,是否使用mock等,必传
  serverInfo,
  // 编辑器Ref,必传
  mainEditor,
  editor
}: any) => {
  if (!allowChange) return;
  delRetrieveTag(editor);
  autoSaveSection({ id, generateType, editor, serverInfo });
  autoSaveContent({
    id,
    useProjectData,
    section,
    matchList,
    baseInfo,
    projectData,
    serverInfo,
    mainEditor,
    editor
  });
};

const debounceChange = debounce(valueChange, 1000);

const render = (
  editorManager: any,
  mainEditor: any,
  getArticleTotalNum: any
) => {
  if (mainEditor.current) {
    const timer = setTimeout(() => {
      getArticleTotalNum(mainEditor.current);
      clearTimeout(timer);
    }, 300);
  }
  const adjustedPlugins = mainEditorDefaultPlugins.map((plugin) => {
    return injectStyle(plugin, editorManager.styles);
  });
  const editor: any = mainEditor.current;
  if (!editor || !editorManager.parsed_data)
    return createPlateEditor({
      value: [{ type: "p", children: [{ text: "" }] }]
    });
  return createPlateEditor({
    plugins: [...adjustedPlugins, SelectionMenuPlugin],
    override: {
      components: { ...mainEditorDefaultComponents }
    },
    id: editorManager.id,
    value: editorManager.parsed_data
  });
};
const throttleRender = throttle(render, 300, { leading: true, trailing: true });

export const injectStyle = (plugin: any, styles: any) => {
  if (plugin.key === MentionPlugin.key) {
    return {
      ...plugin,
      // 这里存的样式分2个部分，标签的样式，自定义的class的样式
      inject: {
        ...styles
      }
    };
  } else {
    return plugin;
  }
};

const genInfoInsertTemp = (plate: any, allData: any, editor: any) => {
  return plate.map((node: any) => {
    if (node?.id && allData[node.id]) {
      // 在当前节点的 children 中插入新的节点
      node.children = [
        node.children[0],
        ...customDeserializeMd(editor, allData[node.id])
      ];
    }

    // 如果当前节点有 children，则递归处理
    if (node?.children) {
      node.children = genInfoInsertTemp(node.children, allData, editor);
    }

    return node;
  });
};

const allParagraph = (outlines: any) => {
  const paragraphData: any = {};
  const handleOutlinesParagraph = (outlines: any) => {
    outlines.forEach((item: any) => {
      if (item.section && item.section.content && item.section.id) {
        paragraphData[item.section.id] = item.section.content;
      }
      if (item.subParagraphs) {
        handleOutlinesParagraph(item.subParagraphs);
      }
    });
  };
  handleOutlinesParagraph(outlines);
  return paragraphData;
};

const MainEditor = () => {
  const [open, setOpen] = useState(false);
  const {
    projectData,
    mainEditor,
    editorManager,
    setEditorManager,
    setExportHover,
    serverInfo,
    baseInfo,
    editorType
  } = useStateStore();
  const { getArticleTotalNum } = useGlobalOperators();
  const { addFormData } = useAiEditorOperators();

  // 有内容的情况下展示内容
  const showContent = (editor: any) => {
    // 分段生成
    if (projectData.generateType) {
      // 封面
      let coverPageArr: any = [];
      // 有封面展示封面
      if (
        projectData.customized_style &&
        projectData.customized_style.htmlSchema &&
        projectData.customized_style.formSchemaMap
      ) {
        const coverHtml = insertFormDataToTemp(
          projectData.extraParams,
          projectData.customized_style.htmlSchema,
          projectData.customized_style.formSchemaMap
        );
        coverPageArr = deserializeHtml(editor as any, { element: coverHtml });
      } else {
        // 没封面展示标题
        coverPageArr = getTitleNode(projectData.extraParams?.title || "");
      }
      // 大纲
      let outlinesArr = [];
      if (!projectData.outlines || !projectData.outlines.length) {
        // 不存在大纲
        outlinesArr = [
          {
            id: "1",
            type: "p",
            children: [{ text: "" }]
          }
        ];
      } else {
        // 存在大纲
        const { plateData } = handleOutlines(projectData.outlines);
        const paragraphData = allParagraph(projectData.outlines);
        outlinesArr = genInfoInsertTemp(plateData, paragraphData, editor);
      }
      return [...coverPageArr, ...outlinesArr];
    } else {
      // 全文生成
      if (projectData.outputFormat) {
        // md
        const data = customDeserializeMd(
          editor,
          projectData.article_content || ""
        );
        return data;
      }

      // html,因为存在表单数据被需修改的情况(格式模板的情况)，所以需要进行一次数据同步
      if (
        projectData.customized_style.formSchemaMap &&
        projectData.extraParams
      ) {
        const allNode = editor.api.html.deserialize({
          element: projectData.article_content
        });
        return replaceBaseInfo(allNode, projectData.extraParams);
      }
      return projectData.article_content;
    }
  };

  // 没有内容的情况下，展示模板
  const showTemp = (editor: any) => {
    // 分段生成但是没内容的情况下，展示大纲
    if (projectData.generateType && projectData.outlines) {
      const { plateData } = handleOutlines(projectData.outlines);
      const paragraphData = allParagraph(projectData.outlines);
      return genInfoInsertTemp(plateData, paragraphData, editor);
    }
    // 全文生成的情况下没内容，展示模板
    if (projectData.customized_style && projectData.customized_style.enable) {
      return insertFormDataToTemp(
        {
          ...projectData.extraParams,
          title: projectData.title
        },
        projectData.customized_style?.htmlSchema,
        projectData.customized_style.formSchemaMap
      );
    }

    return [
      {
        id: "1",
        type: "p",
        children: [{ text: "" }]
      }
    ];
  };

  const initData: any = useMemo(() => {
    const editor = mainEditor.current;
    if (editor && projectData.article_content) {
      return showContent(editor);
    } else {
      return showTemp(editor);
    }
  }, [
    projectData.article_content,
    projectData.outputFormat,
    mainEditor,
    projectData.generateType,
    projectData.outlines,
    projectData.customized_style,
    projectData.extraParams,
    projectData.customized_style?.enable,
    projectData.title,
    projectData.coverPage
  ]);

  // 有自定义样式的情况下，使用自定义样式
  useEffect(() => {
    if (projectData.customized_style && projectData.customized_style.enable) {
      setEditorManager((p) => ({
        ...p,
        styles: projectData?.customized_style.styles
      }));
    } else if (projectData.article_type_mode == "1") {
      setEditorManager((p) => ({ ...p, styles: redTitleStyle }));
    }
  }, [projectData.customized_style?.enable]);

  // 监听 delete 按钮事件
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Delete" || event.key === "Backspace") {
        if (open) {
          // 如果菜单打开，关闭菜单
          setOpen(false);
          // 允许 Editor 处理删除事件
          if (mainEditor && mainEditor.current) {
            const editor = mainEditor.current as BaseEditor;
            const location = mainEditor.current.selection;
            if (location != null) {
              Transforms.delete(editor, { at: location });
            }
          }
          console.log(
            "Delete or Backspace pressed, closing menu and allowing editor to delete"
          );
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, setOpen]);

  useEffect(() => {
    setEditorManager((prev) => ({
      ...prev,
      parsed_data: initData
    }));
    // setTimeout(() => {
    //   const editor: any = mainEditor.current;
    //   editor && getArticleTotalNum(editor);
    // }, 300);
  }, [initData]);

  const mainWritingSet = useMemo(() => {
    return render(editorManager, mainEditor, getArticleTotalNum);
    // return throttleRender(editorManager, mainEditor, getArticleTotalNum);
  }, [editorManager.parsed_data, editorManager.id, editorManager.styles]);

  const editorRef = useRef(null);
  return (
    <div className="h-full overflow-y-auto " ref={editorRef}>
      <Plate
        editor={mainWritingSet}
        readOnly={editorType === EditorType.Preview}
        onValueChange={({ editor, value }) => {
          getArticleTotalNum(editor);
          setExportHover(true);
          const _baseInfo: any = addFormData(editor);
          debounceChange({
            id: projectData.id,
            matchList: projectData.files,
            baseInfo: _baseInfo || {},
            projectData,
            serverInfo,
            mainEditor,
            editor,
            generateType: projectData.generateType
          });
        }}
      >
        <TooltipProvider>
          <Toolbar />
          {projectData.currentModule == ModueEnum.Writing && <Catalogue />}
          <div className="relative">
            {editorType !== EditorType.Preview && (
              <SelectionMenu
                editorRef={editorRef}
                open={open}
                setOpen={setOpen}
              />
            )}
            <div className="h-[calc(100vh-150px)] pt-[25px] relative mt-10">
              <Editor
                readOnly={editorType === EditorType.Preview}
                className=" bg-white box-border h-fit min-h-[1169px] pb-[100px] cec-editor"
              />
            </div>
          </div>
        </TooltipProvider>
      </Plate>
    </div>
  );
};

export default MainEditor;
