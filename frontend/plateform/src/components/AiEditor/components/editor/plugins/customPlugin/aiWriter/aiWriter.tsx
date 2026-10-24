import {
  createPlateEditor,
  createPlatePlugin,
  Plate,
  PlatePlugin
} from "@udecode/plate/react";
import { useStateStore } from "../../../../../core/states/useStateStore";
import { useRef, useEffect, useMemo, useState } from "react";
import { getNodes } from "@udecode/plate";
import { Range, Path, Editor } from "slate";
import {
  Select,
  Input,
  Button,
  Menu,
  Modal,
  Space,
  message,
  Flex,
  Form
} from "antd";
import {
  mainEditorDefaultComponents,
  mainEditorDefaultPlugins
} from "../../mainEditorSet";
import { PolishEditor } from "../../polishEditor";
import { injectStyle } from "../../../../MainEditor";
import {
  api_articleFeedback,
  api_optimize
} from "../../../../../core/services/servers";
import Generating from "@/components/AiEditor/assets/img/generating.gif";
import Good from "@/components/AiEditor/assets/icon/good.svg";
import Bad from "@/components/AiEditor/assets/icon/bad.svg";
import Copy from "@/components/AiEditor/assets/icon/copy.svg";
import PolishIcon from "@/components/AiEditor/assets/icon/polish.svg";
import ExtendIcon from "@/components/AiEditor/assets/icon/extend.svg";
import ShortIcon from "@/components/AiEditor/assets/icon/short.svg";
import AiPhoto from "@/assets/img/aiRobit.png";
import { ExclamationCircleOutlined, SendOutlined } from "@ant-design/icons";
import copy from "copy-to-clipboard";
import "./style.css";

enum AiwriterState {
  Wait,
  Process,
  Done,
  Error
}

const AiWriterType = {
  polish: 1,
  extend: 2,
  short: 3
};

export enum LLMStatus {
  Normal = 1,
  Success,
  Error
}

const getAllText = (htmlString) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlString, "text/html");
  const walk = (node, texts) => {
    if (node.nodeType === 3) {
      texts.push(node.data);
    }
    node = node.firstChild;
    while (node) {
      walk(node, texts);
      node = node.nextSibling;
    }
  };

  const texts = [];
  walk(doc.body, texts);
  return texts.join(" ");
};

const getNodePathByType = (type, editor) => {
  const [nodeEntry] = editor.nodes({
    at: [], // 遍历整个文档树
    match: (n: any) => n.type === type // 查找匹配的节点
  });
  const [_, path] = nodeEntry || [];
  if (nodeEntry) return path;
};

