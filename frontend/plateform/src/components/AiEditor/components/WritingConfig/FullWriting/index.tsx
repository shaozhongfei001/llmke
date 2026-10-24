/* eslint-disable no-case-declarations */
import {
  Button,
  Drawer,
  Flex,
  Form,
  Input,
  message,
  Popconfirm,
  Switch,
  Tooltip
} from "antd";
import { CloseOutlined, DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import ProcessDrawer from "@root/src/components/progressDrawer";
import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import w2 from "../../../assets/icon/icon-upload-material.svg";
import w1 from "../../../assets/icon/icon-material-base.svg";
import plusBlue from "../../../../../assets/img/plusBlue.png";
// import aiphoto from "../../../assets/img/aiphoto.png";
import aiphoto from "@/assets/img/aiRobit.png";
import aiphotoDis from "@/assets/img/aiRobitDis.png";
import Vector from "../../../../../assets/img/vector.png";
import closeCircle from "../../../../../assets/img/CloseCircle.png";
import genera from "../../../../../assets/gif/genera.gif";
import failFile from "../../../../../assets/img/failFile.png";
import loseFile from "../../../../../assets/img/loseFile.png";
import successFile from "../../../../../assets/img/successFile.png";
import UploadFileType, {
  UPLOAD_TYPE
} from "@root/src/components/UploadFileType";
import ChooseMaterial from "./components/ChooseMaterial";
import { uid } from "uid";
import {
  api_generateOutlines,
  api_queryMaterialList,
  api_queryMaterialType,
  api_retryParseMaterialUsing,
  api_saveArticleSetting,
  api_getArticleTypeDetails,
  api_getArticleById
} from "../../../core/services/servers";
import { useStateStore } from "../../../core/states/useStateStore";
import Setting from "@/components/AiEditor/assets/icon/setting.svg";
import SettingHover from "@/components/AiEditor/assets/icon/settingHover.svg";
import UploadParse, {
  UPLOAD_EVENTS
} from "@root/src/components/UploadFileType/UploadParse";
import "./common/style.less";
import { createTemplateForm } from "@root/src/components/AiEditor/components/Sidebar/util";
import { BetaSchemaForm } from "@ant-design/pro-form";
import { IProject, ModueEnum, ProjectStatus } from "../../../@types/sys";
import { EDITOR_EVENT_NAME, editorEventBus } from "../../../editorEventBus";
import { useNavigate } from "react-router-dom";
const { TextArea } = Input;
enum ProcessType {
  BASIC_INFO = 1,
  GUIDELINES_MATERAILS = 2,
  OUTLINE = 3,
  GERNERATE_DOC = 4
}
interface IFullWriting {
  open: boolean;
  onClose: () => void;
  articelInfo?: any;
}
const { useForm } = Form;
// const testRes: any = {};
const filterEmptyFields = (obj: any) => {
  return Object.keys(obj).reduce((result: any, key) => {
    const value = obj[key];
    if (value !== null && value !== undefined && value !== "") {
      result[key] = value;
    }
    return result;
  }, {});
};
export const FullWriting = ({ open, onClose, articelInfo }: IFullWriting) => {
  const [curItemKey, setCurItemKey] = useState(ProcessType.BASIC_INFO);
  const { serverInfo, setProjectData, projectData, setWritingSettingOpen } =
    useStateStore();
  const curArticleInfo: React.MutableRefObject<any> = useRef({
    title: "未命名文档",
    // status: ProjectStatus.Waiting,
    // currentModule: ModueEnum.Writing,
    // version: [],
    // customized_style: {
    //   enable: false,
    //   styles: [],
    //   htmlSchema: "",
    //   formSchemaMap: {}
    // },
    //saveArticle: "init",
    //form: Form.useForm()[0],
    //outputFormat: 0,
    articleType: "",
    articleTypeId: "",
    articleTypeVersionId: ""
  });
  const [formSchema, setFormSchema] = useState<any>([]); // 存储表单的 schema

  const [drawerTitleList, setDrawerTitleList] = useState([
    {
      key: ProcessType.BASIC_INFO,
      value: "基本信息",
      isEdit: false
    },
    {
      key: ProcessType.GUIDELINES_MATERAILS,
      value: "关联素材",
      isEdit: false
    },
    {
      key: ProcessType.OUTLINE,
      value: "文章大纲",
      isEdit: false
    }
    // {
    //   key: ProcessType.GERNERATE_DOC,
    //   value: "生成文章",
    //   isEdit: false,
    // },
  ]);
  useEffect(() => {
    if (open && projectData.article_type) {
      getTemplateDetail();
    }
  }, [open, projectData.article_type]);

  // 根据场景信息处理步骤条
  const handleTitleList = (supportMaterials, supportOutlines) => {
    // 根据配置处理步骤条
    if (!supportMaterials && !supportOutlines) {
      setDrawerTitleList([
        {
          key: ProcessType.BASIC_INFO,
          value: "基本信息",
          isEdit: false
        }
      ]);
    } else if (!supportMaterials && supportOutlines) {
      setDrawerTitleList([
        {
          key: ProcessType.BASIC_INFO,
          value: "基本信息",
          isEdit: false
        },
        {
          key: ProcessType.OUTLINE,
          value: "文章大纲",
          isEdit: false
        }
      ]);
    } else if (supportMaterials && !supportOutlines) {
      setDrawerTitleList([
        {
          key: ProcessType.BASIC_INFO,
          value: "基本信息",
          isEdit: false
        },
        {
          key: ProcessType.GUIDELINES_MATERAILS,
          value: "关联素材",
          isEdit: false
        }
      ]);
    }
  };

  //获取模版详情
  const getTemplateDetail = async () => {
    const res = await api_getArticleTypeDetails({
      data: {
        id: projectData.article_type as any
      },
      config: serverInfo
    });
    const { paramsSchema, supportMaterials, supportOutlines } = res;
    handleTitleList(supportMaterials, supportOutlines);
    const temp_schema = JSON.parse(paramsSchema)?.uiSchema || [];
    const schema = createTemplateForm(temp_schema);
    setFormSchema(schema);
  };

  useEffect(() => {
    if (!projectData) return;
    curArticleInfo.current.articleType = projectData.article_type_mode;
    curArticleInfo.current.articleTypeId = projectData.article_type;
    curArticleInfo.current.articleTypeVersionId =
      projectData.articleTypeDetail?.versionId;
  }, [
    projectData.article_type_mode,
    projectData.article_type,
    projectData.articleTypeDetail
  ]);

  const [basicform] = useForm();
  const [btnLoading, setBtnLoading] = useState(false);
  const [materialData, setMaterialData]: any = useState([]);
  const [helpLoading, setHelpLoading] = useState(false);
  const [outLineData, setOutLineData] = useState<
    {
      id?: string;
      title: string;
      contentAbstract?: string;
    }[]
  >([
    {
      id: uid(),
      title: "",
      contentAbstract: ""
    },
    {
      id: uid(),
      title: "",
      contentAbstract: ""
    },
    {
      id: uid(),
      title: "",
      contentAbstract: ""
    }
  ]);
  const [checked, setChecked] = useState(false);
  const navigator = useNavigate();
  const toGenerate = () => {
    setProjectData((p) => ({ ...p, ...curArticleInfo.current }));
    setTimeout(() => {
      projectData.id && navigator(`/docWriting/docs/${projectData.id}`);
      editorEventBus.emit(EDITOR_EVENT_NAME.START_WRITE, "");
    }, 0);
    setWritingSettingOpen(false);
  };

  const goSomeWhere = (to?: ProcessType, defaultTo?: ProcessType) => {
    if (to) {
      if (to !== ProcessType.GERNERATE_DOC) {
        setCurItemKey(to);
      } else {
        toGenerate();
      }
    } else {
      if (defaultTo && defaultTo !== ProcessType.GERNERATE_DOC) {
        setCurItemKey(defaultTo);
      } else {
        toGenerate();
      }
    }
  };

  const submit1 = (to?: ProcessType) => {
    basicform.validateFields().then((data: any) => {
      //const { id, title, extraParams } = curArticleInfo.current;
      recordStepStatus();
      saveSettings({ extraParams: data, title: data.title }, () => {
        if (lastStep === ProcessType.BASIC_INFO) {
          goSomeWhere(to);
        } else {
          const nextKey =
            drawerTitleList[
              drawerTitleList.findIndex((item) => item.key === curItemKey) + 1
            ].key;
          goSomeWhere(to, nextKey);
        }
      });
      // if (
      //   id &&
      //   title === data.title &&
      //   extraParams?.contentAbstract === data?.contentAbstract &&
      //   extraParams?.title === data?.title
      // ) {
      //   goSomeWhere(to, ProcessType.GUIDELINES_MATERAILS);
      // } else {
      //   saveSettings({ extraParams: data, title: data.title }, () => {
      //     goSomeWhere(to, ProcessType.GUIDELINES_MATERAILS);
      //   });
      // }
    });
  };
  const submit2 = (to?: ProcessType) => {
    const curArticle = curArticleInfo.current;
    if (!curArticle?.id) {
      message.warning("没有文章ID");
      return;
    }

    const vali = !materialData?.length
      ? false
      : materialData.every((item: any) => item.state != 3);
    if (vali) {
      return message.warning("文件未解析完成");
    }
    // const sources = getSources();
    // const { id, title, contentSources } = curArticleInfo.current;
    saveSettings(
      {
        id: curArticle.id,
        title: curArticle.title,
        contentSources: getSources()
      },
      () => {
        recordStepStatus();
        if (lastStep === ProcessType.GUIDELINES_MATERAILS) {
          goSomeWhere(to);
        } else {
          const nextKey =
            drawerTitleList[
              drawerTitleList.findIndex((item) => item.key === curItemKey) + 1
            ].key;
          goSomeWhere(to, nextKey);
        }
      }
    );
    // if (
    //   id == curArticle.id &&
    //   title == curArticle.title &&
    //   JSON.stringify(contentSources) === JSON.stringify(sources)
    // ) {
    //   goSomeWhere(to, ProcessType.OUTLINE);
    // } else {
    //   saveSettings(
    //     {
    //       id: curArticle.id,
    //       title: curArticle.title,
    //       contentSources: getSources()
    //     },
    //     () => {
    //       goSomeWhere(to, ProcessType.OUTLINE);
    //     }
    //   );
    // }
  };

  const submit3 = (to?: ProcessType) => {
    const validate =
      !outLineData?.length || !checked
        ? true
        : outLineData.every((item) => {
            return item.title;
          });
    if (!validate) {
      return message.warning("文章标题不能为空");
    }

    const { id, title, outlines } = curArticleInfo.current;
    if (!id) {
      console.log("====================================");
      console.log("没有articleid");
      console.log("====================================");
      return;
    }
    const outlinesData = {
      paragraphs: outLineData.map((item) => {
        delete item.id;
        return item;
      })
    };
    saveSettings(
      {
        id: id,
        title: title,
        outlines: checked ? outlinesData : {}
      },
      () => {
        recordStepStatus();
        goSomeWhere(to);
      }
    );
  };
  const validateNext = (from: ProcessType, to: ProcessType) => {
    switch (from) {
      case ProcessType.BASIC_INFO:
        submit1(to);
        break;
      case ProcessType.GUIDELINES_MATERAILS:
        submit2(to);
        break;
      case ProcessType.OUTLINE:
        submit3(to);
        break;
      case ProcessType.GERNERATE_DOC:
        goSomeWhere(to);
        break;
    }
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
      const refIds: any = [],
        refNames: any = [];
      materialData.forEach((item: any) => {
        refIds.push(item.id);
        refNames.push(item.fileName);
      });
      return [
        {
          sourceType: "materials",
          refIds,
          refNames
        }
      ];
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
    const docDetail = await api_getArticleById({
      data: {
        articleId: id
      },
      config: serverInfo
    });
    if (docDetail) {
      curArticleInfo.current = docDetail;
      const { extraParams, contentSources, outlines } = docDetail;
      if (extraParams) {
        const { title, contentAbstract } = extraParams;
        basicform.setFieldsValue({
          ...extraParams
        });
      }
      if (contentSources.length && contentSources[0].refIds?.length) {
        const sources = contentSources[0];
        const data = sources.refIds.map((item: any, index: number) => {
          return { id: item, fileName: sources.refNames[index], state: 3 };
        });
        setMaterialData(data);
      }
      if (outlines?.paragraphs?.length) {
        setOutLineData(
          outlines.paragraphs.map((item: any) => {
            return {
              ...item,
              id: uid(),
              editable: false
            };
          })
        );
        setChecked(true);
      }
    }
  };

  useEffect(() => {
    if (!open || !projectData.id) return;
    getDocDetail(projectData.id);
    return () => {
      spollingTimer && clearInterval(spollingTimer);
    };
  }, [open, projectData.id]);

  // 点击下一步之后，记录前面步骤已编辑状态
  const recordStepStatus = () => {
    setDrawerTitleList(
      drawerTitleList.map((d) => {
        if (d.key == curItemKey) {
          d.isEdit = true;
        }
        return d;
      })
    );
  };

  const lastStep = useMemo(() => {
    return drawerTitleList[drawerTitleList.length - 1].key;
  }, [drawerTitleList]);

  const renderRooter = useCallback(() => {
    switch (curItemKey) {
      case ProcessType.BASIC_INFO:
        return (
          <Flex align="center" justify="flex-end" gap={16}>
            <Button
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                borderRadius: "4px",
                border: "none"
              }}
              onClick={() => submit1()}
              loading={btnLoading}
            >
              {ProcessType.BASIC_INFO === lastStep ? "生成文章" : "下一步"}
            </Button>
          </Flex>
        );
      case ProcessType.GUIDELINES_MATERAILS:
        return (
          <Flex align="center" justify="flex-end" gap={16}>
            <Button
              style={{
                border: "1px solid #ebebeb",
                borderRadius: "4px",
                color: "#555"
              }}
              onClick={() => {
                goSomeWhere(ProcessType.BASIC_INFO);
              }}
            >
              上一步
            </Button>
            <Button
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                borderRadius: "4px",
                border: "none"
              }}
              loading={btnLoading}
              onClick={() => submit2()}
            >
              {ProcessType.GUIDELINES_MATERAILS === lastStep
                ? "生成文章"
                : "下一步"}
            </Button>
          </Flex>
        );
      case ProcessType.OUTLINE:
        return (
          <Flex align="center" justify="flex-end" gap={16}>
            <Button
              style={{
                border: "1px solid #ebebeb",
                borderRadius: "4px",
                color: "#555"
              }}
              onClick={() => {
                goSomeWhere(ProcessType.GUIDELINES_MATERAILS);
              }}
            >
              上一步
            </Button>
            <Button
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                borderRadius: "4px",
                border: "none"
              }}
              loading={btnLoading}
              onClick={() => submit3()}
            >
              {ProcessType.OUTLINE === lastStep ? "生成文章" : "下一步"}
            </Button>
          </Flex>
        );
      case ProcessType.GERNERATE_DOC:
        return (
          <Flex align="center" justify="flex-end" gap={16}>
            <Button
              style={{
                border: "1px solid #ebebeb",
                borderRadius: "4px",
                color: "#555"
              }}
              loading={btnLoading}
              onClick={() => {
                goSomeWhere(ProcessType.OUTLINE);
              }}
            >
              上一步
            </Button>
            <Button
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                border: "none",
                borderRadius: "4px"
              }}
              onClick={() => goSomeWhere()}
            >
              开始生成
            </Button>
          </Flex>
        );
    }
  }, [
    curItemKey,
    btnLoading,
    materialData,
    outLineData,
    checked,
    drawerTitleList
  ]);

  //  勿删，用完自删
  // useEffect(() => {
  //   basicform.setFieldsValue({
  //     title: "vpn使用手册说明",
  //   });
  // }, []);

  return (
    <div className="w-full h-full">
      <Flex
        vertical
        className="rounded-t-xl bg-white h-full relative box-border"
      >
        <ProcessDrawer
          open={true}
          curItemKey={curItemKey as any}
          clickItem={(item) => {
            validateNext(curItemKey, item.key);
          }}
          onClose={onClose}
          subTitle={projectData?.articleTypeDetail?.name || ""}
          list={drawerTitleList}
          renderFooter={renderRooter()}
        >
          <div
            className="flex justify-center"
            style={{
              display: curItemKey === ProcessType.BASIC_INFO ? "" : "none"
            }}
          >
            <BasicInfo basicform={basicform} formSchema={formSchema} />
          </div>
          <div
            style={{
              display:
                curItemKey === ProcessType.GUIDELINES_MATERAILS ? "" : "none"
            }}
          >
            <GuidelinesMaterails
              materialData={materialData}
              setMaterialData={setMaterialData}
            />
          </div>
          <div
            style={{
              display: curItemKey === ProcessType.OUTLINE ? "" : "none"
            }}
          >
            <OutLine
              outLineData={outLineData}
              setOutLineData={setOutLineData}
              checked={checked}
              setChecked={setChecked}
              handleAIHelper={handleAIHelper}
              helpLoading={helpLoading}
            />
          </div>
        </ProcessDrawer>
      </Flex>
    </div>
  );
};

