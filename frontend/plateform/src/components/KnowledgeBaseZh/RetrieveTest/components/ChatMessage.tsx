import React, { useEffect, useRef, useState, useMemo, act } from "react";
import { ConfigProvider, Drawer, Tabs } from "antd";
import { RobotOutlined, CodeOutlined, ApiOutlined } from "@ant-design/icons";
import { createEditor, Descendant, leaf, Element as SlateElement } from "slate";
import { Slate, Editable, withReact } from "slate-react";
import { deserializeMarkdown } from "./converters/deserializers";
import { renderElement, renderLeaf } from "./richElements";
import { Modal } from "antd";
import {
  dealMinioUrl,
  FILEIMG,
  FileModalSize,
  getFileHost,
  getFileName,
  getFilePath,
  getFileType,
  getInitialZoom,
  getMarkExcludeType,
  getNameBySource,
  isImage,
  TempBaseUrl,
  useAppPassport
} from "@root/src/core/helps";
import { FileItem } from "@root/src/components/FileItem";
import { Code, Settings, Zap, ChevronDown, ChevronUp } from "lucide-react";
import { DrawerContent } from "@root/src/components/AiChat/components/ChatDisplayer/components/DrawerContent";
import { GientechStreamReader } from "@root/src/core/components/StreamReader";

interface ChatMessageProps {
  parentContainerRef: any;
  type: "user" | "ai";
  time: string;
  content: any;
  hasLLMConfig?: boolean;
  retrievedChunks?: Array<{ [key: string]: any }>;
  prompt?: string;
  configInfo?: {
    textChunks: number;
    topP: number;
    topN: number;
    denseWeight: number;
    enableKG: boolean;
    enableRerank: boolean;
    model: string;
    temperature?: number;
    diversity?: number;
    maxTokens?: number;
    recallModel: string;
    llmModel: string;
    respTime?: number;
    tokens?: number;
    search_type?: string | string[];
    search_policy?: string;
  };
  streaming?: boolean;
  isLatest?: boolean;
  finished?: boolean;
}

// 扩展富文本元素类型
type CustomText = {
  text: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  code?: boolean;
};

interface BaseElement {
  type: string;
  children: (CustomText | CustomElement)[];
  url?: string;
  align?: "left" | "center" | "right";
}

interface ParagraphElement extends BaseElement {
  type: "paragraph";
}

interface HeadingElement extends BaseElement {
  type: "heading-one" | "heading-two";
}

interface ListElement extends BaseElement {
  type: "bulleted-list" | "numbered-list";
}

interface ListItemElement extends BaseElement {
  type: "list-item";
}

interface TableElement extends BaseElement {
  type: "table";
}

interface TableRowElement extends BaseElement {
  type: "table-row";
}

interface TableCellElement extends BaseElement {
  type: "table-cell";
}

interface ImageElement extends BaseElement {
  type: "image";
  url: string;
}

type CustomElement =
  | ParagraphElement
  | HeadingElement
  | ListElement
  | ListItemElement
  | TableElement
  | TableRowElement
  | TableCellElement
  | ImageElement;

// 检索策略映射
const searchPolicyMap: Record<string, string> = {
  "1": "混合检索",
  "2": "全文检索",
  "3": "语义检索",
  混合检索: "混合检索",
  全文检索: "全文检索",
  语义检索: "语义检索"
};

interface ChunkCardProps {
  chunk: any;
  index: number;
  editor: any;
  customRenderElement: any;
  customRenderLeaf: any;
  deserializeMarkdown: (md: string) => any;
  TempBaseUrl: string;
  isImage: (type: string) => boolean;
  getType: (source: string) => string;
  getName: (source: string) => string;
  messagesEndRef: React.RefObject<HTMLDivElement>;
}

// 深比较函数
function deepEqual(a: any, b: any) {
  return JSON.stringify(a) === JSON.stringify(b);
}

// 自定义useDeepCompareMemo
function useDeepCompareMemo<T>(factory: () => T, deps: any[]): T {
  const ref = useRef<{ deps: any[]; value: T }>();
  if (!ref.current || !deepEqual(ref.current.deps, deps)) {
    ref.current = { deps, value: factory() };
  }
  return ref.current.value;
}

