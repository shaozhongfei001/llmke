import { usePromptDsigner } from "@/components/Template";
import { useAppPassport } from "@root/src/core/helps";

const useAddTemplate = (
  name: string,
  sceneClass: any,
  sceneKey: string,
  sceneClassTag: string,
  isSegment: boolean,
  sensitiveWords: any[],
  isVersion?: boolean
) => {
  const { getToken } = useAppPassport();
  const token: any = getToken();
  const {
    WidgetElement,
    getPromptTemplate,
    getContentRule,
    selectTag,
    articleTypeKey,
    formSchema,
    setPrompt,
    setConentRule,
    clearPrompt,
    setTableList,
    setSupportMaterials,
    supportMaterials,
    supportOutlines,
    setSupportOutlines,
    traceToMaterial,
    setTraceToMaterial,
    checkedData,
    close
  } = usePromptDsigner({
    layoutProps: { vertical: true },
    token: token,
    name: name,
    sceneClass,
    sceneKey,
    sceneClassTag,
    isSegment,
    isVersion,
    sensitiveWords
  });

  return {
    WidgetElement,
    getPromptTemplate,
    formSchema,
    selectTag,
    articleTypeKey,
    setPrompt,
    setTableList,
    clearPrompt,
    setSupportMaterials,
    supportMaterials,
    supportOutlines,
    setSupportOutlines,
    getContentRule,
    setConentRule,
    traceToMaterial,
    setTraceToMaterial,
    checkedData,
    close
  };
};

export default useAddTemplate;
