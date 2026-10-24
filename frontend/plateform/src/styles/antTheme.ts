import { ThemeConfig } from "antd";

export default {
  token: {
    fontFamily: "PingFangSC, 微软雅黑, Helvetic",
    colorSuccess: "#15ad2c",
    colorPrimary: "#1d70f5",
    colorInfo: "#1d70f5",
    colorWarning: "#fa8015",
    colorError: "#d70016",
    colorText: "#222222",
    colorTextSecondary: "#555555",
    colorTextTertiary: "#999999",
    fontSizeHeading4: 18,
    fontSizeXL: 18,
    sizeStep: 5,
    sizeUnit: 4,
    borderRadius: 4,
    fontColorHeading1: "#222222",
    fontColor: "#55555",
    fontColorHeading2: "#55555",
    fontColorHeading3: "#999999"
  },
  components: {
    Typography: {
      fontFamilyCode: "'PingFangSC',Aral,Helvetica",
      marginXS: 0,
      marginXXS: 0,
      paddingSM: 0,
      titleMarginBottom: "0",
      titleMarginTop: "0"
    },
    Layout: {
      headerPadding: "0px 16px"
    },
    Checkbox: {
      controlInteractiveSize: 14,
      fontSize: 14
    },
    Radio: {
      radioSize: 14
    },
    Tabs: {
      titleFontSize: 16
    },
    Button: {
      // colorPrimary: "#014DDF",
      colorBorder: "#eee"
    },
    Select: {
      optionPadding: 0
    },
    Input: {
      colorBorder: "#cccccc",
      colorTextPlaceholder: "#cccccc"
    },
    Popconfirm: {
      borderRadius: 8
    }
  }
} as ThemeConfig;
