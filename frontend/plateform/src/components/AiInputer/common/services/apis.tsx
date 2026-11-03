import {
  chat_history_data_mock1,
  chat_reference_mock,
  dialog_create_mock,
  dialog_delete_mock,
  dialog_history_mock,
  dialog_rename_mock,
  helper_list_mock
} from "./mocks";

export const apis = {
  dialog_create: {
    url: "/qa/dialogue/create",
    method: "post",
    mockData: dialog_create_mock
  },
  dialog_rename: {
    url: "/qa/dialogue/reName",
    method: "post",
    mockData: dialog_rename_mock
  },
  dialog_history: {
    url: "/qa/dialogue/list",
    method: "get",
    mockData: dialog_history_mock
  },
  dialog_delete: {
    url: "/qa/dialogue/delete",
    method: "delete",
    mockData: dialog_delete_mock
  },
  chat_start: { url: "/qa/ai/question", method: "post", mockData: {} }, // need to use fetch
  sd_chat_start: {
    url: "/qa/ai/questionForSingleDocument",
    method: "post",
    mockData: {}
  }, // need to use fetch
  chat_history_data: {
    url: "/qa/dialogue/getDialogBySessionId",
    method: "get",
    mockData: chat_history_data_mock1
  },
  chat_reference: {
    url: "/qa/ai/knowledge",
    method: "post",
    mockData: chat_reference_mock
  },
  helper_list: {
    url: "/qa/search/config/searchList",
    method: "get",
    mockData: helper_list_mock
  },
  audio_upload: {
    url: "/qa/ai/audioUploadAndIdentify",
    method: "post",
    mockData: {}
  },
  feed_back: {
    url: "/qa/feedback",
    method: "post",
    mockData: {}
  },
  feedback_list: {
    url: "/qa/feedback/que/list",
    method: "get",
    mockData: {}
  },
  // /qa/feedback/cancel?id=47
  feedback_cancel: {
    url: "/qa/feedback/cancel",
    method: "delete",
    mockData: {}
  },
  upload_files: {
    url: "/index/knowledgeBase/file/uploadFiles",
    method: "post",
    mockData: {}
  },
  file_status: {
    url: "/index/knowledgeBase/file/getFileStatusById",
    method: "get",
    mockData: {}
  },
  // PAGE-CITATION-E2E-20261103：global 引用的 metadata 只有 file_id/title/locator，
  // 没有 source/convertedFilePath。点抽屉条目时用 file_id 回查文件详情补路径。
  // 运行时响应为 {success,errorMsg,errorCode,data:KnowledgeBaseFileDTO} 包裹（见 servers.ts 解包）。
  file_detail: {
    url: "/index/knowledgeBase/file/getById",
    method: "get",
    mockData: {}
  },
  file_status_uids: {
    url: "/index/knowledgeBase/file/getFileStatusByUids",
    method: "get",
    mockData: {}
  },
  file_exist: {
    url: "/index/knowledgeBase/file/exist",
    method: "get",
    mockData: {}
  }
};
