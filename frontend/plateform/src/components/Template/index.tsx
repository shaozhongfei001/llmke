import {
  ConfigProvider,
  Flex,
  Typography,
  Switch,
  Button,
  message,
  Input,
  Tag
} from "antd";
import type { InputRef } from "antd";
import { useMemo, useRef, useState, useEffect } from "react";

import { useStateStore } from "./core/useStateStore";
import { tagPlusStyle, tagInputStyle } from "./core/constants";
import { createBracketHighlightPlugin } from "./components/Editor/createBracketHighlightPlugin";
import { PromptEditor } from "./components/Editor";
import { IusePromptDsigner, ICheckedData } from "./@types";
import useOperator from "./core/useOperator";
import { HighlightLeaf } from "./components/Editor/ui/highlight-leaf";
import MenuCom from "./components/MenuCom";
import TableList from "./components/TableList";
import CueWordModal from "./components/CueWordModal";
import { contextMenuPlugin } from "./components/Editor/contextMenu";
import LableCom from "./components/LableCom";
import {
  createPlateEditor,
  HighlightPlugin,
  Plate
} from "@udecode/plate/react";
import { FontColorPlugin } from "@udecode/plate-font";
import { withPlaceholders } from "./components/Editor/ui/placeholder";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { PlusCircleOutlined, CloseCircleFilled } from "@ant-design/icons";
import { uid } from "uid";
import { DataType } from "./components/TableList/editTable";
import { AIHelperModal } from "./components/AIHelperModal/index";
import SelectBox from "./components/SelectBox";
import { api_optimizePrompt, getLibraryList } from "./server";
import aiphoto from "@/assets/img/aiRobit.png";
import aiphotoDis from "@/assets/img/aiRobitDis.png";
import "./index.less";

const { Text } = Typography;
interface PromptValues {
  WidgetElement: React.ReactNode;
  getPromptTemplate: () => string;
  getContentRule: () => string;
  formSchema: Array<{
    dataIndex?: string;
    title?: string;
    required: boolean;
    type: boolean;
  }>;
  selectTag: string | undefined;
  articleTypeKey: string;
  clearPrompt: () => void;
  setPrompt: (arg: string) => void;
  setConentRule: (arg: string) => void;
  setTableList: (val: Array<any>) => void;
  supportMaterials: boolean;
  setSupportMaterials: (val: boolean) => void;
  supportOutlines: boolean;
  setSupportOutlines: (val: boolean) => void;
  traceToMaterial: boolean;
  setTraceToMaterial: (val: boolean) => void;
  checkedData: ICheckedData[];
  close: () => void;
}

