import { uid } from "uid";
import { IProject, ModueEnum } from "../@types/sys";
import { Flex } from "antd";
import WriteBlue from "@/components/AiEditor/assets/icon/writeBlue.svg";
import Write from "@/components/AiEditor/assets/icon/write.svg";
import Review from "@/components/AiEditor/assets/icon/review.svg";
import ReviewBlue from "@/components/AiEditor/assets/icon/reviewBlue.svg";
import Material from "@/components/AiEditor/assets/icon/material.svg";
import MateriaBlue from "@/components/AiEditor/assets/icon/materialBlue.svg";
import { createTemplateForm } from "../components/Sidebar/util";

const writeIcon = (
  <Flex vertical gap={5} className="w-full" justify="center">
    <span>
      <img src={Write} width={24} height={24} className="cursor-pointer" />
    </span>
    <span>写作</span>
  </Flex>
);

const writeClickIcon = (
  <Flex vertical gap={5} className="w-full" justify="center">
    <span>
      <img src={WriteBlue} width={24} height={24} className="cursor-pointer" />
    </span>
    <span className="text-[#2A2A2A] font-bold">写作</span>
  </Flex>
);

const reviewIcon = (
  <Flex vertical gap={5} className="w-full" justify="center">
    <span>
      <img src={Review} width={24} height={24} className="cursor-pointer" />
    </span>
    <span>审核</span>
  </Flex>
);

const reviewClickIcon = (
  <Flex vertical gap={5} className="w-full" justify="center">
    <span>
      <img src={ReviewBlue} width={24} height={24} className="cursor-pointer" />
    </span>
    <span className="text-[#2A2A2A] font-bold">审核</span>
  </Flex>
);

const materialIcon = (
  <Flex vertical gap={5} className="w-full" justify="center">
    <span>
      <img src={Material} width={24} height={24} className="cursor-pointer" />
    </span>
    <span>素材</span>
  </Flex>
);

const materialClickIcon = (
  <Flex vertical gap={5} className="w-full" justify="center">
    <span>
      <img
        src={MateriaBlue}
        width={24}
        height={24}
        className="cursor-pointer"
      />
    </span>
    <span className="text-[#2A2A2A] font-bold">素材</span>
  </Flex>
);

const iconObj: any = {
  [ModueEnum.Writing]: {
    common: writeIcon,
    click: writeClickIcon
  },
  [ModueEnum.Review]: {
    common: reviewIcon,
    click: reviewClickIcon
  },
  [ModueEnum.Material]: {
    common: materialIcon,
    click: materialClickIcon
  }
};

