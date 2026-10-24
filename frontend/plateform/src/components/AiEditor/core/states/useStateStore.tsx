import React, {
  createContext,
  useContext,
  useState,
  useMemo,
  useRef
} from "react";

import {
  EditorStatus,
  EditorType,
  IModule,
  IModulesResult,
  IProject,
  ModueEnum,
  ModuleStatus,
  ProjectStatus
} from "../../@types/sys";
import { PlateEditor } from "@udecode/plate/react";
import { EditorManager } from "../../@types/sys";
import { uid } from "uid";
import WriteBlue from "@/components/AiEditor/assets/icon/writeBlue.svg";
import Review from "@/components/AiEditor/assets/icon/review.svg";
import Material from "@/components/AiEditor/assets/icon/material.svg";
import { Flex, Form } from "antd";
import { defaultStyle } from "../../components/MainEditor/default_style";
// 定义状态类
// 创建 Context
export interface IState {
  // id: string;
  //编辑器实例
  mainEditor: React.MutableRefObject<PlateEditor | undefined>;

  modules: IModule[];
  setModules: React.Dispatch<React.SetStateAction<IModule[]>>;

  modulesResult: IModulesResult;
  setModulesResult: React.Dispatch<React.SetStateAction<IModulesResult>>;

  projectData: IProject;
  setProjectData: React.Dispatch<React.SetStateAction<IProject>>;
  // editorData: any;
  // setEditorData: React.Dispatch<React.SetStateAction<any>>;
  // selectedData: any;
  // setSelectedData: React.Dispatch<React.SetStateAction<any>>;
  // currentModule: ModueEnum | undefined;
  // setCurrentModule: React.Dispatch<React.SetStateAction<ModueEnum | undefined>>;
  serverInfo: { token: string; baseURL: string; enableMock?: boolean };
  setServerInfo: React.Dispatch<
    React.SetStateAction<{
      token: string;
      baseURL: string;
      enableMock?: boolean;
    }>
  >;
  editorManager: EditorManager;
  setEditorManager: React.Dispatch<React.SetStateAction<EditorManager>>;
  sseController: React.MutableRefObject<AbortController>;
  useTemp: boolean;
  setUseTemp: React.Dispatch<React.SetStateAction<boolean>>;
  displayOriginTemp: boolean;
  setDisplayOriginTemp: React.Dispatch<React.SetStateAction<boolean>>;
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  writingSettingOpen: boolean;
  setWritingSettingOpen: React.Dispatch<React.SetStateAction<boolean>>;
  exportHover: boolean;
  setExportHover: React.Dispatch<React.SetStateAction<boolean>>;
  baseInfo: { [key: string]: any };
  setBaseInfo: React.Dispatch<React.SetStateAction<{ [key: string]: any }>>;
  reqSchedule: {
    total: number;
    cur: number;
  };
  setReqSchedule: React.Dispatch<
    React.SetStateAction<{
      total: number;
      cur: number;
    }>
  >;
  // 文章预览模式
  editorType: EditorType;
  setEditorType: React.Dispatch<React.SetStateAction<EditorType>>;
  // setArticleValue: React.Dispatch<React.SetStateAction<any>>;
  // articleValue: any;
}
const NlpWriterContext = createContext<IState | undefined>(undefined);

