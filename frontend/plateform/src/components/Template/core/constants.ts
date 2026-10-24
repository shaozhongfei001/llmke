export const regex = /\{\{([^{}]+)\}\}/; ///\{\{([^}]+)\}\}/;
const empty_regex = /\{\{[^{}]*\}\}/;
const strictRegex = /(?<![a-zA-Z]){{[^{}]+}}(?![a-zA-Z])/g;
export const TypeOptions = [
  { value: "string", label: "string" },
  { value: "int", label: "int" },
  { value: "number", label: "number" },
  { value: "date", label: "date" },
  { value: "longString", label: "longString" },
  { value: "select", label: "select" }
];

export const primaryColor = "#155EEF";

export const TypeToValueType = {
  string: "text",
  int: "digit",
  number: "digit"
};

export const defaultColor = "#475467";

export const tagPlusStyle: React.CSSProperties = {
  height: 22,
  // background: token.colorBgContainer,
  borderStyle: "dashed"
};

export const tagInputStyle: React.CSSProperties = {
  width: 140,
  height: 32,
  marginInlineEnd: 8,
  verticalAlign: "top"
};