export default FullWriting;

const OutLine = ({
  outLineData,
  setOutLineData,
  checked,
  setChecked,
  handleAIHelper,
  helpLoading
}: any) => {
  const [open, setOpen] = useState(false);
  const [curItem, setCurItem]: any = useState({});
  const [curHoverIcon, setCurHoverIcon] = useState("");
  const addRow = () => {
    setOutLineData((pre: any) => {
      return [...pre, { id: uid() }];
    });
  };

  return (
    <>
      <div className="text-[#2A2A2A] font-bold text-[14px]">大纲</div>
      <div className="mt-[20px]">
        <div className="flex justify-between items-center">
          <div className="flex justify-between items-center">
            <span className="mr-[20px]">文章大纲</span>
            <Switch
              value={checked}
              onChange={(v) => {
                setChecked(v);
              }}
            />
          </div>
          <Button
            type="link"
            className={`${checked ? "text-[#055AFF]" : "text-text-color3"} text-[14px] px-[0px] flex flex-row justify-between items-center`}
            onClick={handleAIHelper}
            disabled={!checked}
            icon={
              <img
                className="mr-[-8px]"
                src={!checked ? aiphotoDis : helpLoading ? genera : aiphoto}
                width={20}
                height={20}
              />
            }
          >
            <span className="leading-[25px]">AI帮写</span>
          </Button>
        </div>
        <div className="mt-[16px]" style={{ display: checked ? "" : "none" }}>
          <div className="outlineData h-[100%-300px] overflow-auto">
            <div
              className="bg-[#FAFAFA] border-[1px] h-[46px] pl-[12px] leading-[45px] flex justify-between"
              style={{ borderBottom: "1px solid #eeeeee" }}
            >
              <div>标题</div>
              <div
                className="w-[150px] ml-5 pl-4"
                style={{
                  borderLeft: "1px solid #fff"
                }}
              >
                操作
              </div>
            </div>
            {outLineData.map((item: any, index: number) => {
              return (
                <div
                  key={item.id || index}
                  className="h-[80px] bg-white flex items-center hover:bg-[#F1F5FF]   pl-3"
                  style={{ borderBottom: "1px solid #eeeeee" }}
                  onClick={(e) => {
                    setOutLineData((pre: any) => {
                      return pre.map((p) => {
                        if (p.id == item.id) {
                          return {
                            ...p,
                            editable: true
                          };
                        } else {
                          return {
                            ...p,
                            editable: false
                          };
                        }
                      });
                    });
                  }}
                  onMouseLeave={(e) => {
                    setOutLineData((pre: any) => {
                      return pre.map((p) => {
                        return {
                          ...p,
                          editable: false
                        };
                      });
                    });
                  }}
                >
                  {item.editable ? (
                    <Input
                      size="small"
                      className="w-full border-transparent h-[32px]"
                      value={item.title}
                      onChange={(e) => {
                        item.title = e.target.value;
                        setOutLineData((pre: any) => {
                          console.log("pre", pre);
                          return [...pre];
                        });
                      }}
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <>
                      {item?.title?.trim()?.length > 0 ? (
                        <span className="w-full px-[7px] full-outline-title ">
                          {item.title}
                        </span>
                      ) : (
                        <span className="text-[#FF4D4F] w-full  px-[7px] full-outline-title">
                          未填写标题
                        </span>
                      )}
                    </>
                  )}

                  <div className="w-[170px] flex cursor-pointer ml-[20px] pl-4">
                    {/* <PlusOutlined className="mr-[12px] cursor-pointer" /> */}
                    <Tooltip
                      arrow={false}
                      title="配置"
                      color="#fff"
                      overlayInnerStyle={{
                        color: "#2a2a2a"
                      }}
                    >
                      <img
                        onMouseEnter={() =>
                          setCurHoverIcon(`setting${item.id}`)
                        }
                        onMouseLeave={() => {
                          setCurHoverIcon("");
                        }}
                        src={
                          curHoverIcon === `setting${item.id}`
                            ? SettingHover
                            : Setting
                        }
                        alt=""
                        className="mr-[20px]"
                        onClick={() => {
                          setCurItem({ ...item, index });
                          setOpen(true);
                        }}
                      />
                    </Tooltip>

                    <Popconfirm
                      title="删除"
                      description="是否确认删除"
                      onConfirm={() => {
                        setOutLineData((pre: any) => {
                          return pre.filter((v: any) => {
                            return v.id !== item.id;
                          });
                        });
                      }}
                      okText="确认"
                      cancelText="取消"
                      cancelButtonProps={{
                        style: {
                          borderRadius: "4px",
                          color: "#555",
                          borderColor: "#EEEEEE"
                        }
                      }}
                      okButtonProps={{
                        style: {
                          background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                          color: "#fff",
                          border: "none",
                          borderRadius: "4px"
                        }
                      }}
                      overlayInnerStyle={{
                        width: "224px"
                      }}
                      disabled={!item.title && !item.contentAbstract}
                      placement="topLeft"
                    >
                      <Tooltip
                        arrow={false}
                        title="删除"
                        color="#fff"
                        overlayInnerStyle={{
                          color: "#2a2a2a"
                        }}
                      >
                        <DeleteOutlined
                          onMouseEnter={() => setCurHoverIcon(`del${item.id}`)}
                          onMouseLeave={() => {
                            setCurHoverIcon("");
                          }}
                          style={{
                            width: "16px",
                            color:
                              curHoverIcon === `del${item.id}` ? "#1538ff" : ""
                          }}
                          onClick={(e) => {
                            if (!item.title && !item.contentAbstract) {
                              e.stopPropagation();
                              setOutLineData((pre: any) => {
                                return pre.filter((v: any) => {
                                  return v.id !== item.id;
                                });
                              });
                            }
                          }}
                        />
                      </Tooltip>
                    </Popconfirm>
                  </div>
                </div>
              );
            })}
          </div>
          <Button
            size="small"
            className="text-text-color2 border-[#EEEEEE] mt-[10px] mb-[20px]  w-[94px]"
            icon={<img src={plusBlue} className="w-[14px] h-[14px]" />}
            onClick={addRow}
          >
            添加标题
          </Button>
        </div>
      </div>
      <Drawer
        title={
          <Flex justify="space-between" align="center">
            <span>编辑写作配置</span>
            <CloseOutlined
              className="cursor-pointer"
              onClick={() => setOpen(false)}
            />
          </Flex>
        }
        closeIcon={false}
        onClose={() => setOpen(false)}
        open={open}
        width={430}
      >
        <div>
          <span>内容要求</span>
          <TextArea
            showCount
            maxLength={500}
            placeholder="请输入内容要求"
            style={{ height: 120, resize: "none", marginTop: "12px" }}
            value={curItem.contentAbstract}
            onChange={(e) => {
              setCurItem({ ...curItem, contentAbstract: e.target.value });
              setOutLineData((pre: any) => {
                pre[curItem.index].contentAbstract = e.target.value;
                return [...pre];
              });
            }}
          />
        </div>
      </Drawer>
    </>
  );
};

