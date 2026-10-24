// 参考文档根据文件名和素材id去重
// 溯源文档rag溯源根据order_num去重

import { uniqBy } from "lodash";
import {
  api_saveArticleContent,
  api_saveArticleSetting
} from "../../services/servers";
import { message } from "antd";
import { customSerializeHtml, customSerializeMd } from "./index";
import { cloneDeep } from "lodash";

// 溯源文档素材根据id和paragraphNo去重
const uniqueArr = (files: any[], sourceList: any[]) => {
  let _files: any[] = [];
  let _sourceList: any[] = [];
  let _ragFiles: any[] = [];
  let _cecFiles: any[] = [];
  let _ragSourceList: any[] = [];
  let _cecSourceList: any[] = [];
  files.forEach((i) => {
    if (i.order_num) {
      _ragFiles.push(i);
    } else {
      _cecFiles.push(i);
    }
  });

  sourceList.forEach((i) => {
    if (i.order_num) {
      _ragSourceList.push(i);
    } else {
      _cecSourceList.push(i);
    }
  });
  _ragFiles = uniqBy(_ragFiles, "parsedFilePath");
  _cecFiles = uniqBy(_cecFiles, "materialId");
  _files = [..._ragFiles, ..._cecFiles];

  _ragSourceList = uniqBy(_ragSourceList, "order_num");
  _cecSourceList = uniqBy(_cecSourceList, "id");
  _sourceList = [..._ragSourceList, ..._cecSourceList];

  return [_files, _sourceList];
};

// 保存文章配置
const articleSettingSave = async (params: any, serverInfo: any) => {
  const res = await api_saveArticleSetting({
    data: { params },
    config: serverInfo
  });
  return res;
};

// 根据用户编辑内容更改extraParams配置，格式模板情况下使用
const articleSettingSaveByBaseInfo = async ({
  projectData,
  baseInfo,
  id,
  serverInfo
}: any) => {
  const newExtraParams = {
    ...(projectData.extraParams || {}),
    ...(baseInfo || {})
  };
  await articleSettingSave(
    {
      id: id,
      extraParams: newExtraParams,
      title: newExtraParams.title || "未命名文档"
    },
    serverInfo
  );
};
// 获取除了封面的所有内容
const getAllSectionContent = (editor: any) => {
  const _articleInfo = cloneDeep(editor.children);
  return _articleInfo.filter(
    (item: any) => !(item.class || "").includes("cover")
  );
};

// 根据不同的情况获取需要保存的数据
const getSaveContent = ({ editor, isMd, isSection }: any) => {
  const content = isMd
    ? customSerializeMd(editor, isSection ? getAllSectionContent(editor) : "")
    : customSerializeHtml(editor);
  return content;
};

export const articleContentSave = async ({
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
  // 非必传，避免setState异步造成的数据获取不到的问题，需要手动将数据传递进来
  files,
  sourceList
}: any) => {
  // 参考文档与溯源文档数组
  files = files ? files : projectData?.files || [];
  sourceList = sourceList ? sourceList : projectData?.sourceList || [];

  // 保存时将参考文档和溯源文档去重
  const [_files, _sourceList] = uniqueArr(files || [], sourceList || []);
  // 如果拥有格式模板基本信息字段被修改的情况
  if (JSON.stringify(baseInfo) !== "{}") {
    await articleSettingSaveByBaseInfo({
      projectData,
      baseInfo,
      id,
      serverInfo
    });
  }
  // 使用state进行保存而不使用编辑器内容进行保存，
  // 例如刚生成完成，编辑器还未渲染完成，使用编辑器数据保存最后几个字会丢失
  // 使用接口返回数据进行保存
  if (useProjectData) {
    const res = await api_saveArticleContent({
      config: serverInfo,
      data: {
        params: {
          id: id,
          content: projectData.article_content,
          contentReference: JSON.stringify({
            files: _files,
            sourceList: _sourceList
          })
        }
      }
    });
    return res;
  }

  const editor: any = mainEditor.current;
  if (!editor) {
    message.error("编辑器内部错误，请联系管理员");
    return;
  }

  // 从编辑器获得现需要保存的内容
  const content = getSaveContent({
    editor: editor,
    isMd: projectData.outputFormat,
    isSection: projectData.generateType
  });

  // 保存文章内容
  const res = await api_saveArticleContent({
    config: serverInfo,
    data: {
      params: {
        id: id,
        content: section || content,
        contentReference: JSON.stringify({
          files: _files,
          sourceList: _sourceList
        })
      }
    }
  });
  return res;
};
