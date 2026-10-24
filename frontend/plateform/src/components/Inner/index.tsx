import { Breadcrumb, Button, ConfigProvider, Divider, Spin } from 'antd';
import { ReactNode, useMemo } from 'react';

interface InnerProps {
  children?: any;
  title?: string;
  nav?: NavItemType[];
  btn_group?: BtnItemType[];
  event_emitter?: (eventName: string, data: any) => any;
  style?: any;
  breakProps?: any;
  sub?: any;
  showBread?: boolean;
  separator?: string;
  loading?: boolean;
}
interface NavItemType {
  label: string;
  key: string;
  children?: string | ReactNode;
}

interface BtnItemType {
  eventName: string;
  type?: 'primary' | 'dashed' | 'link' | 'text' | 'default';
  text: string;
  icon?: ReactNode;
  loading?: boolean | { delay: number };
}
function Inner(props: InnerProps) {
  const {
    title,
    nav,
    sub,
    btn_group,
    event_emitter,
    style,
    children,
    showBread = false,
    separator = '>',
    loading = false,
  } = props;
  // const dynamicHeight = useMemo(() => {
  //   if (title && sub && btn_group) {
  //     return 'calc(100% - 168px)';
  //   } else if (title && sub) {
  //     return 'calc(100% - 115px)';
  //   } else if (btn_group && sub) {
  //     return 'calc(100% - 115px)';
  //   } else if (title) {
  //     return 'calc(100% - 75px)';
  //   } else if (btn_group) {
  //     return 'calc(100% - 45px)';
  //   } else if (sub) {
  //     return 'calc(100% - 45px)';
  //   } else {
  //     return 'calc(100% - 25px)';
  //   }
  // }, [title, sub, btn_group]);
  return (
    <ConfigProvider
    // theme={{
    //   token: {
    //     colorBorder: '#f6f6f6',
    //     colorText: '#232111',
    //     colorTextDisabled: '#999',
    //     colorTextPlaceholder: '#999',
    //     colorBgContainerDisabled: '#666',
    //     colorBgBase: '#fff',
    //     ...style?.token,
    //   },
    //   components: {
    //     Button: {
    //       defaultBg: '#1D70F5',
    //       defaultColor: '#fff',
    //       colorText: '#fff',
    //       defaultActiveBg: '#1D70F5',
    //       colorIcon: '#fff',
    //       defaultHoverBg: '#1D70F5',
    //     },
    //     Tabs: {
    //       colorBorder: '#f6f6f6',
    //       cardPaddingSM: '4px 10px',
    //     },
    //     ...style?.components,
    //   },
    // }}
    >
      <div
        className="h-full w-full"
        style={{
          // padding: '12px 24px',
          backgroundColor: props?.style?.setting?.bgColor ? props.style.setting.bgColor : '#fff',
          overflow: props?.style?.setting?.container ? props.style.setting.container : 'auto',
          padding: sub ? '16px 16px 16px 16px' : '0',
        }}
      >
        <div className="flex justify-between items-baseline flex-col">
          <div className="flex flex-col">
            {title && (
              <div className="flex gap-x-1 items-center justify-start">
                <div
                  className="rounded"
                  style={{
                    width: '3.5px',
                    height: '20px',
                    background: '#000',
                  }}
                ></div>
                <label
                  className="py-3 text-slate-800"
                  style={{
                    fontFamily: 'Source Han Sans CN',
                    fontSize: '20px',
                    fontWeight: '500',
                  }}
                >
                  {title}
                </label>
              </div>
            )}
            <Breadcrumb items={sub} separator={separator}></Breadcrumb>
          </div>
          {btn_group && sub && <Divider style={{ marginBottom: '8x' }} />}
          <div className="flex w-full  items-center justify-end">
            {btn_group &&
              btn_group?.length > 0 &&
              btn_group.map((btn: BtnItemType) => {
                return (
                  <Button
                    key={btn.text}
                    size="small"
                    type={btn?.type || 'default'}
                    icon={btn.icon}
                    loading={btn.loading}
                    style={{ fontSize: 12 }}
                    onClick={(e) => event_emitter && event_emitter(btn.eventName, e)}
                  >
                    {btn.text}
                  </Button>
                );
              })}
          </div>
        </div>

        <div className="children-holder relative w-full min-h-[400px]">{children}</div>

        {loading && (
          <div className="absolute bg-slate-50 top-0 left-0 flex justify-center items-center w-full h-full">
            <Spin size="large" />
          </div>
        )}
      </div>
    </ConfigProvider>
  );
}

export default Inner;