const useDataTransformer = () => {
  const modulesToMenuData = (modules_set: any, currentModule: any) => {
    return modules_set.map((module: any) => {
      return {
        key: module.value,
        icon: iconObj[module.value][
          currentModule === module.value ? "click" : "common"
        ],
        label: module.name
      };
    });
  };

  const dataModeTypeToModeType = (rawData: any[]) => {
    // First, check if rawData exists and is an array
    if (!Array.isArray(rawData)) {
      throw new Error("Invalid input: rawData must be an array");
    }
    // Perform data transformation
    return rawData.map((item) => {
      if (typeof item !== "object" || item === null) {
        throw new Error(
          "Invalid item in array: Each item must be a non-null object"
        );
      }

      const { id, name, promptTemplateUser, versionId, articleTypeKey } = item;

      // Validate required fields
      if (typeof id !== "number" || typeof name !== "string") {
        throw new Error(
          "Invalid data format: id must be a number and name must be a string"
        );
      }

      return {
        type_id: "2",
        id: String(id),
        version: String(versionId),
        name,
        promptTemplateUser, // Include as is, could add default value or validation if needed
        isSystem: false, // Set isSystem to false as specified
        articleTypeKey: articleTypeKey
      };
    });
  };

  // 为文章大纲添加id字段
  const handleOutlines = (outlines: any[]): any => {
    return outlines.map((item: any) => ({
      ...item,
      id: uid(32),
      subParagraphs: handleOutlines(item.subParagraphs || [])
    }));
  };

  const toProjectData = (data: any) => {
    const contentReference = data.contentReference
      ? data?.contentReference
      : "{}";
    return {
      title: data.title,
      id: data.id.toString(),
      status: data.status,
      article_type: data.articleTypeId?.toString(),
      article_type_version: data.articleTypeVersionId
        ? String(data.articleTypeVersionId)
        : "0",
      article_type_mode: data.articleType.toString(),
      article_content: data.content || undefined,
      //articleTypeVersionId: data.articleTypeVersionId?.toString() || undefined,
      updateTime: new Date(data.gmtModified).getTime(),
      currentModule: ModueEnum.Writing, // 根据你的逻辑设置适当的值
      defaultOpenSilde: true, // 根据需要设置
      outlines:
        (data?.outlines || {})?.paragraphs || ""
          ? handleOutlines((data?.outlines || {})?.paragraphs || "")
          : "",
      contentSources: data?.contentSources,
      extraParams: data?.extraParams,
      contentAbstract: data.contentAbstract || undefined,
      lengthLimit: data.lengthLimit || undefined,
      useTemplate: (data?.extraParams || {})?.template,
      contentFormat: data.contentFormat || 0,
      articelInfo: data,
      outputFormat: data.outputFormat,
      files: JSON.parse(contentReference || "{}").files || [],
      sourceList: JSON.parse(contentReference || "{}").sourceList || [],
      coverPage: (data?.outlines || {})?.coverPage || "",
      taskState: data.taskState || "",
      totalTasks: data.totalTasks || 0,
      completedTasks: data.completedTasks || 0,
      totalSections: data.totalSections || 0,
      generatedSections: data.generatedSections || 0
    };
  };

  const articleTypeDataToProject = (articleTypeData: any) => {
    const {
      formatTemplate,
      supportMaterials,
      supportOutlines,
      outputFormat,
      contentRule,
      generateType,
      versionId,
      id,
      articleTypeKey,
      sensitiveWords
    } = articleTypeData;
    let customized_style = {
      enable: false,
      styles: [],
      htmlSchema: "",
      formSchemaMap: {},
      originHtmlSchema: ""
    };
    if (formatTemplate && formatTemplate.length > 0) {
      const template = JSON.parse(formatTemplate);
      // 把接口返回的htmlSchema转换成前端编辑器展示的模版
      let newHtmlSchema = template.htmlSchema;
      const form_schema_dataIndex: any = {}; //存放{dataIndex:title}映射
      let form_schema = [];
      const temp_schema =
        JSON.parse(articleTypeData.paramsSchema)?.uiSchema || [];
      form_schema = createTemplateForm(temp_schema);
      form_schema.forEach((s: any) => {
        form_schema_dataIndex[s.dataIndex] = s.title;
      });
      for (const key in form_schema_dataIndex) {
        newHtmlSchema = newHtmlSchema.replace(
          new RegExp(`{${key}}`, "g"),
          `{${form_schema_dataIndex[key]}}`
        );
      }
      customized_style = {
        enable: true,
        styles: JSON.parse(template.cssSchema),
        htmlSchema: newHtmlSchema,
        formSchemaMap: form_schema_dataIndex,
        originHtmlSchema: template.htmlSchema //存储接口返回的原始htmlSchema，saveSetting接口需要使用
      };
    }
    return {
      outputFormat,
      contentRule,
      generateType,
      supportMaterials,
      supportOutlines,
      customized_style,
      article_type_version: versionId,
      article_type: id,
      articleTypeKey,
      sensitiveWords,
      articleTypeDetail: articleTypeData
    };
  };

  return {
    // articleValueToFormData,
    // articleTypeDetailseToUiSchema,
    dataModeTypeToModeType,
    toProjectData,
    modulesToMenuData,
    articleTypeDataToProject
  };
};
export { useDataTransformer };
