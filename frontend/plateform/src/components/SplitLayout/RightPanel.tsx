import React, { useState } from "react";
import {
  Card,
  Button,
  Statistic,
  List,
  Typography,
  Input,
  message
} from "antd";
import {
  useSplitLayout,
  EventTypes
} from "@/components/SplitLayout/SplitLayoutContext";

const { Title, Text } = Typography;

const RightPanel: React.FC = () => {
  const [randomNumber, setRandomNumber] = useState<number | null>(null);
  const [receivedMessages, setReceivedMessages] = useState<string[]>([]);
  const [messageText, setMessageText] = useState("你好，左侧！");

  const { publish, useSubscribe } = useSplitLayout();

  useSubscribe<number>(EventTypes.DEMO_RANDOM_NUM, (number) => {
    setRandomNumber(number);
  });

  useSubscribe<string>(EventTypes.DEMO_MSG_LEFT, (msg) => {
    setReceivedMessages((prev) => [msg, ...prev.slice(0, 4)]);
  });

  const handleSendMessage = () => {
    if (messageText.trim()) {
      publish(EventTypes.DEMO_MSG_RIGHT, messageText.trim());
      setMessageText("");
      message.success("已发送消息到左侧");
    }
  };

  return (
    <div className="p-6 h-full overflow-auto">
      <Title level={3} className="mb-6">
        右侧区域
      </Title>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="随机数展示" className="shadow-sm">
          <div className="flex flex-col items-center justify-center py-8">
            {randomNumber !== null ? (
              <Statistic
                title="来自左侧的随机数"
                value={randomNumber}
                className="text-center"
                valueStyle={{
                  color: "#3f8600",
                  fontSize: "48px",
                  fontWeight: "bold"
                }}
              />
            ) : (
              <div className="text-center py-4">
                <Text type="secondary">等待来自左侧的随机数...</Text>
                <p className="text-sm mt-2">请点击左侧的按钮</p>
              </div>
            )}
          </div>
        </Card>

        <Card title="通信机制说明" className="shadow-sm">
          <div className="space-y-3">
            <div className="flex items-start">
              <span className="inline-block w-6 h-6 rounded-full bg-blue-500 text-white text-center mr-2 flex-shrink-0">
                1
              </span>
              <div>
                <Text strong>发布/订阅模式</Text>
                <p className="text-sm text-gray-600 mt-1">
                  容器组件提供事件总线，允许左右通过事件通信而不直接耦合
                </p>
              </div>
            </div>

            <div className="flex items-start">
              <span className="inline-block w-6 h-6 rounded-full bg-green-500 text-white text-center mr-2 flex-shrink-0">
                2
              </span>
              <div>
                <Text strong>双向通信</Text>
                <p className="text-sm text-gray-600 mt-1">
                  左右可以互相发送消息，支持任意数据类型
                </p>
              </div>
            </div>

            <div className="flex items-start">
              <span className="inline-block w-6 h-6 rounded-full bg-purple-500 text-white text-center mr-2 flex-shrink-0">
                3
              </span>
              <div>
                <Text strong>独立业务逻辑</Text>
                <p className="text-sm text-gray-600 mt-1">
                  容器组件仅负责布局和通信，业务逻辑由面板自行实现
                </p>
              </div>
            </div>

            <div className="mt-4">
              <Input.TextArea
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                placeholder="输入要发送到左侧的消息"
                rows={2}
                className="mb-2"
              />
              <Button type="primary" block onClick={handleSendMessage}>
                发送消息到左侧
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <Card title="来自左侧的消息" className="mt-6 shadow-sm">
        {receivedMessages.length > 0 ? (
          <List
            itemLayout="horizontal"
            dataSource={receivedMessages}
            renderItem={(msg, index) => (
              <List.Item>
                <List.Item.Meta
                  title={`消息 #${index + 1}`}
                  description={<Text>{msg}</Text>}
                />
                <div className="text-gray-400 text-sm">
                  {index === 0 ? "刚刚" : `${index + 1}分钟前`}
                </div>
              </List.Item>
            )}
          />
        ) : (
          <div className="text-center py-8">
            <Text type="secondary">暂无消息</Text>
            <p className="text-sm mt-2">左侧可以发送自定义消息到此处</p>
          </div>
        )}
      </Card>
    </div>
  );
};

export default RightPanel;
