/**
 * LLMKE · SPECTRA 主题（Ant Design ThemeConfig）
 *
 * 设计口径（docs/reviews/.../01_设计风格与页面规范.md §3、§5）：
 * - 只改颜色与表面；fontFamily / fontSize* / sizeStep / sizeUnit / borderRadius 与
 *   原 antTheme.ts 的中文字体链、控件密度**完全一致**（由 baseTheme 展开继承）。
 * - 不在这里写 fontSize、fontSizeSM、fontSizeLG、lineHeight 等字号类 token。
 * - components 中每个组件都先展开 baseTheme 的同名配置，避免覆盖既有
 *   Tabs.titleFontSize=16、Checkbox.fontSize=14、Layout.headerPadding 等显式值。
 */
import { theme, type ThemeConfig } from "antd";

export const spectraColors = {
  canvas: "#090D11",
  shell: "#0B1014",
  surface: "#10181C",
  surfaceRaised: "#142026",
  surfaceHover: "#1A292E",
  line: "#344044",
  lineSoft: "#243035",
  text: "#F0F2F0",
  textSecondary: "#B8C3C3",
  textMuted: "#91A1A3",
  gold: "#D8BD89",
  goldSoft: "#A98D62",
  goldHover: "#E7CFA1",
  cyan: "#94CED2",
  mint: "#A9D8BA",
  warning: "#D9AA6D",
  danger: "#E28683",
  focus: "#E8D4A7",
  onGold: "#111915"
} as const;