let spollingTimer: undefined | number | null = undefined;

const GuidelinesMaterails = ({ materialData, setMaterialData }: any) => {
  const [uploadModalOpen, setUploadOpen] = useState(false);
  const [materailModalOpen, setMaterailModalOpen] = useState(false);
  const [materialTypes, setMaterialTypes] = useState([]);
  const { serverInfo } = useStateStore();
  const handleUploadEvents = (action: string, payload: any) => {
    console.log("====================================");
    console.log("action", action);
    console.log("payload", payload);
    console.log("====================================");
    switch (action) {
      case UPLOAD_TYPE.CONFIRM:
        setMaterialData((pre: any) => {
          const ids = pre.map((item: any) => item.id);
          return [
            ...pre,
            ...(payload || []).filter((item: any) => {
              return !ids.includes(item.id);
            })
          ];
        });
        setMaterailModalOpen(false);
        break;
      case UPLOAD_EVENTS.MODAL_CLOSE:
        const ids = materialData.map((item: any) => item.id);
        const curData: any = [
          ...materialData,
          ...(payload || []).filter((item: any) => {
            return !ids.includes(item.id);
          })
        ];
        setMaterialData(curData);
        setUploadOpen(false);
        break;
      case UPLOAD_EVENTS.MODAL_ONLY_CLOSE:
        setUploadOpen(false);
        break;
    }
  };

  useEffect(() => {
    if (
      materialData?.length &&
      materialData.some((item: any) => !item.state || item.state !== 3)
    ) {
      if (spollingTimer) {
        clearInterval(spollingTimer);
        startSpolling(materialData);
      } else {
        startSpolling(materialData);
      }
    }
  }, [materialData]);

  const queryStatus = async (id: string) => {
    try {
      const res = await api_queryMaterialList({
        data: { id, pageSize: 9999, pageNo: 1 },
        config: {
          ...serverInfo,
          enableMock: false
        }
      });
      if (res?.data?.details) {
        const ids = id.split(",");
        const d: any[] = res.data.details;
        const map = new Map();
        const curIds: any[] = [];
        d.forEach((item) => {
          curIds.push(+item.id);
          map.set(+item.id, item);
        });
        const notExist = ids
          .filter((id) => {
            return !curIds.includes(+id);
          })
          .map((id) => +id);
        setMaterialData((pre: any[]) => {
          pre.forEach((item) => {
            const curItem = map.get(+item.id);
            if (curItem) {
              item.state = curItem.state;
            }
            if (notExist.includes(+item.id)) {
              item.state = 6;
            }
          });
          return [...pre];
        });
      }
    } catch (error) {
      console.log("====================================");
      console.log(error);
      console.log("====================================");
    }
  };

  const polling = (curData: any[]) => {
    const ids = curData
      .filter(
        (item: any) => item.state === 1 || item.state === 2 || !item.state
      )
      .map((item: any) => item.id)
      .join(",");
    if (ids) {
      queryStatus(ids);
    } else {
      spollingTimer && clearInterval(spollingTimer);
      spollingTimer = null;
    }
  };

  const startSpolling = (curData: any[]) => {
    //polling(curData);
    spollingTimer = setInterval(() => {
      polling(curData);
    }, 5000);
  };

  const retryParse = async (id: string) => {
    const res = await api_retryParseMaterialUsing({
      data: { id },
      config: {
        ...serverInfo,
        enableMock: false
      }
    });
    if (res) {
      setMaterialData((pre: any[]) => {
        const cur = pre.find((item) => item.id === id);
        cur.state = 2;
        const data = [...pre];
        return data;
      });
    }
  };

  const getMaterialType = async () => {
    const res = await api_queryMaterialType({
      data: {},
      config: serverInfo
    });
    setMaterialTypes(
      res?.data.map((item: any) => {
        return { ...item, value: item.id, label: item.fileName };
      })
    );
  };

  useEffect(() => {
    if (!serverInfo.token) return;
    getMaterialType();
  }, [serverInfo]);

  useEffect(() => {
    return () => {
      spollingTimer && clearInterval(spollingTimer);
    };
  }, []);

  return (
    <div>
      <span className="text-[16px] font-bold text-[#2a2a2a]">上传素材</span>
      <div className="border-[1px] border-[#D9D9D9] border-dashed h-[106px] w-full bg-[#F9FAFC] mt-[16px] rounded-[2px] flex items-center flex-col">
        <div className="mt-[16px]">
          <Button
            size="large"
            icon={<img src={w2} />}
            className="mr-[16px] border-[#eeeeee] w-[140px] rounded-[4px] text-[#055AFF] text-[14px]"
            onClick={() => setUploadOpen(true)}
            style={{
              borderRadius: "4px"
            }}
          >
            上传素材
          </Button>
          <Button
            size="large"
            icon={<img src={w1} />}
            className="mr-[16px] border-[#eeeeee] w-[140px] rounded-[4px] text-[#055AFF] text-[14px]"
            onClick={() => setMaterailModalOpen(true)}
            style={{
              borderRadius: "4px"
            }}
          >
            从素材库选择
          </Button>
        </div>
        <div className="text-[12px] text-[#999999] mt-[16px]">
          支持单篇或批量上传，支持 doc、docx、excel、pdf、txt、ppt格式
        </div>
      </div>
      <div className="mt-[20px]">
        {materialData.map((item: any) => {
          return (
            <div
              className="mt-[8px] h-[32px] rounded-[4px] px-[8px] flex items-center justify-between"
              style={{ border: "1px solid #eeeeee" }}
              onMouseOver={() => {
                item.showDelete = true;
                setMaterialData((pre: any) => {
                  return [...pre];
                });
              }}
              onMouseOut={() => {
                item.showDelete = false;
                setMaterialData((pre: any) => {
                  return [...pre];
                });
              }}
              key={item.id}
            >
              <div className="flex justify-center">
                <img
                  src={
                    item.state === 4
                      ? failFile
                      : item.state === 6
                        ? loseFile
                        : successFile
                  }
                  alt="ellipse"
                  width={14}
                  height={14}
                  className="mr-[8px] mt-[2px]"
                />
                <div
                  className={`${item.state === 4 ? "text-[#FF4D4F]" : item.state === 6 ? "#BBBBBB" : "text-text-color1"}`}
                >
                  {item.fileName}
                </div>
              </div>
              <div>
                {item.state === 4 || item.state === 6 ? (
                  item.state === 6 ? (
                    <div className="flex items-center">
                      <span
                        className={`${item.showDelete ? "text-primary-color" : "text-[#BBBBBB]"} text-[12px] cursor-pointer`}
                        onClick={() => {
                          if (item.showDelete) {
                            setMaterialData((pre: any) => {
                              return pre.filter((v: any) => v.id !== item.id);
                            });
                            setUploadOpen(true);
                            //retryParse(item.id);
                          }
                        }}
                      >
                        {item.showDelete ? "重新上传" : "丢失"}
                      </span>
                      {item.showDelete && (
                        <img
                          width={14}
                          height={14}
                          onClick={() => {
                            if (item.showDelete) {
                              setMaterialData((pre: any) => {
                                return pre.filter((v: any) => v.id !== item.id);
                              });
                            }
                          }}
                          className="cursor-pointer  ml-[12px]"
                          src={closeCircle}
                        />
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center">
                      <span
                        className={`${item.showDelete ? "text-primary-color" : "text-[#FF4D4F]"} text-[12px] cursor-pointer`}
                        onClick={() => {
                          if (item.showDelete) {
                            retryParse(item.id);
                          }
                        }}
                      >
                        {item.showDelete ? "重新解析" : "解析失败"}
                      </span>
                      {item.showDelete && (
                        <img
                          width={14}
                          height={14}
                          onClick={() => {
                            if (item.showDelete) {
                              setMaterialData((pre: any) => {
                                return pre.filter((v: any) => v.id !== item.id);
                              });
                            }
                          }}
                          className="cursor-pointer  ml-[12px]"
                          src={closeCircle}
                        />
                      )}
                    </div>
                  )
                ) : (
                  <img
                    width={14}
                    height={14}
                    onClick={() => {
                      if (item.showDelete) {
                        setMaterialData((pre: any) => {
                          return pre.filter((v: any) => v.id !== item.id);
                        });
                      }
                    }}
                    className="cursor-pointer"
                    src={
                      item.showDelete === true
                        ? closeCircle
                        : item.state === 3
                          ? Vector
                          : item.state === 1 || item.state === 2 || !item.state
                            ? genera
                            : genera
                    }
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
      <UploadParse
        open={uploadModalOpen}
        uploadEvents={handleUploadEvents}
        kbId={0}
        fileListType={0}
      />
      <ChooseMaterial
        open={materailModalOpen}
        handleChooseEvent={handleUploadEvents}
        close={() => setMaterailModalOpen(false)}
        defaultData={materialData}
      />
    </div>
  );
};

const BasicInfo = ({ basicform, formSchema }: any) => {
  return (
    <BetaSchemaForm
      layoutType="Form"
      form={basicform}
      columns={formSchema} // 动态根据选择渲染表单
      submitter={false}
      className="w-[914px]"
    />
  );
};
