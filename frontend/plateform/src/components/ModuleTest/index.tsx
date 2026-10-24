import { CloseOutlined } from "@ant-design/icons";
import { Tabs, message } from "antd";
import { useEffect, useState } from "react";
import PreviewEditor from "./components/PreviewEditor";
import FormContainer from "./components/FormContainer";
import { EDITOR_EVENT_NAME, editorEventBus } from "../AiEditor/editorEventBus";
import useEditorStreamFetch from "./components/useEditorStreamFetch";

enum TabKey {
  Input = "1",
  Result = "2"
}

const items: { key: TabKey; label: any }[] = [
  {
    key: TabKey.Input,
    label: "输入"
  },
  {
    key: TabKey.Result,
    label: "结果"
  }
];

interface Iprops {
  formSchema: any[];
  closeModule?: () => any;
  mouduleName: "SECTION" | "ANALYSIS";
  testId: number | string;
}

function ModuleTest({
  formSchema = [],
  closeModule,
  mouduleName,
  testId
}: Iprops) {
  const {
    submitFormData,
    selectFile,
    setSelectFile,
    mdData,
    allFile,
    wirteLoading,
    stopGen
  } = useEditorStreamFetch(testId, mouduleName);
  const [activeKey, setActiveKey] = useState<string>(TabKey.Input);

  const onChange = (activeKey: string) => {
    if (activeKey === TabKey.Input) {
      stopGen();
    }
    setActiveKey(activeKey);
  };

  const handleClose = () => {
    stopGen();
    closeModule && closeModule();
  };

  // 处理rag召回的问题
  const handleRagReCall = (id: any) => {
    const _selectFile = (allFile || []).find((i) => i.order_num === id);
    console.log(_selectFile, id, "rag溯源召回");
    if (!_selectFile || !id) {
      message.warning("当前段落生成成功可查看召回文档");
    }
    setSelectFile(_selectFile);
  };

  // 溯源点击事件监听
  useEffect(() => {
    const handleTagClick = (data: any) => {
      if (data.isRag) {
        if (!data.id) {
          message.error("未找到文件id");
          return;
        }
        data.id && handleRagReCall(data.id);
      } else {
        console.log("老版素材溯源，不应该出现在这里", data);
      }
    };
    editorEventBus.on(EDITOR_EVENT_NAME.CLICKRETRIEVE, handleTagClick);
    return () => {
      editorEventBus.off(EDITOR_EVENT_NAME.CLICKRETRIEVE, handleTagClick);
    };
  }, [allFile]);

  // 点击确定按钮
  const handleConfirm = (formData: any) => {
    onChange(TabKey.Result);
    submitFormData(formData);
  };

  return (
    <div className="w-full h-full box-border px-5 py-4 relative">
      {closeModule && (
        <div className="flex justify-between items-center">
          <span className="text-[#333] font-bold text-[16px]">测试预览</span>
          <CloseOutlined className="cursor-pointer" onClick={handleClose} />
        </div>
      )}

      <Tabs
        className="custom-tab-box text-[#BBB] mb-4"
        style={{ borderBottom: "1px solid #fff" }}
        activeKey={activeKey}
        items={items}
        onChange={onChange}
      />
      <div
        style={{
          height: "calc(100% - 95px)",
          display: activeKey === TabKey.Input ? "block" : "none"
        }}
      >
        <FormContainer
          formSchema={formSchema}
          submitFormData={handleConfirm}
          mouduleName={mouduleName}
        />
      </div>

      <div
        style={{
          height: "calc(100% - 95px)",
          display: activeKey === TabKey.Result ? "block" : "none"
        }}
      >
        <PreviewEditor
          mdData={mdData}
          selectFile={selectFile}
          setSelectFile={setSelectFile}
          wirteLoading={wirteLoading}
        />
      </div>
    </div>
  );
}

export default ModuleTest;
