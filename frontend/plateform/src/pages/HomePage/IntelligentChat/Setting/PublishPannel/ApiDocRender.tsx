import { useEffect, useState } from "react";
import { Select, Spin } from "antd";
import { CodeBlock, getAvailableKeys, ApiKey } from "./index";
import SwaggerUI from "swagger-ui-react";
import "swagger-ui-react/swagger-ui.css";
import { ApiOutlined } from "@ant-design/icons";

interface ApiDocRenderProps {
  keyList: ApiKey[];
  // selectedKey: string;
  // onKeyChange: (k: string) => void;
  apiBaseUrl: string;
  apiDocUrl: string;
  mockOpenApi: any;
}

export const ApiDocRender = ({
  keyList,
  apiBaseUrl,
  apiDocUrl,
  mockOpenApi
}: ApiDocRenderProps) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [useMock, setUseMock] = useState(false);
  const [exampleType, setExampleType] = useState<"curl" | "js" | "python">(
    "curl"
  );
  const [selectedKey, setSelectedKey] = useState(keyList[0]?.apiKey || "");

  useEffect(() => {
    fetch(apiDocUrl)
      .then((res) => {
        if (!res.ok) throw new Error("文档接口不可用");
        return res.json();
      })
      .then(() => setLoading(false))
      .catch(() => {
        setError("API 文档加载失败，已切换为演示文档");
        setUseMock(true);
        setLoading(false);
      });
  }, [apiDocUrl]);

  if (loading)
    return (
      <div className="flex justify-center py-8">
        <Spin />
      </div>
    );

  const apiKey = selectedKey || "<API_KEY>";
  const serverUrl = `http://${apiBaseUrl}apis/create`;
  const exampleMap = {
    curl: `curl -X POST \\
  ${serverUrl} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: ${apiKey}" \\
  -d '{\n    "label": "对话名称",\n    "sessionId": "会话ID",\n    "sysType": "INT_SESSION",\n     "kbId": 0\n  }'`,
    js: `fetch('${serverUrl}', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': '${apiKey}'
  },
  body: JSON.stringify({
    label: '对话名称',
    sessionId: '会话ID',
    sysType: 'INT_SESSION',
    kbId: 0
  })
})
  .then(res => res.json())
  .then(data => console.log(data));`,
    python: `import requests

url = '${serverUrl}'
headers = {
    'Content-Type': 'application/json',
    'Authorization': '${apiKey}'
}
data = {
    'label': '对话名称',
    'sessionId': '会话ID',
    'sysType': 'INT_SESSION',
    'kbId': 0
}
response = requests.post(url, headers=headers, json=data)
print(response.json())`
  };

  return (
    <div>
      <div className="flex items-center mb-2 gap-2">
        <span className="text-gray-500 text-sm">选择用于演示的 API Key：</span>
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
      <CodeBlock>{`Authorization: ${
        selectedKey || "请先生成API Key"
      }`}</CodeBlock>
      <div className="mb-4 px-5">
        <div className="flex items-center gap-2 text-xl mb-2 mt-3">
          {/* <ApiOutlined style={{fontSize: 16}} /> */}
          <span>请求示例</span>
        </div>
        <div className="mb-3">
          <span className="inline-block bg-blue-50 border border-blue-200 text-blue-700 rounded px-3 py-1 font-mono text-base shadow-sm">
            服务器地址: <span className="font-semibold">{apiBaseUrl}</span>
          </span>
        </div>
        <div className="flex flex-col items-end">
          <Select
            size="middle"
            style={{ width: 160, marginBottom: 12 }}
            value={exampleType}
            onChange={setExampleType}
            options={[
              { value: "curl", label: "cURL" },
              { value: "js", label: "JavaScript" },
              { value: "python", label: "Python" }
            ]}
          />
          <div style={{ width: "100%" }}>
            <div
              style={{
                boxShadow: "0 2px 16px 0 #e6e6e6",
                borderRadius: 10,
                overflow: "hidden",
                marginTop: 4
              }}
            >
              <CodeBlock>{exampleMap[exampleType]}</CodeBlock>
            </div>
          </div>
        </div>
      </div>
      <div className="mt-4">
        <SwaggerUI
          {...(useMock ? { spec: mockOpenApi } : { url })}
          docExpansion="list"
          defaultModelsExpandDepth={-1}
          supportedSubmitMethods={[]}
        />
      </div>
    </div>
  );
};
