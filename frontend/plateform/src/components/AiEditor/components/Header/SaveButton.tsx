import { useEditorState } from "@udecode/plate-common/react";
import { Button } from "antd";
import { unified } from "unified";
import markdown from "remark-parse";
import { serializeMd } from "@udecode/plate-serializer-md";
import { serializeHtml } from "@udecode/plate-serializer-html";
// import Html2canvas from 'html2canvas';
// import jsPDF from 'jspdf';
const SaveButton = () => {
  const editor = useEditorState();
  const toSave = () => {
    const htmlContent: any = document.querySelector('div[role="textbox"]');
    if (!htmlContent) return;
    const convertToMarkdown = () => {
      if (!editor) return;
      const editorContent = editor.children;

      return serializeHtml(editor, { nodes: editor.children });
    };
    const md = convertToMarkdown();
  };
  return (
    <Button type="default" size="small" onClick={toSave}>
      保存
    </Button>
  );
};

export default SaveButton;
