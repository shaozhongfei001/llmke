import { ConfigProvider, message, Dropdown, Space } from "antd";
import { useNavigate, useParams } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import { useLayouts } from "./core/layouts/useLayouts";
import { useStateStore } from "./core/states/useStateStore";
import { useEffect, useRef } from "react";
import useAiEditorOperators from "./core/operators/useAiEditorOperators";
import MainEditor from "./components/MainEditor";
import { DocState, EditorType, ModueEnum, ProjectStatus } from "./@types/sys";
import { ArticleLoading } from "./components/ArticleLoading";
import { UploadLoading } from "./components/UploadLoading";
import { EDITOR_EVENT_NAME, editorEventBus } from "./editorEventBus";
import { useGlobalOperators } from "./core/operators/useGlobalOperators";
import WritingConfig from "./components/WritingConfig";
import { useDataTransformer } from "./core/useDataTransformer";
import { api_getArticleById } from "./core/services/servers";
import {
  CaretDownOutlined,
  PlusCircleOutlined,
  HomeOutlined,
  FileTextOutlined,
  FolderOutlined
} from "@ant-design/icons";
import IconMaterial from "@/assets/svg/icon-menu-material.svg";
import HomeIcon from "@/components/AiEditor/assets/img/home.png";
import { v4 as uuidv4 } from "uuid";
import { articleContentSave } from "./core/operators/help";
const headerHight = 45;
const finishStatus = [DocState.success, DocState.failure, DocState.stopped];
interface IuseAiEditor {
  url: string;
  token: string;
  enableMock?: boolean;
  styles?: any;
  device?: string;
  articleId?: string;
  articleType?: string;
  articleTypeId?: string;
  articleTypeKey?: string;
  handleBack?: () => void;
  file?: any;
  fileInfo?: { fileName: string; fileUrl: string; suffix: string };
  editorType?: string;
}
enum menuTypes {
  CREATE_DOC = "createDoc",
  WRITE_INDEX = "writeIndex",
  MY_DOCS = "myDocs",
  WRITE_SCENE = "writeScene",
  MATERIAL = "material"
}
const items = [
  {
    key: menuTypes.CREATE_DOC,
    label: <span className="select-none">新建文档</span>,
    path: "docs",
    icon: <PlusCircleOutlined style={{ fontSize: "16px" }} />
  },
  {
    type: "divider"
  },
  {
    key: menuTypes.WRITE_INDEX,
    label: (
      <span className="inline-block my-[2px] select-none">文档写作首页</span>
    ),
    path: "main",
    icon: <HomeOutlined style={{ fontSize: "16px" }} />
  },
  {
    key: menuTypes.MY_DOCS,
    label: <span className="inline-block my-[2px] select-none">我的文档</span>,
    path: "history",
    icon: <FileTextOutlined style={{ fontSize: "16px" }} />
  },
  {
    key: menuTypes.WRITE_SCENE,
    label: <span className="inline-block my-[2px] select-none">写作场景</span>,
    path: "template",
    icon: <FolderOutlined style={{ fontSize: "16px" }} />
  },
  {
    key: menuTypes.MATERIAL,
    label: <span className="inline-block my-[2px] select-none">素材库</span>,
    path: "resource",
    icon: <img src={IconMaterial} />
  }
];

const pollInterval = 5000;

