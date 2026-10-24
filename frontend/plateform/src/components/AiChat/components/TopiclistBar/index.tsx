import { PlusCircleOutlined } from "@ant-design/icons";
import anime from "animejs";
import {
  Button,
  ConfigProvider,
  Flex,
  Layout,
  message,
  theme,
  Typography
} from "antd";
import React, { useContext, useEffect, useMemo, useRef, useState } from "react";
// import { chunkDataByTimeStamp } from '../helps';
import { cn } from "@udecode/cn";
import { cva } from "class-variance-authority";
import { ListItemType } from "../../@types/props";
import AnimatedIcon from "./AnimatedIcon";
import TopicListItem from "./TopicListItem";
import { useStateStore } from "../../core/useStateStore";
import BScroll from "@better-scroll/core";
import ScrollBar from "@better-scroll/scroll-bar";
import ObserveDOM from "@better-scroll/observe-dom";
import MouseWheel from "@better-scroll/mouse-wheel";
import NestedScroll from "@better-scroll/nested-scroll";
import CollapseIcon from "../../assets/img/collapseIcon.svg";
import UnCollapse from "../../assets/img/unCollapse.png";
import genera from "../../assets/img/genera.gif";
import { DeleteModal } from "../DeleteModal";
import { RenameModal } from "../RenameModal";
import Pullup from "@better-scroll/pull-up";
import { BScrollConstructor } from "@better-scroll/core/dist/types/BScroll";
import { IAppData } from "../../@types/sys";
import {
  api_deleteDialogue,
  api_renameDialogue
} from "../../core/services/servers";
import { useAiChatCore } from "@root/src/components/AiInputer/common/useAiChatCore";
BScroll.use(NestedScroll);
BScroll.use(MouseWheel);
BScroll.use(ObserveDOM);
BScroll.use(ScrollBar);
BScroll.use(Pullup);
const { Title } = Typography;
interface ITopicListBar {
  eventEmit: (type: string, data?: any) => void;
  data: ListItemType[];
  sortRules: any;
  actived: string | undefined;
}

const { Sider } = Layout;

