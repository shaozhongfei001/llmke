import { genInfoInsertTemp } from "./utils";

// 分段写作render函数
export const renderParagraph = ({
  allParagraph,
  setEditorManager,
  globelPlateData,
  mainEditor,
  cover
}: {
  allParagraph: any;
  setEditorManager: any;
  globelPlateData: any;
  mainEditor: any;
  cover?: any[];
}) => {
  // 处理所有数据，并渲染文章
  const data = genInfoInsertTemp(
    globelPlateData,
    allParagraph,
    mainEditor.current
  );
  setEditorManager((p: any) => ({
    ...p,
    parsed_data: [...(cover || []), ...data]
  }));
};