export const useAiEditor = (props: IuseAiEditor) => {
  const { HeadLessContainer } = useLayouts();
  const {
    setServerInfo,
    setProjectData,
    projectData,
    setWritingSettingOpen,
    writingSettingOpen,
    serverInfo,
    useTemp,
    baseInfo,
    mainEditor,
    setEditorType,
    editorType
  } = useStateStore();
  const { fullWriting, stopLLMWriting, segmentedWriting } =
    useAiEditorOperators();
  const { projectInitialized, stopRequest } = useGlobalOperators();
  const { toProjectData } = useDataTransformer();
  const navigator = useNavigate();
  const { id } = useParams();
  const intervalRef = useRef<any>(null);

  const pollingQueryArticleById = ({
    id,
    config,
    toProjectData,
    setProjectData,
    intervalRef
  }: any) => {
    // 启动前先清理旧的
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    const fetchData = async () => {
      try {
        const response = await api_getArticleById({
          data: {
            articleId: id,
            needSectionContent: true
          },
          config
        });
        if (finishStatus.includes(response.taskState)) {
          console.log("任务已完成，停止轮询");
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
        const newPd = toProjectData(response);
        setProjectData((p: any) => ({
          ...p,
          ...newPd
        }));
      } catch (e) {
        console.error("Error fetching article by ID:", e);
      }
    };
    intervalRef.current = setInterval(fetchData, pollInterval);
  };

  // 上传文件进入编辑器
  useEffect(() => {
    if (!props.file) return;
    editorEventBus.emit(EDITOR_EVENT_NAME.UPLOADFILE, props.file);
  }, [props.file]);

  useEffect(() => {
    //首次进入
    if (!props.articleId && !props.articleType && !props.articleTypeKey) {
      // 这个判断用于进入首次的情况
      setWritingSettingOpen(false);
      return;
    }
    setWritingSettingOpen(
      props.articleId || props.file || props.fileInfo ? false : true
    );
  }, [
    props.articleId,
    props.articleType,
    props.articleTypeKey,
    props.file,
    props.fileInfo,
    id
  ]);

  const appInital = () => {
    setServerInfo({
      token: props.token, // 如果props.token存在则使用，否则使用空字符串
      baseURL: props.url, // 如果props.url存在则使用，否则使用空字符串
      enableMock: props.enableMock
    });
  };
  //应用初始化
  useEffect(() => {
    appInital();
  }, [props.url, props.token, props.enableMock]);

  // 预览模式还是编辑模式
  useEffect(() => {
    if (props?.editorType) {
      setEditorType(props.editorType as any);
      if (props.editorType === EditorType.Preview) {
        message.info("文章生成中，内容尚未完成，仅供预览");
      }
    }
  }, [props?.editorType]);

  useEffect(() => {
    if (!props.articleId && !props.articleType && !props.articleTypeKey) return;
    projectInitialized({
      serverInfo: {
        token: props.token,
        baseURL: props.url,
        enableMock: props.enableMock
      },
      id: props.articleId,
      // 新建的类型
      articleType: props.articleType,
      articleTypeId: props.articleTypeId,
      articleTypeKey: props.articleTypeKey
    });
  }, [
    props.articleId,
    props.articleType,
    props.articleTypeId,
    props.articleTypeKey,
    props.token,
    props.url,
    props.enableMock,
    id
  ]);

  useEffect(() => {
    if (editorType !== EditorType.Preview || writingSettingOpen || !id) return;
    pollingQueryArticleById({
      id,
      config: serverInfo,
      toProjectData,
      setProjectData,
      intervalRef
    });
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [editorType, serverInfo, id, writingSettingOpen]);

  useEffect(() => {
    const handleWrite = async () => {
      if (!projectData.id || !projectData.article_type) {
        message.warning("请先保存写作配置");
        return;
      }
      //拉数据初始化iproject
      const articleInfo = await api_getArticleById({
        data: {
          articleId: projectData.id,
          needSectionContent: true
        },
        config: serverInfo
      });
      const newPd = toProjectData(articleInfo);
      setProjectData((p) => {
        return {
          ...p,
          ...newPd
        };
      });
      // await handleArticleTypeDetaile(projectData.article_type, serverInfo);

      setTimeout(() => {
        projectData.generateType
          ? segmentedWriting({
              outlines: newPd.outlines,
              extraParams: newPd.extraParams,
              coverPage: newPd.coverPage
            })
          : fullWriting(projectData.outputFormat);
      }, 10);
    };
    editorEventBus.on(EDITOR_EVENT_NAME.START_WRITE, handleWrite);
    return () => editorEventBus.off(EDITOR_EVENT_NAME.START_WRITE, handleWrite);
  }, [
    projectData.id,
    projectData.article_type,
    useTemp,
    projectData.generateType,
    projectData.outlines,
    projectData.outputFormat,
    projectData.extraParams,
    baseInfo
  ]);

  useEffect(() => {
    if (projectData.saveArticle === "init") return;
    stopLLMWriting(projectData.id, projectData, mainEditor, serverInfo);
  }, [
    projectData.saveArticle,
    // projectData.outputFormat,
    // projectData.files,
    // projectData.sourceList,
    mainEditor,
    serverInfo
  ]);

  const handleItemOnclicked = (item: any) => () => {
    const { key, path } = item;
    if (key) {
      switch (key) {
        case menuTypes.CREATE_DOC:
          refreshApp();
          navigator(
            `/docWriting/${path}/${`temp_${uuidv4()}`}?articleType=${-3}`
          );
          break;
        case menuTypes.WRITE_INDEX:
        case menuTypes.MY_DOCS:
        case menuTypes.WRITE_SCENE:
        case menuTypes.MATERIAL:
          navigator(`/docWriting/${path}`);
          break;
      }
    }
  };

  const refreshApp = () => {
    if (projectData.id) {
      articleContentSave({
        id: projectData.id,
        baseInfo,
        projectData,
        serverInfo,
        mainEditor
      });
    }
    stopRequest();
    setProjectData({
      title: "未命名文档",
      id: "",
      status: ProjectStatus.Waiting,
      currentModule: ModueEnum.Writing,
      version: [],
      customized_style: {
        enable: false,
        styles: [],
        htmlSchema: "",
        formSchemaMap: {}
      },
      saveArticle: "init",
      form: projectData.form,
      outputFormat: 0
    });
  };

  return {
    Element: (
      <ConfigProvider
        theme={{
          token: {
            borderRadius: 4,
            // fontSize: 12,
            fontFamilyCode: "Helvetica",
            colorText: "#555555"
          },
          components: {
            Typography: {
              titleMarginBottom: "0.25rem",
              titleMarginTop: "0.25rem"
            },
            Menu: {
              collapsedIconSize: 14,
              darkItemBg: "#04336B",
              collapsedWidth: 55
            },
            Button: {
              // contentFontSizeSM: 10,
              defaultHoverBorderColor: "",
              defaultHoverColor: "",
              colorBgBase: "#ffffff"
            }
          }
        }}
      >
        <HeadLessContainer>
          {!writingSettingOpen && (
            <div
              style={{
                height: headerHight
              }}
              className="w-full left-0 absolute top-0 h-11 px-6 pt-4 bg-white"
            >
              <Dropdown
                menu={{
                  items: items.map((i: any) =>
                    Object.assign({}, i, {
                      onClick: handleItemOnclicked(i)
                    })
                  )
                }}
              >
                <a onClick={(e) => e.preventDefault()}>
                  <Space>
                    <img src={HomeIcon} width={20} className="cursor-pointer" />
                    <CaretDownOutlined className="text-[#555]" />
                  </Space>
                </a>
              </Dropdown>
            </div>
          )}

          <WritingConfig />
          <div className="flex w-full h-full pt-[45px]">
            <div className="h-full w-full relative flex-wrap flex">
              {/* 全文生成loading */}
              <ArticleLoading />
              {/* 上传文档写作loading */}
              <UploadLoading downloadFile={props.fileInfo} />
              <div className="flex-col relative  w-full h-full">
                <MainEditor />
                {/* <div className="text-center py-5">
                <Text type="secondary">GienTech_Ril</Text>
              </div> */}
              </div>
            </div>
            <Sidebar />
          </div>
        </HeadLessContainer>
      </ConfigProvider>
    ),
    refreshApp,
    itemOnclicked: handleItemOnclicked
  };
};
