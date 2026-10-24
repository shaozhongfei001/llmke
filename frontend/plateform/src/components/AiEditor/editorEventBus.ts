import EventEmitter from "events";

export const editorEventBus = new EventEmitter();

export enum EDITOR_EVENT_NAME {
  // 点击溯源按钮
  CLICKRETRIEVE = "clickRetrieveTag",
  // 上传文档写作
  UPLOADFILE = "uploadFile",
  // 点击保存
  CLICKSAVE = "clickSave",
  // 开始写作
  START_WRITE = "startWrite",
  // 开始审核
  START_REVIEW = "startView",
}
