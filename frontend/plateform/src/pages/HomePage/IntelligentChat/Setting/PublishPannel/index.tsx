import { useState, useEffect } from "react";
import {
  Input,
  Tabs,
  Tooltip,
  message,
  Typography,
  Spin,
  Alert,
  Select
} from "antd";
import {
  CopyOutlined,
  EyeOutlined,
  EyeInvisibleOutlined
} from "@ant-design/icons";
import copy from "copy-to-clipboard";
import "swagger-ui-react/swagger-ui.css";
import { ApiManager } from "./ApiManager";
import dayjs from "dayjs";
import { ApiDocRender } from "./ApiDocRender";
import { EmbeddingRender } from "./EmbeddingRender";
import { getApiKeys, createKey, deleteKey } from "./service.ts";
import openapiData from "./openapi_data.json";

const { Title, Paragraph } = Typography;

export interface ApiKey {
  id: string;
  apiKey: string;
  assistId: string;
  createdBy: string;
  createdAt: string;
  expiredAt: string;
  status: string;
}

export const getAvailableKeys = (list: ApiKey[]) =>
  list.filter(
    (k) => k.status === "active" && dayjs(k.expiredAt).isAfter(dayjs())
  );

export const CodeBlock = ({ children }: { children: React.ReactNode }) => {
  const textToCopy = String(children);
  const onCopy = () => {
    copy(textToCopy);
    message.success("已复制到剪贴板");
  };
  return (
    <div className="relative group">
      <pre className="bg-slate-100 text-slate-800 p-4 pr-12 rounded-md font-mono text-sm whitespace-pre-wrap break-words">
        <code>{children}</code>
      </pre>
      <Tooltip title="复制">
        <button
          onClick={onCopy}
          className="absolute top-3 right-3 p-1.5 border-none bg-slate-200 rounded-md cursor-pointer text-slate-600 hover:bg-slate-300 hover:text-slate-900 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          复制
        </button>
      </Tooltip>
    </div>
  );
};

export const mockOpenApi = {
  openapi: "3.0.0",
  info: {
    title: "Mock 智能体 API",
    version: "1.0.0",
    description: "这是一个用于演示的 mock OpenAPI 文档。"
  },
  paths: {
    "/api/v1/chat/completions": {
      post: {
        summary: "对话补全",
        description: "根据用户输入生成智能回复。",
        requestBody: {
          required: true,
          content: {
            "application/json": {
              schema: {
                $ref: "#/components/schemas/ChatCompletionRequest"
              }
            }
          }
        },
        responses: {
          "200": {
            description: "成功响应",
            content: {
              "application/json": {
                schema: {
                  $ref: "#/components/schemas/ChatCompletionResponse"
                }
              }
            }
          }
        }
      }
    }
  },
  components: {
    schemas: {
      ChatCompletionRequest: {
        type: "object",
        properties: {
          model: { type: "string", example: "your-model-name" },
          messages: {
            type: "array",
            items: {
              type: "object",
              properties: {
                role: { type: "string", example: "user" },
                content: { type: "string", example: "你好" }
              }
            }
          }
        }
      },
      ChatCompletionResponse: {
        type: "object",
        properties: {
          id: { type: "string", example: "chatcmpl-xxxxxxxx" },
          object: { type: "string", example: "chat.completion" },
          choices: {
            type: "array",
            items: {
              type: "object",
              properties: {
                index: { type: "integer", example: 0 },
                message: {
                  type: "object",
                  properties: {
                    role: { type: "string", example: "assistant" },
                    content: {
                      type: "string",
                      example: "你好！有什么可以帮助你的吗？"
                    }
                  }
                },
                finish_reason: { type: "string", example: "stop" }
              }
            }
          },
          usage: {
            type: "object",
            properties: {
              prompt_tokens: { type: "integer", example: 9 },
              completion_tokens: { type: "integer", example: 12 },
              total_tokens: { type: "integer", example: 21 }
            }
          }
        }
      }
    }
  }
};

export const PublishPannel = (props: any) => {
  const { drawConfig } = props;
  const [keyList, setKeyList] = useState<ApiKey[]>([]);
  const [selectedKey, setSelectedKey] = useState(keyList[0]?.apiKey || "");
  const [activeTabKey, setActiveTabKey] = useState("api-manager");
  const [appBaseUrl, setAppBaseUrl] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [apiDocUrl, setApiDocUrl] = useState("");

  useEffect(() => {
    // 从public/config.json中获取配置
    fetch("/config.json")
      .then((response) => response.json())
      .then((config) => {
        setAppBaseUrl(config.appBaseUrl);
        setApiBaseUrl(config.apiBaseUrl);
        setApiDocUrl(config.apiDocUrl);
        console.log("API Base URL:", config.apiBaseUrl);
      })
      .catch((error) => {
        console.error("Failed to load configuration:", error);
      });
  }, []);

  const fetchList = async () => {
    try {
      const param: any = {
        pageNo: 1,
        pageSize: 999,
        targetId: drawConfig.data.id
      };
      const res = await getApiKeys(param);
      if (res) {
        const keyList =
          (res.records || [])
            .filter(
              (k: {
                expireTime:
                  | string
                  | number
                  | Date
                  | dayjs.Dayjs
                  | null
                  | undefined;
              }) => dayjs(k.expireTime).isAfter(dayjs())
            )
            .sort(
              (
                a: {
                  gmtCreate:
                    | string
                    | number
                    | Date
                    | dayjs.Dayjs
                    | null
                    | undefined;
                },
                b: {
                  gmtCreate:
                    | string
                    | number
                    | Date
                    | dayjs.Dayjs
                    | null
                    | undefined;
                }
              ) => dayjs(b.gmtCreate).valueOf() - dayjs(a.gmtCreate).valueOf()
            ) || [];
        const latest = keyList[0]?.apiKey || "";
        if (keyList) {
          setKeyList(keyList);
        }
        if (latest) {
          setSelectedKey(latest);
        }
      }
    } catch (e) {}
  };

  useEffect(() => {
    fetchList();
  }, []);

  return (
    <div className="px-4 bg-white max-w-4xl mx-auto h-[90vh] flex flex-col">
      <div className="shrink-0 z-10 bg-white sticky top-0">
        <Tabs
          activeKey={activeTabKey}
          onChange={setActiveTabKey}
          items={[
            { key: "api-manager", label: "API Key 管理" },
            { key: "api", label: "API 发布" },
            { key: "embed", label: "网页内嵌" }
          ]}
        />
      </div>
      <div className="flex-1 overflow-y-auto min-h-0">
        {activeTabKey === "api-manager" && (
          <ApiManager
            onLatestKeyChange={(k) => setSelectedKey(k || "")}
            onKeyListChange={fetchList}
            agentId={drawConfig.data.id}
          />
        )}
        {activeTabKey === "api" && (
          <ApiDocRender
            keyList={keyList}
            // selectedKey={selectedKey}
            // onKeyChange={setSelectedKey}
            mockOpenApi={openapiData}
            apiBaseUrl={apiBaseUrl}
            apiDocUrl={apiDocUrl}
          />
        )}
        {activeTabKey === "embed" && (
          <EmbeddingRender
            keyList={keyList}
            // selectedKey={selectedKey}
            // onKeyChange={setSelectedKey}
            agentId={drawConfig.data.id}
            appBaseUrl={appBaseUrl}
          />
        )}
      </div>
    </div>
  );
};
