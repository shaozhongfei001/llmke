import { uniqBy } from "lodash";

interface OriginOpt {
  companyName: string;
  tableName: string;
  year: string;
  periodType: string;
  categoryId: number;
  companyFullName?: string;
}

export interface ResOpt {
  label: string;
  value: string;
  companyName: string;
  tableName: string;
  year: string;
  periodType: string;
  categoryId: number;
  companyFullName?: string;
}
export interface ResMap {
  tables: ResOpt[];
  companys: ResOpt[];
  timeRange: ResOpt[];
}

export const handleSelectOpts = (opts: OriginOpt[]): ResMap => {
  let tables: ResOpt[] = [];
  let companys: ResOpt[] = [];
  let timeRange: ResOpt[] = [];

  opts.forEach((item: OriginOpt) => {
    tables.push({
      ...item,
      label: item.tableName,
      value: String(item.categoryId)
    });
    companys.push({
      ...item,
      label: item.companyFullName || item.companyName,
      value: item.companyName
    });
    timeRange.push({
      ...item,
      label: item.year + item.periodType,
      value: item.year + "@" + item.periodType
    });
  });

  return {
    tables: uniqBy(tables, "value"),
    companys: companys,
    timeRange: timeRange
  };
};

export type SelectType = "tables" | "companys" | "timeRange";
export const filterOptions = (
  { table, company }: { table: string; company?: string },
  originOpt: ResOpt[]
): ResOpt[] => {
  if (!originOpt.length) return [];
  if (!company)
    return uniqBy(
      originOpt.filter((i) => String(i.categoryId) == table),
      "value"
    );
  return originOpt.filter(
    (i) => String(i.categoryId) == table && i.companyName == company
  );
};

/**
 * 将数字或数字字符串格式化为带千分位逗号的字符串
 * @param value 数字或字符串
 * @returns 带千分位的字符串
 */
export function formatThousandComma(value: number | string): string {
  if (!value) return "";
  const str = String(value).replace(/,/g, "");
  if (isNaN(Number(str))) return String(value);
  const [intPart, decPart] = str.split(".");
  const intWithComma = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return decPart !== undefined ? `${intWithComma}.${decPart}` : intWithComma;
}
