/** @jsxRuntime classic */
/** @jsx jsx */
import { jsx } from "@udecode/plate-test-utils";
import "./style.less";
jsx;

export const isMarkdownTableData = (str: string) => {
  // 按行拆分字符串
  const lines = str.trim().split("\n");

  // 检查行数是否足够
  if (lines?.length < 3) {
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
  if (!lines[1].trim().includes("-")) {
    return false;
  }

  return true;
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

  for (let i = 2; i < rows.length; i++) {
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
        colSizes={new Array(headers.length).fill("100%")}
        marginLeft={0}
        border={true}
      >
        <htr>
          {headers.map((key, index) => {
            return <hth key={index}>{key || " "}</hth>;
          })}
        </htr>
        {jsonData.map((row, rowIndex) => (
          <htr key={rowIndex}>
            {Object.values(row).map((value, colIndex) => {
              return <htd key={colIndex}>{value || " "}</htd>;
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
