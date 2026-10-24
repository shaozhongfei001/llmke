import { useMemo, useRef, useState, useEffect, memo } from "react";
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
import {
  createPlateEditor,
  HighlightPlugin,
  PlateContent,
  Plate
} from "@udecode/plate/react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { FontColorPlugin } from "@udecode/plate-font";
import useOperator from "@/components/Template/core/useOperator";
import { useStateStore } from "@/components/Template/core/useStateStore";
import { withPlaceholders } from "@/components/Template/components/Editor/ui/placeholder";
import { HighlightLeaf } from "@/components/Template/components/Editor/ui/highlight-leaf";
import { PromptEditor } from "@/components/Template/components/Editor";
import { contextMenuPlugin } from "@/components/Template/components/Editor/contextMenu";
import { createBracketHighlightPlugin } from "@/components/Template/components/Editor/createBracketHighlightPlugin";

interface Iprops {
  prompt: string;
  getPromptValue: (prompt: string) => void;
}

const SectionPrompt = ({ prompt, getPromptValue }: Iprops) => {
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

  const {
    plateValue,
    contentValue,
    setPlateValue,
    restList,
    setRestList,
    tableList,
    setTableList,
    isModalOpen,
    setIsModalOpen
  } = useStateStore();
  const editor = useMemo(() => {
    return createPlateEditor({
      id: "1",
      ...plugins,
      value: plateValue
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

  useEffect(() => {
    setPrompt(prompt);
  }, [prompt]);

  const setPrompt = (str: string) => {
    if (!editor) return;
    editor.tf.setValue([
      {
        type: "p",
        children: [{ text: str }]
      }
    ]);
  };
  const getPromptTemplate = () => {
    if (!editor) return "";

    return serialize(editor.children);
  };

  const clearPlateValue = () => {
    if (!editor) return;

    editor.delete({
      at: {
        anchor: editor.start([]),
        focus: editor.end([])
      }
    });
  };
  console.log("-----rr-", restList);

  return (
    <div className="overflow-y-auto">
      <DndProvider backend={HTML5Backend}>
        <Plate editor={editor}>
          <Flex {...{ gap: "10px 10px" }}>
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
                <PromptEditor
                  ref={editorRef}
                  handlerEvent={handlerEvent}
                  placeholder="示例：帮我写一篇邮件，发送人是{{from}}，接收人是{{to}}，发件人线下地址是{{address}}。邮箱主要目的是{{destination}}"
                />
              </div>
            </div>
          </Flex>
        </Plate>
      </DndProvider>
    </div>
  );
};

export default SectionPrompt;
