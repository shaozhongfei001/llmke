import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Provider } from "react-redux";
import { store } from "./storage/state/index.ts";
import "@/assets/styles/globalLess.less";
import "@/styles/index.css";
import { AiChatProvider } from "./components/AiChat/core/useStateStore.tsx";
import { AiCompareProvider } from "./components/AiChatComparison/core/useStateStore.tsx";
import { SdAiChatProvider } from "./components/SdAiChat/core/useStateStore.tsx";
import "antd/dist/reset.css";
import "@mxmweb/zui/style.css";
import "@mxmweb/rtext/style.css";
import "@mxmweb/fviewer/style.css";
import "@mxmweb/aichat/style.css";
import "@mxmweb/xviewer/style.css";
import "@mxmweb/nodegraph/style.css";
import "@gientech/modual/style.css";

import { registerPDFWorker } from "@gientech/modual/streamFilesReader";
registerPDFWorker("/worker/pdf.worker.min.js");
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false, // default: true
      retry: 0
    }
  }
});
ReactDOM.createRoot(document.getElementById("root")!).render(
  <Provider store={store}>
    <QueryClientProvider client={queryClient}>
      <SdAiChatProvider>
        <AiChatProvider>
          <AiCompareProvider>
            <App />
          </AiCompareProvider>
        </AiChatProvider>
      </SdAiChatProvider>
    </QueryClientProvider>
  </Provider>
);
