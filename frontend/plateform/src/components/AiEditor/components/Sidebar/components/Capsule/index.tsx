import {
  EditorType,
  ModueEnum
} from "@root/src/components/AiEditor/@types/sys";
import { Flex } from "antd";
import AiRobot from "@/components/AiEditor/assets/img/aiRobot.png";
import { useStateStore } from "@root/src/components/AiEditor/core/states/useStateStore";
import { useMemo } from "react";

interface Item {
  value: string;
  key: ModueEnum;
}

const List = [
  {
    value: "写作",
    key: ModueEnum.Writing
  },
  {
    value: "素材",
    key: ModueEnum.Material
  }
];

export const Capsule = () => {
  const {
    setProjectData,
    setOpen,
    mainEditor,
    setWritingSettingOpen,
    baseInfo,
    editorType
  } = useStateStore();

  const isPreview = useMemo(() => {
    return editorType === EditorType.Preview;
  }, [editorType]);

  const handleItem = (item: Item) => {
    setOpen(true);
    if (item.key === ModueEnum.Writing) {
      setWritingSettingOpen(true);
    }

    setProjectData((p) => ({
      ...p,
      currentModule: item.key
    }));
  };
  return (
    <Flex
      vertical
      align="center"
      style={{
        border: "1px solid white"
      }}
      className="fixed right-6 bottom-8 pt-3 px-1 box-border w-12 bg-[rgb(255,255,255,0.7)] rounded-full"
    >
      {List.map((item) => (
        <Flex
          key={item.key}
          align="center"
          className="h-[32px] mt-2 cursor-pointer"
          style={{
            borderBottom: "1px solid #eee",
            color: isPreview ? "#bbb" : "",
            cursor: isPreview ? "not-allowed" : "pointer"
          }}
          onClick={() => !isPreview && handleItem(item)}
        >
          {item.value}
        </Flex>
      ))}
      <Flex
        align="center"
        justify="center"
        className="w-12 h-12 bg-white rounded-full mt-1"
      >
        <img
          src={AiRobot}
          width={48}
          alt=""
          onClick={() => {
            // 调试使用，勿删
            mainEditor.current &&
              console.log(mainEditor.current, baseInfo, "当前编辑器的状态");
          }}
        />
      </Flex>
    </Flex>
  );
};

export default Capsule;
