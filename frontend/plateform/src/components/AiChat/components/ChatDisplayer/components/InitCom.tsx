import { useEditorState } from "@udecode/plate/react";
import { useEffect } from "react";
import { insertInfo } from "./editorUtils";

export const InitCom = ({ data }: any) => {
  const editor = useEditorState();
  useEffect(() => {
    insertInfo(data, editor);
  }, [data]);
  return null;
};