const TopicListBar = (props: ITopicListBar) => {
  const { eventEmit } = props;
  const {
    serverInfo,
    appData,
    setAppData,
    setConversationData,
    conversationData,
    inputer
  } = useStateStore();
  const { setChatList, chunkDataByTimeStamp } = useAiChatCore({
    inputer,
    appData,
    setAppData,
    serverInfo,
    conversationData
  });
  const bscrollRef = useRef<BScrollConstructor>();
  const scrollRef = useRef(null);
  const [hovered, setHovered] = useState(false);
  const [curEditData, setCurEditData] = useState({ sessionId: "" });
  const [isModalOpen, setisModalOpen] = useState(false);
  const [isRenameModalOpen, setisRenameModalOpen] = useState(false);
  const [isPullUpLoad, setIsPullUpLoad] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const sideIcon = useRef(null);

  const serverInfoRef = useRef<{
    token: string;
    baseURL: string;
    mockMode?: boolean | undefined;
  }>();

  const appDataRef = useRef<IAppData>();

  const pullingUpHandler = () => {
    const _appData: IAppData | undefined = appDataRef.current;
    if (!_appData) return;
    const curPageNo = _appData.conversations_list_pagging.pageNo;
    if (curPageNo + 1 > _appData.conversations_list_pagging.totalPages) return;
    setIsPullUpLoad(true);

    setChatList({ page: curPageNo + 1 }, serverInfoRef.current, () => {
      setIsPullUpLoad(false);
    });
  };

  useEffect(() => {
    appDataRef.current = appData;
  }, [appData.conversations_list_pagging]);

  useEffect(() => {
    serverInfoRef.current = serverInfo;
    if (serverInfo.baseURL) {
      setChatList({ page: 1 }, serverInfoRef.current);
    }
  }, [serverInfo]);

  const deleteDialog = async (id: string) => {
    try {
      const createDialogueResponse = await api_deleteDialogue({
        data: {
          id
        },
        config: {
          url: serverInfo.baseURL,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      });
      if (createDialogueResponse) {
        setisModalOpen(false);
        message.success("删除成功!");
        eventEmit && eventEmit("create");
        setChatList({ page: 1 }, serverInfoRef.current);
        setAppData((pre) => {
          return {
            ...pre,
            activedConversation: undefined
          };
        });
        const defaultAssis = appData.assist_list.filter(
          (i: any) => i.isDefault
        );
        setConversationData((pre) => {
          const assist_id = defaultAssis.length
            ? defaultAssis[0].value
            : pre.assist_id
              ? pre.assist_id
              : appData.assist_list?.[0]?.value;
          return {
            ...pre,
            assist_id: assist_id || undefined
          };
        });
      } else {
        message.success("删除失败!");
      }
    } catch (error) {
      console.log(error);
    }
  };
  const deleteData = useRef({ sessionId: "" });
  const editDialog = async (data: any) => {
    try {
      const res = await api_renameDialogue({
        data: {
          label: data.new_name,
          sessionId: curEditData.sessionId
        },
        config: {
          url: serverInfo.baseURL,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      });
      if (res) {
        setisRenameModalOpen(false);
        setChatList({ page: 1 }, serverInfoRef.current);
        message.success("重命名成功!");
      } else {
        message.error("重命名失败");
      }
    } catch (e) {
      console.log(e);
    }
  };

  const handleEvent = (type: string, data?: any) => {
    console.log(type, data);

    switch (type) {
      case "click":
        eventEmit && eventEmit("click", data);
        break;
      case "edit":
        setCurEditData(data);
        setisRenameModalOpen(true);
        break;
      case "close_rename":
        setisRenameModalOpen(false);
        break;
      case "ok_rename":
        editDialog(data);
        break;
      case "delete":
        deleteData.current = data;
        setisModalOpen(true);
        break;
      case "ok":
        deleteDialog(deleteData.current.sessionId);
        break;
      case "close":
        setisModalOpen(false);
        break;
    }
  };

  useEffect(() => {
    if (sideIcon.current) {
      anime({
        targets: sideIcon.current,
        left: collapsed ? "5px" : "244px", // 动态调整位置
        easing: "easeInOutQuad", // 平滑的动画效果
        duration: collapsed ? 300 : 185 // 控制展开和收起的动画速率
      });
    }
  }, [collapsed]);

  useEffect(() => {
    if (scrollRef.current) {
      const scroll = new BScroll(scrollRef.current, {
        scrollY: true, // 使能垂直滚动
        pullUpLoad: true,
        click: true,
        probeType: 3, // 开启探针模式，可以监听滚动事件
        observeDOM: true, // 开启 observe-dom 插件
        // scrollbar: {
        //   fade: false,
        //   interactive: true,
        //   scrollbarTrackClickable: true,
        // },
        bounce: { top: false, bottom: false }, // 禁用上下回弹效果
        mouseWheel: {
          speed: 20,
          invert: false,
          easeTime: 300
        }
      });
      bscrollRef.current = scroll;
      scroll.on("pullingUp", () => {
        scroll.finishPullUp();
        pullingUpHandler();
      });
    }
  }, []);

  const listDataElements = useMemo(() => {
    if (!props.data) {
      return <div className=" flex justify-center items-center">no Data</div>;
    } else {
      // 排序列表
      const rules = props.sortRules
        ? props.sortRules
        : [{ label: "当天", dayPeriod: 1 }];
      const sortedList = chunkDataByTimeStamp(props.data, rules);
      const hasOtherOnly = rules.every(
        (rule: any) =>
          !sortedList[rule.label] || sortedList[rule.label].length === 0
      );
      return (
        <>
          {rules.map(
            (rule: any) =>
              sortedList[rule.label] &&
              sortedList[rule.label].length > 0 && (
                <React.Fragment key={rule.label}>
                  <div className="pt-[16px] w-full">
                    <div className="text-[12px] text-[#888888]">
                      {rule.label}
                    </div>
                  </div>
                  <div className="mt-[8px]">
                    {sortedList[rule.label].map((i: any) => (
                      <TopicListItem
                        isActive={props.actived === i.sessionId}
                        isDisabled={false}
                        key={i.sessionId}
                        data={i}
                        handleEvent={handleEvent}
                      />
                    ))}
                  </div>
                </React.Fragment>
              )
          )}
          {sortedList.other.length > 0 && !hasOtherOnly && (
            <React.Fragment key="other">
              <div className="pt-[16px] w-full">
                <div className="text-[12px] text-[#888888]">1年前</div>
              </div>

              {sortedList.other.map((i: any) => (
                <TopicListItem
                  isActive={props.actived === i.sessionId}
                  isDisabled={false}
                  key={i.sessionId}
                  data={i}
                  handleEvent={handleEvent}
                />
              ))}
            </React.Fragment>
          )}
          {hasOtherOnly && sortedList.other.length > 0 && (
            <React.Fragment key="other">
              {sortedList.other.map((i: any) => (
                <TopicListItem
                  isActive={props.actived === i.sessionId}
                  isDisabled={false}
                  key={i.sessionId}
                  data={i}
                  handleEvent={handleEvent}
                />
              ))}
            </React.Fragment>
          )}
        </>
      );
    }
  }, [props.data, appData.activedConversation]);

  return (
    <>
      <Sider
        collapsedWidth={0}
        width={244}
        collapsed={collapsed}
        theme={"light"}
        style={{
          minHeight: "100%",
          background: "transparent",
          boxShadow: `3px -9px 24px 0px #AFCAF333`,
          borderLeft: `1px solid #e9e9eb`,
          overflow: "hidden"
        }}
        className="rounded-tr-[4px] rounded-br-[4px] shadow-sm topic-list-bar"
      >
        <div className="side-container h-full w-full select-none relative px-[12px] py-[16px]">
          <Button
            block
            shape="default"
            type="default"
            size="large"
            className="z-[999] rounded-[4px] h-[40px] text-[14px]"
            style={{
              background: `linear-gradient(313.7deg, #BD9CFF -2.37%, #0359FF 100%)`,
              color: "#fff",
              opacity: 0.8,
              border: "none",
              width: "219px"
            }}
            onClick={() => {
              setAppData((pre) => {
                return {
                  ...pre,
                  activedConversation: undefined
                };
              });
              const defaultAssis = appData.assist_list.filter(
                (i: any) => i.isDefault
              );
              setConversationData((pre) => {
                const assist_id = defaultAssis.length
                  ? defaultAssis[0].value
                  : pre.assist_id
                    ? pre.assist_id
                    : appData.assist_list?.[0]?.value;

                return {
                  ...pre,
                  assist_id: assist_id || undefined
                };
              });
              eventEmit && eventEmit("create");
            }}
            icon={<PlusCircleOutlined />}
          >
            新建对话
          </Button>

          <div className="list h-[calc(100%-86px)] w-full flex-col gap-y-[5px] overflow-hidden">
            <div ref={scrollRef} className="h-full w-full">
              <div>{listDataElements}</div>
            </div>
          </div>
          <div className="w-full flex justify-center items-center">
            {isPullUpLoad && <img src={genera} width={30} />}
          </div>
        </div>
      </Sider>
      <div
        onClick={() => setCollapsed && setCollapsed(!collapsed)}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        ref={sideIcon}
        style={{
          position: "absolute",
          top: "45%",
          cursor: "pointer",
          zIndex: 999,
          transition: "none" // 移除CSS的transition，使用anime.js控制
        }} // 这里同样使用了具体的字符串值 'relative'
      >
        {/* <AnimatedIcon collapsed={collapsed} hovered={hovered} /> */}
        <img
          src={collapsed ? UnCollapse : CollapseIcon}
          width={12}
          height={40}
          className="ml-[8px]"
        />
      </div>
      {/* <div className="deleteModal">
        <DeleteModal
          isModalOpen={isModalOpen}
          handleOk={() => handleEvent('ok')}
          handleCancel={() => handleEvent('close')}
        />
      </div> */}
      <RenameModal
        isModalOpen={isRenameModalOpen}
        handleOk={handleEvent}
        handleCancel={() => handleEvent("close_rename")}
        data={curEditData}
      />
    </>
  );
};

export default TopicListBar;
