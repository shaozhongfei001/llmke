import { CaretDownOutlined, MinusOutlined } from "@ant-design/icons";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import Thick from "../editor/plugins/customPlugin/partingLine/partLine/Thick";
import Double from "../editor/plugins/customPlugin/partingLine/partLine/Double";
import ThickThinSmallGap from "../editor/plugins/customPlugin/partingLine/partLine/ThickThinSmallGap";
import ThinThickSmallGap from "../editor/plugins/customPlugin/partingLine/partLine/ThinThickSmallGap";
import { useEditorState } from "@udecode/plate-common/react";
import { insertNodes } from "@udecode/plate-common";
import {
  partingLineOptions,
  RED_LINE_PARAGRAPH,
} from "../editor/plugins/customPlugin/partingLine/redLinePlugin";

const PartingLineSelect = () => {
  const editor = useEditorState();
  const { selection } = editor;

  const addPartingLine = (value: string) => {
    if (!editor || !selection) return;
    insertNodes(editor, {
      type: RED_LINE_PARAGRAPH,
      children: [{ text: "" }],
      lineType: value,
    });
  };

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <div className="flex gap-x-[3px] h-[45px] cursor-pointer items-center justify-start px-[3px] ">
          <div className="text-center truncate">
            <MinusOutlined style={{ color: "red", fontSize: "16px" }} />
          </div>
          <CaretDownOutlined className="text-[10px]" />
        </div>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="start"
          className="bg-white z-[99] shadow w-[120px]"
          sideOffset={-9}
          //   defaultValue={selectedValue}
        >
          {partingLineOptions &&
            partingLineOptions.map((i, index) => {
              return (
                <div key={index}>
                  <DropdownMenu.Item
                    className="flex cursor-pointer text-[12px] justify-between w-full px-3 box-border py-2  hover:bg-sky-100 hover:border-none hover:ring-none"
                    onSelect={() => addPartingLine(i.value)}
                    key={i.value}
                  >
                    <div className="w-full opacity-70 hover:opacity-100 ">
                      {i.label}
                    </div>
                    {/* <div> {i.icon ? i.icon : ""} </div> */}
                  </DropdownMenu.Item>
                </div>
              );
            })}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
};
export default PartingLineSelect;
