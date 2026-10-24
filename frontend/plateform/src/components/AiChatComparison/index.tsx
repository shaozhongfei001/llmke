import { ConfigProvider, Drawer, Layout, Row, Col, Button } from "antd";
import { useEffect, useState } from "react";
import { useLayouts } from "./core/layouts/useLayouts";
import ChatDisplayer from "./components/ChatDisplayer";
import ChatInputer from "./components/ChatInputer";
import { useStateStore } from "./core/useStateStore";
import { FILEIMG } from "./core/constants";
import { DrawerContent } from "../AiChat/components/ChatDisplayer/components/DrawerContent";
import { ClearOutlined } from "@ant-design/icons";
import { useAiCompareCore } from "./core/operators/useAiCompareCore.tsx";

const { Content } = Layout;

interface IuseAiChat {
  url: string;
  token?: string;
  mockMode?: boolean;
  styles?: any;
  device?: string;
  sortRules?: { label: string; dayPeriod: number }[];
  handleEvent?: (type: string, data?: any) => void;
  dataChange?: (data: any[]) => void;
}
export const useAiChatComparison = (props: IuseAiChat) => {
  const { setServerInfo } = useStateStore();
  const { HeadLessContainer } = useLayouts();
  const { handleEvent } = props;
  const [sendLoading, setSendLoading] = useState(0);
  const [refreshIndex, setRefreshIndex] = useState(1);
  const [isShowClearBtn, setIsShowClearBtn] = useState(false);
  const { isRetriveSideOpen } = useAiCompareCore();

  //应用初始化
  useEffect(() => {
    appInital();
  }, [props.url, props.token, props.mockMode]);

  //应用初始化
  const appInital = () => {
    setServerInfo({
      token: props.token || "/", // 如果props.token存在则使用，否则使用空字符串
      url: props.url, // 如果props.url存在则使用，否则使用空字符串
      mockMode: props.mockMode
    });
  };

  const [content, setContent] = useState<any>(null);
  const [open, setOpen] = useState(false);
  const onClose = () => {
    setOpen(false);
  };

  const clickIndexes = async (data: any) => {
    setContent(data);
    setOpen(true);
  };

  const dataChange = (data: any[]) => {
    const _isShowClearBtn = !!data.length;
    if (isShowClearBtn !== _isShowClearBtn) {
      setIsShowClearBtn(_isShowClearBtn);
    }
  };

  return {
    AppElement: (
      <ConfigProvider
        theme={{
          algorithm: [],
          token: {
            borderRadius: 3,
            fontSize: 14,
            fontFamilyCode: "Helvetica",
            colorText: "#555555",
            fontSizeHeading4: 14,
            fontSizeHeading5: 12,
            lineHeightHeading5: 1.25,
            colorBgElevated: "#EFEFEF",
            colorError: "#D70016",
            colorWarning: "#FA8015",
            colorInfo: "#1D70F5",
            colorSuccess: "#15AD2C",
            colorPrimary: "#1963D1",
            colorPrimaryActive: "#1D70F5",
            colorTextSecondary: "#cccccc"
          },
          components: {
            Typography: {
              titleMarginBottom: "0.25rem",
              titleMarginTop: "0.25rem"
            },
            Layout: {
              siderBg: "#04336B"
            },
            Button: {
              contentFontSize: 12,
              contentFontSizeSM: 10,
              defaultHoverBorderColor: "",
              defaultHoverColor: "",
              colorBgBase: "#ffffff"
            }
          }
        }}
      >
        <HeadLessContainer>
          <Content>
            <HeadLessContainer isContent>
              <div className="w-full h-full relative min-h-[500px] overflow-y-auto">
                <ChatDisplayer
                  key={refreshIndex}
                  isNew={true}
                  clickIndexes={clickIndexes}
                  setSendLoading={setSendLoading}
                  handleEvent={handleEvent}
                  dataChange={dataChange}
                />
                {isShowClearBtn ? (
                  <div className="absolute bottom-[48px] w-full left-0 pl-1">
                    <Col
                      span={isRetriveSideOpen ? 12 : 16}
                      offset={isRetriveSideOpen ? 2 : 4}
                    >
                      <Row gutter={8} align={"bottom"} wrap={false}>
                        <Button
                          icon={<ClearOutlined />}
                          className="text-[#666] mb-[5px]"
                          onClick={() => setRefreshIndex(refreshIndex + 1)}
                        >
                          清空对话
                        </Button>
                      </Row>
                    </Col>
                  </div>
                ) : null}
                <div
                  className={`${isShowClearBtn ? "" : "absolute bottom-6 w-full"}`}
                >
                  <ChatInputer btnLoading={sendLoading} />
                </div>
                <ConfigProvider
                  drawer={{
                    styles: {
                      body: { padding: 0 },
                      header: { display: "none" }
                    }
                  }}
                >
                  <Drawer
                    title={
                      <div className="flex items-center">
                        <img
                          src={FILEIMG[content?.file_type || "doc"]}
                          width={18}
                          height={18}
                          className="mr-[6px]"
                        />
                        <div>{`${content?.title}.${content?.file_type}`}</div>
                      </div>
                    }
                    autoFocus={false}
                    onClose={onClose}
                    open={open}
                    width={600}
                    className="overflow-x-hidden"
                    destroyOnClose
                    afterOpenChange={(open) => {
                      if (!open) {
                        setContent(null);
                      }
                    }}
                  >
                    <DrawerContent content={content} onClose={onClose} />
                  </Drawer>
                </ConfigProvider>
              </div>
            </HeadLessContainer>
          </Content>
        </HeadLessContainer>
      </ConfigProvider>
    )
  };
};
