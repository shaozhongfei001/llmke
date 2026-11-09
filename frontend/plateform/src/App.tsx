import { useEffect } from "react";
import { BrowserRouter } from "react-router-dom";
import { MyRoutes } from "@/router/index";
import { ConfigProvider } from "antd";
import zh_CN from "antd/es/locale/zh_CN";
import antTheme from "@/styles/antTheme";
import { makeSpectraTheme } from "@/styles/spectraTheme";
import "@/styles/spectra.tokens.css";
import "@/styles/spectra-pages.less";
import { RAG_APP_NAME } from "./const";
import { AppPassportProvider } from "./core/helps";

/** SPECTRA 主题作用域挂在 body 上：只用于 CSS 变量作用域，不设置任何字号 */
const SPECTRA_ATTR = "data-spectra-theme";

function App() {
  useEffect(() => {
    document.body.setAttribute(SPECTRA_ATTR, "1");
    return () => document.body.removeAttribute(SPECTRA_ATTR);
  }, []);

  return (
    <ConfigProvider theme={makeSpectraTheme(antTheme)} locale={zh_CN}>
      <BrowserRouter>
        <AppPassportProvider name={RAG_APP_NAME}>
          <MyRoutes />
        </AppPassportProvider>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
