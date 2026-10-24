import { DeleteOutlined, EditOutlined, EllipsisOutlined } from '@ant-design/icons';
import { cn } from '@udecode/cn';
import { useClickAway, useHover } from 'ahooks';
import { Button, ConfigProvider, Divider, Dropdown, Popconfirm, Typography } from 'antd';
import { useContext, useEffect, useRef, useState } from 'react';
import './style.less';
import { useStateStore } from '../../core/useStateStore';
import { ListItemType } from '../../@types/props';
import { useAiChatCore } from '../../core/operators/useAiCompareCore';
import { ConfigContext } from 'antd/es/config-provider';
import { Menu } from 'antd';

const { Item } = Menu;
const { Text, Title } = Typography;

const items = [
  {
    key: 'rename',
    label: '重命名',
  },
  {
    key: 'delete',
    label: '删除',
  },
];

interface ITopicListItem {
  data: ListItemType;
  isActive: boolean;
  isDisabled: boolean;
}
const baseClass =
  'topicListItem cursor-pointer relative flex items-start justify-between rounded-[4px] !text-[#555555] flex items-center px-[16px] h-[32px] text-[12px] relative';
const activeClass = 'bg-[#fff] !text-[#2A2A2A] border-none shadow-sm';
const disabledClass = 'disabled';
const hoveredClass = 'hover:bg-[#91BFFF]';

const TopicListItem = (props: ITopicListItem) => {
  const { theme, slider } = useContext(ConfigContext);
  const ref = useRef<HTMLDivElement>(null);
  const { isActive, isDisabled, data } = props;
  const iconRef = useRef(null);
  const propagationFlag = useRef(false);
  const [showMenu, setShowMenu] = useState(false);
  const { setActiveChat } = useAiChatCore();
  // const { freshAndSetChatToCurrent } = useNlpChatCore();
  const isHovered = useHover(ref, {});
  const ItemStyles = cn(
    baseClass,
    { [activeClass]: isActive },
    { [disabledClass]: isDisabled }
    // { [hoveredClass]: isHovered && !isDisabled && !isActive } // 仅在非禁用状态下应用悬停样式
  );
  useEffect(() => {
    console.log('showMenu', showMenu);
  }, [showMenu]);
  const handleItemEvents = (e) => {
    if (!propagationFlag.current) {
      setShowMenu(false);
    }
    propagationFlag.current = false;
    console.log('showMenu', showMenu);
    e.preventDefault();
    e.stopPropagation();
    setActiveChat(data.sessionId);
  };

  const clickMenu = () => {
    propagationFlag.current = true;
    if (isActive) {
      setShowMenu(!showMenu);
    } else {
      setShowMenu(true);
    }
  };

  useClickAway(() => {
    setShowMenu(false);
  }, iconRef);
  return (
    <div key={data.sessionId} onClick={handleItemEvents} ref={ref} className={ItemStyles}>
      <div className="line-clamp-1 break-words text-ellipsis w-[160px]">
        {data.label ? data.label : '未命名聊天'}
      </div>{' '}
      <div className="h-full flex items-center" onClick={clickMenu}>
        <EllipsisOutlined />
      </div>
      {isActive && showMenu && (
        <div
          ref={iconRef}
          className="absolute w-[99px] h-[80px] rounded-[4px] shadow bg-[#fff] z-50 top-[-1px] left-[219px] px-[8px] py-[8px]"
        >
          <Button
            type="text"
            className="w-[83px] h-[32px]"
            onClick={(e) => {
              setShowMenu(false);
              handleItemEvents(e);
            }}
            icon={<EditOutlined />}
          >
            重命名
          </Button>
          <Button
            type="text"
            className="w-[83px] h-[32px]"
            onClick={(e) => {
              setShowMenu(false);
              handleItemEvents(e);
            }}
            icon={<DeleteOutlined type="danger" />}
          >
            删除
          </Button>
        </div>
      )}
    </div>
  );
};

export default TopicListItem;
{
  /* <div className="flex-col px-[12px]">
        <Text
            style={{
              color: isActive ? '#EFEFEF' : '',
            }}
            ellipsis
            type="secondary"
          >
            {data.gmtModified}
          </Text>
      </div> 
      <div className="absolute top-2 right-2">
        <div className="flex gap-x-1">
          <Button
            type="text"
            size="small"
            onClick={(e) => handleItemEvents(e)}
            icon={<EditOutlined />}
          ></Button>
          <Button
            size="small"
            type="text"
            onClick={(e) => handleItemEvents(e)}
            icon={<DeleteOutlined type="danger" />}
          ></Button>
        </div>
      </div>*/
}
