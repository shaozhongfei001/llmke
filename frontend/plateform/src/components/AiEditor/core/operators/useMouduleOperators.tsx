import { FormInstance, message } from "antd";
import { useStateStore } from "../states/useStateStore";
import { redTitleHtml } from "../configs/red_head_temp";
import dayjs from "dayjs";
import { ModueEnum } from "../../@types/sys";

interface SubmitFromProps {
  outlineData?: any[];
  useOutline: boolean;
  form: FormInstance<any>;
  selectedOption: string | undefined;
  curMaterialList: any[];
  useTemp?: boolean;
}

const getQueryObject = (selectedOption: string) => {
  const selectValue = new URLSearchParams(selectedOption);
  const queryObject: Record<string, string> = {};
  selectValue.forEach((value, key) => {
    queryObject[key] = value;
  });
  return queryObject;
};

const redTitleObj = {
  title: "通知标题",
  target: "主送机关",
  publisher: "发文机关",
  publishDate: "发文时间",
  documentNumber: "发文字号",
};

const getHtmlTemp = (formData: any, htmlTemp: any, titleObj: any) => {
  let newHtmlString = htmlTemp;
  for (const key in formData) {
    newHtmlString = newHtmlString.replace(
      new RegExp(`{${titleObj[key]}}`, "g"),
      formData[key]
    );
  }
  return newHtmlString;
};

