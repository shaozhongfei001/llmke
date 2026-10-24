import React, { useEffect, useState, useMemo } from "react";
import { Input, Button, message } from "antd";
import { PrimaryBtn } from "@/pages/HomePage/Writing/common/components/PrimaryBtn";
import AutoSaveInput from "@/components/AutoSaveInput";
import { ISection } from "../common/type.ts";
import { useServices } from "../common/server.ts";
const { TextArea } = Input;

interface Iprops {
  id: number;
  section: ISection;
  setSection: React.Dispatch<React.SetStateAction<ISection | undefined>>;
  showTest: (prompt?: string, isShow?: boolean) => void;
  updateTreeData: (key: string, property: string, value: any) => void;
}

const Section = ({
  id,
  section,
  setSection,
  showTest,
  updateTreeData
}: Iprops) => {
  const { updateChanpter } = useServices();

  const saveValue = async (value: string, type: "prompt" | "example") => {
    const newPartSeciton: ISection = {
      [type == "prompt" ? "sectionPrompt" : "sectionContentExample"]: value
    };
    type == "prompt" && showTest(value);
    await saveSection(newPartSeciton, type);
  };

  const saveSection = async (
    newSection: ISection,
    type: "prompt" | "example",
    showMessage?: boolean
  ) => {
    try {
      const res: any = await updateChanpter.mutateAsync({
        ...newSection,
        id
      });
      if (res && res.success && type == "prompt") {
        const hasSectionPrompt =
          newSection.sectionPrompt && newSection.sectionPrompt?.length > 0
            ? true
            : false;
        updateTreeData(id.toString(), "hasSectionPrompt", hasSectionPrompt);
      }

      if (res && showMessage) {
        message.success("章节组件保存成功！");
      }
    } catch (e) {
      console.log("update chapter failed-------->", e);
    }
  };

  return (
    <div className={`w-full h-full flex flex-col justify-between relative`}>
      <div className="h-[calc(100%-106px)]  flex flex-col justify-between ">
        <div className="h-[calc(50%-0px)] mb-[20px]">
          <div className="font-bold mb-[12px]">内容要求</div>
          <AutoSaveInput
            initValue={section.sectionPrompt}
            save={saveValue}
            valueType="prompt"
            setSection={setSection}
          />
        </div>
        <div className="h-[calc(50%-0px)] mb-[20px]">
          <div className="font-bold mb-[12px]">参考示例</div>
          <AutoSaveInput
            initValue={section.sectionContentExample}
            save={saveValue}
            valueType="example"
            setSection={setSection}
          />
        </div>
      </div>

      {/* <div className="w-full mt-[14px] flex justify-end">
        <Button
          type="primary"
          onClick={async () => {
            await saveSection(section);
            showTest(section.sectionPrompt, true);
          }}
          disabled={!canSave}
          style={{
            color: `#555555`,
            backgroundColor: "#fff",
            borderRadius: "4px",
            border: "1px solid #dedede",
            marginRight: "14px",
            opacity: !canSave ? "50%" : "100%"
          }}
        >
          测试
        </Button>
        <PrimaryBtn
          onClick={() => saveSection(section, true)}
          // disabled={!canSave}
          style={
            {
              // opacity: !canSave ? "50%" : "100%"
            }
          }
        >
          保存
        </PrimaryBtn>
      </div> */}
    </div>
  );
};

export default Section;