/** 在既有 baseTheme 之上叠加 SPECTRA 颜色；字号/字族/尺寸原样继承 */
export function makeSpectraTheme(baseTheme: ThemeConfig): ThemeConfig {
  const baseToken = baseTheme.token || {};
  const baseComponents = baseTheme.components || {};

  return {
    ...baseTheme,
    algorithm: theme.darkAlgorithm,
    token: {
      ...baseToken,
      colorPrimary: spectraColors.gold,
      colorInfo: spectraColors.cyan,
      colorSuccess: spectraColors.mint,
      colorWarning: spectraColors.warning,
      colorError: spectraColors.danger,
      colorLink: spectraColors.cyan,
      colorBgBase: spectraColors.canvas,
      colorBgLayout: spectraColors.canvas,
      colorBgContainer: spectraColors.surface,
      colorBgElevated: spectraColors.surfaceRaised,
      colorBgSpotlight: spectraColors.surfaceRaised,
      colorBgMask: "rgba(4, 7, 9, 0.72)",
      colorText: spectraColors.text,
      colorTextSecondary: spectraColors.textSecondary,
      colorTextTertiary: spectraColors.textMuted,
      colorTextQuaternary: "#6F7E81",
      colorTextPlaceholder: spectraColors.textMuted,
      colorTextHeading: spectraColors.text,
      colorBorder: spectraColors.line,
      colorBorderSecondary: spectraColors.lineSoft,
      colorSplit: spectraColors.lineSoft,
      colorFillSecondary: "rgba(148, 206, 210, 0.06)",
      colorFillTertiary: "rgba(148, 206, 210, 0.04)",
      colorFillQuaternary: "rgba(148, 206, 210, 0.03)"
    },
    components: {
      ...baseComponents,
      Layout: {
        ...baseComponents.Layout,
        headerBg: spectraColors.shell,
        siderBg: spectraColors.shell,
        bodyBg: spectraColors.canvas,
        footerBg: spectraColors.canvas
      },
      Tabs: {
        ...baseComponents.Tabs,
        itemColor: spectraColors.textSecondary,
        itemHoverColor: spectraColors.focus,
        itemSelectedColor: spectraColors.gold,
        itemActiveColor: spectraColors.gold,
        inkBarColor: spectraColors.gold
        // 保留 baseComponents.Tabs.titleFontSize = 16
      },
      Menu: {
        ...baseComponents.Menu,
        darkItemBg: spectraColors.shell,
        itemBg: "transparent",
        itemColor: spectraColors.textSecondary,
        itemHoverColor: spectraColors.focus,
        itemSelectedColor: spectraColors.gold,
        itemSelectedBg: "rgba(216, 189, 137, 0.10)",
        subMenuItemBg: "transparent"
      },
      Input: {
        ...baseComponents.Input,
        colorBgContainer: spectraColors.surface,
        colorTextPlaceholder: spectraColors.textMuted,
        colorBorder: spectraColors.line,
        activeBorderColor: spectraColors.cyan,
        hoverBorderColor: spectraColors.line
      },
      InputNumber: {
        colorBgContainer: spectraColors.surface,
        colorBorder: spectraColors.line,
        activeBorderColor: spectraColors.cyan
      },
      Button: {
        ...baseComponents.Button,
        // gold 底深字；同时保留 baseComponents.Button.colorBorder = "#eee" 的显式值，
        // 因此这里覆盖为 SPECTRA 分隔线色（颜色项，不是字号项）
        colorBorder: spectraColors.line,
        colorBgContainer: spectraColors.surface,
        defaultBg: spectraColors.surface,
        defaultColor: spectraColors.textSecondary,
        defaultBorderColor: spectraColors.line,
        defaultHoverBg: spectraColors.surfaceHover,
        defaultHoverColor: spectraColors.focus,
        defaultHoverBorderColor: spectraColors.goldSoft,
        defaultActiveBg: spectraColors.surfaceHover,
        defaultActiveColor: spectraColors.focus,
        primaryColor: spectraColors.onGold,
        primaryShadow: "none"
      },
      Table: {
        headerBg: "#0E171B",
        headerColor: spectraColors.textSecondary,
        headerSplitColor: spectraColors.lineSoft,
        rowHoverBg: spectraColors.surfaceHover,
        borderColor: spectraColors.lineSoft,
        colorBgContainer: "transparent",
        footerBg: "transparent"
      },
      Select: {
        ...baseComponents.Select,
        selectorBg: spectraColors.surface,
        optionSelectedBg: "rgba(216, 189, 137, 0.14)",
        optionSelectedColor: spectraColors.gold,
        optionActiveBg: spectraColors.surfaceHover,
        colorBorder: spectraColors.line,
        colorTextPlaceholder: spectraColors.textMuted
      },
      Modal: {
        contentBg: spectraColors.surfaceRaised,
        headerBg: spectraColors.surfaceRaised,
        titleColor: spectraColors.text,
        colorBgMask: "rgba(4, 7, 9, 0.72)"
      },
      Drawer: {
        colorBgElevated: spectraColors.surfaceRaised
      },
      Dropdown: {
        colorBgElevated: spectraColors.surfaceRaised,
        controlItemBgHover: spectraColors.surfaceHover
      },
      Tooltip: {
        colorBgSpotlight: spectraColors.surfaceRaised,
        colorTextLightSolid: spectraColors.text
      },
      Tag: {
        defaultBg: "rgba(148, 206, 210, 0.10)",
        defaultColor: spectraColors.cyan
      },
      Pagination: {
        itemBg: "transparent",
        itemActiveBg: "rgba(216, 189, 137, 0.16)",
        colorPrimary: spectraColors.gold,
        colorPrimaryHover: spectraColors.goldHover
      },
      Card: {
        colorBgContainer: spectraColors.surface,
        colorBorderSecondary: spectraColors.line
      },
      Empty: {
        colorTextDescription: spectraColors.textMuted
      },
      Slider: {
        railBg: "#223034",
        railHoverBg: "#2C3C41",
        trackBg: spectraColors.gold,
        trackHoverBg: spectraColors.goldHover,
        handleColor: spectraColors.gold,
        handleActiveColor: spectraColors.goldHover
      },
      Switch: {
        colorPrimary: spectraColors.gold,
        colorPrimaryHover: spectraColors.goldHover,
        handleBg: spectraColors.text
      },
      Radio: {
        ...baseComponents.Radio,
        buttonSolidCheckedBg: spectraColors.gold,
        buttonSolidCheckedColor: spectraColors.onGold,
        buttonCheckedBg: spectraColors.surfaceHover
      },
      Checkbox: {
        ...baseComponents.Checkbox,
        colorPrimary: spectraColors.gold
      },
      Divider: {
        colorSplit: spectraColors.lineSoft
      },
      Collapse: {
        headerBg: "transparent",
        contentBg: "transparent"
      },
      Message: {
        contentBg: spectraColors.surfaceRaised
      },
      Notification: {
        colorBgElevated: spectraColors.surfaceRaised
      },
      Segmented: {
        itemSelectedBg: spectraColors.surfaceHover,
        itemSelectedColor: spectraColors.gold,
        trackBg: "#0E171B"
      },
      Form: {
        labelColor: spectraColors.textSecondary
      },
      Typography: {
        ...baseComponents.Typography,
        colorText: spectraColors.text,
        colorTextDescription: spectraColors.textMuted
      },
      Progress: {
        defaultColor: spectraColors.gold,
        remainingColor: "#223034"
      },
      Popover: {
        colorBgElevated: spectraColors.surfaceRaised
      },
      Tree: {
        colorBgContainer: "transparent",
        nodeSelectedBg: "rgba(216, 189, 137, 0.12)"
      },
      Upload: {
        colorFillAlter: "transparent"
      }
    }
  };
}

export default makeSpectraTheme;