const useMouduleOperators = () => {
  const { projectData, setProjectData, setModules, modules } = useStateStore();

  const getCommonParams = ({
    outlineData,
    useOutline,
    form,
    curMaterialList,
  }: Omit<SubmitFromProps, "selectedOption">) => {
    return new Promise((resolve) => {
      let params: any = {};
      form
        .validateFields()
        .then((res) => {
          if (useOutline) {
            const outline = (outlineData || []).map((i) => ({
              title: i.title,
              contentAbstract: i.contentAbstract,
            }));
            params.outlines = {
              paragraphs: outline,
            };
            setProjectData((P) => ({
              ...P,
              outlineData: outline,
            }));
          }
          if (curMaterialList.length) {
            const refIds: number[] = [];
            const refNames: string[] = [];
            curMaterialList.forEach((i: any) => {
              refNames.push(i.fileName);
              refIds.push(i.id);
            });
            params.contentSources = [
              {
                sourceType: "materials",
                refIds,
                refNames,
              },
            ];
          }
          params = {
            ...params,
            ...res,
            articleType: 0,
            extraParams: res.languageStyle
              ? {
                  languageStyle: res.languageStyle,
                }
              : undefined,
            // 暂无用处，固定写死字段
            articleSubType: 0,
            title: projectData?.title,
          };
          if (projectData.id) {
            params.id = projectData.id;
          }
          resolve(params);
        })
        .catch((e) => {
          const { errorFields } = e;
          if (errorFields && errorFields.length > 0) {
            const msg = (errorFields[0]?.errors || [])[0] || "";
            msg && message.warning(msg);
          }
          console.log(e, "++++++++++++++");
        });
    });
  };

  const getNotifyParams = ({
    form,
    useTemp,
  }: {
    form: FormInstance<any>;
    useTemp: boolean;
  }) => {
    return new Promise((resolve) => {
      let params: any = {};
      form
        .validateFields()
        .then((res) => {
          params = {
            ...res,
            extraParams: {
              ...res,
              template: useTemp
                ? getHtmlTemp(
                    { ...res, title: projectData.title },
                    redTitleHtml,
                    redTitleObj
                  )
                : "",
            },
            title: projectData?.title,
            articleType: 1,
            // 暂无用处，固定写死字段
            articleSubType: 1,
          };
          if (projectData.id) {
            params.id = projectData.id;
          }
          resolve(params);
        })
        .catch((e) => {
          const { errorFields } = e;
          if (errorFields && errorFields.length > 0) {
            const msg = (errorFields[0]?.errors || [])[0] || "";
            msg && message.warning(msg);
          }
          console.log(e, "++++++++++++++");
        });
    });
  };

  const getCustomizedParams = ({
    form,
    selectedOption,
    useTemp,
    curMaterialList,
    outlineData,
    useOutline,
  }: {
    form: FormInstance<any>;
    selectedOption: string | undefined;
    useTemp: boolean;
    curMaterialList: any[];
    outlineData: any;
    useOutline: any;
  }) => {
    return new Promise((resolve) => {
      const queryObject = getQueryObject(selectedOption as string);
      let params: any = {};

      form
        .validateFields()
        .then((res) => {
          let extraParams = res;
          console.log("+++++++res", res);
          if (projectData.customized_style.enable) {
            extraParams = {
              ...res,
              template: useTemp
                ? projectData.customized_style.originHtmlSchema
                : "",
            };
          }
          if (useOutline) {
            const outline = (outlineData || []).map((i) => ({
              title: i.title,
              contentAbstract: i.contentAbstract,
            }));
            params.outlines = {
              paragraphs: outline,
            };
            setProjectData((P) => ({
              ...P,
              outlineData: outline,
            }));
          }
          if (curMaterialList?.length) {
            const refIds: number[] = [];
            const refNames: string[] = [];
            curMaterialList.forEach((i: any) => {
              refNames.push(i.fileName);
              refIds.push(i.id);
            });
            params.contentSources = [
              {
                sourceType: "materials",
                refIds,
                refNames,
              },
            ];
          }
          params = {
            extraParams: extraParams,
            outlines: params.outlines,
            title: projectData?.title,
            articleType: 2,
            contentSources: params.contentSources,
            articleTypeId: queryObject.id,
            articleTypeVersionId: queryObject.version,
          };
          if (projectData.id) {
            params.id = projectData.id;
          }
          resolve(params);
        })
        .catch((e) => {
          const { errorFields } = e;
          if (errorFields && errorFields.length > 0) {
            const msg = (errorFields[0]?.errors || [])[0] || "";
            msg && message.warning(msg);
          }
          console.log(e, "++++++++++++++");
        });
    });
  };

  const getSubmitFromData = async ({
    outlineData,
    useOutline,
    form,
    selectedOption,
    curMaterialList,
    useTemp = false,
  }: SubmitFromProps) => {
    // 将其转换为对象
    const queryObject = getQueryObject(selectedOption as string);
    switch (queryObject["type_id"]) {
      // 通用文稿
      case "0":
        return await getCommonParams({
          outlineData,
          useOutline,
          form,
          curMaterialList,
        });
      // 通知公告
      case "1":
        return await getNotifyParams({ form, useTemp });
      // 自定义文稿
      case "2":
        return await getCustomizedParams({
          form,
          selectedOption,
          useTemp,
          curMaterialList,
          outlineData,
          useOutline,
        });
      default:
        break;
    }
  };

  const openFeedback = (data: {
    id: string;
    source: string;
    errorType: string | number | null;
    target?: string;
    suggestion?: string;
    scene: number;
  }) => {
    if (projectData.currentModule !== ModueEnum.Review) return;
    setModules((prevModules) => {
      return prevModules.map((module) => {
        if (module.value === ModueEnum.Review) {
          return {
            ...module,
            feedback: {
              openModal: true,
              data,
            },
          };
        }
        return module;
      });
    });
    console.log(modules);
  };

  const closeFeedback = () => {
    console.log("取消反馈");
    setModules((prevModules) =>
      prevModules.map((module) =>
        module.value === ModueEnum.Review
          ? {
              ...module,
              feedback: {
                openModal: false,
                data: {
                  id: "",
                  source: "",
                  target: "",
                  errorType: null,
                  scene: 0,
                },
              },
            }
          : module
      )
    );
  };

  return {
    getSubmitFromData,
    openFeedback,
    closeFeedback,
  };
};

export { useMouduleOperators };
