export const helper_list_mock = {
  success: true,
  errorMsg: null,
  errorCode: null,
  data: {
    records: [
      {
        id: 114,
        status: 1,
        isDefault: 1,
        configJson:
          '{"config_name":"sdtest1","description":null,"model_name":"Qwen1.5-32B-Chat","temperature":0.3,"max_tokens":4096,"knowledge_base_name":"sdtest_config0","top_k":10,"score_threshold":0.3,"prompt":"你是一个智能助手，请总结知识库的内容来回答问题,请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括“知识库中未找到您要的答案!","similar_threshold":0.1,"system_prompt":"你是一个智能助手，请总结知识库的内容来回答问题,请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括“知识库中未找到您要的答案!","default":true}',
        name: 'sdtest1',
        des: null,
        createBy: 'sdtest',
        gmtCreate: '2024-08-22 14:09:24',
        permission: null,
        sensitiveWordIds: '',
        defaultAnswer:
          '您好！我注意到您的消息中可能包含了一些敏感的内容。为了保证社区的友好氛围，我们无法继续就此话题进行讨论。如果您有其他问题或需要帮助，我很乐意继续为您服务！谢谢您的理解和支持。',
        model: false,
        enabledFaq: 0,
      },
      {
        id: 138,
        status: 1,
        isDefault: 0,
        configJson:
          '{"config_name":"sdtest_faq","description":null,"model_name":"Qwen1.5-32B-Chat","temperature":0.3,"max_tokens":4096,"knowledge_base_name":"","top_k":10,"score_threshold":0.8,"prompt":"你是一个智能助手，请总结知识库的内容来回答问题,请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括“知识库中未找到您要的答案!","similar_threshold":0.1,"system_prompt":"你是一个智能助手，请总结知识库的内容来回答问题,请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括“知识库中未找到您要的答案!"}',
        name: 'sdtest_faq',
        des: null,
        createBy: 'sdtest',
        gmtCreate: '2024-08-28 10:03:19',
        permission: null,
        sensitiveWordIds: '',
        defaultAnswer:
          '您好！我注意到您的消息中可能包含了一些敏感的内容。为了保证社区的友好氛围，我们无法继续就此话题进行讨论。如果您有其他问题或需要帮助，我很乐意继续为您服务！谢谢您的理解和支持。',
        model: false,
        enabledFaq: 0,
      },
    ],
    total: 2,
    size: 999,
    current: 1,
    pages: 1,
  },
};

export const a = {
  success: true,
  errorMsg: null,
  errorCode: null,
  data: {
    records: [
      {
        id: 111,
        status: 1,
        isDefault: 1,
        configJson:
          '{"config_name":"sdtest_config","description":null,"model_name":"Qwen1.5-32B-Chat","temperature":0.3,"max_tokens":4096,"knowledge_base_name":"sdtest1","top_k":10,"score_threshold":0.8,"prompt":"你是一个智能助手，请总结知识库的内容来回答问题,请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括“知识库中未找到您要的答案!","default":true,"similar_threshold":0.5}',
        name: 'sdtest_config',
        des: null,
        createBy: 'admin',
        gmtCreate: '2024-08-13 14:33:56',
        permission: null,
        model: false,
      },
      {
        id: 134,
        status: 1,
        isDefault: 0,
        configJson:
          '{"model_name":"Qwen1.5-32B-Chat","temperature":0.3,"max_tokens":4096,"knowledge_base_name":"客服场景知识库;金融知识库","top_k":10,"score_threshold":0.8,"prompt":"你是一个智能助手，请总结知识库的内容来回答问题,请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括“知识库中未找到您要的答案!","similar_threshold":0.1}',
        name: '客服问答',
        des: null,
        createBy: 'admin',
        gmtCreate: '2024-08-26 12:55:49',
        permission: null,
        model: false,
      },
      {
        id: 133,
        status: 1,
        isDefault: 0,
        configJson:
          '{"model_name":"Qwen1.5-32B-Chat","temperature":0.5,"max_tokens":5012,"knowledge_base_name":"sdtest2","top_k":12,"score_threshold":0.8,"prompt":"你是一个智能助手，请总结知识库的内容来回答问题,请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括“知识库中未找到您要的答案!","similar_threshold":1.1}',
        name: 'sdtest_config2',
        des: null,
        createBy: 'admin',
        gmtCreate: '2024-08-23 18:14:23',
        permission: null,
        model: false,
      },
    ],
    total: 3,
    size: 999,
    current: 1,
    pages: 1,
  },
};
