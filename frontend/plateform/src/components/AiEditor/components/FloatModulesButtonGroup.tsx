import { useEffect, useState } from 'react';
// import { useStateStore } from '../../hooks/useStateStore';
// import { useNlpWriterCore } from '../../hooks/useNlpWriterCore';
import { QuestionCircleOutlined, SyncOutlined } from '@ant-design/icons';
import { FloatButton, Switch } from 'antd';
import type { DrawerProps, RadioChangeEvent } from 'antd';
import { Button, Drawer, Radio, Space } from 'antd';
const FloatModulesButtonGroup = () => {
  const [open, setOpen] = useState(false);
  const [placement, setPlacement] = useState<DrawerProps['placement']>('right');

  const showDrawer = () => {
    setOpen(true);
  };

  const onClose = () => {
    setOpen(false);
  };

  const onChange = (e: RadioChangeEvent) => {
    setPlacement(e.target.value);
  };

  return (
    <FloatButton.Group shape="square" style={{ insetInlineEnd: 24, insetBlockEnd: '40%' }}>
      <FloatButton icon={<QuestionCircleOutlined />} onClick={() => setOpen((p) => !p)} />
      <FloatButton />
      <FloatButton icon={<SyncOutlined />} />
      <FloatButton.BackTop visibilityHeight={0} />
    </FloatButton.Group>
  );
};

export default FloatModulesButtonGroup;