const AiWriterProvider: React.FC<any> = ({ children, name }) => {
  //如果不需要同级互传的设计可以把这些值都移动到core代码
  const mainEditor = useRef<PlateEditor>();
  const [modulesResult, setModulesResult] = useState<IModulesResult>({
    [ModueEnum.Writing]: "",
    //[ModueEnum.Polish]: '',
    [ModueEnum.Review]: "",
    [ModueEnum.Material]: ""
  });

  // 使用模板时展示模板本身还是文章本身
  const [displayOriginTemp, setDisplayOriginTemp] = useState(true);
  // 是否使用格式模板
  const [useTemp, setUseTemp] = useState<boolean>(true);
  // 侧边栏是否打开
  const [open, setOpen] = useState<boolean>(false);
  const [writingSettingOpen, setWritingSettingOpen] = useState<boolean>(false);
  const [editorManager, setEditorManager] = useState<EditorManager>({
    id: uid(32),
    status: EditorStatus.Waiting,
    parsed_data: [
      {
        id: "1",
        type: "p",
        children: [{ text: "" }]
      }
    ],
    version: undefined,
    styles: defaultStyle
  });
  const [projectData, setProjectData] = useState<IProject>({
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
    form: Form.useForm()[0],
    outputFormat: 0,
    total: 0
  });

  const [serverInfo, setServerInfo] = useState<{
    token: string;
    baseURL: string;
    enableMock?: boolean;
  }>({
    baseURL: "/cecProxy",
    token: "",
    enableMock: false
  });

  const sseController = useRef(new AbortController());
  const [modules, setModules] = useState<IModule[]>([
    {
      name: "",
      value: ModueEnum.Writing,
      uiSchema: [],
      formData: {},
      status: ModuleStatus.Waiting,
      icon: (
        <Flex vertical gap={5} className="w-full" justify="center">
          <span>
            <img
              src={WriteBlue}
              width={24}
              height={24}
              className="cursor-pointer"
            />
          </span>
          <span className="text-[#2A2A2A] font-bold">写作</span>
        </Flex>
      )
    },
    {
      name: "",
      value: ModueEnum.Review,
      uiSchema: [],
      formData: {},
      icon: (
        <Flex vertical gap={5} className="w-full" justify="center">
          <span>
            <img
              src={Review}
              width={24}
              height={24}
              className="cursor-pointer"
            />
          </span>
          <span className="text-[14px]">审核</span>
        </Flex>
      )
    },
    {
      name: "",
      value: ModueEnum.Material,
      uiSchema: [],
      formData: {},
      icon: (
        <Flex vertical gap={5} className="w-full" justify="center">
          <span>
            <img
              src={Material}
              width={24}
              height={24}
              className="cursor-pointer"
            />
          </span>
          <span className="text-[14px]">素材</span>
        </Flex>
      )
    }
  ]);

  // 分段生成进度
  const [reqSchedule, setReqSchedule] = useState<{
    total: number;
    cur: number;
  }>({
    total: 0,
    cur: 0
  });

  // 文章修改导出hover提示
  const [exportHover, setExportHover] = useState(false);

  // 改变文章内容时保存的基本信息
  const [baseInfo, setBaseInfo] = useState({});

  // 编辑器是否是预览模式
  const [editorType, setEditorType] = useState(EditorType.Edit);

  const providerValue = useMemo(
    () => ({
      mainEditor,
      projectData,
      setProjectData,
      editorManager,
      setEditorManager,
      modules,
      setModules,
      serverInfo,
      setServerInfo,
      modulesResult,
      setModulesResult,
      sseController,
      useTemp,
      setUseTemp,
      displayOriginTemp,
      setDisplayOriginTemp,
      open,
      setOpen,
      writingSettingOpen,
      setWritingSettingOpen,
      reqSchedule,
      setReqSchedule,
      exportHover,
      setExportHover,
      baseInfo,
      setBaseInfo,
      editorType,
      setEditorType
    }),
    [
      exportHover,
      projectData,
      mainEditor.current,
      modules,
      serverInfo,
      editorManager,
      modulesResult,
      useTemp,
      displayOriginTemp,
      open,
      writingSettingOpen,
      reqSchedule,
      baseInfo,
      editorType
    ]
  );

  return (
    <NlpWriterContext.Provider value={providerValue}>
      {children}
    </NlpWriterContext.Provider>
  );
};

const useStateStore = () => {
  const context = useContext(NlpWriterContext);
  if (!context) {
    console.error("useNlpWriter must be used within a AiWriterProvider");
    throw new Error("useNlpWriter must be used within a AiWriterProvider");
  }

  return context;
};

export { AiWriterProvider, useStateStore };
