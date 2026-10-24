import { reference_data_transformData } from "../../CommonEditor/utils/tools";
import {
  ChatProcess,
  IReference,
  QAChatItem,
  StatusType
} from "../@types/props";
import { IConversation } from "../@types/sys";

const useDataTransformer = () => {
  const createDialog_to_conversationData = (rawdata: any): IConversation => {
    return {
      id: rawdata.sessionId,
      name: rawdata.label,
      status: StatusType.Pending, // 假设状态为 'active'，可以根据实际情况调整
      modify_timeStamp: new Date(rawdata.gmtModified).getTime(),
      assist_id: rawdata.createBy,
      history_data: rawdata.queryReplyPairList || [],
      queryId: ""
    };
  };
  // 处理 reference
  const parseReference = (referenceStr: string) => {
    try {
      return referenceStr ? JSON.parse(referenceStr) : [];
    } catch (error) {
      console.error("Failed to parse reference JSON:", error);
      return [];
    }
  };

  const parseHistoryData = (rawData: any) => {
    // 处理 reference
    if (!rawData) {
      console.error("No data provided");
      return null;
    }

    // 构建 chat_list，确保 queryList 存在且为数组
    const chatList = Array.isArray(rawData.queryReplyPairList)
      ? rawData.queryReplyPairList.map((item: any) => {
          const o = {
            id: item.query.queryId || item.reply.queryId || "unknown", // 确保有 ID，如果没有提供则设置为 'unknown'
            timeStamp: item.reply?.lastDate || item.query?.lastDate, // 确保有创建时间
            query: {
              content: item.query.content || "", // 默认为空字符串
              type: item.query.type || "text",
              audioUrl: item.query.audioUrl || "",
              queryId: item.query.queryId || item.reply.queryId || "unknown"
            },
            answer: {
              id: (item.reply && item.reply.id) || undefined,
              feedbackResult: isNaN(item?.reply?.feedbackResult)
                ? undefined
                : item.reply.feedbackResult,
              content: (item.reply && item.reply.content) || "", // 检查 reply 是否存在
              type: (item.reply && item.reply.type) || "text",
              reference:
                item.reply && item.reply.reference
                  ? reference_data_transformData(
                      parseReference(item.reply.reference),
                      item.reply.content
                    )
                  : []
            }
          };
          // console.log(o);
          return o;
        })
      : [];
    return chatList;
  };

  const assistantDTO_to_SelectOption = (data: any) => {
    return data.map((item: any) => {
      const config = JSON.parse(item.configJson);

      return {
        details: {
          model_name: config.model_name || "",
          temperature: config.temperature || "",
          max_tokens: config.max_tokens || "",
          prologue: config.prologue || ""
        },
        label: item.name,
        value: item.id
      };
    });
  };

  const stremDataToQAdata = (
    rawData: any
  ): {
    chat_status: ChatProcess;
    qaData: QAChatItem;
    modify_time: string;
  } => {
    const qaData: QAChatItem = {
      id: rawData.queryId || "",
      timeStamp: rawData.lastDate || Date.now(),
      query: {
        content: "", // 流数据中似乎没有提供查询内容，可能需要从其他地方获取
        type: "text" // 假设查询类型为文本
      },
      answer: {
        content: rawData.reply?.content || "",
        type: rawData.reply?.type || "markdown",
        reference:
          rawData?.reference || rawData?.docs
            ? reference_data_transformData(
                JSON.parse(rawData.reference || rawData.docs),
                rawData.reply?.content
              )
            : []
      }
    };

    return {
      chat_status: rawData.status,
      qaData: qaData,
      modify_time: new Date(rawData.lastDate).toISOString()
    };
  };

  return {
    parseHistoryData,
    assistantDTO_to_SelectOption,
    stremDataToQAdata,
    createDialog_to_conversationData
  };
};

export { useDataTransformer };
