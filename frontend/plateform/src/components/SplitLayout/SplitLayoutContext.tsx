import {
  createContext,
  useContext,
  useCallback,
  useRef,
  useEffect,
  ReactNode,
  FC
} from "react";

type EventHandler<T = any> = (data: T) => void;

type EventBus = {
  subscribe: <T>(event: string, handler: EventHandler<T>) => void;
  unsubscribe: (event: string, handler: EventHandler) => void;
  publish: <T>(event: string, data?: T) => void;
};

interface SplitLayoutContextType {
  eventBus: EventBus;
}

interface SplitLayoutProviderProps {
  children: ReactNode;
}

const SplitLayoutContext = createContext<SplitLayoutContextType | null>(null);

export enum EventTypes {
  DEMO_RANDOM_NUM = "randomNumber",
  DEMO_MSG_LEFT = "messageFromLeft",
  DEMO_MSG_RIGHT = "messageFromRight",
  INDICATOR_FORM_CLICK = "indicatorFormClick",
  INDICATOR_FILTER = "indicatorFilter",
  CATEGORY_DESC_CHANGE = "categoryDescChange",
  CATEGORY_DESC_CHANGE_DONE = "categoryDescChangeDone",
  SAVE_CALCULATOR = "saveCalculator",
  SAVE_CALCULATOR_CONFIRM = "saveCalculatorConfirm",
  SAVE_CALCULATOR_ID = "saveCalculatorID"
}

const createEventBus = (): EventBus => {
  const handlers: Record<string, EventHandler[]> = {};

  return {
    subscribe<T>(event: string, handler: EventHandler<T>) {
      if (!handlers[event]) {
        handlers[event] = [];
      }
      handlers[event].push(handler as EventHandler);
    },

    unsubscribe(event: string, handler: EventHandler) {
      if (handlers[event]) {
        handlers[event] = handlers[event].filter((h) => h !== handler);
      }
    },

    publish<T>(event: string, data?: T) {
      if (handlers[event]) {
        handlers[event].forEach((handler) => handler(data));
      }
    }
  };
};

export const SplitLayoutProvider: FC<SplitLayoutProviderProps> = ({
  children
}) => {
  const eventBus = useRef(createEventBus()).current;

  return (
    <SplitLayoutContext.Provider value={{ eventBus }}>
      {children}
    </SplitLayoutContext.Provider>
  );
};

export const useSplitLayout = () => {
  const context = useContext(SplitLayoutContext);
  if (!context) {
    throw new Error("useSplitLayout must be used within a SplitLayoutProvider");
  }

  const publish = useCallback(
    <T,>(event: string, data?: T) => {
      context.eventBus.publish(event, data);
    },
    [context.eventBus]
  );

  const subscribe = useCallback(
    <T,>(event: string, handler: EventHandler<T>) => {
      context.eventBus.subscribe(event, handler);
      return () => context.eventBus.unsubscribe(event, handler);
    },
    [context.eventBus]
  );

  const useSubscribe = <T,>(event: string, handler: EventHandler<T>) => {
    useEffect(() => {
      const unsubscribe = subscribe(event, handler);
      return () => unsubscribe();
    }, [event, handler, subscribe]);
  };

  return {
    publish,
    subscribe,
    useSubscribe
  };
};
