import { BrowserRouter } from "react-router-dom";
import { MyRoutes } from "@/router/index";
import { Button, ConfigProvider } from "antd";
import zh_CN from "antd/es/locale/zh_CN";
import antTheme from "@/styles/antTheme";
import { RAG_APP_NAME } from "./const";
import { AppPassportProvider } from "./core/helps";
import CustomTooltip from "./components/CustomTooltip";

function App() {
  return (
    <>
      <ConfigProvider theme={antTheme} locale={zh_CN}>
        <BrowserRouter>
          <AppPassportProvider name={RAG_APP_NAME}>
            <MyRoutes />

          </AppPassportProvider>
        </BrowserRouter>
      </ConfigProvider>
    </>
  );
}

export default App;
