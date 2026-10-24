import { useEffect, useRef, useState } from "react";
import {
  api_completeArticle,
  api_completeSection,
  TYPE_api_completeArticle,
  TYPE_api_completeSection,
} from "../services/servers";
import { useStateStore } from "../states/useStateStore";
import { LLMStatus } from "./useAiEditorOperators";
import { message } from "antd";

type DataPayload = {
  articleId: string | number;
  // sectionId: string | number;
};

interface State {
  index: number;
  articleId: string | number;
  // sectionId: string | number;
  stream?: any;
  error?: any;
}

export const useSequentialSSE = () => {
  // const [current, setCurrent] = useState(0);
  const abortControllers = useRef<AbortController>(new AbortController());
  const { serverInfo } = useStateStore();
  const [state, setState] = useState<State>();
  const currentIndex = useRef<number>(0);

  const startRequests = (dataPayloads: DataPayload[]) => {
    if (currentIndex.current >= dataPayloads.length) {
      currentIndex.current = 0;
      return;
    }

    const dataPayload = dataPayloads[currentIndex.current];

    // abortControllers.current.push(abortController);

    // 在这里创建完整的 TYPE_api_completeSection 对象
    const completeSectionPayload: TYPE_api_completeArticle = {
      config: serverInfo,
      data: {
        ...dataPayload,
        signal: abortControllers.current.signal,
        onmessage: (ev: any) => {
          const result = ev.data;
          // setResults((prevResults: any) => [...prevResults, result]);
          // setCurrent((prevCurrent) => prevCurrent + 1);
          const curRes = JSON.parse(ev.data);
          console.log(curRes);
          setState({
            index: currentIndex.current,
            articleId: dataPayload.articleId,
            // sectionId: dataPayload.sectionId,
            stream: curRes, // 你需要根据实际情况来设置这个值
          });
        },
        onerror: (err: any) => {
          // 处理错误
          setState((p) => ({
            index: currentIndex.current,
            articleId: dataPayload.articleId,
            // sectionId: dataPayload.sectionId,
            error: err,
          }));
          currentIndex.current = 0; // 出错时重置 current
          closeAll();
          throw err;
        },
        onclose: () => {
          // 处理连接关闭
          // setCurrent((prevCurrent) => prevCurrent + 1);
          currentIndex.current += 1;
          startRequests(dataPayloads);
        },
      },
    };
    api_completeArticle(completeSectionPayload);
  };
  const closeAll = () => {
    abortControllers.current.abort();
    abortControllers.current = new AbortController();
  };
  return { state, startRequests, closeAll };
};
