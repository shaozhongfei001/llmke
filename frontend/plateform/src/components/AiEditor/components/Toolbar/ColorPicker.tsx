import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { getMarks } from '@udecode/plate';
import { useEditorState } from '@udecode/plate-common/react';
import { Button, Popover, Typography } from 'antd';
import React, { ReactNode, useEffect, useState } from 'react';
import { TwitterPicker } from 'react-color';

const { Text } = Typography;

const subjectColors = [
  '#2B4B9D',
  '#8BC34A',
  '#673AB7',
  '#C62828',
  '#6BBD6F',
  '#FFA000',
  '#1565C0',
  '#8E24AA',
  '#F4511E',
  '#FFC107',
  '#3F51B5',
  '#C2185B',
  '#EF6C00',
  '#CDDC39',
];
export interface ColorPickerProps {
  format: string;
  icon: ReactNode;
}

const ColorPicker: React.FC<ColorPickerProps> = (props) => {
  const { format, icon } = props;
  const [color, setColor] = useState();
  const editor = useEditorState();
  const { selection } = editor;

  const isMarkActive = () => {
    if (!editor) return;
    const marks = getMarks(editor);
    // eslint-disable-next-line no-prototype-builtins
    if (marks?.hasOwnProperty(format)) {
      setColor(marks[format] as any);
    } else {
      setColor(undefined);
    }
  };

  useEffect(() => {
    isMarkActive();
  }, [selection]);

  const handleColorChange = (color) => {
    if (selection) {
      setColor(color.hex);
      editor.addMark(`${format}`, color.hex);
    }
  };

  return (
    // <Popover
    //   trigger="click"
    //   placement="leftBottom"
    //   content={<TwitterPicker colors={subjectColors} onChangeComplete={handleColorChange} />}
    // >
    //   <Button
    //     size="small"
    //     style={{ border: 0, background: 'transparent', boxShadow: 'none', color: color }}
    //     icon={icon}
    //   ></Button>
    // </Popover>

    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <div
          className="flex h-[45px] cursor-pointer 
          items-center justify-start "
        >
          <Button
            size="small"
            style={{ border: 0, background: 'transparent', boxShadow: 'none', color: color }}
            icon={icon}
          ></Button>
        </div>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="start"
          className="bg-white z-[99] shadow w-[120px]"
          sideOffset={-9}
          // defaultValue={selectedValue}
        >
          <TwitterPicker colors={subjectColors} onChangeComplete={handleColorChange} />
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
};

export default ColorPicker;
