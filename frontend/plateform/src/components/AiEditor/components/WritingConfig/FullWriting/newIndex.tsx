import { Button, Flex, Form, Tooltip, message, Spin } from "antd";
import { BetaSchemaForm } from "@ant-design/pro-form";
import { useState, useRef, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useStateStore } from "@/components/AiEditor/core/states/useStateStore";
import { createTemplateForm } from "@/components/AiEditor/components/Sidebar/util";
import {
  EDITOR_EVENT_NAME,
  editorEventBus
} from "@/components/AiEditor/editorEventBus";
import {
  classifyMaterialToApi,
  classifyMaterialToRender
} from "../SegmentedWriting/utils";
import { uid } from "uid";
import {
  api_generateOutlines,
  api_saveArticleSetting,
  api_getArticleTypeDetails,
  api_getArticleById,
  api_addArticleTask
} from "@/components/AiEditor/core/services/servers";
import ProcessDrawer from "@root/src/components/progressDrawer";
import GuidelinesMaterails from "./components/GuidelinesMaterails";
import Outlines from "./components/Outlines";
import "./common/style.less";
import "./style.less";

const { useForm } = Form;

export enum sourceTypes {
  knowledge_base = "knowledge_base",
  database = "database"
}

enum ProcessType {
  BASIC_INFO = 1,
  GUIDELINES_MATERAILS = 2,
  OUTLINE = 3
}

enum writeTypes {
  ONLINE,
  OFFLINE
}

interface IFullWriting {
  open: boolean;
  onClose: () => void;
  articelInfo?: any;
}

const stepList = [
  {
    key: ProcessType.BASIC_INFO,
    value: "基本信息"
  },
  {
    key: ProcessType.GUIDELINES_MATERAILS,
    value: "关联素材"
  },
  {
    key: ProcessType.OUTLINE,
    value: "文章大纲"
  }
];
const initialOutlines = new Array(3)
  .fill({ title: "", contentAbstract: "" })
  .map((i) => Object.assign({}, i, { id: uid() }));

