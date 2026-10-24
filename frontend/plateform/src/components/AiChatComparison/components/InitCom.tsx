import { useEditorState } from '@udecode/plate/react';
import { useEffect } from 'react';
import { insertInfo } from './editor/editorUtils';

export const InitCom = ({ data }) => {
  const editor = useEditorState();
  useEffect(() => {
    insertInfo(data, editor);
  }, [data]);
  return null;
};
