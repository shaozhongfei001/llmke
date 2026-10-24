import { Modal, Flex, Button, Tooltip } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { createBracketHighlightPlugin } from "../Editor/createBracketHighlightPlugin";
import { PromptEditor } from "../Editor";
import { HighlightLeaf } from "../Editor/ui/highlight-leaf";
import { contextMenuPlugin } from "../Editor/contextMenu";
import LableCom from "../LableCom";
import {
  createPlateEditor,
  HighlightPlugin,
  Plate
} from "@udecode/plate/react";
import { withPlaceholders } from "../Editor/ui/placeholder";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { RedoOutlined, LoadingOutlined } from "@ant-design/icons";
import { FontColorPlugin } from "@udecode/plate-font";
interface AIHelperModal {
  open: boolean;
  AIhelperRes: any;
  setAIhelperModalOpen: (open: boolean) => void;
  setNewPrompt: (data: any) => void;
  handleAIHelper: any;
  AIhelperLoading: boolean;
  handlerEvent: (type: string, data?: any) => void;
  AIhelperModalClose: () => void;
}

export const AIHelperModal = ({
  open,
  setAIhelperModalOpen,
  AIhelperRes,
  setNewPrompt,
  handleAIHelper,
  AIhelperLoading,
  handlerEvent,
  AIhelperModalClose
}: AIHelperModal) => {
  const editorRef = useRef<any>(null);
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
      value: ""
    });
  }, []);

  const setPrompt = (str: string) => {
    if (!editor) return;
    editor.tf.setValue([
      {
        type: "p",
        children: [{ text: str }]
      }
    ]);
  };

  useEffect(() => {
    setPrompt(AIhelperRes);
  }, [AIhelperRes]);

  return (
    <Modal
      open={open}
      title="AI帮写"
      okText="确认"
      cancelText="取消"
      width={"1000px"}
      onCancel={() => AIhelperModalClose()}
      footer={() => {
        return (
          <>
            <Button
              type="primary"
              onClick={() => AIhelperModalClose()}
              style={{
                color: `#555555`,
                backgroundColor: "#fff",
                borderRadius: "4px",
                border: "1px solid #dedede"
              }}
            >
              取消
            </Button>
            <Tooltip
              title={() => {
                return (
                  <span className="text-[#333]">确认后将替换原系统提示词</span>
                );
              }}
              color="#fff"
            >
              <Button
                ghost
                onClick={() => {
                  setAIhelperModalOpen(false);
                  setNewPrompt(AIhelperRes);
                  setTimeout(() => {
                    handlerEvent("onBlur");
                  }, 10);
                }}
                style={{
                  background: "linear-gradient(#2867FF, #8789FF)",
                  border: "none",
                  borderRadius: "4px",
                  marginLeft: "10px"
                }}
                loading={AIhelperLoading}
              >
                确认
              </Button>
            </Tooltip>
          </>
        );
      }}
      forceRender
    >
      <div className="overflow-y-auto">
        <DndProvider backend={HTML5Backend}>
          <Plate editor={editor}>
            <Flex>
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
                  <div className="w-full flex flex-row justify-between">
                    <LableCom title="系统提示词" />

                    <div>
                      {AIhelperLoading ? (
                        <Button
                          type="text"
                          className="text-[#055AFF] text-sm"
                          onClick={() => {
                            return;
                          }}
                          icon={<LoadingOutlined />}
                        >
                          生成中
                        </Button>
                      ) : (
                        <Button
                          type="text"
                          className="text-[#055AFF] text-sm"
                          onClick={handleAIHelper}
                          icon={<RedoOutlined />}
                        >
                          重新生成
                        </Button>
                      )}
                    </div>
                  </div>
                  <PromptEditor ref={editorRef} />
                </div>
              </div>
            </Flex>
          </Plate>
        </DndProvider>
      </div>
    </Modal>
  );
};
