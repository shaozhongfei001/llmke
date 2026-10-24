import React, { useState } from "react";
import { Button, Card, Input, Space, Typography, message } from "antd";
import {
  useSplitLayout,
  EventTypes
} from "@/components/SplitLayout/SplitLayoutContext";

const { Text } = Typography;

const LeftPanel: React.FC = () => {
  const [messageText, setMessageText] = useState("你好，右侧！");
  const [randomHistory, setRandomHistory] = useState<number[]>([]);
  const [receivedMessages, setReceivedMessages] = useState<string[]>([]);

  const { publish, useSubscribe } = useSplitLayout();

  useSubscribe<string>(EventTypes.DEMO_MSG_RIGHT, (msg) => {
    setReceivedMessages((prev) => [msg, ...prev.slice(0, 4)]);
  });

  const handleGenerateRandom = () => {
    const random = Math.floor(Math.random() * 1000);
    publish(EventTypes.DEMO_RANDOM_NUM, random);
    setRandomHistory((prev) => [random, ...prev.slice(0, 4)]);
    message.success("已发送随机数到右侧");
  };

  const handleSendMessage = () => {
    if (messageText.trim()) {
      publish(EventTypes.DEMO_MSG_LEFT, messageText.trim());
      setMessageText("");
      message.success("已发送消息到右侧");
    }
  };

  return (
    <div className="p-4 h-full flex flex-col">
      <Card
        title="左侧区域"
        className="mb-4"
        headStyle={{ background: "#f0f2f5" }}
      >
        <div className="space-y-4">
          <Text type="secondary">此面板宽度可控，高度占满屏幕</Text>

          <div>
            <Button type="primary" block onClick={handleGenerateRandom}>
              生成随机数
            </Button>
            <Text type="secondary" className="block mt-1">
              点击发送随机数到右侧
            </Text>
          </div>

          <div>
            <Input.TextArea
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              placeholder="输入要发送的消息"
              rows={2}
              className="mb-2"
            />
            <Button block onClick={handleSendMessage}>
              发送消息到右侧
            </Button>
          </div>
        </div>
      </Card>

      <Card title="最近发送的随机数" className="mb-4">
        {randomHistory.length > 0 ? (
          <Space direction="vertical" className="w-full">
            {randomHistory.map((num, index) => (
              <div key={index} className="flex justify-between items-center">
                <Text>{num}</Text>
                <Text type="secondary" className="text-xs">
                  {index === 0 ? "最新" : `${index + 1}分钟前`}
                </Text>
              </div>
            ))}
          </Space>
        ) : (
          <Text type="secondary">暂无发送记录</Text>
        )}
      </Card>

      <Card title="从右侧接收的消息" className="flex-1">
        {receivedMessages.length > 0 ? (
          <div className="space-y-2">
            {receivedMessages.map((msg, index) => (
              <div key={index} className="p-2 bg-blue-50 rounded">
                <Text>{msg}</Text>
              </div>
            ))}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center">
            <Text type="secondary">等待来自右侧的消息...</Text>
          </div>
        )}
      </Card>
    </div>
  );
};

export default LeftPanel;
