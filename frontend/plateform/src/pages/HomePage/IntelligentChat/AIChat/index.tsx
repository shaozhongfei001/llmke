import GientechChat from "@gientech/modual/chat";
import {
  dealMinioUrl,
  downloadByStream,
  FILEIMG,
  fileViewTypes,
  getFileName,
  getMarkExcludeType,
  getNameBySource,
  getUrlPrefix,
  handleDownLoad,
  TempBaseUrl,
  useAppPassport
} from "@root/src/core/helps";
import { useEffect, useMemo, useState } from "react";
import { ConfigProvider, Drawer, message } from "antd";
import { DeleteModal } from "./components/DeleteModal";
import SdqaDrawer from "@root/src/components/SdqaDrawer";
import { RenameModal } from "./components/RenameModal";
import { DrawerContent } from "./components/DrawerContent";
import DrawerVideo from "./components/DrawerVideo";
import DrawerPreview from "./components/DrawerPreview";
import { defaultStyles } from "./config";
import DrawerDatabase from "./components/DrawerDatabase";
import { api_getFileStatusByUid } from "@root/src/components/AiInputer/common/services/servers";
import DrawerGraphPreview from "./components/DrawerGraphPreview";
import { registerPreviewViewer } from "@mxmweb/nodegraph";
import "@gientech/modual/style.css";
import { Brain, Globe, Paperclip, Search } from "lucide-react";
import { ReactComponent as Net } from "./assets/net.svg";
import { ReactComponent as Mind } from "./assets/mind.svg";
import {
  installGlobalModeFetchPatch,
  readGlobalMode,
  setGlobalMode
} from "./graphGlobal";
const showVideo = import.meta.env.VITE_CONFIG_SHOW_VIDEO === "true";

registerPreviewViewer();
const mockSenderConfig = {
  // 文件大小限制（字节数），例如：100MB = 100 * 1024 * 1024
  upload_size_limit: 50 * 1024 * 1024,

  // 文件数量限制
  upload_number_limit: 10,

  // 允许的文件类型列表
  // 支持扩展名（如 'pdf', 'docx', 'jpg'）
  // 支持 MIME 类型（如 'image/*', 'application/pdf'）
  upload_file_type_limit: [
    "ppt",
    "pptx",
    "doc",
    "docx",
    "xlsx",
    "csv",
    "pdf",
    "text",
    "html",
    "jpg",
    "jpeg",
    "md",
    "json",
    "png"
  ],

  // 自定义错误提示信息（可选）
  upload_limit_message: "文件不符合上传要求，请检查后重试",
  actions: [
    {
      name: "upload",
      icon: <Paperclip color="#4E5969" size={20} />,
      // badgeCount: 0,
      tip: `最多上传10个文件（每个最大 50 MB），支持单次或批量上传ppt(x)、doc(x)、xlsx、csv、pdf、text、html、jp(e)g、md、json、png等文件`
    }
  ],
  switchs: [
    ...(showVideo
      ? [
          {
            name: "qaChannel",
            label: "问答渠道",
            type: "select" as const,
            defaultValue: 1,
            enabled: true,
            options: [
              { label: "默认", value: 1 },
              { label: "文档", value: 2 },
              { label: "视频", value: 3 }
            ]
          }
        ]
      : []),
    {
      label: "联网搜索",
      name: "netSearch",
      type: "checkbox",
      defaultValue: false,
      enabled: true,
      icon: <Net className="w-[16px] h-[16px] " />
    },
    {
      // R13：普通检索 / 全局(GraphRAG) 切换。
      // type 必须是 switch，库内部才会用 defaultValue 初始化开关状态
      // 并通过 onSenderConfigChange / sender:configChange 回传 all[name]。
      label: "全局(GraphRAG)",
      name: "globalMode",
      type: "switch",
      defaultValue: readGlobalMode(),
      enabled: true,
      icon: <Globe className="w-[16px] h-[16px]" />
    },
    {
      label: "推理思考",
      name: "reasoning",
      type: "checkbox",
      defaultValue: false,
      enabled: true,
      icon: <Mind className="w-[16px] h-[16px]" />
    }
  ]
};

