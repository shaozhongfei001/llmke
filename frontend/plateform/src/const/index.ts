export const RAG_APP_NAME = "rag_ai";
export const RAG_AUTH_PLUGIN_PREFIX = "gitech_ril:";
export const MOCK_MODEL_NAME = "GienModel-32b-Finance";

/**
 * @description explanation for fields in setting page
 */

export const EXPLANATION_TEMPERATURE = `温度是模型回答的倾向性，取值范围一般是0～1; 取值趋近0代表着模型回答会更严谨，适合回答检索类问题; 取值趋近1则代表回答更发散，适合回答创新性的问题；`;
export const EXPLANATION_TOP_P = `top_p 用于控制大模型生成策略，决定了模型在生成下一个词时，从累积概率达到 p 的最小词集合中进行采样。通常设置在0.8 - 0.95之间，top_p越低模型用词越保守，越高越活跃。`;
export const EXPLANATION_MAXTOKENS = `max_tokens代表模型窗口大小，即一次问答大模型一次能够接受的字符串最大长度，包括用户的提问和模型的回答；多轮对话中历史对话内容也包括在内；最大值取决于大模型本身是否支持；`;
export const EXPLANATION_TOP_K = `top_k代表模型最终取信的文本块数，例如门槛top_p = 0.8，top_k = 3，意味着模型会依据相似度高低取前3个大于0.8的文本块，即使当前可能有大于3个文本块的相似度大于0.8；`;
export const EXPLANATION_KB_NAME = `当前选中的知识库列表，支持多选；`;
export const EXPLANATION_PROMPT = `提示词用于指定聊天的背景和上下文，或者让助手采取某个人格来回答你的问题；`;
export const EXPLANATION_SIMILAR_THRESHOLD = `score_threshold参数是模型进行重排序时，对于文本块取舍的门槛值；`;
export const EXPLANATION_MAX_ROUND = `交互对话场景里，系统能够记忆并有效关联的用户与模型之间来回交流的最大次数；`;
export const EXPLANATION_DEPENDON_KB = `开关开启，则若系统未在知识库、数据库等企业知识数据范围内检索到答案，则直接拒绝回答相关问题；`;

export const version = "V1.1";

//temperature 0.3
//score_threshold  0.1
// top_k： 10
// top_p： 0.8
// max_tokens： 4096
// max_round： 5
// defaultAnswer： "您好！我注意到您的消息中可能包含了一些敏感的内容。为了保证社区的友好氛围，我们无法继续就此话题进行讨论。如果您有其他问题或需要帮助，我很乐意继续为您服务！谢谢您的理解和支持。"
