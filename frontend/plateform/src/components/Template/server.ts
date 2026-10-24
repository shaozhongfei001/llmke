import { fetchEventSource } from "@microsoft/fetch-event-source";
import axios$ from "@root/src/apis";
interface ServerBase<D> {
  data: D;
  config: {
    signal: AbortSignal;
    baseURL: string;
    token: string;
    enableMock?: boolean;
  };
}

interface TYPE_api_optimize
  extends ServerBase<{
    signal: AbortSignal;
    params: any;
    onmessage: (ev: any) => any;
    onerror: (err: any) => any;
    onClose: () => any;
  }> {}
export const api_optimizePrompt = (props: TYPE_api_optimize) => {
  const { config, data } = props;
  const { onmessage, onerror, params, signal } = data;
  const eventSourceUrl = `${config.baseURL}/dw/prompt/optimize`;

  // 实际的 fetchEventSource 请求
  fetchEventSource(eventSourceUrl, {
    openWhenHidden: true,
    signal,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: config.token
    },
    body: JSON.stringify(params),
    onmessage: onmessage,
    onerror: onerror
  });
};

const prefix = "/proxy/sensitive";

export const getLibraryList = async (params: any) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/library?${new URLSearchParams(params).toString()}`
    );
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};