let registerTimer: any = null;

export function ChatMessage({
  type,
  time,
  content,
  hasLLMConfig = true,
  retrievedChunks = [],
  prompt,
  configInfo,
  parentContainerRef
}: ChatMessageProps) {
  const [open, setOpen] = useState(false);
  const [drawerContent, setDrawerContent] = useState<{
    file_source: string;
    contents: any[];
    curMark: string;
    file_type: string;
    title: string;
    pdfPages: number;
  } | null>(null);
  useEffect(() => {
    console.log("retrievedChunks", retrievedChunks);
  }, [retrievedChunks]);
  const [slateContent, setSlateContent] = useState<Descendant[]>(() =>
    deserializeMarkdown(content)
  );
  const editor = useRef(withReact(createEditor()));
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [showViewer, setShowViewer] = useState(false);
  const [activeTabKey, setActiveTabKey] = useState("1");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const callContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeTabKey !== "3") return;
    registerTimer = setInterval(() => {
      if (!callContainerRef.current) return;

      registerTimer && clearInterval(registerTimer);
      callContainerRef.current.addEventListener("wheel", handleWheel);
    }, 100);

    const handleWheel = (e: any) => {
      const { scrollTop, scrollHeight, clientHeight }: any =
        callContainerRef.current;
      if (
        (scrollTop <= 0 && e.deltaY < 0) ||
        (scrollTop + clientHeight >= scrollHeight && e.deltaY > 0)
      ) {
        const pContainer = parentContainerRef.current;
        if (pContainer) {
          e.preventDefault();
          pContainer.scrollTop -= e.deltaY;
        }
      }
    };

    return () => {
      callContainerRef.current &&
        callContainerRef.current.removeEventListener("wheel", handleWheel);
      registerTimer && clearInterval(registerTimer);
    };
  }, [activeTabKey]);

  useEffect(() => {
    setSlateContent(
      deserializeMarkdown(typeof content === "string" ? content : "")
    );
  }, [content]);

  // 生成与 retrievedChunks 数量一致的 editor 实例数组
  const editors = useMemo(
    () => (retrievedChunks || []).map(() => withReact(createEditor())),
    [retrievedChunks?.length]
  );

  // 格式化检索块为字符串
  const formattedChunks = retrievedChunks
    .map((chunk, index) => `[${index + 1}] ${chunk.content}`)
    .join("\n\n");

  // leaf/attributes 兼容新版 retrive-tag 回调
  const handleRetriveTagClick = (leaf: any, attributes: any) => {
    // 你可以根据 leaf.text 或 leaf.id 做业务处理
    // 这里假设 leaf.text 是 order_num
    const match = retrievedChunks.find((chunk) => {
      return String(chunk.order_num) === String(leaf.id);
    });

    if (match && match.metadata) {
      const { metadata, parsedFilePath } = match;
      if (!metadata) return;
      const { source } = metadata;
      const fileParts = source.split(".");
      const label = fileParts.slice(0, -1).join(".") || "Unknown Label";
      const file_type = fileParts[fileParts.length - 1] || "Unknown Type";
      setDrawerContent({
        file_source: getMarkExcludeType(file_type)
          ? `${metadata.source}`
          : parsedFilePath,
        contents: [{ mark: "1", metadata }],
        curMark: "1",
        file_type,
        title: label,
        pdfPages: match.pdfPages
      });
      setOpen(true);
    }
    // 你可以在这里暴露更多自定义逻辑
    // 比如弹窗、跳转、通知父组件等
    // console.log('retrive tag click:', leaf, attributes, match);
  };

  const handleClose = () => {
    setShowViewer(false);
    setPdfUrl(null);
  };

  // 高阶函数传递回调
  const customRenderElement = (props: any) =>
    renderElement({ ...props, onRetriveTagClick: handleRetriveTagClick });

  // 高阶函数传递回调给 renderLeaf
  const customRenderLeaf = (props: any) =>
    renderLeaf({ ...props, onRetriveTagClick: handleRetriveTagClick });

  // 解析 search_type 为数组
  let searchTypes: string[] = [];
  if (Array.isArray(configInfo?.search_type)) {
    searchTypes = configInfo.search_type;
  } else if (typeof configInfo?.search_type === "string") {
    try {
      searchTypes = JSON.parse(configInfo.search_type);
      if (!Array.isArray(searchTypes)) {
        searchTypes = configInfo.search_type
          .split(",")
          .map((s: string) => s.trim());
      }
    } catch {
      searchTypes = configInfo.search_type
        .split(",")
        .map((s: string) => s.trim());
    }
  }

  if (type === "user") {
    return (
      <div className="flex items-start mb-6 animate-fadeIn w-full text-wrap">
        <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-400 to-blue-500 flex items-center justify-center mr-3 shadow-sm">
          <span className="text-white text-sm">用</span>
        </div>
        <div className="flex-1">
          <div className="flex-col">
            <div className="text-xs text-gray-400 mb-1">{time}</div>
            <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-4 inline-block max-w-[80%] shadow-sm">
              <span className="text-gray-700">{content}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const getType = (source: string) => {
    const arr = source.split(".");
    return arr[arr.length - 1];
  };

  const sourceFile = useDeepCompareMemo(() => {
    if (retrievedChunks && Array.isArray(retrievedChunks)) {
      const seen = new Set<string>();
      return retrievedChunks.filter((chunk) => {
        const source = chunk?.metadata?.source;
        if (!source || seen.has(source)) return false;
        seen.add(source);
        return true;
      });
    }
    return [];
  }, [retrievedChunks]);

  // 单独的ChunkCard子组件，管理自己的hooks
  function ChunkCard({
    chunk,
    index,
    editor,
    customRenderElement,
    customRenderLeaf,
    deserializeMarkdown,
    TempBaseUrl,
    isImage,
    getType,
    getName,
    messagesEndRef
  }: ChunkCardProps) {
    const [expanded, setExpanded] = useState(false);
    const contentRef = useRef<HTMLDivElement>(null);
    const [showExpand, setShowExpand] = useState(false);
    useEffect(() => {
      console.log("chunkchunkchunkchunk", chunk);

      const timer = setTimeout(() => {
        if (contentRef.current) {
          setShowExpand(contentRef.current.scrollHeight > 60);
        }
      }, 0);
      return () => clearTimeout(timer);
    }, [chunk.page_content, chunk.type, expanded]);
    return (
      <div
        key={index}
        className="bg-gradient-to-r w-full from-gray-50 to-white rounded-lg p-4 border border-gray-100 shadow-sm transition-all hover:shadow-md"
      >
        <div className="flex-col items-center justify-between mb-3">
          <div className="text-sm font-medium text-gray-700 flex items-center">
            <span className="w-2 h-2 rounded-full bg-blue-400 mr-2"></span>
            召回片段 {index + 1}
          </div>
        </div>
        <div className="flex pb-2  flex-col items-start pt-4 text-xs space-y-2">
          <div className="flex items-center mb-2 mt-2">
            <span className="inline-block w-1 h-4 bg-blue-500 rounded-sm mr-2"></span>
            <span className="text-gray-900 text-[14px] font-semibold tracking-wide  opacity-75">
              chunk信息
            </span>
          </div>
          {/* 分数标签组 */}
          <div className="w-auto overflow-x-auto">
            <table className=" border-collapse text-xs text-gray-700">
              <tbody>
                <tr className="text-gray-300">
                  <td className="border-b border-gray-200 px-3 py-1 whitespace-nowrap text-center">
                    召回位置
                  </td>
                  <td className="border-b border-gray-200 px-3 py-1 whitespace-nowrap text-center">
                    召回得分
                  </td>
                  <td className="border-b border-gray-200 px-3 py-1 whitespace-nowrap text-center">
                    重排位置
                  </td>
                  <td className="border-b border-gray-200 px-3 py-1 whitespace-nowrap text-center">
                    重排得分
                  </td>
                  <td className="border-b border-gray-200 px-3 py-1 whitespace-nowrap text-center">
                    索引来源
                  </td>
                </tr>
                <tr className="text-gray-800 font-semibold">
                  <td className="border-r border-gray-200 px-3 py-1 whitespace-nowrap text-center">
                    {chunk.rrf_score_rank ? Number(chunk.rrf_score_rank) : "-"}
                  </td>
                  <td className="border-r border-gray-200 px-3 py-1 whitespace-nowrap text-center">
                    {chunk.rrf_score ? Number(chunk.rrf_score).toFixed(3) : "-"}
                  </td>
                  <td className="border-r border-gray-200 px-3 py-1 whitespace-nowrap text-center">
                    {chunk.rerank_score_rank
                      ? Number(chunk.rerank_score_rank)
                      : "-"}
                  </td>
                  <td className="border-r border-gray-200 px-3 py-1 px-3 py-1 whitespace-nowrap text-center">
                    {chunk.score ? Number(chunk.score).toFixed(3) : "-"}
                  </td>
                  <td className="px-3 py-1 whitespace-nowrap text-center">
                    {chunk.metadata.search_type.map(
                      (type: string, idx: number) => (
                        <span
                          key={type + idx}
                          className="block border border-gray-200 text-gray-700 px-2 py-0.5 text-xs"
                        >
                          {type}
                        </span>
                      )
                    )}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        {/* 内容区域按类型渲染 */}
        <div className="text-gray-800 leading-relaxed">
          <div className="flex items-center mb-2 mt-2">
            <span className="inline-block w-1 h-4 bg-green-500 rounded-sm mr-2"></span>
            <span className="text-gray-900 text-[14px] font-semibold tracking-wide  opacity-75">
              chunk内容
            </span>
          </div>
          <div
            ref={contentRef}
            style={{
              maxHeight: expanded
                ? "none"
                : chunk.type === "image"
                ? ""
                : "60px",
              overflow: expanded ? "visible" : "hidden",
              position: "relative",
              transition: "max-height 0.3s"
            }}
          >
            {chunk.type === "image" ? (
              (() => {
                const imagePath = chunk.metadata?.image_path;
                return imagePath ? (
                  <img
                    src={imagePath}
                    alt={`图片片段${index + 1}`}
                    style={{
                      maxWidth: 240,
                      maxHeight: 180,
                      borderRadius: 6,
                      border: "1px solid #eee",
                      cursor: "pointer"
                    }}
                    onClick={() => window.open(imagePath, "_blank")}
                  />
                ) : (
                  <span style={{ color: "#aaa" }}>无图片</span>
                );
              })()
            ) : chunk.type === "table" ? (
              <div style={{ minWidth: 400, overflowX: "auto" }}>
                <Slate
                  editor={editor}
                  initialValue={deserializeMarkdown(chunk.page_content || "")}
                  key={JSON.stringify(
                    deserializeMarkdown(chunk.page_content || "")
                  )}
                  onChange={() => {}}
                >
                  <Editable
                    readOnly
                    renderElement={customRenderElement}
                    renderLeaf={customRenderLeaf}
                    className="min-h-[30px] p-2 rounded border border-gray-50 bg-white"
                  />
                </Slate>
              </div>
            ) : (
              <Slate
                editor={editor}
                initialValue={deserializeMarkdown(chunk.page_content || "")}
                key={JSON.stringify(
                  deserializeMarkdown(chunk.page_content || "")
                )}
                onChange={() => {}}
              >
                <Editable
                  readOnly
                  renderElement={customRenderElement}
                  renderLeaf={customRenderLeaf}
                  className="min-h-[30px] p-2 rounded border border-gray-50 bg-white"
                />
              </Slate>
            )}
          </div>
          {showExpand && (
            <div
              className="text-blue-500 flex items-center justify-center w-full cursor-pointer text-xs mt-1 select-none"
              onClick={() => setExpanded((v) => !v)}
            >
              <div className="flex items-center pt-1 justify-center gap-1">
                {expanded ? (
                  <ChevronUp size={14} className="mr-0.5" />
                ) : (
                  <ChevronDown size={14} className="mr-0.5" />
                )}
                {expanded ? "收起" : "展开全部"}
              </div>
            </div>
          )}
        </div>
        <div className="flex-col items-center py-2 justify-between">
          <div className="flex  pb-2 items-center mb-2 mt-2">
            <span className="inline-block w-1 h-4 bg-gray-500 rounded-sm mr-2"></span>
            <span className="text-gray-900 text-[14px] font-semibold tracking-wide  opacity-75">
              文件来源
            </span>
          </div>
          <div className="text-xs text-gray-500">
            <FileItem
              fileList={[
                {
                  convertedFilePath: chunk.parsedFilePath,
                  filePath: `${getFileHost(chunk.parsedFilePath || "")}${
                    chunk.metadata?.source
                  }`,
                  type: isImage(getType(chunk.metadata.source))
                    ? "image"
                    : getType(chunk.metadata.source),
                  name: getNameBySource(chunk.metadata.source),
                  pdfPages: chunk.pdfPages || 0
                }
              ]}
              idx={index}
              type="view"
            />
          </div>
          {/* 滚动锚点 */}
          <div ref={messagesEndRef} />
        </div>
      </div>
    );
  }
  const { getToken } = useAppPassport();
  const curData = useMemo(() => {
    const token = getToken();
    if (content && token) {
      console.log("content999", content);
      const filePath = dealMinioUrl(getFilePath(content));
      return {
        filePath,
        fileName: getFileName(content),
        fileType: getFileType(content, filePath),
        totalPages: content.pdfPages || 0,
        token
      };
    } else {
      return {};
    }
  }, [content]);

  const renderFileCom = useMemo(() => {
    if (!curData.filePath) return <></>;
    return (
      <GientechStreamReader
        convertedFilePath={curData.filePath}
        fileName={curData.fileName}
        fileType={curData.fileType}
        initialPage={1}
        totalPages={curData.totalPages}
        authorization={curData.token}
        streamApiUrl="/proxy/index/knowledgeBase/file/stream"
        eventsEmit={(name) => {
          switch (name) {
            case "viewer:close":
              handleClose();
              break;
          }
        }}
        tools={{
          close: true
        }}
      />
    );
  }, [curData]);

  return (
    <>
      <div className="flex items-start mb-6 animate-fadeIn w-full text-wrap">
        <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-400 to-purple-500 flex items-center justify-center mr-3 shadow-sm">
          <span className="text-white w-10 h-10 flex items-center justify-center text-sm">
            AI
          </span>
        </div>
        <div className="flex-1 w-[calc(100%-40px)]">
          <div className="flex flex-col w-full relative">
            <div className="text-xs text-gray-400 mb-1">{time}</div>
            <div className="bg-white rounded-lg shadow-md w-full overflow-hidden border border-gray-100">
              <Tabs
                activeKey={activeTabKey}
                onChange={setActiveTabKey}
                className="[&_.ant-tabs-nav]:mb-0 [&_.ant-tabs-nav]:px-4 [&_.ant-tabs-nav]:bg-gradient-to-r [&_.ant-tabs-nav]:from-gray-50 [&_.ant-tabs-nav]:to-white [&_.ant-tabs-nav]:border-b [&_.ant-tabs-nav]:border-gray-100
                        [&_.ant-tabs-tab]:relative [&_.ant-tabs-tab]:transition-all [&_.ant-tabs-tab]:duration-300 [&_.ant-tabs-tab]:mx-3 [&_.ant-tabs-tab]:py-3 [&_.ant-tabs-tab]:px-0 [&_.ant-tabs-tab]:opacity-75
                        [&_.ant-tabs-tab:hover]:opacity-100 [&_.ant-tabs-tab:hover]:text-blue-500 [&_.ant-tabs-tab:hover]:bg-transparent
                        [&_.ant-tabs-tab-active_.ant-tabs-tab-btn]:text-blue-500 [&_.ant-tabs-tab-active_.ant-tabs-tab-btn]:font-medium
                        [&_.ant-tabs-tab-active]:opacity-100 [&_.ant-tabs-tab-active]:after:content-[''] [&_.ant-tabs-tab-active]:after:absolute [&_.ant-tabs-tab-active]:after:bottom-0 [&_.ant-tabs-tab-active]:after:left-0 [&_.ant-tabs-tab-active]:after:w-full [&_.ant-tabs-tab-active]:after:h-0.5 [&_.ant-tabs-tab-active]:after:bg-blue-500 [&_.ant-tabs-tab-active]:after:rounded-t
                        [&_.ant-tabs-ink-bar]:hidden"
                items={[
                  {
                    key: "1",
                    label: (
                      <span className="px-1 py-1 inline-flex items-center text-sm bg-gray-100 text-gray-700">
                        <RobotOutlined className="mr-1.5 text-gray-500" />
                        <span>语义回答</span>
                      </span>
                    ),
                    children: (
                      <div className="p-4 bg-gradient-to-r from-gray-50 to-white w-full">
                        {hasLLMConfig ? (
                          <>
                            <div className="mb-4 p-3 bg-white rounded-lg border border-gray-100">
                              <div className="text-sm text-gray-600 font-medium mb-3 flex items-center">
                                <span className="w-2 h-2 rounded-full bg-blue-400 mr-2"></span>
                                LLM 配置信息
                              </div>
                              <div className="grid grid-cols-2 gap-3 text-xs text-gray-500">
                                <div className="flex items-center space-x-2">
                                  <span className="w-2 h-2 rounded-full bg-green-400"></span>
                                  <span>
                                    模型：{configInfo?.llmModel || "-"}
                                  </span>
                                </div>

                                <div className="flex items-center space-x-2">
                                  <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                                  <span>
                                    温度：
                                    {configInfo?.temperature?.toFixed(2) || "-"}
                                  </span>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                                  <span>
                                    多样性：
                                    {configInfo?.diversity?.toFixed(2) || "-"}
                                  </span>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <span className="w-2 h-2 rounded-full bg-yellow-400"></span>
                                  <span>
                                    最大令牌：{configInfo?.maxTokens || "-"}
                                  </span>
                                </div>
                              </div>
                            </div>
                            <div className="text-gray-800 w-full leading-relaxed">
                              <Slate
                                editor={editor.current}
                                initialValue={slateContent}
                                key={JSON.stringify(slateContent)}
                                onChange={setSlateContent}
                              >
                                <Editable
                                  readOnly
                                  renderElement={customRenderElement}
                                  renderLeaf={customRenderLeaf}
                                  className="min-h-[50px] w-full p-4 rounded-lg border border-gray-100 bg-white"
                                />
                              </Slate>
                            </div>
                            {!!sourceFile?.length && (
                              <div className="flex-col items-center py-2 justify-between">
                                <div className="text-xs text-gray-500 pt-4 ">
                                  来源文件
                                </div>
                                <div className="text-xs text-gray-500">
                                  <FileItem
                                    fileList={sourceFile.map(
                                      (chunk: any, index: number) => {
                                        console.log("chunkchunk", chunk);

                                        return {
                                          pdfPages: chunk.pdfPages,
                                          convertedFilePath:
                                            chunk.parsedFilePath,
                                          filePath: `${getFileHost(
                                            chunk.parsedFilePath || ""
                                          )}${chunk.metadata?.source}`,
                                          type: isImage(
                                            getType(chunk.metadata.source)
                                          )
                                            ? "image"
                                            : getType(chunk.metadata.source),
                                          name: getNameBySource(
                                            chunk.metadata.source
                                          )
                                        };
                                      }
                                    )}
                                    type="view"
                                    idx={1}
                                    className="flex"
                                  />
                                </div>
                              </div>
                            )}

                            {typeof configInfo?.respTime === "number" &&
                              typeof configInfo?.tokens === "number" && (
                                <div className="flex pt-2 gap-x-5 justify-start text-gray-500 leading-relaxed">
                                  <div>
                                    总耗时：
                                    {(configInfo.respTime / 1000).toFixed(2)}s
                                  </div>
                                  <div>共使用: {configInfo.tokens} tokens</div>
                                </div>
                              )}
                          </>
                        ) : (
                          <div className="flex flex-col items-center justify-center py-8 text-gray-500">
                            <RobotOutlined
                              style={{ fontSize: "48px" }}
                              className="mb-4 text-gray-300"
                            />
                            <p className="text-sm">未配置大语言模型</p>
                            <p className="text-xs mt-2">
                              请在左侧设置面板开启并配置大语言模型
                            </p>
                          </div>
                        )}
                      </div>
                    )
                  },
                  {
                    key: "2",
                    label: (
                      <span
                        className={`px-1 py-1 inline-flex items-center text-sm transition-all ${
                          activeTabKey === "2"
                            ? "font-bold text-black"
                            : "text-gray-700"
                        }`}
                      >
                        <Code
                          size={16}
                          className={`mr-1 ${
                            activeTabKey === "2"
                              ? "text-black"
                              : "text-gray-500"
                          }`}
                        />
                        <span>Prompt</span>
                      </span>
                    ),
                    children: (
                      <div className="p-4">
                        {hasLLMConfig && prompt ? (
                          <div className="bg-gray-50 p-4 rounded-lg border border-gray-100 font-mono text-sm whitespace-pre-wrap leading-relaxed text-gray-700 shadow-inner">
                            {prompt}
                          </div>
                        ) : (
                          <div className="flex flex-col items-center justify-center py-8 text-gray-500">
                            <CodeOutlined
                              style={{ fontSize: "48px" }}
                              className="mb-4 text-gray-300"
                            />
                            <p className="text-sm">未配置 Prompt</p>
                            <p className="text-xs mt-2">
                              当前仅执行向量检索，未使用大语言模型
                            </p>
                          </div>
                        )}
                      </div>
                    )
                  },
                  {
                    key: "3",
                    label: (
                      <span
                        className={`px-1 py-1 inline-flex items-center text-sm transition-all ${
                          activeTabKey === "3"
                            ? "font-bold text-black"
                            : "text-gray-700"
                        }`}
                      >
                        <Zap
                          size={16}
                          className={`mr-1 ${
                            activeTabKey === "3"
                              ? "text-black"
                              : "text-gray-500"
                          }`}
                        />
                        <span className="relative">
                          召回信息
                          {retrievedChunks.length > 0 && (
                            <span className="absolute -top-1 -right-4 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                              {retrievedChunks.length}
                            </span>
                          )}
                        </span>
                      </span>
                    ),
                    children: (
                      <div
                        className="p-4 space-y-4"
                        ref={callContainerRef}
                        style={{ maxHeight: "60vh", overflowY: "auto" }}
                      >
                        {retrievedChunks.length > 0 ? (
                          retrievedChunks.map((chunk, index) => (
                            <ChunkCard
                              key={index}
                              chunk={chunk}
                              index={index}
                              editor={editors[index]}
                              customRenderElement={customRenderElement}
                              customRenderLeaf={customRenderLeaf}
                              deserializeMarkdown={deserializeMarkdown}
                              TempBaseUrl={TempBaseUrl}
                              isImage={isImage}
                              getType={getType}
                              getName={getNameBySource}
                              messagesEndRef={messagesEndRef}
                            />
                          ))
                        ) : (
                          <div className="flex flex-col items-center justify-center py-8 text-gray-400">
                            <ApiOutlined
                              style={{ fontSize: "48px" }}
                              className="mb-4 text-gray-300"
                            />
                            <p className="text-sm">暂无召回信息</p>
                            <p className="text-xs mt-2">
                              当前未检索到任何相关文本片段
                            </p>
                          </div>
                        )}
                      </div>
                    )
                  },
                  {
                    key: "4",
                    label: (
                      <span
                        className={`px-1 py-1 inline-flex items-center text-sm transition-all ${
                          activeTabKey === "4"
                            ? "font-bold text-black"
                            : "text-gray-700"
                        }`}
                      >
                        <Settings
                          size={16}
                          className={`mr-1 ${
                            activeTabKey === "4"
                              ? "text-black"
                              : "text-gray-500"
                          }`}
                        />
                        <span>检索配置</span>
                      </span>
                    ),
                    children: configInfo && (
                      <div className="p-4">
                        <div className="grid grid-cols-2 gap-6">
                          <div className="bg-gradient-to-r from-gray-50 to-white rounded-lg p-4 border border-gray-100">
                            <div className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                              <span className="w-2 h-2 rounded-full bg-blue-400 mr-2"></span>
                              召回配置
                            </div>
                            <div className="space-y-2 text-sm text-gray-600">
                              <div className="flex items-center justify-between p-2 bg-white rounded border border-gray-50">
                                <span>返回文本片数量</span>
                                <span className="font-mono">
                                  {configInfo.textChunks}
                                </span>
                              </div>
                              <div className="flex items-center justify-between p-2 bg-white rounded border border-gray-50">
                                <span>相似度阈值</span>
                                <span className="font-mono">
                                  {configInfo.topP}
                                </span>
                              </div>
                              <div className="flex items-center justify-between p-2 bg-white rounded border border-gray-50">
                                <span>召回数量</span>
                                <span className="font-mono">
                                  {configInfo.topN}
                                </span>
                              </div>
                              <div className="flex items-center justify-between p-2 bg-white rounded border border-gray-50">
                                <span>Dense Weight</span>
                                <span className="font-mono">
                                  {configInfo.denseWeight}
                                </span>
                              </div>
                              <div className="flex items-center justify-between p-2 bg-white rounded border border-gray-50">
                                <span>检索策略</span>
                                <span className="font-mono">
                                  {configInfo?.search_policy
                                    ? searchPolicyMap[
                                        String(configInfo.search_policy)
                                      ] || configInfo.search_policy
                                    : "-"}
                                </span>
                              </div>
                            </div>
                          </div>
                          <div className="bg-gradient-to-r from-gray-50 to-white rounded-lg p-4 border border-gray-100">
                            <div className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                              <span className="w-2 h-2 rounded-full bg-green-400 mr-2"></span>
                              功能开关
                            </div>
                            <div className="space-y-2 text-sm text-gray-600">
                              <div className="flex items-center justify-between p-2 bg-white rounded border border-gray-50">
                                <span>图谱增强</span>
                                <span
                                  className={
                                    configInfo.enableKG
                                      ? "text-green-500"
                                      : "text-gray-500"
                                  }
                                >
                                  {configInfo.enableKG ? "开启" : "关闭"}
                                </span>
                              </div>
                              <div className="flex items-center justify-between p-2 bg-white rounded border border-gray-50">
                                <span>重排模型</span>
                                <span
                                  className={
                                    configInfo.enableRerank
                                      ? "text-green-500"
                                      : "text-gray-500"
                                  }
                                >
                                  {configInfo.enableRerank ? "开启" : "关闭"}
                                </span>
                              </div>
                              <div className="flex items-center justify-between p-2 bg-white rounded border border-gray-50">
                                <span>检索模型</span>
                                <span className="font-mono">
                                  {configInfo.recallModel}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  }
                ]}
              />
            </div>
          </div>
        </div>
      </div>
      <ConfigProvider
        modal={{
          styles: {
            body: {
              padding: 0
            },
            content: {
              padding: 0
            }
          }
        }}
      >
        <Modal
          open={showViewer}
          closable={false}
          footer={null}
          width={FileModalSize.width}
          height={FileModalSize.height}
          destroyOnClose
        >
          {pdfUrl && (
            <div style={{ width: "100%", height: "100%" }}>{renderFileCom}</div>
          )}
        </Modal>
      </ConfigProvider>
      <ConfigProvider
        drawer={{
          styles: {
            body: { padding: 0 },
            header: { display: "none" }
          }
        }}
      >
        <Drawer
          title={
            <div className="flex items-center">
              <img
                src={FILEIMG[drawerContent?.file_type || "doc"]}
                width={18}
                height={18}
                className="mr-[6px]"
              />
              <div>{`${drawerContent?.title}.${drawerContent?.file_type}`}</div>
            </div>
          }
          autoFocus={false}
          onClose={() => setOpen(false)}
          open={open}
          width={600}
          className="overflow-x-hidden"
          destroyOnClose
          afterOpenChange={(open) => {
            if (!open) {
              setDrawerContent(null);
            }
          }}
        >
          <DrawerContent
            content={drawerContent as any}
            onClose={() => setOpen(false)}
          />
        </Drawer>
      </ConfigProvider>
    </>
  );
}

export const Welcome = () => (
  <div
    className="flex flex-col items-center justify-center pb-[20%] text-gray-400 animate-fadeIn"
    style={{ transform: "rotate(180deg)" }}
  >
    <RobotOutlined style={{ fontSize: 48 }} className="mb-4 text-blue-300" />
    <div className="text-lg font-semibold mb-2">Hi，我是检索测试助手</div>
    <div className="text-sm">欢迎体验知识库检索与多模态召回测试</div>
  </div>
);
