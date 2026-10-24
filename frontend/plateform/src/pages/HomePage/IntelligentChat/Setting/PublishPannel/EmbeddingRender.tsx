import { Select, Typography, Divider } from "antd";
import { CodeBlock, getAvailableKeys, ApiKey } from "./index";
import { useState } from "react";
import { useLocation } from "react-router-dom";

const { Paragraph, Text, Title } = Typography;

const initStyle = 'style="margin: 0; padding: 0; border: none"\n';

const platformOptions = [
  {
    label: "React",
    value: 'style={{ margin: 0, padding: 0, border: "none" }}\n'
  },
  {
    label: "Vue",
    value: initStyle
  },
  {
    label: "Html",
    value: initStyle + " "
  }
];

const EmbedIllustration = () => (
  <div className="flex justify-center my-2">
    {/* SVG插画占位，实际可替换为更美观的插画 */}
    <svg
      width="120"
      height="80"
      viewBox="0 0 120 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect x="10" y="20" width="100" height="50" rx="10" fill="#E8F3FF" />
      <rect
        x="25"
        y="35"
        width="70"
        height="20"
        rx="4"
        fill="#1677ff"
        fillOpacity="0.15"
      />
      <rect
        x="40"
        y="45"
        width="40"
        height="6"
        rx="3"
        fill="#1677ff"
        fillOpacity="0.3"
      />
    </svg>
  </div>
);

export const EmbeddingRender = ({
  keyList,
  agentId,
  appBaseUrl
}: {
  keyList: ApiKey[];
  // selectedKey: string;
  agentId: number;
  appBaseUrl: string;
  // onKeyChange: (k: string) => void;
}) => {
  const [selectPlatform, setSelectPlatform] = useState(platformOptions[0]);
  const [selectedKey, setSelectedKey] = useState(keyList[0]?.apiKey || "");

  return (
    <div className="bg-white rounded-lg px-2 shadow-sm">
      <span className="font-bold mr-[10px]">平台选择:</span>
      <Select
        size="small"
        style={{ minWidth: 220 }}
        labelInValue
        value={selectPlatform}
        onChange={(value) => {
          setSelectPlatform(value);
        }}
        options={platformOptions}
        disabled={keyList.length === 0}
      />
      {/* 免登录嵌入 */}
      <div className="flex justify-between items-start mt-[20px]">
        <div className="flex flex-col items-start gap-2">
          <Title level={5} className="text-[#1D2129] text-center mb-2">
            1. 免登录嵌入
          </Title>
          <Paragraph className=" w-[420px]  text-left text-wrap text-gray-400 mb-4">
            适用于无需用户身份校验的场景，iframe 代码中直接携带 API
            Key，用户无需登录即可访问。
          </Paragraph>
        </div>

        <Select
          size="small"
          style={{ minWidth: 220 }}
          value={selectedKey}
          onChange={setSelectedKey}
          options={keyList.map((k: ApiKey) => ({
            value: k.apiKey,
            label: k.apiKey.slice(0, 8) + "****" + k.apiKey.slice(-4)
          }))}
          disabled={keyList.length === 0}
        />
      </div>

      <div className="flex items-center mb-2 gap-2 justify-center">
        <Text type="secondary">嵌入代码：</Text>
      </div>
      <CodeBlock>
        {`<iframe\n  src=\"${appBaseUrl}?token=${
          selectedKey || "请先生成API Key"
        }\"\n  width=\"100%\"\n  height=\"100%\"\n ${
          selectPlatform.value
        }></iframe>`}
      </CodeBlock>
      <Paragraph type="warning" className="text-yellow-500 mt-2 text-center">
        免登录嵌入适合公开场景，API Key 可能被泄露，请妥善保管嵌入代码。
      </Paragraph>

      <Divider className="!my-8" />

      {/* 平台账号登录嵌入 */}
      <div className="flex flex-col items-start gap-2">
        <Title level={5} className="text-[#1D2129] text-center mb-2">
          2. 平台账号登录嵌入
        </Title>
        <Paragraph className="w-[620px]  text-left text-wrap text-gray-400 mb-4">
          适用于需要用户身份校验的场景，iframe 不携带 API
          Key，用户需在嵌入页面内登录平台账号后才能访问服务。
        </Paragraph>
      </div>

      <div className="flex items-center mb-2 gap-2 justify-center">
        <Text type="secondary">嵌入代码：</Text>
      </div>
      <CodeBlock>
        {`<iframe\n  src=\"${appBaseUrl}${agentId}\"\n  width=\"100%\"\n  height=\"100%\"\n ${selectPlatform.value}></iframe>`}
      </CodeBlock>
      <Paragraph type="warning" className="text-yellow-600 mt-2 text-center">
        用户需在嵌入页面内完成平台账号登录，适合有权限控制的业务场景。
      </Paragraph>
    </div>
  );
};
