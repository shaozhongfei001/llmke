import EventEmitter from 'events';

export const editorEventBus = new EventEmitter();

export enum EDITOR_EVENT_NAME {
  PROMPT = 'prompt',
}