export const usePromptDsigner = ({
  layoutProps = { gap: "10px 10px" },
  token,
  name,
  sceneClass,
  sceneKey,
  sceneClassTag,
  isSegment,
  sensitiveWords,
  isVersion = false
}: IusePromptDsigner): PromptValues => {
  const editorRef = useRef<any>(null);
  const editorContentRef = useRef<any>(null);
  const sseController = useRef(new AbortController());
  const [AIhelperModalOpen, setAIhelperModalOpen] = useState(false);
  const [AIhelperRes, setAIhelperRes] = useState("");
  const [AIhelperLoading, setAIhelperLoading] = useState(false);
  const [serverInfo, setServerInfo] = useState<{
    token: string;
    baseURL: string;
    enableMock?: boolean;
  }>({
    baseURL: "/cecProxy",
    token: token,
    enableMock: true
  });
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<InputRef>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [selectTag, setSelectTag] = useState<string>();
  const [articleTypeKey, setArticleTypeKey] = useState("");
  // ------------敏感词------------
  const [checkedData, setCheckedData] = useState<ICheckedData[]>([]);
  const [sensitiveWordsOption, setSensitiveWordsOption] = useState<any[]>([]);

  const {
    plateValue,
    contentValue,
    setPlateValue,
    restList,
    setRestList,
    tableList,
    setTableList,
    isModalOpen,
    setIsModalOpen,
    supportMaterials,
    setSupportMaterials,
    supportOutlines,
    setSupportOutlines,
    traceToMaterial,
    setTraceToMaterial,
    close
  } = useStateStore();
  const plugins: any = {
    plugins: [
      createBracketHighlightPlugin,
      contextMenuPlugin,
      FontColorPlugin,
      HighlightPlugin
    ],
    override: {
      components: withPlaceholders({
        [HighlightPlugin.key]: HighlightLeaf
      })
    }
  };
  const editor = useMemo(() => {
    return createPlateEditor({
      id: "1",
      ...plugins,
      value: plateValue
    });
  }, []);

  useEffect(() => {
    fetchList(); //获取敏感词列表
  }, []);

  const fetchList = async () => {
    try {
      // setTableLoading(true);
      const param: any = {
        pageNo: 1,
        pageSize: 999
      };
      const res = await getLibraryList(param);

      // setTableLoading(false);
      if (res) {
        const { records, total } = res;
        const _records = (records || []).map((item: any) => {
          return {
            id: item.id,
            name: item.name
          };
        });
        setSensitiveWordsOption([..._records]);
      }
    } catch (e) {
      // setTableLoading(false);
    }
  };

  const editorContent = useMemo(() => {
    return createPlateEditor({
      id: "2",
      ...plugins,
      value: contentValue
    });
  }, []);

  const { handlerEvent, serialize } = useOperator({
    restList,
    setRestList,
    setIsModalOpen,
    tableList,
    setTableList,
    editor
  });
  const clearPlateValue = () => {
    if (!editor) return;

    editor.delete({
      at: {
        anchor: editor.start([]),
        focus: editor.end([])
      }
    });
  };

  const handleAdd = () => {
    const newData: DataType = {
      key: uid(),
      dataIndex: "",
      title: "",
      required: false,
      type: "string"
    };
    setTableList([...tableList, newData]);
  };

  const getPromptTemplate = () => {
    if (!editor) return "";

    return serialize(editor.children);
  };

  const getContentRule = () => {
    if (!editorContent) return "";
    return serialize(editorContent.children);
  };

  // AI 帮写
  const handleAIHelper = async () => {
    if (!name) {
      message.info("请先输入场景名称");
      return;
    }
    setAIhelperModalOpen(true);
    const promptTemplate = getPromptTemplate();
    const list = tableList.map((table) => {
      const { title, dataIndex, type } = table;
      return {
        key: dataIndex,
        name: title,
        type
      };
    });
    let re = "";
    setAIhelperLoading(true);
    await api_optimizePrompt({
      config: serverInfo,
      data: {
        signal: sseController.current.signal,
        params: {
          title: name,
          prompt: promptTemplate,
          schemeParams: list
        },
        onmessage: async ({ data }) => {
          const curRes = JSON.parse(data);
          if (curRes.status == 1) {
            re += curRes.reply.content;
            setAIhelperRes(re);
          }
          if (curRes.status == 2) {
            setAIhelperLoading(false);
          }
        },
        onClose: () => console.log("++++++"),
        onerror: (err) => console.log("optimize----->", err)
      }
    });
  };

  const AIhelperModalClose = () => {
    setAIhelperModalOpen(false);
    sseController.current.abort();
  };
  const setPrompt = (str: string) => {
    if (!editor) return;
    editor.tf.setValue([
      {
        type: "p",
        children: [{ text: str }]
      }
    ]);
  };

  const setConentRule = (str: string) => {
    if (!editorContent) return;
    editorContent.tf.setValue([
      {
        type: "p",
        children: [{ text: str }]
      }
    ]);
  };

  // 场景分类tag
  useEffect(() => {
    if (sceneClass) {
      setTags([...sceneClass]);
    }
    if (sceneClassTag) {
      setSelectTag(sceneClassTag);
    } else if (sceneClass) {
      setSelectTag(sceneClass[0]);
    }
    if (sceneKey) {
      setArticleTypeKey(sceneKey);
    }
  }, [sceneClass, sceneKey, sceneClassTag]);
  const handleClose = (removedTag: string) => {
    const newTags = tags.filter((tag) => tag !== removedTag);
    setTags(newTags);
    if (removedTag === selectTag) {
      const index = tags.indexOf(removedTag);
      const selTag = index > 0 ? newTags[index - 1] : newTags[0];
      setSelectTag(selTag);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleInputConfirm = () => {
    if (inputValue && !tags.includes(inputValue)) {
      tags.splice(tags.length - 1, 0, inputValue);
      setTags([...tags]);
      setSelectTag(inputValue);
    }
    setInputValue("");
  };

  const handleSelectTag = (tag: string) => {
    setSelectTag(tag);
  };

  return {
    WidgetElement: (
      <ConfigProvider
        theme={{
          components: {
            Layout: {
              siderBg: "#fff",
              bodyBg: "transparent"
            },
            Modal: {
              titleFontSize: 16
            },
            Popover: {
              titleMinWidth: 50
            },
            List: {
              footerBg: "#fff",
              headerBg: "#fff",
              contentWidth: 250,
              itemPaddingSM: "5px 5px"
            },
            Table: {
              headerBg: "#FAFAFA"
            }
          }
        }}
      >
        <div className="mb-[28px] scene-class">
          <LableCom title="场景分类" />
          <Flex gap="4px 0" wrap>
            {tags.map<React.ReactNode>((tag, index) => {
              const tagElem = (
                <Tag
                  key={tag}
                  bordered={false}
                  closable={
                    index > sceneClass.length - 2 && index !== tags.length - 1
                  }
                  className={`${tag == selectTag ? "ant-tag-checkable-checked" : "ant-tag-uncheck"} text-[14px] h-[32px] leading-[32px] ${isVersion ? "opacity-80 !cursor-default" : ""}`}
                  onClose={() => handleClose(tag)}
                  onClick={() => (!isVersion ? handleSelectTag(tag) : null)}
                  closeIcon={<CloseCircleFilled />}
                >
                  {tag}
                </Tag>
              );
              return tagElem;
            })}
            {!isVersion ? (
              <Input
                ref={inputRef}
                type="text"
                placeholder="自定义输入"
                style={tagInputStyle}
                value={inputValue}
                onChange={handleInputChange}
                onBlur={handleInputConfirm}
                onPressEnter={handleInputConfirm}
              />
            ) : null}
          </Flex>
        </div>
        {isSegment ? (
          <DndProvider backend={HTML5Backend}>
            <Plate editor={editor}>
              <Flex {...layoutProps}>
                <div
                  style={{
                    width: "100%",
                    borderRadius: "4px",
                    marginBottom: "28px"
                  }}
                >
                  <div
                    id="plateBox"
                    style={{ position: "relative", borderRadius: "4px" }}
                  >
                    <div className="w-full flex flex-row justify-between items-center">
                      <LableCom
                        title="系统提示词"
                        popContent={
                          <Text>
                            <span>提示词用于对 AI 的回复做出一系</span>
                            <br />
                            <span>列指令和约束。可插入表单变量，</span>
                            <br />
                            <span>{"例如 {{ input }}。这段提示词不会"}</span>
                            <br />
                            <span>被最终用户所看到。</span>
                          </Text>
                        }
                      />
                      <Button
                        type="text"
                        className="text-[#055AFF] text-[14px] px-[0px] flex flex-row justify-between items-center mb-2"
                        onClick={handleAIHelper}
                        icon={
                          <img
                            className="mr-[-8px]"
                            src={!name ? aiphotoDis : aiphoto}
                            width={20}
                            height={20}
                          />
                        }
                        disabled={!name || isVersion}
                      >
                        AI帮写
                      </Button>
                    </div>

                    <PromptEditor
                      disabled={isVersion}
                      ref={editorRef}
                      handlerEvent={handlerEvent}
                      placeholder="请输入系统提示词"
                    />
                  </div>
                </div>
              </Flex>
            </Plate>
          </DndProvider>
        ) : (
          <DndProvider backend={HTML5Backend}>
            <Plate editor={editor}>
              <Flex {...layoutProps}>
                <div
                  style={{
                    width: "100%",
                    borderRadius: "4px",
                    marginBottom: "28px"
                  }}
                >
                  <div
                    id="plateBox"
                    style={{ position: "relative", borderRadius: "4px" }}
                  >
                    <div className="w-full flex flex-row justify-between items-center">
                      <LableCom
                        title="系统提示词"
                        popContent={
                          <Text>
                            <span>提示词用于对 AI 的回复做出一系</span>
                            <br />
                            <span>列指令和约束。可插入表单变量，</span>
                            <br />
                            <span>{"例如 {{ input }}。这段提示词不会"}</span>
                            <br />
                            <span>被最终用户所看到。</span>
                          </Text>
                        }
                      />
                      <Button
                        type="text"
                        className="text-[#055AFF] text-[14px] px-[0px] flex flex-row justify-between items-center mb-2"
                        onClick={handleAIHelper}
                        icon={
                          <img
                            className="mr-[-8px]"
                            src={!name ? aiphotoDis : aiphoto}
                            width={20}
                            height={20}
                          />
                        }
                        disabled={!name || isVersion}
                      >
                        AI帮写
                      </Button>
                    </div>

                    <PromptEditor
                      disabled={isVersion}
                      ref={editorRef}
                      handlerEvent={handlerEvent}
                      placeholder="示例：帮我写一篇邮件，发送人是{{from}}，接收人是{{to}}，发件人线下地址是{{address}}。邮箱主要目的是{{destination}}"
                    />
                    <MenuCom
                      allList={tableList
                        .filter(
                          (item) =>
                            item.dataIndex !== undefined &&
                            item.dataIndex !== null &&
                            item.dataIndex !== ""
                        )
                        .map((item) => item.dataIndex)}
                      editorRef={editorRef}
                    />
                  </div>
                </div>
                <CueWordModal
                  isModalOpen={isModalOpen}
                  setIsModalOpen={setIsModalOpen}
                  modalList={restList}
                  handlerEvent={handlerEvent}
                />
              </Flex>
            </Plate>
          </DndProvider>
        )}
        <div className="relative">
          {isVersion ? (
            <div className="absolute top-6 bottom-0 left-0 right-0 bg-white opacity-40 z-10"></div>
          ) : null}
          <DndProvider backend={HTML5Backend}>
            <Plate editor={editorContent}>
              <Flex {...layoutProps}>
                <LableCom
                  title="内容规范"
                  required={false}
                  popContent={
                    <Text>
                      <span>可针对场景特点，输入对模型生成内容的规范要求</span>
                      <br />
                      <span>{"例如："}</span>
                      <br />
                      <span>
                        -
                        引用上级等单位文件时，应按照“先引文件标题后引发文字号”的格式，如:《关于xxx的批复》(国资产权〔2023〕545
                        号)
                      </span>
                      <br />
                      <span>- 同一篇公文中，简称应当一致</span>
                    </Text>
                  }
                />
                <PromptEditor
                  ref={editorContentRef}
                  handlerEvent={handlerEvent}
                />
              </Flex>
            </Plate>
          </DndProvider>
        </div>
        <div className="w-full mt-[28px]">
          <div className="w-full flex flex-row justify-between">
            <LableCom title="参数列表" />
            <Button
              disabled={isVersion}
              type="text"
              className="text-[#055AFF] text-sm px-[0px]"
              onClick={handleAdd}
              icon={<PlusCircleOutlined />}
            >
              添加
            </Button>
          </div>

          <TableList
            isVersion={isVersion}
            tableList={tableList}
            setTableList={setTableList}
            supportOutlines={supportOutlines}
          />
        </div>
        <Flex>
          {!isSegment && (
            <>
              <div className="flex flex-row mt-4 mr-10">
                <label className=" text-sm mr-3">支持上传素材</label>
                <Switch
                  disabled={isVersion}
                  value={supportMaterials}
                  onChange={setSupportMaterials}
                />
              </div>
              <div className="flex flex-row mt-4 mr-10">
                <label className=" text-sm mr-3">支持大纲写作</label>
                <Switch
                  disabled={isVersion}
                  value={supportOutlines}
                  onChange={setSupportOutlines}
                />
              </div>
            </>
          )}
          <div className="flex flex-row mt-3 mr-10">
            <label className=" text-sm mr-3">支持文章溯源</label>
            <Switch
              disabled={isVersion}
              value={traceToMaterial}
              onChange={setTraceToMaterial}
            />
          </div>
        </Flex>
        <div className="mt-4">
          <SelectBox
            title="选择敏感词库"
            options={sensitiveWordsOption}
            isVersion={isVersion}
            sensitiveWords={sensitiveWords}
            checkedData={checkedData}
            setCheckedData={setCheckedData}
          ></SelectBox>
        </div>
        <div className="mt-4">
          <LableCom
            title="场景KEY"
            required={false}
            popContent={
              <Text>
                <span>场景唯一标识，供OpenAPI使用</span>
              </Text>
            }
          />
          <Input
            disabled={!!sceneKey || isVersion}
            value={articleTypeKey}
            onChange={(val) => {
              setArticleTypeKey(val.target.value);
            }}
          />
        </div>

        <AIHelperModal
          open={AIhelperModalOpen}
          setAIhelperModalOpen={setAIhelperModalOpen}
          AIhelperRes={AIhelperRes}
          setNewPrompt={setPrompt}
          handleAIHelper={handleAIHelper}
          AIhelperLoading={AIhelperLoading}
          handlerEvent={handlerEvent}
          AIhelperModalClose={AIhelperModalClose}
        />
      </ConfigProvider>
    ),
    getPromptTemplate,
    getContentRule,
    selectTag,
    articleTypeKey,
    formSchema: tableList,
    clearPrompt: clearPlateValue,
    setPrompt,
    setConentRule,
    setTableList,
    setSupportMaterials,
    supportMaterials,
    supportOutlines,
    setSupportOutlines,
    traceToMaterial,
    setTraceToMaterial,
    checkedData,
    close
  };
};
