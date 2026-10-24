import EventEmitter from "events";

export const eventBus = new EventEmitter();

export enum EventBusList {
  SHOW_SIDE_MENU = "show_side_menu"
}
