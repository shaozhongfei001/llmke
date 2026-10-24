import { getMarks, toggleMark } from '@udecode/plate';
import { useEditorState } from '@udecode/plate-common/react';
import { Button, Tooltip } from 'antd';
const MarkButton = ({ format, icon, title }) => {
  const editor = useEditorState();
  const { selection } = editor;
  const isMarkActive = () => {
    if (!editor) return false;
    const marks = getMarks(editor);
    // eslint-disable-next-line no-prototype-builtins
    if (marks?.hasOwnProperty(format)) {
      return !!marks[format];
    }
    return false;
  };

  return (
    // <Tooltip placement="bottom" arrow title={title}>
      <Button
        size="small"
        style={{ border: 0, background: 'transparent', boxShadow: 'none' }}
        type={isMarkActive() ? 'link' : 'text'} // Changes the button style based on whether the mark is active
        icon={icon}
        onClick={(event) => {
          event.preventDefault();
          if (editor) {
            toggleMark(editor, { key: format });
          }
        }}
      />

  );
};

export default MarkButton;
