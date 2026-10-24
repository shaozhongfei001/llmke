import { Flex, List, theme, Typography } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useClickAway } from 'ahooks';
import { select, Transforms } from 'slate';
const { Text } = Typography;
const { useToken } = theme;
import { editorEventBus, EDITOR_EVENT_NAME } from './Editor/editorEventBus';
import VarCom from './VarCom';
import { PiSquare } from 'lucide-react';
import { useEditorState } from '@udecode/plate/react';
const LIST_WIDTH = 250;
const MenuCom = ({ editorRef, allList }: any) => {
  const { token } = useToken();
  const [menuConfig, setMenuConfig] = useState({ position: { top: 0, left: 0 }, showMenu: false });
  const editor: any = useEditorState();
  const [menu, setMenu]: any[] = useState([]);
  const [initPoint, setInitPoint] = useState({ x: 0, y: 0, width: 0 });
  const getElementCoordinates = (element) => {
    var rect = element?.getBoundingClientRect();
    console.log('rect------->', rect);

    return {
      x: rect?.left || 0,
      y: rect?.top || 0,
      width: rect?.width || 0,
    };
  };
  useEffect(() => {
    const handleE = (data: any) => {
      setMenuConfig({
        ...menuConfig,
        ...data,
      });
    };
    try {
      editorEventBus.on(EDITOR_EVENT_NAME.PROMPT, handleE);
    } catch (e) {
      console.log('e', e);
    }
    return () => {
      try {
        editorEventBus.off(EDITOR_EVENT_NAME.PROMPT, handleE);
      } catch (e) {
        console.log(e);
      }
    };
  }, []);

  const handleClickAway = () => {
    setMenuConfig({ ...menuConfig, showMenu: false });
  };

  // 使用 useClickAway Hook 监听点击事件
  useClickAway(() => {
    handleClickAway();
  }, editorRef);

  const getMenu = () => {
    setMenu(
      allList
        .map((t) => {
          return { label: t, value: t };
        })
        .concat([{ label: '添加新变量', value: 'add' }])
    );
  };

  const clickItem = (e, item: any) => {
    e.stopPropagation();
    e.preventDefault();
    const { anchor, focus }: any = editor.selection;
    if (anchor.offset - 1 > -1) {
      const curSelection: any = {
        ...editor.selection,
        anchor: { ...editor.selection.anchor, offset: anchor.offset - 1 },
      };
      select(editor, curSelection);
      editor.delete(curSelection);
      editor.remove;
      Transforms.insertText(editor, `{{${item.value === 'add' ? '' : item.value}}}`);
      setMenuConfig({
        ...menuConfig,
        showMenu: false,
      });
    }
  };

  const handleResize = () => {
    const point = getElementCoordinates(document.getElementById('plateBox'));
    setInitPoint(point);
  };

  useEffect(() => {
    if (!menuConfig.showMenu) return;
    handleResize();
    getMenu();
  }, [menuConfig]);

  useEffect(() => {
    window.addEventListener('resize', handleResize);

    return () => {
      // 在组件卸载时取消事件监听
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const getLeft = useMemo(() => {
    const { position } = menuConfig;
    let left = position.left - initPoint.x - 3;
    if (!initPoint.width || left + 250 > initPoint.width) {
      return left - 250;
    } else {
      return left;
    }
  }, [menuConfig, initPoint]);

  return (
    <List
      size="small"
      bordered
      style={{
        top: menuConfig.position.top - initPoint.y + 18 + 'px',
        left: getLeft + 'px',
        backgroundColor: token.colorBgBase,
        zIndex: token.zIndexPopupBase,
        position: 'absolute',
        maxHeight: '200px',
        overflowY: 'auto',
        width: `${LIST_WIDTH}px`,
        display: menuConfig.showMenu ? '' : 'none',
      }}
      dataSource={menu}
      renderItem={(item: any) => (
        <List.Item onClick={(e) => clickItem(e, item)} style={{}}>
          <Flex
            align="center"
            gap="0 5px"
            style={{
              borderRadius: token.borderRadius,
              width: '100%',
              height: '100%',
              paddingLeft: token.paddingXXS,
              paddingRight: token.paddingXXS,
            }}
            className="hover:bg-[#EEF4FF]"
          >
            <VarCom />
            <Text>{item.label}</Text>
          </Flex>
        </List.Item>
      )}
    />
  );
};

export default MenuCom;
