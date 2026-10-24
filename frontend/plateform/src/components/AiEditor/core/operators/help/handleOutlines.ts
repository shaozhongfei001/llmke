// 判断当前大纲下是否有内容，用于灰色显示
const hasContent = (node: any): boolean => {
  return node.some((item: any) => {
    return (
      item.contentOperation === "1" ||
      (item?.section && item.section.content) ||
      (item?.subParagraphs ? hasContent(item.subParagraphs) : false)
    );
  });
};

// 将大纲处理成为编辑器想要的数据结构
export const handleOutlines = (outlines?: any[]): any => {
  if (!outlines || !outlines.length)
    return { reqArr: [], hasDependency: {}, plateData: [], chartReqArr: [] };
  // 需要请求的段落
  const reqArr: any[] = [];
  // 拥有依赖的段落
  const hasDependency: any = {};
  // 需要单独请求的图表
  const chartReqArr: any[] = [];
  const handleRecursion = (outlines?: any[], level = 2): any => {
    if (!outlines || !outlines.length) return [];
    return outlines.map((item) => {
      // NEEDTOGENERATE代表需要调用接口生成内容
      const className = item.sectionId
        ? `sectionId-${item.sectionId} content-h${level}`
        : `content-h${level}`;

      // 没有内容且不生成的大纲灰色
      const headClassName = hasContent([item]) ? "" : "no-content";

      // 需要请求的段落
      if (
        (!item.subParagraphs || !item.subParagraphs.length) &&
        item?.contentOperation !== "0" &&
        item.sectionId &&
        (!item.extraInfo || !item.extraInfo.isChartSection)
      ) {
        reqArr.push({
          sectionId: String(item?.sectionId),
          title: item?.title
        });
        if (item.dependency && item.dependency[0]) {
          hasDependency[String(item.sectionId)] = item.dependency[0].refIds;
        }
      }

      // 需要请求图表(例如：股权结构图)的段落
      if (
        item?.contentOperation !== "0" &&
        item.extraInfo &&
        item.extraInfo.isChartSection
      ) {
        chartReqArr.push({
          sectionId: item?.sectionId,
          title: item?.title
        });
      }
      // 返回slate数据结构
      return {
        type: "div",
        id: item.sectionId,
        class: className,
        children: [
          {
            type: `h${level}`,
            id: item.id,
            class: `${headClassName}`,
            children: [
              {
                text: item.title
              }
            ]
          },
          ...handleRecursion(item?.subParagraphs, level + 1)
        ]
      };
    });
  };
  const plateData = handleRecursion(outlines, 2);

  return { reqArr, plateData, chartReqArr, hasDependency };
};
