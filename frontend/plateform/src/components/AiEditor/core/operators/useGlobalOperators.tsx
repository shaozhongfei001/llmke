import { useStateStore } from "../states/useStateStore";
import { cloneDeep } from "lodash";
import { ModueEnum, ModuleStatus, ProjectStatus } from "../../@types/sys";
import { message } from "antd";
import {
  api_editSectionById,
  api_exportArticleById,
  api_getArticleById,
  api_getArticleTypeDetails
} from "../services/servers";
import { useDataTransformer } from "../useDataTransformer";
import { Node } from "slate";
import {
  articleContentSave,
  customSerializeHtml,
  insertFormDataToTemp
} from "./help";
import { deserializeHtml } from "@udecode/plate-common";

const useGlobalOperators = () => {
  const {
    modules,
    setModules,
    setProjectData,
    sseController,
    projectData,
    serverInfo,
    baseInfo,
    mainEditor
  } = useStateStore();
  const { toProjectData, articleTypeDataToProject } = useDataTransformer();

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

  const setProjectStatus = (status: ProjectStatus) => {
    setProjectData((p) => ({
      ...p,
      status: status
    }));
  };

  const setModuleStatus = (status: ModuleStatus, moduleVale: ModueEnum) => {
    const index = modules.findIndex((i) => i.value === moduleVale);
    const newModule = cloneDeep(modules);
    newModule[index] = { ...newModule[index], status: status };
    setModules(newModule);
  };

  const stopRequest = () => {
    if (!sseController.current) {
      message.warning("无法停止，请联系管理员");
      return;
    }
    sseController.current.abort();
    sseController.current = new AbortController();
  };

  // 初始化信息的请求，文章详情请求
  const queryArticleDetaile = async (
    id: string,
    serverInfo: {
      token: string;
      baseURL: string;
      enableMock?: boolean;
    }
  ) => {
    const data = await api_getArticleById({
      data: {
        articleId: id,
        needSectionContent: true
      },
      config: serverInfo
    });
    if (data) return data;
  };
  // 初始化信息的请求，场景详情请求
  const queryArticleTypeDetaile = async (
    articleType: string,
    serverInfo: {
      token: string;
      baseURL: string;
      enableMock?: boolean;
    }
  ) => {
    const articleTypeDetaile = await api_getArticleTypeDetails({
      data: {
        id: articleType
      },
      config: serverInfo
    });
    if (articleTypeDetaile) return articleTypeDetaile;
  };
  const handleArticleTypeDetaile = async (
    articleTypeId: string,
    serverInfo: {
      token: string;
      baseURL: string;
      enableMock?: boolean;
    }
  ) => {
    const articleTypeData: any = await queryArticleTypeDetaile(
      articleTypeId,
      serverInfo
    );
    // 处理格式模板需要的数据
    const data = articleTypeDataToProject(articleTypeData);
    setProjectData((p) => ({
      ...p,
      ...data
    }));
  };

  //应用初始化的时候进行数据获取和表单填充
  const projectInitialized = async ({
    serverInfo,
    id = "",
    articleType,
    articleTypeId,
    articleTypeKey
  }: any) => {
    setModuleStatus(ModuleStatus.Process, ModueEnum.Writing);
    setProjectData((p) => {
      return {
        ...p,
        article_type_mode: articleType,
        article_type: articleTypeId,
        articleTypeKey: articleTypeKey
      };
    });
    //初始化project数据
    if (id) {
      //拉数据初始化iproject
      const articleInfo = await queryArticleDetaile(id, serverInfo);
      const newPd = toProjectData(articleInfo);
      setProjectData((p) => {
        return {
          ...p,
          ...newPd
        };
      });
      if (articleInfo?.articleTypeId)
        handleArticleTypeDetaile(articleInfo.articleTypeId, serverInfo);

      setModuleStatus(ModuleStatus.Waiting, ModueEnum.Writing);
    } else {
      await handleArticleTypeDetaile(
        articleTypeKey || articleTypeId,
        serverInfo
      );
      //初始化一个空白项目
      setModuleStatus(ModuleStatus.Waiting, ModueEnum.Writing);
    }
  };

  const handleCover = async () => {
    const { extraParams, coverPage } = projectData;
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
    }
  };

  const handleDownLoad = async (version = "docx") => {
    if (!projectData.id) {
      message.warning("请先保存文章");
      return;
    }
    const title = projectData.title || "未命名文章";
    try {
      // 有封面保存封面
      await handleCover();
      // 保存文章内容
      await articleContentSave({
        id: projectData.id,
        baseInfo,
        projectData,
        serverInfo,
        mainEditor
      });
      const res: any = await api_exportArticleById({
        data: { articleId: projectData.id, version: version },
        config: serverInfo
      });

      const file = new Blob([res], {
        type: "application/msword;charset=UTF-8"
      });

      const url = window.URL.createObjectURL(file);
      const a = document.createElement("a");
      a.download = `${title}.${version}`;
      a.href = url;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      message.error("请求出错，请稍后再试");
    }
  };

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

  return {
    setProjectStatus,
    setModuleStatus,
    stopRequest,
    projectInitialized,
    handleArticleTypeDetaile,
    queryArticleDetaile,
    handleDownLoad,
    getArticleTotalNum
  };
};

export { useGlobalOperators };
