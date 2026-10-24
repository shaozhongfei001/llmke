/** @jsxRuntime classic */
/** @jsx jsx */
import { jsx } from "@udecode/plate-test-utils";
import "./style.less";
jsx;

export const isMarkdownTableData = (str: string) => {
  // 按行拆分字符串
  const lines = str.trim().split("\n");

  // 检查行数是否足够
  if (lines?.length < 2) {
    return false;
  }
  const cols = lines[0].split("|").length;
  const r = lines.every((item: any) => {
    return item.split("|").length === cols;
  });

  if (!r) return r;
  // 检查表头和数据行是否以 | 开头和结尾
  for (let i = 0; i < lines.length; i++) {
    if (!lines[i].trim().startsWith("|") || !lines[i].trim().endsWith("|")) {
      return false;
    }
  }

  // 检查第二行是否包含分隔线
  // if (!lines[1].trim().includes("-")) {
  //   return false;
  // }

  return true;
};

const isMarkdownTableSeparator = (line: string) => {
  // 1. 基础检查：忽略首尾空格，并检查是否包含必要的字符
  const trimmedLine = line.trim();
  if (!trimmedLine.includes("|") || !trimmedLine.includes("-")) {
    return false;
  }

  // 2. 核心正则表达式：匹配有效的分割线模式
  // 解释：
  // ^\|?          -> 行首可以有一个可选的竖线
  // (\\s*:?-+:?\\s*\|)+  -> 核心模式单元（例如 " :---: |"），必须至少出现一次
  // \\s*          -> 可选的空白字符
  // :?            -> 一个可选的冒号（用于左对齐或居中）
  // -+            -> 至少一个连字符（构成分割线的主体）
  // :?            -> 一个可选的冒号（用于右对齐或居中）
  // \\s*          -> 可选的空白字符
  // \|            -> 一个竖线（分隔符）
  // \\s*\|?      -> 行尾可以有一个可选的竖线
  const separatorRegex = /^\|?(\s*:?-+:?\s*\|)+\s*\|?$/;

  return separatorRegex.test(trimmedLine);
};

const markdownTableToJSON = (mdTable: string) => {
  const rows = mdTable.trim().split("\n");
  const headers = rows[0].split("|").map((header) => header.trim());

  if (headers?.length > 2) {
    headers.pop();
    headers.shift();
  }

  const feakHeaders = headers.map((i, index) => index);

  const jsonData: any[] = [];

  let n = 1;

  if (rows.length > 1 && isMarkdownTableSeparator(rows[1])) {
    n = 2;
  }
  for (let i = n; i < rows.length; i++) {
    const cells = rows[i].split("|").map((cell) => cell.trim());
    if (cells?.length > 2) {
      cells.pop();
      cells.shift();
    }
    if (cells.length === headers.length) {
      const rowObject: any = {};
      feakHeaders.forEach((header, index) => {
        rowObject[header] = cells[index];
      });
      jsonData.push(rowObject);
    }
  }

  return { jsonData, headers };
};

export const createTable = (data: any): any => {
  const { jsonData, headers } = markdownTableToJSON(data);
  return (
    <fragment>
      <htable
        colSizes={new Array(headers.length - 1).fill("100%")}
        marginLeft={0}
        border={true}
      >
        <htr>
          {headers.map((key, index) => {
            return (
              <hth key={index}>
                <hp>
                  <htext bold>{key}</htext>
                </hp>
              </hth>
            );
          })}
        </htr>
        {jsonData.map((row, rowIndex) => (
          <htr key={rowIndex}>
            {Object.values(row).map((value, colIndex) => {
              return (
                <htd key={colIndex}>
                  <hp>{value}</hp>
                </htd>
              );
            })}
          </htr>
        ))}
      </htable>
      {/* <htable colSizes={[100, 100, 100, 100]} marginLeft={0} border={true}>
        <htr>
          <hth>
            <hp>
              <htext bold>序号</htext>
            </hp>
          </hth>
          <hth>
            <hp>
              <htext bold>姓名</htext>
            </hp>
          </hth>
        </htr>
        <htr>
          <htd>
            <hp>1</hp>
          </htd>
          <htd>
            <hp>张三</hp>
          </htd>
        </htr>
        <htr>
          <htd>
            <hp>2</hp>
          </htd>
          <htd>
            <hp>李四</hp>
          </htd>
        </htr>
      </htable> */}
    </fragment>
  );
};

export const tableValue: any = (data: any) => {
  return <fragment>{createTable(data)}</fragment>;
};
