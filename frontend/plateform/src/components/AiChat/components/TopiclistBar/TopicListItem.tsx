import {
  DeleteOutlined,
  EditOutlined,
  EllipsisOutlined
} from "@ant-design/icons";
import { cn } from "@udecode/cn";
import { useClickAway, useHover } from "ahooks";
import {
  Button,
  ConfigProvider,
  Divider,
  Dropdown,
  Input,
  Popconfirm,
  Typography
} from "antd";
import { useContext, useEffect, useRef, useState } from "react";
import "./style.less";
import warning from "../../assets/img/warning.png";
import { ListItemType } from "../../@types/props";
import { ConfigContext } from "antd/es/config-provider";
import { Menu } from "antd";
import { useAiChatCore } from "@root/src/components/AiInputer/common/useAiChatCore";
import { useStateStore } from "../../core/useStateStore";

const { Item } = Menu;
const { Text, Title } = Typography;

const items = [
  {
    key: "rename",
    label: "重命名"
  },
  {
    key: "delete",
    label: "删除"
  }
];

interface ITopicListItem {
  data: ListItemType;
  isActive: boolean;
  isDisabled: boolean;
  handleEvent: (type: string, data?: any) => void;
}
const baseClass =
  "topicListItem cursor-pointer relative flex items-start justify-between rounded-[4px] !text-[#2A2A2A] flex items-center px-[16px] h-[32px] text-[12px] relative";
const activeClass =
  "!text-[#2A2A2A] shadow-sm border-[1px] border-solid border-white shadow";
const disabledClass = "disabled";
const hoveredClass = "hover:bg-[#91BFFF]";

const TopicListItem = (props: ITopicListItem) => {
  const { theme, slider } = useContext(ConfigContext);
  const ref = useRef<HTMLDivElement>(null);
  const { isActive, isDisabled, data, handleEvent } = props;
  const iconRef = useRef(null);
  const inputRef: React.MutableRefObject<null> = useRef(null);
  const propagationFlag = useRef(false);
  const [showMenu, setShowMenu] = useState(false);
  const { appData, setAppData, serverInfo, conversationData, inputer } =
    useStateStore();
  const { setActiveChat } = useAiChatCore({
    inputer,
    appData,
    setAppData,
    serverInfo,
    conversationData
  });
  const [isEdit, setIsEdit] = useState(false);
  const [name, setName] = useState("");
  const isHovered = useHover(ref, {});
  const ItemStyles = cn(
    baseClass,
    { [activeClass]: isActive },
    { [disabledClass]: isDisabled }
    // { [hoveredClass]: isHovered && !isDisabled && !isActive } // 仅在非禁用状态下应用悬停样式
  );
  const handleItemEvents = (e: any) => {
    if (!propagationFlag.current) {
      setShowMenu(false);
    }
    propagationFlag.current = false;
    e.preventDefault();
    e.stopPropagation();
    handleEvent && handleEvent("click", data);
    setActiveChat(data.sessionId);
  };

  // const clickMenu = () => {
  //   propagationFlag.current = true;
  //   if (isActive) {
  //     setShowMenu(!showMenu);
  //   } else {
  //     setShowMenu(true);
  //   }
  // };

  useClickAway(() => {
    setShowMenu(false);
  }, iconRef);
  return (
    <div
      key={data.sessionId}
      onClick={handleItemEvents}
      ref={ref}
      className={ItemStyles}
      style={{
        background: isActive
          ? "linear-gradient(to right,rgba(3,89,255,.13),#ffffff)"
          : ""
      }}
    >
      {isEdit ? (
        <Input
          ref={inputRef}
          bordered={false}
          value={name}
          className="px-0 text-[12px]"
        />
      ) : (
        <div
          className="line-clamp-1 break-words text-ellipsis w-[140px]"
          title={data.label ? data.label : "未命名聊天"}
        >
          {data.label ? data.label : "未命名聊天"}
        </div>
      )}
      {isActive && (
        <div className="h-full flex items-center">
          <EditOutlined
            className="mr-[8px] text-[#999999]"
            onClick={(e) => {
              e.stopPropagation();
              handleEvent("edit", data);
            }}
          />
          <Popconfirm
            placement="right"
            icon={null}
            style={{ width: "224px", borderRadius: "8px" }}
            title={
              <>
                <div className="flex items-center">
                  <img src={warning} />
                  <div className="text-[14px] text-[#000000] font-bold ml-[8px]">
                    删除
                  </div>
                </div>
                <div className="flex items-center">
                  <div className="w-[24px]" />
                  <div className="text-[14px] text-[#000000] mt-[8px]">
                    <span>删除后无法恢复，是否继续</span>
                    <br />
                    <span>删除？</span>
                  </div>
                </div>
              </>
            }
            onConfirm={(e) => {
              e?.stopPropagation();
              handleEvent("ok");
            }}
            onCancel={(e) => {
              e?.stopPropagation();
            }}
            okText="确认"
            cancelText="取消"
          >
            <DeleteOutlined
              className="text-[#999999]"
              onClick={(e) => {
                e.stopPropagation();
                handleEvent("delete", data);
              }}
            />
          </Popconfirm>
        </div>
      )}
      {/* {isActive && showMenu && (
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
      )} */}
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
