import {
  mainEditorDefaultComponents,
  mainEditorDefaultPlugins
} from "@root/src/components/AiEditor/components/editor/plugins/mainEditorSet";
import { injectStyle } from "@root/src/components/AiEditor/components/MainEditor";
import { defaultStyle } from "@root/src/components/AiEditor/components/MainEditor/default_style";
import { createPlateEditor, Plate } from "@udecode/plate-common/react";
import { useMemo, useRef } from "react";
import { Editor } from "./components/Editor";
import { MarkdownPlugin } from "@udecode/plate-markdown";
import { customDeserializeMd } from "@root/src/components/AiEditor/core/operators/help";
import { Spin } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import RagReCallDrawer from "@root/src/components/AiEditor/components/RagReCallDrawer";

const render = ({ editorManager, mdData }: any) => {
  // 用于序列化
  const curEditor = createPlateEditor({
    plugins: [MarkdownPlugin],
    value: [{ type: "p", children: [{ text: "" }] }]
  });

  // 插入样式
  const adjustedPlugins = mainEditorDefaultPlugins.map((plugin) => {
    return injectStyle(plugin, editorManager.styles);
  });

  // 处理空数据情况
  if (!mdData)
    return createPlateEditor({
      value: [{ type: "p", children: [{ text: "" }] }]
    });

  // 序列化数据
  const _data = customDeserializeMd(curEditor, mdData);
  return createPlateEditor({
    plugins: adjustedPlugins,
    override: {
      components: { ...mainEditorDefaultComponents }
    },
    id: editorManager.id,
    value: _data
  });
};

interface Iprops {
  mdData: string;
  selectFile: any;
  setSelectFile: React.Dispatch<any>;
  wirteLoading?: boolean;
}

const editorManager = {
  id: "preview-editor",
  styles: defaultStyle
};

function PreviewEditor({
  mdData,
  selectFile,
  setSelectFile,
  wirteLoading = false
}: Iprops) {
  const editorRef = useRef<HTMLDivElement>(null);

  const mainWritingSet = useMemo(() => {
    return render({ editorManager, mdData });
  }, [mdData]);

  return (
    <>
      <RagReCallDrawer
        selectFile={selectFile}
        clearSelect={() => {
          setSelectFile("");
        }}
      />
      <div className="h-full w-full overflow-y-auto " ref={editorRef}>
        {wirteLoading ? (
          <div className="flex justify-center items-center w-full mt-6">
            <Spin
              indicator={<LoadingOutlined spin />}
              size="large"
              spinning={true}
            ></Spin>
          </div>
        ) : (
          <Plate editor={mainWritingSet}>
            <Editor
              className="box-border h-fit min-h-[100%] cec-editor"
              readOnly
            />
          </Plate>
        )}
      </div>
    </>
  );
}

export default PreviewEditor;
