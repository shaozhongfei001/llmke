import EventEmitter from "events";

export const templateEventBus = new EventEmitter();

export enum TEMPLATE_EVENT_NAME {
  SAVE = "save"
}
