import React, { useState, useEffect, useRef } from "react";
import { Form } from "antd";
import { Paperclip } from "lucide-react";
import dayjs from "dayjs";
import { ConfigPanel } from "./components/ConfigPanel";
import { ChatMessage, Welcome } from "./components/ChatMessage";
import { ChatInput } from "./components/ChatInput";
import { HttpClient } from "@/apis/api/http-client";
import { getTokenLocal } from "@/apis/token";
import { uid } from "uid";
import useSystemApi from "@/apis/system";
import "./style.css";
import { getUrlPrefix } from "@root/src/core/helps";

interface Message {
  type: "user" | "ai";
  time: string;
  content: string;
  hasLLMConfig?: boolean;
  retrievedChunks?: Array<{
    content: string;
    similarity: number;
    rerank: number;
    chunk_id: number;
    source: string;
  }>;
  prompt?: string;
  configInfo?: any;
  queryId?: string;
  fullContent?: string;
  finished?: boolean;
  typedLength?: number;
}

interface RetrieveTestProps {
  messages?: Message[];
  onSearch?: (query: string, config: any) => void;
  setKbInfo?: any;
}

interface FilePreview {
  file: File;
  preview?: string;
  type: "image" | "document";
}

export default function RetrieveTest({
  messages: initialMessages,
  onSearch,
  setKbInfo
}: RetrieveTestProps) {
  const [form] = Form.useForm();
  const [enableLLM, setEnableLLM] = useState(false);
  const [settingPanelVisible, setSettingPanelVisible] = useState(true);
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>(
    (initialMessages || [])
      .filter((msg) => typeof msg.content === "string")
      .map((msg) => ({ ...msg, content: msg.content as string }))
  );

  const [sliderValues, setSliderValues] = useState({
    textChunks: 10,
    topP: 0.1,
    topN: 10,
    denseWeight: 0.5,
    temperature: 0.3,
    diversity: 0.8,
    maxTokens: 4096
  });

  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<FilePreview[]>([]);

  // 新增：AI检索接口
  const httpClient = new HttpClient({ baseURL: `${getUrlPrefix()}/qa` });
  httpClient.instance.interceptors.request.use((config: any) => {
    config.headers.Authorization = getTokenLocal();
    return config;
  });

  // 进入组件时生成sessionId
  const sessionIdRef = useRef<string>(uid(32));

  const [aiLoading, setAiLoading] = useState(false);

  // 获取大模型列表
  const [modelOptions, setModelOptions] = useState<
    { label: string; value: string }[]
  >([]);
  // 获取检索召回模型列表
  const [recallModelOptions, setRecallModelOptions] = useState<
    { label: string; value: string }[]
  >([]);

  // 保存当前prompt和configInfo，供流式消息使用
  const currentPromptRef = useRef("");
  const currentConfigInfoRef = useRef<any>({});

  // 检索召回模型
  // useEffect(() => {
  //   const fetchRecallModels = async () => {
  //     const systemApi = useSystemApi({ baseURL: getUrlPrefix() });
  //     try {
  //       const res = await systemApi.getRerankModelInfos();
  //       const list = res?.data || [];
  //       const options = list.map((item: any) => ({
  //         label: item.modelName || item.name,
  //         value: item.modelName || item.name
  //       }));
  //       setRecallModelOptions(options);
  //       if (options.length > 0) {
  //         form.setFieldsValue({ recallModel: options[0].value });
  //       }
  //     } catch (e) {
  //       setRecallModelOptions([]);
  //     }
  //   };
  //   fetchRecallModels();
  // }, []);

  //获取模型列表
  // 1. rerenk模型下拉选项:/index/modelInfo/allPage?pageNum=1&pageSize=9999&status=1&type=3
  // 2. 问答模型下拉选项:/index/modelInfo/allPage?pageNum=1&pageSize=9999&status=1&type=1
  // 2. 规划模型下拉选项:/index/modelInfo/allPage?pageNum=1&pageSize=9999&status=1&type=1
  useEffect(() => {
    const fetchModels = async () => {
      const systemApi = useSystemApi({ baseURL: getUrlPrefix() });
      try {
        const [modelRes, recallModelRes] = await Promise.allSettled([
          systemApi.getAllModelList({
            pageNum: 1,
            pageSize: 9999,
            status: 1,
            type: 1
          }),
          systemApi.getAllModelList({
            pageNum: 1,
            pageSize: 9999,
            status: 1,
            type: 3
          })
        ]);
        if (modelRes.status === "fulfilled" && modelRes.value) {
          const list = modelRes.value.data?.records || [];
          const options = list.map((item: any) => ({
            label: item.modelName,
            value: item.modelName
          }));
          setModelOptions(options);
          if (options.length > 0) {
            form.setFieldsValue({ llmModel: options[0].value });
            form.setFieldsValue({ plan_model_name: options[0].value });
          }
        }

        if (recallModelRes.status === "fulfilled" && recallModelRes.value) {
          const options = (recallModelRes.value?.data?.records || []).map(
            (item: any) => ({
              label: item.modelName || item.name,
              value: item.modelName || item.name
            })
          );
          setRecallModelOptions(options);
          if (options.length > 0) {
            form.setFieldsValue({ recallModel: options[0].value });
          }
        }
        // const res = await systemApi.getAllModelList({
        //   pageNum: 1,
        //   pageSize: 9999,
        //   status: 1
        // });
        // const list = res?.data?.records || [];
        // const options = list.map((item: any) => ({
        //   label: item.modelName,
        //   value: item.modelName
        // }));
        // setModelOptions(options);
        // if (options.length > 0) {
        //   form.setFieldsValue({ llmModel: options[0].value });
        // }
      } catch (e) {
        setModelOptions([]);
      }
    };
    fetchModels();
  }, []);

  // 当接收到新的messages时更新
  useEffect(() => {
    if (initialMessages) {
      setMessages(
        initialMessages.map((msg) => ({
          ...msg,
          content: typeof msg.content === "string" ? msg.content : ""
        }))
      );
    }
  }, [initialMessages]);

  // 初始化表单数据
  useEffect(() => {
    form.setFieldsValue({
      ...sliderValues,
      enableKG: false,
      enableRerank: true,
      recallModel: recallModelOptions[0]?.value,
      llmModel: modelOptions[0]?.value
    });

    // 测试 Markdown 转换
    // console.log('=== 测试 Markdown 转换 ===');
    // console.log('原始 Markdown:');
    // console.log(markdownExample);

    // console.log('\n转换为 Slate:');
    // const slateFromMarkdown = deserializeMarkdown(markdownExample);
    // console.log(JSON.stringify(slateFromMarkdown, null, 2));

    // console.log('\n转换回 Markdown:');
    // console.log(serializeToMarkdown(slateFromMarkdown));
  }, []);

  const handleSliderChange = (
    field: keyof typeof sliderValues,
    value: number
  ) => {
    setSliderValues((prev) => ({ ...prev, [field]: value }));
    form.setFieldsValue({ [field]: value });
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const timeStr = dayjs().format("YYYY/MM/DD HH:mm:ss");

    // 添加用户消息
    const newMessage: Message = {
      type: "user",
      time: timeStr,
      content: String(inputValue)
    };
    setMessages((prev) => [...prev, newMessage]);
    setAiLoading(true);
    setInputValue("");

    // 组装当前prompt和configInfo，保存到ref
    const currentPrompt = form.getFieldValue("prompt") || "";
    const currentConfigInfo = {
      textChunks: sliderValues.textChunks,
      topP: sliderValues.topP,
      topN: sliderValues.topN,
      denseWeight: sliderValues.denseWeight,
      enableKG: form.getFieldValue("enableKG"),
      enableRerank: form.getFieldValue("enableRerank"),
      recallModel: form.getFieldValue("recallModel"),
      llmModel: form.getFieldValue("llmModel"),
      plan_model_name: form.getFieldValue("plan_model_name"),
      temperature: sliderValues.temperature,
      diversity: sliderValues.diversity,
      maxTokens: sliderValues.maxTokens,
      search_policy: form.getFieldValue("search_policy"),
      search_type: form.getFieldValue("search_type")
    };
    currentPromptRef.current = currentPrompt;
    currentConfigInfoRef.current = currentConfigInfo;

    // 组装接口参数
    const params = {
      sessionId: sessionIdRef.current,
      queryId: `query-${uid(32)}`,
      sysType: "RETRIEVE_RECALL_TEST",
      lastDate: new Date().toISOString(),
      audioUrl: "",
      type: "text",
      content: inputValue,
      configId: 0,
      fileUids: [],
      config: JSON.stringify({
        top_k: sliderValues.textChunks,
        enabled_rerank: true,
        knowledge_base_name: setKbInfo?.primitiveName,
        enabled_graph: form.getFieldValue("enableKG"),
        rerank_model_name: form.getFieldValue("recallModel"),
        top_n: sliderValues.topN,
        dense_weight: sliderValues.denseWeight,
        enabled_llm: enableLLM,
        model_name: form.getFieldValue("llmModel"),
        plan_model_name: form.getFieldValue("plan_model_name"),
        temperature: sliderValues.temperature,
        // 接口定义 score_threshold：相似度阈值 top_p：多样性，与前端渲染不一致
        score_threshold: sliderValues.topP,
        top_p: sliderValues.diversity,
        max_tokens: sliderValues.maxTokens,
        system_prompt: form.getFieldValue("prompt") || "",
        search_policy: form.getFieldValue("search_policy")
      })
    };

    // console.log('打印看看',params)
    // fetch + ReadableStream 方式请求 SSE
    try {
      const response = await fetch(
        `${getUrlPrefix()}/qa/ai/retrieveTecallTest`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: getTokenLocal()
          },
          body: JSON.stringify(params)
        }
      );
      if (!response.body) throw new Error("无响应流");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let done = false;
      while (!done) {
        const { value, done: readDone } = await reader.read();
        done = readDone;
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (let line of lines) {
          if (line.startsWith("data:")) {
            try {
              const json = JSON.parse(line.replace("data:", "").trim());
              handleStreamMessage(json);
            } catch (e) {
              console.warn("SSE解析失败", line, e);
            }
          }
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          type: "ai",
          time: dayjs().format("YYYY/MM/DD HH:mm:ss"),
          content: "[AI接口请求失败]",
          hasLLMConfig: enableLLM
        }
      ]);
    } finally {
      setAiLoading(false);
    }

    // ...如需调用父组件onSearch可保留
    if (onSearch) {
      const currentConfig = {
        textChunks: sliderValues.textChunks,
        topP: sliderValues.topP,
        topN: sliderValues.topN,
        denseWeight: sliderValues.denseWeight,
        enableKG: form.getFieldValue("enableKG"),
        enableRerank: form.getFieldValue("enableRerank"),
        model: form.getFieldValue("llmModel"),
        temperature: sliderValues.temperature,
        diversity: sliderValues.diversity,
        maxTokens: sliderValues.maxTokens
      };
      onSearch(inputValue, currentConfig);
    }
  };

  // 流式AI消息拼接
  const handleStreamMessage = (streamMsg: any) => {
    // console.log('收到stream流:', streamMsg);
    setMessages((prev) => {
      //console.log("[流式拼接] prev:", prev, streamMsg);
      const newMessages = [...prev];
      const last = newMessages[newMessages.length - 1];
      const isLastAi =
        last && last.type === "ai" && last.queryId === streamMsg.queryId;

      if (isLastAi) {
        // 拼接 fullContent
        const prevFull =
          typeof last.fullContent === "string" ? last.fullContent : "";
        const curContent = streamMsg.reply.content || "";
        const newFull = prevFull + curContent;
        last.fullContent = newFull;
        last.content = newFull; // 保证每次流拼接都能触发 useEffect，实现滚动跟随
        // 结束标记
        if ("reference" in streamMsg || "docs" in streamMsg) {
          let reference = streamMsg.reference || streamMsg.docs;
          console.log(
            "[流式拼接] reference 原始:",
            reference,
            "类型:",
            typeof reference
          );
          if (typeof reference === "string") {
            try {
              reference = JSON.parse(reference);
              console.log(
                "[流式拼接] reference 解析后:",
                reference,
                "类型:",
                typeof reference
              );
            } catch (e) {
              reference = [];
              console.log("[流式拼接] reference 解析失败:", e);
            }
          } else {
            console.log(
              "[流式拼接] reference 非字符串:",
              reference,
              "类型:",
              typeof reference
            );
          }
          last.retrievedChunks = Array.isArray(reference)
            ? reference.map((doc: any, idx: number) =>
                typeof doc === "string"
                  ? {
                      content: doc,
                      similarity: 0,
                      rerank: idx + 1,
                      chunk_id: idx,
                      source: ""
                    }
                  : doc
              )
            : [];
        }
        // console.log('streamMsg---------', streamMsg.promptContent !==null||streamMsg.promptContent !== undefined && streamMsg.promptContent)
        last.prompt = streamMsg.promptContent;
        if (streamMsg.status === 2) {
          last.finished = true; // 可用于 UI loading
          // 记录总耗时和t
          //
          // console.log("streamMsg---------", streamMsg, streamMsg.tokens);
          if (last.configInfo) {
            last.configInfo.respTime = streamMsg.respTime;
            last.configInfo.tokens = streamMsg.tokens;
          }
        }
        // 保证configInfo和prompt不丢失
        last.configInfo = currentConfigInfoRef.current;

        last.hasLLMConfig = enableLLM;
        // 启动打字机
        if (typeof last.content !== "string") last.content = "";
        if (typeof last.typedLength !== "number")
          last.typedLength = last.content.length;
        if (last.finished || last.typedLength >= last.fullContent.length) {
          last.content = String(last.fullContent);
          return [...prev.slice(0, -1), last];
        }
        last.typedLength += 1;
        last.content = String(last.fullContent.slice(0, last.typedLength));
        setTimeout(() => typeWriterUpdate(streamMsg.queryId), 20);
        // console.log("[setMessages后]", newMessages);
        return [...prev.slice(0, -1), last];
      } else {
        // 新增一条AI消息
        // console.log(
        //   "[流式拼接] last 不存在或不匹配，新增AI消息",
        //   last,
        //   streamMsg
        // );
        let reference = streamMsg.reference || streamMsg.docs;
        if (typeof reference === "string") {
          try {
            reference = JSON.parse(reference);
          } catch (e) {
            reference = [];
          }
        } else {
        }
        const configInfo = { ...currentConfigInfoRef.current };
        console.log("ca,ni,mei", currentConfigInfoRef.current);
        if (streamMsg.status === 2) {
          configInfo.respTime = streamMsg.respTime;
          configInfo.tokens = streamMsg.tokens;
        }
        return [
          ...prev,
          {
            type: "ai",
            time: dayjs(streamMsg.lastDate).format("YYYY/MM/DD HH:mm:ss"),
            content: "",
            fullContent: streamMsg.reply.content || "",
            queryId: streamMsg.queryId,
            finished: streamMsg.status === 2,
            retrievedChunks: Array.isArray(reference)
              ? reference.map((doc: any, idx: number) =>
                  typeof doc === "string"
                    ? {
                        content: doc,
                        similarity: 0,
                        rerank: idx + 1,
                        chunk_id: idx,
                        source: ""
                      }
                    : doc
                )
              : [],
            configInfo,
            prompt: streamMsg.promptContent || currentPromptRef.current,
            typedLength: 0,
            hasLLMConfig: enableLLM
          }
        ];
      }
    });
  };

  const handleUpload = async (files: FileList) => {
    const newFiles = Array.from(files).map((file) => ({
      file,
      type: file.type.startsWith("image/")
        ? ("image" as const)
        : ("document" as const),
      preview: file.type.startsWith("image/")
        ? URL.createObjectURL(file)
        : undefined
    }));

    setUploadedFiles((prev) => [...prev, ...newFiles]);
  };

  const handleRemoveFile = (index: number) => {
    setUploadedFiles((prev) => {
      const newFiles = [...prev];
      if (newFiles[index].preview) {
        URL.revokeObjectURL(newFiles[index].preview);
      }
      newFiles.splice(index, 1);
      return newFiles;
    });
  };

  const handleVoice = () => {
    console.log("Voice input triggered");
  };

  // 处理拖拽事件
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleUpload(files);
    }
  };

  // 打字机动画函数，实现简单的逐字显示效果
  function typeWriterUpdate(queryId: string) {
    setMessages((prev) => {
      const newMessages = [...prev];
      if (newMessages.length === 0) return newMessages;
      const last = { ...newMessages[newMessages.length - 1] };
      if (
        last &&
        last.type === "ai" &&
        last.queryId === queryId &&
        typeof last.fullContent === "string"
      ) {
        if (typeof last.content !== "string") last.content = "";
        if (typeof last.typedLength !== "number")
          last.typedLength = last.content.length;
        if (last.finished || last.typedLength >= last.fullContent.length) {
          last.content = String(last.fullContent);
          newMessages[newMessages.length - 1] = last;
          return newMessages;
        }
        last.typedLength += 1;
        last.content = String(last.fullContent.slice(0, last.typedLength));
        newMessages[newMessages.length - 1] = last;
        setTimeout(() => {
          typeWriterUpdate(queryId);
          // 打字机动画期间直接滚动到底部
        }, 20);
      }
      return newMessages;
    });
  }

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleWheel = (e: any) => {
      // 检测当前滚动区域
      const isChildScrollable = Array.from(e.composedPath()).some((el: any) => {
        return (
          el !== container &&
          el.scrollHeight > el.clientHeight &&
          window.getComputedStyle(el).overflowY === "auto"
        );
      });

      // 当操作子元素滚动时跳过处理
      if (isChildScrollable) return;

      // 仅处理父容器滚动
      e.preventDefault();
      if (!isChildScrollable) {
        container.scrollTop -= e.deltaY;
      }
    };

    container.addEventListener("wheel", handleWheel);
    return () => container.removeEventListener("wheel", handleWheel);
  }, []);

  return (
    <div className="w-full h-[calc(100vh-245px)] bg-background rounded-md">
      <div className="w-full h-full relative flex">
        <ConfigPanel
          form={form}
          visible={settingPanelVisible}
          enableLLM={enableLLM}
          sliderValues={sliderValues}
          onSliderChange={handleSliderChange}
          onEnableLLMChange={setEnableLLM}
          onVisibleChange={setSettingPanelVisible}
          modelOptions={modelOptions}
          recallModelOptions={recallModelOptions}
        />

        <div className=" w-8/12 h-full bg-white relative flex flex-col">
          {/* 拖拽提示层 - 固定定位 */}
          {isDragging && (
            <div className="fixed inset-0 bg-blue-50 bg-opacity-30 backdrop-blur-sm z-50 flex items-center justify-center pointer-events-none">
              <div className="bg-white/80 backdrop-blur-sm p-6 rounded-xl shadow-lg flex flex-col items-center">
                <Paperclip className="w-8 h-8 text-blue-500 mb-3" />
                <span className="text-blue-600 font-medium">
                  将文件拖放到这里
                </span>
                <span className="text-sm text-gray-500 mt-2">
                  支持 PDF、Word、图片等文件
                </span>
              </div>
            </div>
          )}

          <div
            className=" w-full  overflow-y-auto h-full py-6 px-6 relative flex flex-col hide-scrollBar"
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            ref={messagesContainerRef}
            style={{ direction: "ltr", transform: "rotate(180deg)" }}
          >
            <div
              style={{
                flexGrow: 1,
                flexShrink: 1,
                flex: 1
              }}
            ></div>
            {messages.length === 0 ? (
              <Welcome />
            ) : (
              <div
                className="w-full relative"
                style={{ transform: "rotate(180deg)" }}
              >
                {messages.map((message, index) => (
                  <ChatMessage
                    key={index}
                    type={message.type}
                    time={message.time}
                    content={message.content}
                    hasLLMConfig={message.hasLLMConfig}
                    retrievedChunks={message.retrievedChunks}
                    prompt={message.prompt}
                    configInfo={message.configInfo}
                    streaming={true}
                    isLatest={index === messages.length - 1}
                    parentContainerRef={messagesContainerRef}
                  />
                ))}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSend}
            onUpload={handleUpload}
            onVoice={handleVoice}
            onClear={() => setInputValue("")}
            uploadedFiles={uploadedFiles}
            onRemoveFile={handleRemoveFile}
          />
        </div>
      </div>
    </div>
  );
}
