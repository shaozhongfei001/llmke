// 将表单值key插入格式模板中
export const insertFormDataToTemp = (
  allValues: any,
  newHtmlString: string,
  titleObj: any
) => {
  for (const key in allValues) {
    if (allValues[key]) {
      newHtmlString = newHtmlString.replace(
        new RegExp(`{${titleObj[key]}}`, "g"),
        allValues[key]
      );
    }
  }
  return newHtmlString;
};
