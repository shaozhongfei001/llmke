import { PlusCircleOutlined } from '@ant-design/icons';
import anime from 'animejs';
import { Button, ConfigProvider, Flex, Layout, theme, Typography } from 'antd';
import React, { useContext, useEffect, useMemo, useRef, useState } from 'react';
// import { chunkDataByTimeStamp } from '../helps';
import { cn } from '@udecode/cn';
import { cva } from 'class-variance-authority';
import AnimatedIcon from './AnimatedIcon';
import TopicListItem from './TopicListItem';
import { useStateStore } from '../../core/useStateStore';
import { ConfigContext } from 'antd/es/config-provider';
import BScroll from '@better-scroll/core';
import ScrollBar from '@better-scroll/scroll-bar';
import ObserveDOM from '@better-scroll/observe-dom';
import MouseWheel from '@better-scroll/mouse-wheel';
import NestedScroll from '@better-scroll/nested-scroll';
import CollapseIcon from '../../../../../assets/nlpChat/collapseIcon.svg';
import { useAiChatCore } from '@/hfz/applications/AiChat/core/operators/useAiChatCore';
BScroll.use(NestedScroll);
BScroll.use(MouseWheel);
BScroll.use(ObserveDOM);
BScroll.use(ScrollBar);
const { Title } = Typography;
interface ITopicListBar {
  data: any[];
  sortRules: any;
  actived: string | undefined;
}

const { Sider } = Layout;

const TopicListBar = (props: ITopicListBar) => {
  const { appData, setAppData } = useStateStore();
  const scrollRef = useRef(null);
  const [hovered, setHovered] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const { chunkDataByTimeStamp } = useAiChatCore();
  const sideIcon = useRef(null);
  useEffect(() => {
    if (sideIcon.current) {
      anime({
        targets: sideIcon.current,
        left: collapsed ? '25px' : '244px', // 动态调整位置
        easing: 'easeInOutQuad', // 平滑的动画效果
        duration: collapsed ? 300 : 185, // 控制展开和收起的动画速率
      });
    }
  }, [collapsed]);

  useEffect(() => {
    if (scrollRef.current) {
      const scroll = new BScroll(scrollRef.current, {
        scrollY: true, // 使能垂直滚动
        click: true,
        probeType: 3, // 开启探针模式，可以监听滚动事件
        observeDOM: true, // 开启 observe-dom 插件
        scrollbar: {
          fade: false,
          interactive: true,
          scrollbarTrackClickable: true,
        },
        bounce: { top: false, bottom: false }, // 禁用上下回弹效果
        mouseWheel: {
          speed: 20,
          invert: false,
          easeTime: 300,
        },
      });
    }
  }, []);

  const listDataElements = useMemo(() => {
    if (!props.data) {
      return <div className=" flex justify-center items-center">no Data</div>;
    } else {
      // 排序列表
      const rules = props.sortRules ? props.sortRules : [{ label: '当天', dayPeriod: 1 }];
      const sortedList = chunkDataByTimeStamp(props.data, rules);
      const hasOtherOnly = rules.every(
        (rule) => !sortedList[rule.label] || sortedList[rule.label].length === 0
      );
      return (
        <>
          {rules.map(
            (rule) =>
              sortedList[rule.label] &&
              sortedList[rule.label].length > 0 && (
                <React.Fragment key={rule.label}>
                  <div className="pt-[16px] w-full">
                    <div className="text-[12px] text-[#888888]">{rule.label}</div>
                  </div>
                  <div className="mt-[16px]">
                    {sortedList[rule.label].map((i) => (
                      <TopicListItem
                        isActive={props.actived === i.sessionId}
                        isDisabled={false}
                        key={i.sessionId}
                        data={i}
                      />
                    ))}
                  </div>
                </React.Fragment>
              )
          )}
          {sortedList.other.length > 0 && !hasOtherOnly && (
            <React.Fragment key="other">
              <div className="pt-[16px] w-full">
                <div className="text-[12px] text-[#888888]">其他</div>
              </div>

              {sortedList.other.map((i) => (
                <TopicListItem
                  isActive={props.actived === i.sessionId}
                  isDisabled={false}
                  key={i.sessionId}
                  data={i}
                />
              ))}
            </React.Fragment>
          )}
          {hasOtherOnly && sortedList.other.length > 0 && (
            <React.Fragment key="other">
              {sortedList.other.map((i) => (
                <TopicListItem
                  isActive={props.actived === i.sessionId}
                  isDisabled={false}
                  key={i.sessionId}
                  data={i}
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
        theme={'light'}
        style={{
          minHeight: '100%',
          backgroundColor: 'rgba(255,255,255,.3)',
        }}
        className="rounded-tr-[4px] rounded-br-[4px] shadow-sm"
      >
        <div className="side-container h-full w-full select-none relative px-[16px] py-[16px]">
          <Button
            block
            shape="default"
            type="default"
            size="large"
            className="z-[999] rounded-[4px] h-[40px] text-[14px]"
            style={{ background: 'linear-gradient(#BD9CFF,#0359FF)', color: '#fff' }}
            onClick={() =>
              setAppData((pre) => {
                return {
                  ...pre,
                  activedConversation: undefined,
                };
              })
            }
            icon={<PlusCircleOutlined />}
          >
            新建对话
          </Button>

          <div ref={scrollRef} className="list h-full w-full flex-col gap-y-[5px]">
            <div className="h-auto w-full pb-[60px]">{listDataElements}</div>
          </div>
        </div>
      </Sider>
      <div
        onClick={() => setCollapsed && setCollapsed(!collapsed)}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        ref={sideIcon}
        style={{
          position: 'absolute',
          top: '45%',
          cursor: 'pointer',
          zIndex: 999,
          transition: 'none', // 移除CSS的transition，使用anime.js控制
        }} // 这里同样使用了具体的字符串值 'relative'
      >
        {/* <AnimatedIcon collapsed={collapsed} hovered={hovered} /> */}
        <img src={CollapseIcon} width={12} height={40} className="ml-[8px]" />
      </div>
    </>
  );
};

export default TopicListBar;
