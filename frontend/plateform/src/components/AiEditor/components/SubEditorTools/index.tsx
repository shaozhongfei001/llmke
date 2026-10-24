import {
  AlignCenterOutlined,
  AlignLeftOutlined,
  AlignRightOutlined,
  CheckOutlined,
  FontSizeOutlined,
  StopOutlined,
} from '@ant-design/icons';

import { Button, Col, Divider, Row } from 'antd';

import { cn } from '@udecode/cn';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';

// const alignOptions = [
//   { value: 'left', label: '左对齐', icon: <AlignLeftOutlined /> },
//   { value: 'center', label: '居中对齐', icon: <AlignCenterOutlined /> },
//   { value: 'right', label: '右对齐', icon: <AlignRightOutlined /> },
// ];

// const fontSizeOptions = [
//   { value: 12, label: '12' },
//   { value: 14, label: '14' },
//   { value: 16, label: '16' },
//   { value: 18, label: '18' },
//   { value: 20, label: '20' },
//   { value: 22, label: '22' },
// ];

// const lineHeightOptions = [
//   { value: 1, label: '1' },
//   { value: 1.5, label: '1.5' },
//   { value: 2, label: '2' },
//   { value: 3, label: '3' },
// ];

// const letterSpaceOptions = [
//   { value: '2px', label: '1' },
//   { value: '4px', label: '2' },
//   { value: '6px', label: '3' },
//   { value: '8px', label: '4' },
// ];

interface IToolbar {
  toolbarEvents?: () => any;
  className?: string;
  isScrolled?: boolean;
  withCompareEditor?: boolean;
  dynamicWidth?: number;
}

export const SubEditorTools = (props: IToolbar) => {
  const { toolbarEvents } = props;
  // const editor = useEditorState();
  const elementRef = useRef<HTMLDivElement>();

  return (
    <div
      style={{
        width: props.dynamicWidth,
      }}
      className={cn(
        '  fixed bg-slate-50  !text-[#555555] box-border h-[45px] mx-auto  justify-between items-center ',
        ' z-50',
        props.withCompareEditor ? props.dynamicWidth + '' : 'w-full '
      )}
    >
      {/* <Row className="w-full relative ">
        <Col span={18} offset={2}> */}
      <div className=" w-full relative max-w-[680px] px-[30px] mx-auto">
        <div className="editor-tools  w-full h-[45px] overflow-x-hidden  flex justify-end items-center gap-x-1 ">
          <Button type="text" icon={<CheckOutlined />} />
          <Button type="text" icon={<StopOutlined />} />
        </div>
      </div>
      {/* </Col>
      </Row> */}
    </div>
  );
};