const ChatPage = () => {
  const { getToken } = useAppPassport();
  const token: any = getToken();
  const AI_CHAT = useMemo(() => {
    return GientechChat();
  }, []);
  // R13：普通检索 / 全局(GraphRAG)，状态持久化在 localStorage（r13_global_mode）
  const [globalMode, setGlobalModeState] = useState<boolean>(() =>
    readGlobalMode()
  );
  // 注意：该函数会被 renderAIChat 的 useMemo 闭包捕获，不要在这里读 globalMode
  // 做「值相同就跳过」的判断，否则会读到首帧旧值导致状态不再更新。
  const handleGlobalModeChange = (enabled: boolean) => {
    setGlobalMode(enabled);
    setGlobalModeState(enabled);
  };

  /**
   * R14-D-FIX-03：「全局(GraphRAG)」开关兜底。
   *
   * 事实：`@gientech/modual` 的 sender 开关点击后只做内部转发
   * （控制台 `sender:configChange {all:…} core内部转发`），**不回调宿主**
   * `eventsEmit`；而 `chat.d.ts` 的 `GientechChatAdopterProps` 里也没有
   * `onSenderConfigChange`（那条通道是死代码）。结果：按钮视觉变蓝，
   * 但 `r13_global_mode` 恒为 0，`globalMode` 从不注入请求体 → 全局检索点了等于没点。
   *
   * 兜底做法：监听该按钮点击，等库把激活态渲染出来后**读真实渲染态**
   * （激活时 inline style 的 border-color/color 为 rgb(78,110,242)），
   * 再写回同一份状态。
   *
   * TODO(R14-D-FIX-03)：这是**临时方案**，属技术债。一旦 @gientech/modual 在
   * sender 开关变化时真的回调宿主 `eventsEmit("sender:configChange", …)`（或
   * `GientechChatAdopterProps` 正式提供 onSenderConfigChange），**请整体删除本 useEffect**，
   * 只保留原有的回调通道。判定依赖按钮 inline style 颜色（rgb(78,110,242)），
   * 库若改主题色/改用 class，本兜底会同时失效——这是它必须被替换的原因。
   */
  useEffect(() => {
    const LABEL = "全局(GraphRAG)";
    const ACTIVE = "78,110,242";
    const findBtn = () =>
      Array.from(document.querySelectorAll("button")).find(
        b => (b.textContent || "").trim() === LABEL
      ) as HTMLButtonElement | undefined;
    const onClick = (ev: MouseEvent) => {
      const el = ev.target as HTMLElement | null;
      const btn = el?.closest?.("button") as HTMLButtonElement | null;
      if (!btn || (btn.textContent || "").trim() !== LABEL) return;
      window.setTimeout(() => {
        const cur = findBtn();
        if (!cur) return;
        const style = (cur.getAttribute("style") || "").replace(/\s/g, "");
        handleGlobalModeChange(style.includes(ACTIVE));
      }, 80);
    };
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, []);
  const [isRenameModalOpen, setisRenameModalOpen] = useState(false);
  const [isRemoveModalOpen, setisRemoveModalOpen] = useState(false);
  const [curEditData, setCurEditData] = useState<any>(null);
  const [sdDrawerOpen, setSdDrawerOpen] = useState(false);
  const [drawerData, setDrawerData]: any = useState({});
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState<
    | {
        title: "";
        file_type: "";
        metadata: { offset: [] };
      }
    | any
  >(null);
  const [drawerType, setDrawerType] = useState<string>("mark");
  const [curFileInfo, setCurFileInfo] = useState({
    url: "",
    parse_url: "",
    file_type: "",
    file_name: ""
  });
  const editDialog = (data: any) => {
    const newLabel = data.new_name;
    const oldLabel = curEditData.data.label;
    if (newLabel && newLabel !== oldLabel) {
      curEditData
        .async_renameConversation(newLabel)
        .then(() => {
          curEditData.fn_renameItemInList(newLabel);
          setisRenameModalOpen(false);
        })
        .catch(() => {
          // 重命名失败
        });
    } else {
      setisRenameModalOpen(false);
    }
  };

  const editRemove = (data: any) => {
    curEditData
      .async_deleteConversation()
      .then(() => {
        curEditData.fn_removeItemFromList();
        setisRemoveModalOpen(false);
      })
      .catch(() => {
        // 删除失败
      });
  };

  useEffect(() => {
    console.log("contentcontent", content);
  }, [content]);

  // R13：聊天页挂载期间才劫持 fetch，离开页面立即还原，避免影响其它请求
  useEffect(() => {
    setGlobalMode(readGlobalMode());
    const release = installGlobalModeFetchPatch();
    return release;
  }, []);

  const handleSd = (type: string, data?: any) => {
    switch (type) {
      case "click:indexes":
        setDrawerType("mark");
        setOpen(true);
        setContent(data);
        break;
      case "open":
        setDrawerData(data);
        setSdDrawerOpen(true);
        break;
      case "close":
        setSdDrawerOpen(false);
        break;
    }
  };

  const handleEvent = (type: string, data?: any) => {
    console.log(type, data);

    switch (type) {
      case "close_remove":
        setisRemoveModalOpen(false);
        break;
      case "close_rename":
        setisRenameModalOpen(false);
        break;
      case "ok_rename":
        editDialog(data);
        break;
      case "ok_remove":
        editRemove(data);
        break;
    }
  };

  const referenceFile_question_upload = async (data: any) => {
    if (fileViewTypes.includes(data.file_type)) {
      setCurFileInfo({
        ...data,
        parse_url:
          data.url || data.metadata.source
            ? `${TempBaseUrl}${data.metadata.source}`
            : data.url
      });

      setDrawerType("preview");
      setOpen(true);
      return;
    }
    try {
      const res: any[] = await api_getFileStatusByUid({
        data: { uids: data.uid },
        config: {
          url: getUrlPrefix(),
          token,
          enableMock: false
        }
      });
      if (res?.length) {
        const d = res[0];
        setCurFileInfo({
          ...data,
          parse_url: d.convertedFilePath
        });

        setDrawerType("preview");
        setOpen(true);
      }
    } catch (error) {}
  };

  const renderAIChat = useMemo(() => {
    return (
      <AI_CHAT
        token={token}
        url={"/proxy"}
        CustomComponents={{
          LogoBox: null
        }}
        senderConfig={mockSenderConfig}
        styles={defaultStyles}
        onSenderConfigChange={(cfg: any) => {
          // R13：输入区开关变化（含 globalMode）
          if (cfg?.name === "globalMode") {
            handleGlobalModeChange(!!cfg.checked);
          }
        }}
        eventsEmit={(event: any, data: any) => {
          console.log("事件触发:", event, data);
          switch (event) {
            // R13：发送器开关汇总（{all:{globalMode:boolean,...}}），与
            // onSenderConfigChange 双通道兜底，二者都只是写同一份状态
            case "sender:configChange":
              if (typeof data?.all?.globalMode === "boolean") {
                handleGlobalModeChange(data.all.globalMode);
              }
              break;
            // 点击title
            case "knowledge_referenceFile_title:click":
              const d3 = data?.data;
              if (data?.data?.file_type == "video") {
                const curTag: any = (d3?.tags || []).find(
                  (item: any) => item.id === d3.order_num
                );
                setCurFileInfo(curTag.metadata);
                setDrawerType("video");
                setOpen(true);
                return;
              }
              if (!data?.data?.metadata?.source) {
                if (d3?.tags?.length) {
                  let curTag = d3.tags.find((item: any) => {
                    return item.id === d3.order_num;
                  });
                  if (!curTag) {
                    curTag = d3.tags[0];
                  }
                  d3.metadata = curTag.metadata;
                }
              }
              setCurFileInfo(d3);
              setDrawerType("preview");
              setOpen(true);

              break;
            case "graph_reference:click":
              if (!data) return;
              setDrawerType("graphPreview");
              setCurFileInfo(data);
              setOpen(true);
              break;
            case "conversations:rename_icon_clicked":
              setCurEditData(data);
              setisRenameModalOpen(true);
              break;
            case "conversations:delete_icon_clicked":
              setCurEditData(data);
              setisRemoveModalOpen(true);
              break;
            case "referenceFile_download":
              const d1 = data.data;
              downloadByStream({
                filePath: `${TempBaseUrl}${d1.metadata.source}`,
                fileName: getFileName(d1)
              });

              break;
            // case "referenceFile_question":
            //   referenceFile_question_upload(data.data);
            //   break;
            case "referenceFile_view":
              const d2 = data.data;
              setCurFileInfo({
                ...d2,
                url: fileViewTypes.includes(d2.file_type)
                  ? d2.metadata.source
                    ? `${TempBaseUrl}${d2.metadata.source}`
                    : d2.convertedFilePath || d2.parsedFilePath
                  : d2.convertedFilePath || d2.parsedFilePath
              });

              setDrawerType("preview");
              setOpen(true);
              break;
            case "reference_file:click":
              if (data.file_type === "image") return;

              if (!data.parse_url) {
                if (!data.uid) {
                  if (data.references) return;
                  return message.warning("文件还未解析完成,请稍后预览");
                }
                referenceFile_question_upload(data);
                return;
              }
              setCurFileInfo({
                ...data,
                file_type: data.type,
                file_name: data.file
              });
              setDrawerType("preview");
              setOpen(true);
              break;
            // 知识库溯源单文档问答
            case "referenceFile_filechat":
              const d = data.data;
              if (d.tags?.length) {
                d.metadata = d.tags[0].metadata;
              }
              if (d.isUploadFile) {
                setDrawerData({
                  ...d,
                  file_source: d.parsedFilePath,
                  file_type: d.type
                });
              } else {
                setDrawerData({ ...d, file_source: d.parsedFilePath });
              }
              setDrawerType("preview");
              setSdDrawerOpen(true);
              break;
            case "database_referenceFile_title:click":
              setDrawerType("database");
              setCurFileInfo(data.data);
              setOpen(true);
              break;
            // 点击溯源
            case "action_retrive_tag":
            case "retrive_tag:click":
              if (data?.graph?.id) {
                //图谱溯源
                setDrawerType("graphPreview");
                setCurFileInfo({ ...data.graph, traceNode: data.traceNode });
                setOpen(true);
                return;
              }
              if (!data?.tagInfo && !data?.file && !data?.referenceDoc) return;
              const curFile = data?.referenceDoc || data?.file || data?.tagInfo;
              const { pdfPages, parsedFilePath, order_num, metadata, tags } =
                curFile;
              if (curFile.type == "video") {
                setCurFileInfo({
                  ...metadata,
                  displayType: "retrive"
                });
                setDrawerType("video");
                setOpen(true);
                return;
              }

              const id = curFile.id || order_num || "Unknown ID";
              // 解析 source 字段
              const sourceParts = metadata.source.split("/");
              const fileName = sourceParts[sourceParts.length - 1] || "";
              const fileParts = fileName.split(".");
              const label = fileParts.slice(0, -1).join(".") || "Unknown Label";
              const file_type =
                fileParts[fileParts.length - 1] || "Unknown Type";

              setContent({
                id,
                title: label,
                file_name: fileName,
                file_type: file_type,
                file_source: getMarkExcludeType(file_type)
                  ? `${TempBaseUrl}${metadata.source}`
                  : parsedFilePath,
                metadata: metadata,
                pdfPages: pdfPages
              });
              setDrawerType("mark");
              setOpen(true);
              break;
          }

          // 监听所有交互事件
        }}
        disclaimer="内容由AI生成，仅供参考，不代表本公司观点。"
      />
    );
  }, [token]);

  return (
    <>
      <div className="h-full relative">
        {/* R13：全局模式可见标识（叠加在回答区上方，不改动回答渲染逻辑） */}
        {globalMode && (
          <div
            className="pointer-events-none absolute left-1/2 top-2 z-20 -translate-x-1/2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-600 shadow-sm"
            title="当前使用 GraphRAG 全局模式：回答由社区摘要 map-reduce 聚合生成，引用为社区→来源文件级"
          >
            GraphRAG 全局
          </div>
        )}
        <div className="h-full">{renderAIChat}</div>
      </div>
      <RenameModal
        isModalOpen={isRenameModalOpen}
        handleOk={handleEvent}
        handleCancel={() => handleEvent("close_rename")}
        data={curEditData?.data || {}}
      />
      <DeleteModal
        isModalOpen={isRemoveModalOpen}
        handleOk={handleEvent}
        handleCancel={() => handleEvent("close_remove")}
        data={curEditData?.data || {}}
      />
      <SdqaDrawer
        open={sdDrawerOpen}
        title={
          getNameBySource(drawerData?.metadata?.source) || drawerData.file_name
        }
        close={() => handleSd("close")}
        content={drawerData}
        setContent={setDrawerData}
        is_download={true}
      />
      <ConfigProvider
        drawer={{
          styles: {
            body: { padding: 0 },
            header: { display: "none" }
          }
        }}
      >
        <Drawer
          autoFocus={false}
          onClose={() => setOpen(false)}
          open={open}
          width={drawerType === "graphPreview" ? "100%" : 720}
          className="overflow-x-hidden"
          destroyOnClose
          afterOpenChange={(open) => {
            if (!open) {
              setContent(null);
            }
          }}
        >
          {drawerType === "graphPreview" && (
            <DrawerGraphPreview
              curFileInfo={curFileInfo as any}
              onClose={() => setOpen(false)}
            />
          )}
          {drawerType === "mark" && (
            <DrawerContent
              content={content as any}
              onClose={() => setOpen(false)}
            />
          )}
          {drawerType === "preview" && (
            <DrawerPreview
              curFileInfo={curFileInfo}
              onClose={() => setOpen(false)}
            />
          )}
          {drawerType === "database" && (
            <DrawerDatabase
              curFileInfo={curFileInfo}
              onClose={() => setOpen(false)}
            />
          )}
          {drawerType == "video" && (
            <DrawerVideo
              curFileInfo={curFileInfo}
              onClose={() => setOpen(false)}
            />
          )}
        </Drawer>
      </ConfigProvider>
    </>
  );
};

export default ChatPage;