export const AiWriterInput = (props) => {
  const { attributes, children, element, editor, nodeProps } = props;
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { editorManager, mainEditor, serverInfo, sseController } =
    useStateStore();
  const [state, setState] = useState<AiwriterState>(AiwriterState.Wait);
  const [data, setData] = useState();
  // 生成时保存参数，用于重新生成
  const [genParams, setGenParams] = useState({ method: "", value: "" });
  const inputRef = useRef<HTMLDivElement>(null);
  const parsedData = useMemo(() => {
    // 这里放请求流整理的数据，html转slate dom/
    return data;
  }, [data]);

  const mainWritingSet = useMemo(() => {
    const adjustedPlugins = mainEditorDefaultPlugins.map((plugin) => {
      return injectStyle(plugin, editorManager.styles);
    });

    return createPlateEditor({
      plugins: adjustedPlugins,
      override: {
        components: { ...mainEditorDefaultComponents }
      },
      value: parsedData
    });
  }, [parsedData]);

  const handleClose = () => {
    if (!editor) return;
    const nodes = Array.from(getNodes(editor));
    let aiWriterNodeEntry: any = null;
    nodes.forEach(([node, path]) => {
      if (node.type === "aiwriter") {
        aiWriterNodeEntry = [node, path];
      }
    });

    if (aiWriterNodeEntry) {
      editor.undo();
    } else {
      console.log("没有找到 aiwriter 元素");
    }
  };
  const handleClickOutside = (event) => {
    const target = event.target;
    const isDropdownClick = target.closest(".ant-select-dropdown"); // 检查是否点击在下拉菜单内
    const isMenuClick = target.closest(".ant-menu"); // 检查是否点击在下拉菜单内
    const isSubMenuClick = target.closest(".ant-menu-submenu"); // 检查是否点击在下拉菜单内
    if (
      inputRef.current &&
      !inputRef.current.contains(target) &&
      !isDropdownClick &&
      !isMenuClick &&
      !isSubMenuClick
    ) {
      console.log("点击在输入框外部");
      setIsModalOpen(true);
      // 这里可以添加关闭下拉菜单的逻辑
      // if (state === AiwriterState.Process || state === AiwriterState.Done) {

      // } else {
      //   handleClose()
      // }
    } else {
      console.log("点击在输入框内部");
    }
  };

  useEffect(() => {
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleCurData = (data) => {
    setData(data);
  };

  const startAiWrite = (params) => {
    let totalData = "";
    setState(AiwriterState.Process);
    api_optimize({
      config: serverInfo,
      data: {
        signal: sseController.current.signal,
        params,
        onmessage: ({ data }) => {
          const curRes = JSON.parse(data);
          if (curRes.status === LLMStatus.Error) {
            message.error(curRes.reply.content);
            setState(AiwriterState.Error);
          }
          if (curRes.status === LLMStatus.Normal) {
            totalData += curRes.reply.content;
            handleCurData(totalData);
          }
          if (curRes.status === LLMStatus.Success) {
            totalData = "";
            setState(AiwriterState.Done);
          }
        },
        onerror: (err) => {
          console.log(err);
          totalData = "";
          setState(AiwriterState.Error);
          throw err;
        },
        onclose: () => {
          totalData = "";
          setState(AiwriterState.Done);
        }
      }
    });
  };

  const handleSendClick = (method, value) => {
    console.log("发送:", method, value, nodeProps);
    setState(AiwriterState.Process);
    // 在这里添加发送逻辑
    const sourceText = (nodeProps || {})["sourceText"] || "";
    const params = {
      optType: AiWriterType[method],
      rawContent: sourceText
    };
    setGenParams({ method, value });
    switch (method) {
      case "polish":
        params["userPrompt"] = value;
        break;
      case "extend":
        params["lengthLimitLow"] = sourceText.length;
        params["lengthLimit"] = sourceText.length * value;
        break;
      case "short":
        params["lengthLimit"] = sourceText.length * value;
        break;
    }

    startAiWrite(params);
  };
  const handleDoneEvent = (method: string) => {
    const newContent = data;
    console.log(props.nodeProps, newContent, editor.children);
    if (props.nodeProps && props.nodeProps.selection) {
      const path = getNodePathByType("aiwriter", editor);
      switch (method) {
        // 处理完过后重置选区
        case "replace":
          editor.select(path);
          editor.delete();
          editor.select(props.nodeProps.selection);
          // 用于处理溯源问题
          const endPoint = Range.end(props.nodeProps.selection);
          const [_, endPath] = editor.node(endPoint);
          const [parentNode]: any = Editor.parent(editor, endPath);
          if (parentNode.type === "retrieve-tag") {
            editor.delete();
            const [nodeEntry] = editor.nodes({
              at: [], // 遍历整个文档树
              match: (n: any) =>
                n.type === "retrieve-tag" && n.id === parentNode.id // 查找匹配的节点
            });
            const [_, retrieveTagPath] = nodeEntry;
            if (retrieveTagPath) {
              editor.removeNodes({ at: retrieveTagPath });
            }
          } else {
            editor.delete();
          }
          editor.insertText(newContent);
          editor.select(editor.end([]));
          break;
        case "insert":
          editor.select(path);
          editor.delete();
          editor.insertText(newContent);
          editor.select(editor.end([]));
          break;
      }
    } else {
      console.log("未找到匹配的文本");
    }
  };

  const handleOk = () => {
    console.log(mainEditor.current?.selection);
    handleClose();
    setIsModalOpen(false);
  };
  const handleCancel = () => {
    setIsModalOpen(false);
    return;
  };

  // 停止生成
  const stopGen = () => {
    sseController.current.abort();
    sseController.current = new AbortController();
    setState(AiwriterState.Done);
  };

  const [feedbackLoading, setFeedbackLoading] = useState(false);
  // 反馈
  const handleFeedback = async (feedbackType, method, userComment = "") => {
    setFeedbackLoading(true);
    const feedbackTypeObj = {
      like: 1,
      unlike: 2,
      comment: 0
    };
    try {
      const res = await api_articleFeedback({
        config: serverInfo,
        data: {
          feedbackType: feedbackTypeObj[feedbackType],
          scene: AiWriterType[method],
          rawContent: (nodeProps || {})["sourceText"] || "",
          targetContent: data,
          userComment: userComment
        }
      });
      setFeedbackLoading(false);
      if (res) {
        feedbackType === "like" && message.success("感谢您的支持");
        feedbackType === "unlike" && message.success("反馈成功");
      }
    } catch (e) {
      setFeedbackLoading(false);
    }
  };

  // 复制
  const handleCopy = async (data: string) => {
    const text = getAllText(data);
    copy(text);
    message.success("复制成功");
  };

  const surrender = () => {
    setState(AiwriterState.Wait);
    handleClose();
  };

  // 点踩反馈相关
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const { TextArea } = Input;

  return (
    <>
      <Modal
        open={open}
        okText="确认"
        cancelText="取消"
        centered={true}
        width={412}
        onOk={async () => {
          await handleFeedback(
            "unlike",
            genParams.method,
            form.getFieldValue("suggestion")
          );
          form.setFieldValue("suggestion", "");
          setOpen(false);
          setIsModalOpen(false);
        }}
        onCancel={() => {
          form.setFieldValue("suggestion", "");
          setOpen(false);
          setIsModalOpen(false);
        }}
        okButtonProps={{ loading: feedbackLoading }}
        destroyOnClose={true}
      >
        <span className="text-[#2a2a2a] text-[16px] font-bold">
          感谢您的反馈！这将帮助我们不断优化与提升。
        </span>
        <Flex vertical className="mt-[20px] w-[364px]" gap={12}>
          <Form form={form}>
            <Form.Item
              name={"suggestion"}
              rules={[
                {
                  max: 151,
                  message: "最多150字"
                }
              ]}
            >
              <TextArea
                placeholder="请输入产品功能问题及改进建议(150字以内)"
                autoSize={{
                  minRows: 5,
                  maxRows: 5
                }}
              ></TextArea>
            </Form.Item>
          </Form>
        </Flex>
      </Modal>

      <Modal
        title={
          <Flex gap={14} align="center">
            <ExclamationCircleOutlined
              style={{ fontSize: "24px", color: "#FAAD14" }}
            />
            放弃
          </Flex>
        }
        open={isModalOpen && !open}
        closable={false}
        okButtonProps={{
          style: {
            background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
            border: "none",
            borderRadius: "4px",
            color: "#fff"
          }
        }}
        footer={
          <div className="text-right">
            <Button
              style={{
                border: "1px solid #e8e8e8",
                color: "#555",
                borderRadius: "4px",
                marginRight: "16px"
              }}
              onClick={handleCancel}
            >
              取消
            </Button>
            <Button
              style={{
                background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                color: "#fff",
                border: "none",
                borderRadius: "4px"
              }}
              onClick={handleOk}
            >
              确定
            </Button>
          </div>
        }
      >
        <p className="pl-10">是否丢弃当前内容?</p>
      </Modal>
      <div
        ref={inputRef}
        contentEditable={false}
        className="w-full border-solid border-[#055AFF] border-[1px] rounded-[4px]"
      >
        {state === AiwriterState.Wait && (
          <AiWriterInputField
            onSend={handleSendClick}
            onClose={handleClose}
            state={state}
          />
        )}

        {state !== AiwriterState.Wait && (
          <div className="extend px-5 py-3">
            <Plate editor={mainWritingSet} readOnly={true}>
              <PolishEditor className=" bg-white mb-[5px] mt-[10px] box-border h-fit max-h-[480px] overflow-y-scroll" />
            </Plate>

            {state === AiwriterState.Process && (
              <Flex justify="space-between">
                <Button type="link" className="14px text-[#055aff]">
                  <img src={Generating} width={"16px"} alt="" /> 生成中...
                </Button>
                <Button
                  type="link"
                  className="14px text-[#888]"
                  onClick={stopGen}
                >
                  停止生成
                </Button>
              </Flex>
            )}

            {state === AiwriterState.Done && (
              <div className="flex items-center pt-3 justify-between">
                <div className="flex">
                  <img
                    src={Good}
                    alt=""
                    className="cursor-pointer"
                    onClick={() => handleFeedback("like", genParams.method)}
                  />
                  {/* <Divider type="vertical" /> */}
                  <span
                    className="inline-block w-[1px] h-[10px] mx-2 mt-1"
                    style={{ borderLeft: "1px solid #d8d8d8" }}
                  ></span>
                  <img
                    src={Bad}
                    alt=""
                    className="cursor-pointer"
                    onClick={() => setOpen(true)}
                  />
                  {/* <Divider type="vertical" /> */}
                  <span
                    className="inline-block w-[1px] h-[10px] mx-2 mt-1"
                    style={{ borderLeft: "1px solid #d8d8d8" }}
                  ></span>
                  <img
                    src={Copy}
                    alt=""
                    className="cursor-pointer"
                    onClick={() => handleCopy(data)}
                  />
                </div>
                <Space>
                  <Button
                    style={{
                      border: "1px solid #e8e8e8",
                      color: "#555",
                      fontSize: "14px",
                      borderRadius: "4px"
                    }}
                    size="small"
                    onClick={surrender}
                  >
                    放弃
                  </Button>
                  <Button
                    style={{
                      border: "1px solid #e8e8e8",
                      color: "#555",
                      fontSize: "14px",
                      borderRadius: "4px"
                    }}
                    size="small"
                    onClick={() =>
                      handleSendClick(genParams.method, genParams.value)
                    }
                  >
                    重新生成
                  </Button>
                  <Button
                    style={{
                      border: "1px solid #e8e8e8",
                      color: "#555",
                      fontSize: "14px",
                      borderRadius: "4px"
                    }}
                    onClick={() => handleDoneEvent("replace")}
                    size="small"
                  >
                    替换所选
                  </Button>
                  <Button
                    size="small"
                    style={{
                      background: `linear-gradient(313.7deg, #BD9CFF -2.37%, #3C6DFF 68.78%, #0359FF 100%)`,
                      color: "#fff",
                      border: "none",
                      borderRadius: "4px"
                    }}
                    onClick={() => handleDoneEvent("insert")}
                  >
                    插入下方
                  </Button>
                </Space>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
};
const AiWriterInputField = ({ onSend, onClose, state }) => {
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<any>(null); // 确保定义 inputRef

  const [selectedOption, setSelectedOption] = useState("");
  const aiComponentRef = useRef<HTMLDivElement>(null);
  const [openSelect, setOpenSelect] = useState(true);

  const handleInputFocus = () => {
    if (openSelect) {
      setOpenSelect(false);
    }
  };

  const options = [
    { label: "润色", key: "polish", icon: <img src={PolishIcon} /> },
    {
      label: "扩写",
      key: "extend",
      icon: <img src={ExtendIcon} />,
      children: [
        { label: "120%", key: 1.2 },
        { label: "150%", key: 1.5 },
        { label: "180%", key: 1.8 },
        { label: "200%", key: 2 }
      ]
    },
    {
      label: "缩写",
      key: "short",
      icon: <img src={ShortIcon} />,
      children: [
        { label: "80%", key: 0.8 },
        { label: "70%", key: 0.7 },
        { label: "60%", key: 0.6 },
        { label: "50%", key: 0.5 }
      ]
    }
  ];

  const handleIconClicked = () => {
    if (openSelect) {
      return;
    } else {
      inputRef.current?.blur();
      setOpenSelect(true);
    }
  };
  const handleSelectChange = (value) => {
    console.log("选中的值:", value); // 添加日志输出
    setSelectedOption(value);
    if (openSelect) {
      setOpenSelect(false);
      inputRef.current?.focus();
      if (value.includes("extend") || value.includes("short")) {
        onSend(value[1], value[0]);
      }
      if (value.includes("polish")) {
        onSend("polish", inputValue);
      }
    }
  };

  const handleSendClick = () => {
    onSend("polish", inputValue);
  };

  return (
    <div className="flex ai-inputer" ref={aiComponentRef}>
      <Select
        defaultValue={"polish"}
        // onChange={handleSelectChange}
        //onDropdownVisibleChange={handleDropdownVisibleChange} // 监听下拉菜单的可见性变化
        open={openSelect}
        style={{ width: 154, marginRight: 8 }}
        className=" absolute -z-[1] left-1"
        showSearch
        dropdownRender={() => (
          <Menu
            mode="vertical"
            items={options}
            onSelect={(e) => handleSelectChange(e.keyPath)}
            className="ai-writer"
            style={{
              padding: 0,
              border: "none"
            }}
          />
        )}
      />

      <Input
        value={inputValue}
        ref={inputRef}
        className="py-2 px-2"
        onChange={(e) => setInputValue(e.target.value)}
        onFocus={handleInputFocus}
        placeholder="请输入写作要求，或从下方选择创作要求。"
        style={{ flex: 1, border: "none" }}
        prefix={
          <div className=" cursor-pointer" onClick={() => handleIconClicked()}>
            <img src={AiPhoto} alt="" width={24} />
          </div>
        }
        suffix={
          <Button
            style={{
              background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
              color: "#fff",
              border: "none",
              padding: "0"
            }}
            shape="circle"
            onClick={() => handleSendClick()}
            icon={
              <SendOutlined
                rotate={-35}
                style={{
                  fontSize: "16px",
                  position: "relative",
                  top: "-1px",
                  left: "1px"
                }}
              />
            }
          />
        }
      />
    </div>
  );
};
//const MemoizedAiWriterInputField = memo(AiWriterInputField);

const AiWriterPlugin: PlatePlugin = createPlatePlugin({
  key: "aiwriter",
  node: {
    isElement: true,
    isInline: false,
    type: "aiwriter",
    isVoid: true
  }
});

export default AiWriterPlugin;