export const FullWriting = ({ open, onClose }: IFullWriting) => {
  const { serverInfo, setProjectData, projectData, setWritingSettingOpen } =
    useStateStore();
  const navigator = useNavigate();
  const [basicform] = useForm();

  const curArticleInfo: React.MutableRefObject<any> = useRef({
    title: "未命名文档",
    articleType: "",
    articleTypeId: "",
    articleTypeVersionId: ""
  });
  const [formSchema, setFormSchema] = useState<any>([]); // 存储表单的 schema
  const [curItemKey, setCurItemKey] = useState(ProcessType.BASIC_INFO);
  const [materialData, setMaterialData] = useState<any[]>([]);
  const [outLineData, setOutLineData] = useState<
    {
      id?: string;
      title: string;
      contentAbstract?: string;
    }[]
  >([...initialOutlines]);
  const [isSupportMaterial, setIsSupportMaterial] = useState<boolean>(false);
  const [isSupportOutline, setIsSupportOutline] = useState<boolean>(false);
  const [btnLoading, setBtnLoading] = useState(false);
  const [helpLoading, setHelpLoading] = useState(false);
  const [checked, setChecked] = useState(false);
  const [articleTypeLoading, setArticleTypeLoading] = useState<boolean>(true);
  const [docDetailLoading, setDocDetailLoading] = useState(false);
  const [offGenLoading, setOffGenLoading] = useState(false);
  const [articleType, setArticleType] = useState<string>("");

  //获取模版详情
  const getTemplateDetail = async (id: string) => {
    setArticleTypeLoading(true);
    console.log("api_getArticleTypeDetails");
    try {
      const res = await api_getArticleTypeDetails({
        data: {
          id
        },
        config: serverInfo
      });
      const { paramsSchema, supportMaterials, supportOutlines } = res;
      setIsSupportMaterial(!!supportMaterials);
      setIsSupportOutline(!!supportOutlines);

      const temp_schema = JSON.parse(paramsSchema)?.uiSchema || [];
      const schema = createTemplateForm(temp_schema);
      setFormSchema(schema);
      setArticleTypeLoading(false);
    } catch (e) {
      console.log(e);
      setArticleTypeLoading(false);
    }
  };

  const toGenerate = () => {
    setProjectData((p) => ({ ...p, ...curArticleInfo.current }));
    setTimeout(() => {
      projectData.id && navigator(`/docWriting/docs/${projectData.id}`);
      editorEventBus.emit(EDITOR_EVENT_NAME.START_WRITE, "");
    }, 0);
    setWritingSettingOpen(false);
  };

  const saveBasicInfo = () => {
    basicform.validateFields().then((data: any) => {
      //const { id, title, extraParams } = curArticleInfo.current;
      saveSettings({ extraParams: data, title: data.title }, () => {
        if (lastStep !== ProcessType.BASIC_INFO) {
          const nextKey =
            stepsList[
              stepsList.findIndex((item) => item.key === curItemKey) + 1
            ].key;
          setCurItemKey(nextKey);
        }
      });
    });
  };
  const saveMaterialList = () => {
    const curArticle = curArticleInfo.current;
    if (!curArticle?.id) {
      message.warning("没有文章ID");
      return;
    }

    saveSettings(
      {
        id: curArticle.id,
        title: curArticle.title,
        contentSources: getSources()
      },
      () => {
        if (lastStep !== ProcessType.GUIDELINES_MATERAILS) {
          const nextKey =
            stepsList[
              stepsList.findIndex((item) => item.key === curItemKey) + 1
            ].key;
          setCurItemKey(nextKey);
        }
      }
    );
  };

  const writingArticle = (params: any, writeType: writeTypes) => {
    switch (writeType) {
      case writeTypes.ONLINE:
        saveSettings(params, toGenerate);
        break;
      case writeTypes.OFFLINE:
        saveSettings(params, offlineWrite);
        break;
    }
  };

  const beginWrite = (writeType: writeTypes) => () => {
    console.log(String(curItemKey === ProcessType.GUIDELINES_MATERAILS));
    // return;
    const validate =
      !outLineData?.length || !checked
        ? true
        : outLineData.every((item) => {
            return item.title;
          });
    if (!validate) {
      return message.warning("文章标题不能为空");
    }

    const { id, title } = curArticleInfo.current;
    if (!id) {
      if (curItemKey === ProcessType.BASIC_INFO) {
        basicform.validateFields().then((data: any) => {
          writingArticle(
            {
              ...data,
              taskType: writeType === writeTypes.ONLINE ? 0 : 1
            },
            writeType
          );
        });
        return;
      }
      console.log("没有articleid");
      return;
    }
    const _outlinesData = checked
      ? {
          paragraphs: outLineData.map((item) => {
            const { contentAbstract, title } = item;
            return { contentAbstract, title };
          })
        }
      : {};
    const params: any = {
      id: id,
      title: title,
      taskType: writeType === writeTypes.ONLINE ? 0 : 1,
      outlines: _outlinesData
    };
    if (curItemKey === ProcessType.GUIDELINES_MATERAILS) {
      params.contentSources = getSources();
    }
    writingArticle(params, writeType);
  };

  const offlineWrite = async (articleId?: string | number) => {
    setOffGenLoading(true);
    const res: any = await api_addArticleTask({
      data: {
        articleId: articleId || curArticleInfo.current.id
      },
      config: serverInfo
    });
    setOffGenLoading(false);
    if (!res || !res.success) return;
    message.loading("文档已开始离线生成，可在我的文档中查看进度", 3, () => {
      setOffGenLoading(false);
      navigator(`/docWriting/history?highlightId=${articleId}`);
    });
  };

  const articleSettingSave = async (params: any) => {
    const res = await api_saveArticleSetting({
      data: { params },
      config: {
        ...serverInfo,
        enableMock: false
      }
    });
    return res;
  };

  const saveSettings = async (params: any, cb?: () => void) => {
    setBtnLoading(true);
    try {
      const p = {
        id: curArticleInfo.current.id,
        articleType: curArticleInfo.current.articleType,
        articleTypeId: curArticleInfo.current.articleTypeId,
        articleTypeVersionId: curArticleInfo.current.articleTypeVersionId,
        title: curArticleInfo.current.title,
        extraParams: curArticleInfo.current.extraParams,
        contentSources: curArticleInfo.current.contentSources,
        outlines: curArticleInfo.current.outlines,
        ...params
      };
      const settingRes = await articleSettingSave(p);
      setBtnLoading(false);
      if (settingRes) {
        curArticleInfo.current = settingRes;
        setProjectData((p) => ({ ...p, id: settingRes.id }));
        cb && cb();
      } else {
        message.error("保存失败");
      }
    } catch (error) {
      setBtnLoading(false);
      console.log("error", error);
    }
  };

  const getSources = () => {
    if (!materialData?.length) {
      return [];
    } else {
      return classifyMaterialToApi(materialData);
    }
  };

  const handleAIHelper = async () => {
    setHelpLoading(true);
    try {
      const outlines = await api_generateOutlines({
        config: serverInfo,
        data: {
          params: {
            contentAbstract:
              curArticleInfo.current?.extraParams?.contentAbstract ||
              basicform.getFieldValue("contentAbstract"),
            title: curArticleInfo.current?.title,
            sources: curArticleInfo.current?.contentSources
          }
        }
      });
      setHelpLoading(false);
      if (outlines && outlines.paragraphs) {
        const allData = outlines.paragraphs.map((i: any) => ({
          title: i.title,
          id: uid(32),
          contentAbstract: i.contentAbstract
        }));
        setOutLineData(allData);
      }
    } catch (error) {
      setHelpLoading(false);
    }
  };

  // 获取文章详情
  const getDocDetail = async (id: string) => {
    setDocDetailLoading(true);
    const docDetail = await api_getArticleById({
      data: {
        articleId: id
      },
      config: serverInfo
    });
    if (docDetail) {
      curArticleInfo.current = docDetail;
      const { extraParams, contentSources, outlines } = curArticleInfo.current;
      if (extraParams) {
        basicform.setFieldsValue({
          ...extraParams
        });
      }
      if (contentSources?.length) {
        const newContentSources = (contentSources || []).filter(
          (c: any) => c.sourceType === sourceTypes.knowledge_base
        );

        const data = classifyMaterialToRender(newContentSources);
        setMaterialData(data);
      }
      if (outlines?.paragraphs?.length) {
        setOutLineData(
          outlines.paragraphs.map((item: any) => {
            return {
              ...item,
              id: uid()
            };
          })
        );
        setChecked(true);
      }
    }
    setDocDetailLoading(false);
  };

  const nextConfirm = () => {
    switch (curItemKey) {
      case ProcessType.BASIC_INFO:
        saveBasicInfo();
        break;
      case ProcessType.GUIDELINES_MATERAILS:
        saveMaterialList();
        break;
    }
  };

  const goPreStep = () => {
    switch (curItemKey) {
      case ProcessType.GUIDELINES_MATERAILS:
        setCurItemKey(ProcessType.BASIC_INFO);
        break;
      case ProcessType.OUTLINE:
        if (isSupportMaterial) {
          setCurItemKey(ProcessType.GUIDELINES_MATERAILS);
        } else {
          setCurItemKey(ProcessType.BASIC_INFO);
        }
        break;
    }
  };

  const stepsList = useMemo(() => {
    const list: any[] = [stepList[0]];
    if (isSupportMaterial) {
      list.push(stepList[1]);
    }
    if (isSupportOutline) {
      list.push(stepList[2]);
    }

    return list;
  }, [isSupportMaterial, isSupportOutline]);

  const lastStep = useMemo(() => {
    return stepsList[stepsList.length - 1].key;
  }, [stepsList]);

  useEffect(() => {
    if (projectData && projectData.article_type) {
      const { id, article_type_mode, article_type, articleTypeDetail } =
        projectData;
      curArticleInfo.current = {
        ...curArticleInfo.current,
        articleType: article_type_mode,
        articleTypeId: article_type,
        articleTypeVersionId: articleTypeDetail?.versionId
      };
      if (open) {
        if (id) {
          getDocDetail(id);
        }
        if (article_type && String(article_type) !== String(articleType)) {
          // console.log("setArticleType", article_type, articleType);
          setArticleType(article_type);
          getTemplateDetail(article_type);
        }
      }
    }
  }, [open, projectData.article_type]);

  return (
    <div className="w-full h-full relative z-10">
      <Flex
        vertical
        className="rounded-t-xl bg-none h-full relative box-border"
      >
        <ProcessDrawer
          curItemKey={curItemKey}
          onClose={onClose}
          subTitle={projectData?.articleTypeDetail?.name || ""}
          list={stepsList}
          renderFooter={
            <>
              <Flex align="center" justify="flex-end" gap={16}>
                {curItemKey !== ProcessType.BASIC_INFO ? (
                  <Button
                    className="text-text-color2 rounded px-4"
                    style={{
                      border: "1px solid #ebebeb"
                    }}
                    disabled={btnLoading || offGenLoading}
                    onClick={goPreStep}
                  >
                    上一步
                  </Button>
                ) : null}
                {curItemKey !== lastStep && !articleTypeLoading ? (
                  <Button
                    className="text-text-color2 rounded px-4"
                    onClick={nextConfirm}
                    loading={btnLoading}
                  >
                    下一步
                  </Button>
                ) : null}
                {curItemKey === lastStep && !articleTypeLoading ? (
                  <Tooltip
                    title={
                      <span className="text-gray-2a">
                        流式输出，实时查看进度
                      </span>
                    }
                    color="#fff"
                  >
                    <Button
                      className="text-primary-color rounded px-3 online-btn"
                      onClick={beginWrite(writeTypes.ONLINE)}
                      loading={btnLoading}
                      disabled={offGenLoading}
                    >
                      在线生成
                    </Button>
                  </Tooltip>
                ) : null}
                {curItemKey === lastStep && !articleTypeLoading ? (
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
                        background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`
                      }}
                      onClick={beginWrite(writeTypes.OFFLINE)}
                      loading={offGenLoading}
                      disabled={btnLoading}
                    >
                      离线生成
                    </Button>
                  </Tooltip>
                ) : null}
              </Flex>
            </>
          }
        >
          <Spin spinning={articleTypeLoading}>
            <div className="px-5 pt-5 min-h-60">
              {/* <div className="a">asdsad{JSON.stringify(formSchema)}</div> */}
              <div
                className={`${curItemKey !== ProcessType.BASIC_INFO ? "hidden" : "flex"} justify-center`}
              >
                <BetaSchemaForm
                  layoutType="Form"
                  form={basicform}
                  columns={formSchema} // 动态根据选择渲染表单
                  submitter={false}
                  className="w-[914px]"
                />
              </div>
              {isSupportMaterial ? (
                <div
                  className={`${curItemKey !== ProcessType.GUIDELINES_MATERAILS ? "hidden" : ""}`}
                >
                  <GuidelinesMaterails
                    idDocLoading={docDetailLoading}
                    materialData={materialData}
                    setMaterialData={setMaterialData}
                  />
                </div>
              ) : null}
              {isSupportOutline ? (
                <div
                  className={`${curItemKey !== ProcessType.OUTLINE ? "hidden" : ""}`}
                >
                  <Outlines
                    outLineData={outLineData}
                    isShow={checked}
                    helpLoading={helpLoading}
                    setOutLineData={setOutLineData}
                    setChecked={setChecked}
                    handleAIHelper={handleAIHelper}
                  />
                </div>
              ) : null}
            </div>
          </Spin>
        </ProcessDrawer>
      </Flex>
    </div>
  );
};

export default FullWriting;
